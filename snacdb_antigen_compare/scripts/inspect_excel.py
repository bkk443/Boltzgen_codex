#!/usr/bin/env python3
import csv
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

NS_MAIN = {'a': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
NS_REL = {'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}

NORMALIZED_HEADERS = [
    'source_sheet','source_row','target_name','target_symbol','protein_name','gene_symbol',
    'uniprot_accession','pdb_id_hint','organism','aliases','notes','structure_hint',
    'status','unresolved_reason'
]


def slug(text: str) -> str:
    text = (text or '').strip().lower()
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text.strip('_')


def parse_xlsx(path: Path):
    with zipfile.ZipFile(path) as zf:
        shared = []
        if 'xl/sharedStrings.xml' in zf.namelist():
            root = ET.fromstring(zf.read('xl/sharedStrings.xml'))
            for si in root.findall('a:si', NS_MAIN):
                shared.append(''.join(t.text or '' for t in si.iter('{%s}t' % NS_MAIN['a'])))

        wb = ET.fromstring(zf.read('xl/workbook.xml'))
        rels = ET.fromstring(zf.read('xl/_rels/workbook.xml.rels'))
        rel_map = {rel.attrib['Id']: rel.attrib['Target'] for rel in rels}
        sheets = []
        for sheet in wb.find('a:sheets', NS_MAIN):
            name = sheet.attrib['name']
            rid = sheet.attrib['{%s}id' % NS_REL['r']]
            target = 'xl/' + rel_map[rid].lstrip('/')
            root = ET.fromstring(zf.read(target))
            rows = []
            max_col = 0
            for row in root.findall('.//a:sheetData/a:row', NS_MAIN):
                record = {}
                for cell in row.findall('a:c', NS_MAIN):
                    ref = cell.attrib.get('r', '')
                    col_letters = re.sub(r'\d+', '', ref) or 'A'
                    col_idx = col_to_index(col_letters)
                    max_col = max(max_col, col_idx)
                    value = ''
                    cell_type = cell.attrib.get('t')
                    if cell_type == 'inlineStr':
                        value = ''.join(t.text or '' for t in cell.iter('{%s}t' % NS_MAIN['a']))
                    else:
                        v = cell.find('a:v', NS_MAIN)
                        if v is not None and v.text is not None:
                            value = v.text
                            if cell_type == 's':
                                value = shared[int(value)]
                    record[col_idx] = value
                if record:
                    rows.append([record.get(i, '') for i in range(1, max_col + 1)])
            sheets.append((name, rows))
        return sheets


def col_to_index(letters: str) -> int:
    value = 0
    for ch in letters:
        value = value * 26 + (ord(ch.upper()) - 64)
    return value


def detect_header(rows):
    best = (0, -1)
    for idx, row in enumerate(rows[:10]):
        nonempty = sum(1 for cell in row if str(cell).strip())
        alpha = sum(1 for cell in row if re.search(r'[A-Za-z]', str(cell) or ''))
        score = nonempty + alpha
        if score > best[1]:
            best = (idx, score)
    return best[0]


def infer_roles(headers):
    rules = {
        'gene_symbol': [r'gene', r'symbol', r'^target$'],
        'protein_name': [r'protein', r'antigen', r'target name', r'name'],
        'uniprot_accession': [r'uniprot', r'accession'],
        'pdb_id_hint': [r'\bpdb\b', r'structure'],
        'organism': [r'organism', r'species', r'taxon'],
        'notes': [r'note', r'comment', r'remark'],
        'aliases': [r'alias', r'synonym'],
        'structure_hint': [r'hint', r'structure', r'model'],
    }
    roles = {}
    for idx, header in enumerate(headers):
        normalized = slug(header)
        for role, patterns in rules.items():
            if role in roles:
                continue
            if any(re.search(p, normalized.replace('_', ' ')) for p in patterns):
                roles[role] = idx
    return roles


def clean(v):
    return re.sub(r'\s+', ' ', str(v or '')).strip()


def first_nonempty(*values):
    for value in values:
        if clean(value):
            return clean(value)
    return ''


def extract_pdbs(text):
    return '; '.join(dict.fromkeys(re.findall(r'\b[0-9][A-Za-z0-9]{3}\b', text or '', flags=re.I)))


def main():
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('INPUT_ANTIGENS.xlsx')
    out_root = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('snacdb_antigen_compare')
    manifest_dir = out_root / '01_manifest'
    manifest_dir.mkdir(parents=True, exist_ok=True)
    normalized_csv = manifest_dir / 'antigen_manifest_normalized.csv'
    unresolved_csv = manifest_dir / 'antigen_manifest_unresolved.csv'
    schema_md = manifest_dir / 'excel_schema_summary.md'

    unresolved_rows = []
    normalized_rows = []
    summary_lines = ['# Excel schema summary', '']
    if not input_path.exists():
        summary_lines += [
            f'- Workbook path expected: `{input_path}`.',
            '- Result: file not found during the agent run.',
            '- Consequence: no antigen rows could be inspected or normalized.',
            '- Action taken: created empty normalized outputs plus an unresolved manifest entry so reruns fail loudly rather than silently.',
        ]
        unresolved_rows.append({
            'source_sheet': '', 'source_row': '', 'target_name': '', 'target_symbol': '', 'protein_name': '',
            'gene_symbol': '', 'uniprot_accession': '', 'pdb_id_hint': '', 'organism': '', 'aliases': '',
            'notes': f'Missing workbook: {input_path}', 'structure_hint': '', 'status': 'unresolved',
            'unresolved_reason': 'input_workbook_not_found'
        })
    else:
        sheets = parse_xlsx(input_path)
        summary_lines.append(f'- Workbook path: `{input_path}`.')
        summary_lines.append(f'- Sheet count: {len(sheets)}.')
        summary_lines.append('')
        for sheet_name, rows in sheets:
            if not rows:
                summary_lines += [f'## Sheet `{sheet_name}`', '', '- Sheet was empty.', '']
                continue
            header_idx = detect_header(rows)
            headers = [clean(v) or f'column_{i+1}' for i, v in enumerate(rows[header_idx])]
            roles = infer_roles(headers)
            summary_lines += [f'## Sheet `{sheet_name}`', '']
            summary_lines.append(f'- Row count (including header-like rows): {len(rows)}.')
            summary_lines.append(f'- Detected header row index (1-based): {header_idx + 1}.')
            summary_lines.append('- Columns:')
            for i, h in enumerate(headers, start=1):
                assigned = [role for role, idx in roles.items() if idx == i - 1]
                suffix = f" → {assigned[0]}" if assigned else ''
                summary_lines.append(f'  - {i}. `{h}`{suffix}')
            summary_lines.append('')
            data_rows = rows[header_idx + 1:]
            for offset, row in enumerate(data_rows, start=header_idx + 2):
                padded = row + [''] * (len(headers) - len(row))
                rec = {headers[i]: clean(padded[i]) for i in range(len(headers))}
                gene = rec.get(headers[roles['gene_symbol']], '') if 'gene_symbol' in roles else ''
                protein = rec.get(headers[roles['protein_name']], '') if 'protein_name' in roles else ''
                uniprot = rec.get(headers[roles['uniprot_accession']], '') if 'uniprot_accession' in roles else ''
                organism = rec.get(headers[roles['organism']], '') if 'organism' in roles else ''
                aliases = rec.get(headers[roles['aliases']], '') if 'aliases' in roles else ''
                notes = rec.get(headers[roles['notes']], '') if 'notes' in roles else ''
                structure_hint = rec.get(headers[roles['structure_hint']], '') if 'structure_hint' in roles else ''
                pdb_id_hint = rec.get(headers[roles['pdb_id_hint']], '') if 'pdb_id_hint' in roles else ''
                merged_struct = '; '.join([x for x in [pdb_id_hint, structure_hint] if x])
                normalized = {
                    'source_sheet': sheet_name,
                    'source_row': offset,
                    'target_name': first_nonempty(protein, gene, uniprot),
                    'target_symbol': gene or '',
                    'protein_name': protein,
                    'gene_symbol': gene,
                    'uniprot_accession': uniprot,
                    'pdb_id_hint': extract_pdbs(merged_struct),
                    'organism': organism,
                    'aliases': aliases,
                    'notes': notes,
                    'structure_hint': structure_hint,
                    'status': 'resolved_for_structure_selection',
                    'unresolved_reason': '',
                }
                if not normalized['target_name']:
                    normalized['status'] = 'unresolved'
                    normalized['unresolved_reason'] = 'missing_target_identifier'
                    unresolved_rows.append(normalized)
                else:
                    normalized_rows.append(normalized)

        counts = Counter(r['status'] for r in normalized_rows + unresolved_rows)
        summary_lines += ['## Normalization summary', '']
        for key in sorted(counts):
            summary_lines.append(f'- `{key}`: {counts[key]} rows.')

    with normalized_csv.open('w', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=NORMALIZED_HEADERS)
        writer.writeheader()
        writer.writerows(normalized_rows)
    with unresolved_csv.open('w', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=NORMALIZED_HEADERS)
        writer.writeheader()
        writer.writerows(unresolved_rows)
    schema_md.write_text('\n'.join(summary_lines) + '\n')
    print(f'Wrote {normalized_csv}')
    print(f'Wrote {unresolved_csv}')
    print(f'Wrote {schema_md}')


if __name__ == '__main__':
    main()
