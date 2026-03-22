#!/usr/bin/env python3
import csv
import sys
from collections import defaultdict
from pathlib import Path

ALL_HEADERS = ['target','chosen_query_structure','best_hit','best_hit_antigen_name','best_hit_structure_identifier','tm_score','rank','notes']


def load_query_manifest(path):
    by_structure = {}
    if not path.exists():
        return by_structure
    with path.open() as fh:
        for row in csv.DictReader(fh):
            by_structure[row.get('query_filename', '').rsplit('.', 1)[0]] = row
    return by_structure


def parse_report(report_path, query_lookup):
    rows = []
    if not report_path.exists():
        return rows
    with report_path.open() as fh:
        for line in fh:
            parts = line.strip().split()
            if len(parts) < 6 or 'checkpoint' in line:
                continue
            query_id, hit_id = parts[0], parts[1]
            tm_score = max(float(parts[4]), float(parts[5]))
            qmeta = query_lookup.get(query_id, {})
            rows.append({
                'target': qmeta.get('target_name', query_id),
                'chosen_query_structure': qmeta.get('chosen_structure_id', query_id),
                'query_id': query_id,
                'best_hit': hit_id,
                'best_hit_antigen_name': '',
                'best_hit_structure_identifier': hit_id,
                'tm_score': tm_score,
                'rank': '',
                'notes': 'Parsed from SNAC-DB Foldseek report.',
            })
    rows.sort(key=lambda r: (r['target'], -r['tm_score'], r['best_hit']))
    per_target_rank = defaultdict(int)
    for row in rows:
        per_target_rank[row['target']] += 1
        row['rank'] = per_target_rank[row['target']]
    return rows


def write_csv(path, headers, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def main():
    out_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('snacdb_antigen_compare')
    query_manifest = out_root / '02_queries/query_structure_manifest.csv'
    raw_report = out_root / '03_raw_results/foldseek_report.tsv'
    unresolved_manifest = out_root / '01_manifest/antigen_manifest_unresolved.csv'
    results_dir = out_root / '04_results'
    query_lookup = load_query_manifest(query_manifest)
    all_rows = parse_report(raw_report, query_lookup)
    best_rows = []
    top5_rows = []
    seen = set()
    for row in all_rows:
        if row['target'] not in seen:
            best_rows.append(row)
            seen.add(row['target'])
        if row['rank'] <= 5:
            top5_rows.append(row)
    unresolved_rows = []
    if unresolved_manifest.exists():
        with unresolved_manifest.open() as fh:
            for row in csv.DictReader(fh):
                unresolved_rows.append({'target': row.get('target_name', ''), 'reason': row.get('unresolved_reason', ''), 'notes': row.get('notes', '')})
    if not raw_report.exists():
        unresolved_rows.append({'target': '', 'reason': 'snacdb_raw_report_missing', 'notes': f'Expected raw report at {raw_report}'})
    write_csv(results_dir / 'snacdb_antigen_hits_all.csv', ['target','chosen_query_structure','query_id','best_hit','best_hit_antigen_name','best_hit_structure_identifier','tm_score','rank','notes'], all_rows)
    write_csv(results_dir / 'snacdb_antigen_best_hits.csv', ALL_HEADERS, best_rows)
    write_csv(results_dir / 'snacdb_antigen_top5_hits.csv', ALL_HEADERS, top5_rows)
    write_csv(results_dir / 'unresolved_or_failed_targets.csv', ['target','reason','notes'], unresolved_rows)
    print(f'Wrote outputs in {results_dir}')


if __name__ == '__main__':
    main()
