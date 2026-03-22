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


def value_ratio(values, predicate):
    usable = [clean(v) for v in values if clean(v)]
    if not usable:
        return 0.0
    return sum(1 for v in usable if predicate(v)) / len(usable)


def is_uniprot_accession(value):
    return bool(re.fullmatch(r'(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})', value))


def is_gene_symbol_like(value):
    return bool(re.fullmatch(r'[A-Z0-9][A-Z0-9-]{1,14}', value)) and not value.isdigit()


def looks_numeric(value):
    return bool(re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)', value))


def looks_textual_name(value):
    return any(ch.isalpha() for ch in value) and (' ' in value or value[0].isupper()) and not looks_numeric(value)


def is_valid_pdb_code(value):
    value = (value or '').strip()
    return len(value) == 4 and value[0].isdigit() and any(ch.isalpha() for ch in value[1:]) and value.isalnum()


def infer_roles(headers, sample_rows):
    column_values = list(zip(*sample_rows)) if sample_rows else [tuple() for _ in headers]
    header_rules = {
        'gene_symbol': [r'gene symbol', r'hgnc', r'gene', r'symbol', r'^target$'],
        'protein_name': [r'protein', r'gene description', r'description', r'pref name', r'full name', r'antigen', r'target name'],
        'uniprot_accession': [r'uniprot', r'accession'],
        'pdb_id_hint': [r'\bpdb\b', r'structure'],
        'organism': [r'organism', r'species', r'taxon'],
        'notes': [r'note', r'comment', r'remark'],
        'aliases': [r'alias', r'synonym'],
        'structure_hint': [r'hint', r'model'],
    }
    roles = {}
    for role in header_rules:
        best_idx, best_score = None, 0.0
        for idx, header in enumerate(headers):
            if idx in roles.values():
                continue
            normalized = slug(header).replace('_', ' ')
            values = column_values[idx] if idx < len(column_values) else []
            score = 0.0
            for pattern in header_rules[role]:
                if re.search(pattern, normalized):
                    score += 4.0 if pattern in {'gene symbol', 'gene description', 'pref name', 'full name'} else 2.5
            if role == 'uniprot_accession':
                score += 8.0 * value_ratio(values, is_uniprot_accession)
            elif role == 'gene_symbol':
                score += 5.0 * value_ratio(values, is_gene_symbol_like)
            elif role == 'protein_name':
                score += 4.0 * value_ratio(values, looks_textual_name)
                score -= 6.0 * value_ratio(values, looks_numeric)
            elif role == 'pdb_id_hint':
                score += 5.0 * value_ratio(values, lambda v: any(is_valid_pdb_code(code.upper()) for code in re.findall(r'\b[0-9][A-Za-z0-9]{3}\b', v, flags=re.I)))
            if score > best_score:
                best_idx, best_score = idx, score
        if best_idx is not None and best_score >= 2.5:
            roles[role] = best_idx
    return roles


def clean(v):
    return re.sub(r'\s+', ' ', str(v or '')).strip()


def first_nonempty(*values):
    for value in values:
        if clean(value):
            return clean(value)
    return ''


def extract_pdbs(text):
    return '; '.join(dict.fromkeys(code for code in re.findall(r'\b[0-9][A-Za-z0-9]{3}\b', text or '', flags=re.I) if is_valid_pdb_code(code.upper())))



def looks_like_headerless_target_sheet(rows):
    if not rows:
        return False
    first = rows[0] + [''] * (31 - len(rows[0]))
    return (
        bool(re.fullmatch(r'Y[A-Z]{2}\d{3}[CW]', clean(first[0]) or ''))
        and bool(re.fullmatch(r'ENSP\d+', clean(first[1]) or ''))
        and clean(first[3]).isupper()
        and any(is_valid_pdb_code(code.upper()) for code in re.findall(r'\b[0-9][A-Za-z0-9]{3}\b', clean(first[25]), flags=re.I))
    )


def normalize_headerless_target_sheet(sheet_name, rows):
    normalized_rows = []
    unresolved_rows = []
    for offset, row in enumerate(rows, start=1):
        padded = row + [''] * (31 - len(row))
        normalized = {
            'source_sheet': sheet_name,
            'source_row': offset,
            'target_name': first_nonempty(padded[4], padded[3], padded[1]),
            'target_symbol': clean(padded[3]),
            'protein_name': clean(padded[4]),
            'gene_symbol': clean(padded[3]),
            'uniprot_accession': '',
            'pdb_id_hint': extract_pdbs(clean(padded[25])),
            'organism': 'Homo sapiens',
            'aliases': '; '.join(v for v in [clean(padded[0]), clean(padded[1]), clean(padded[14])] if v),
            'notes': '; '.join(v for v in [clean(padded[21]), clean(padded[24]), clean(padded[27]), clean(padded[28])] if v),
            'structure_hint': clean(padded[25]),
            'status': 'resolved_for_structure_selection',
            'unresolved_reason': '',
        }
        if not normalized['target_name']:
            normalized['status'] = 'unresolved'
            normalized['unresolved_reason'] = 'missing_target_identifier'
            unresolved_rows.append(normalized)
        else:
            normalized_rows.append(normalized)
    return normalized_rows, unresolved_rows

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
        candidate_files = sorted(str(p) for p in input_path.parent.glob('*.xlsx'))
        summary_lines += [
            f'- Workbook path expected: `{input_path}`.',
            '- Result: file not found during the agent run.',
            '- Consequence: no antigen rows could be inspected or normalized.',
            '- Action taken: created empty normalized outputs plus an unresolved manifest entry so reruns fail loudly rather than silently.',
        ]
        if candidate_files:
            summary_lines.append('- Other `.xlsx` files found in the same directory:')
            for candidate in candidate_files:
                summary_lines.append(f'  - `{candidate}`')
        else:
            summary_lines.append('- No alternative `.xlsx` files were found in the same directory.')
        unresolved_rows.append({
            'source_sheet': '', 'source_row': '', 'target_name': '', 'target_symbol': '', 'protein_name': '',
            'gene_symbol': '', 'uniprot_accession': '', 'pdb_id_hint': '', 'organism': '', 'aliases': '',
            'notes': f'Missing workbook: {input_path}; candidates={candidate_files}', 'structure_hint': '', 'status': 'unresolved',
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
            summary_lines += [f'## Sheet `{sheet_name}`', '']
            summary_lines.append(f'- Row count (including header-like rows): {len(rows)}.')
            if looks_like_headerless_target_sheet(rows):
                summary_lines.append('- Detected layout: headerless target sheet with fixed columns (yeast ORF / ENSP / Entrez / symbol / description / ... / PDB list).')
                summary_lines.append('- Key fixed columns used: A=yeast ORF, B=ENSP, D=gene symbol, E=protein description, O=Ensembl gene ID, Z=PDB hints, Y=localization, AB/AC=free-text notes/flags.')
                summary_lines.append('')
                add_norm, add_unres = normalize_headerless_target_sheet(sheet_name, rows)
                normalized_rows.extend(add_norm)
                unresolved_rows.extend(add_unres)
                continue
            header_idx = detect_header(rows)
            headers = [clean(v) or f'column_{i+1}' for i, v in enumerate(rows[header_idx])]
            sample_rows = [r + [''] * (len(headers) - len(r)) for r in rows[header_idx + 1: header_idx + 21]]
            roles = infer_roles(headers, sample_rows)
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
