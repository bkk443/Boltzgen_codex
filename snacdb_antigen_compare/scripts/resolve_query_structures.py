#!/usr/bin/env python3
import csv
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

QUERY_HEADERS = [
    'target_name','normalized_target_symbol','chosen_structure_id','source_database','structure_class',
    'chain','coverage_notes','selection_rationale','query_filename','status','failure_reason'
]


def http_json(url, method='GET', payload=None):
    data = None
    headers = {'User-Agent': 'snacdb-antigen-compare/1.0'}
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode('utf-8'))


def pdb_candidates(text):
    return list(dict.fromkeys(code.upper() for code in re.findall(r'\b[0-9][A-Za-z0-9]{3}\b', text or '', flags=re.I)))


def rcsb_entry(entry_id):
    return http_json(f'https://data.rcsb.org/rest/v1/core/entry/{entry_id}')


def experimental_method(entry_json):
    methods = [m.get('method', '') for m in entry_json.get('exptl', [])]
    joined = '; '.join(m for m in methods if m)
    return joined, bool(methods)


def rcsb_search_by_uniprot(uniprot):
    payload = {
        'query': {
            'type': 'terminal',
            'service': 'text',
            'parameters': {
                'attribute': 'rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_accession',
                'operator': 'exact_match',
                'value': uniprot,
            },
        },
        'return_type': 'entry',
        'request_options': {'pager': {'start': 0, 'rows': 20}},
    }
    res = http_json('https://search.rcsb.org/rcsbsearch/v2/query', method='POST', payload=payload)
    return [item['identifier'] for item in res.get('result_set', [])]


def select_structure(row):
    hints = pdb_candidates(' ; '.join([row.get('pdb_id_hint', ''), row.get('structure_hint', ''), row.get('notes', '')]))
    checked = []
    for pdb_id in hints:
        try:
            entry = rcsb_entry(pdb_id)
            methods, is_experimental = experimental_method(entry)
            checked.append((pdb_id, methods or 'unknown'))
            if is_experimental:
                return {
                    'chosen_structure_id': pdb_id,
                    'source_database': 'RCSB PDB',
                    'structure_class': 'experimental',
                    'chain': '',
                    'coverage_notes': f'Whole entry used; experimental method: {methods}.',
                    'selection_rationale': 'User-provided spreadsheet/prompt PDB hint selected because it resolves to an experimental PDB entry.',
                }
        except Exception as exc:
            checked.append((pdb_id, f'lookup_failed:{exc}'))
    accession = row.get('uniprot_accession', '').strip()
    if accession:
        try:
            for pdb_id in rcsb_search_by_uniprot(accession):
                entry = rcsb_entry(pdb_id)
                methods, is_experimental = experimental_method(entry)
                if is_experimental:
                    return {
                        'chosen_structure_id': pdb_id,
                        'source_database': 'RCSB PDB',
                        'structure_class': 'experimental',
                        'chain': '',
                        'coverage_notes': f'Whole entry used; matched by UniProt accession {accession}; method: {methods}.',
                        'selection_rationale': 'Selected the first experimental RCSB entry returned by an exact UniProt accession search. Review chain/domain coverage before production use.',
                    }
        except Exception as exc:
            checked.append((f'uniprot:{accession}', f'lookup_failed:{exc}'))
        return {
            'chosen_structure_id': f'AF-{accession}-F1-model_v4',
            'source_database': 'AlphaFold DB',
            'structure_class': 'predicted',
            'chain': 'A',
            'coverage_notes': 'Full-length AlphaFold fallback selected because no experimental structure was confidently resolved automatically.',
            'selection_rationale': 'Predicted-model fallback used only after experimental-structure resolution failed.',
        }
    details = '; '.join(f'{k}={v}' for k, v in checked) if checked else 'no viable PDB hints or UniProt accession provided'
    return None, details


def main():
    manifest = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('snacdb_antigen_compare/01_manifest/antigen_manifest_normalized.csv')
    out_csv = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('snacdb_antigen_compare/02_queries/query_structure_manifest.csv')
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    rows_out = []
    if not manifest.exists():
        pass
    else:
        with manifest.open() as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                symbol = row.get('target_symbol') or row.get('gene_symbol') or row.get('target_name')
                symbol = re.sub(r'[^A-Za-z0-9]+', '_', symbol or 'unknown').strip('_') or 'unknown'
                try:
                    selected = select_structure(row)
                    if isinstance(selected, tuple):
                        payload, reason = selected
                    else:
                        payload, reason = selected, ''
                    if payload:
                        rows_out.append({
                            'target_name': row.get('target_name', ''),
                            'normalized_target_symbol': symbol,
                            'chosen_structure_id': payload['chosen_structure_id'],
                            'source_database': payload['source_database'],
                            'structure_class': payload['structure_class'],
                            'chain': payload['chain'],
                            'coverage_notes': payload['coverage_notes'],
                            'selection_rationale': payload['selection_rationale'],
                            'query_filename': f"{symbol}__{payload['chosen_structure_id']}.cif",
                            'status': 'selected',
                            'failure_reason': '',
                        })
                    else:
                        rows_out.append({
                            'target_name': row.get('target_name', ''),
                            'normalized_target_symbol': symbol,
                            'chosen_structure_id': '', 'source_database': '', 'structure_class': '', 'chain': '',
                            'coverage_notes': '', 'selection_rationale': '', 'query_filename': '',
                            'status': 'unresolved', 'failure_reason': reason,
                        })
                except Exception as exc:
                    rows_out.append({
                        'target_name': row.get('target_name', ''),
                        'normalized_target_symbol': symbol,
                        'chosen_structure_id': '', 'source_database': '', 'structure_class': '', 'chain': '',
                        'coverage_notes': '', 'selection_rationale': '', 'query_filename': '',
                        'status': 'unresolved', 'failure_reason': f'structure_resolution_error:{exc}',
                    })
    with out_csv.open('w', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=QUERY_HEADERS)
        writer.writeheader()
        writer.writerows(rows_out)
    print(f'Wrote {out_csv}')


if __name__ == '__main__':
    main()
