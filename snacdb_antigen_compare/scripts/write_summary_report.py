#!/usr/bin/env python3
import csv
import sys
from pathlib import Path


def load_rows(path):
    if not path.exists():
        return []
    with path.open() as fh:
        return list(csv.DictReader(fh))


def main():
    out_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('snacdb_antigen_compare')
    input_workbook = sys.argv[2] if len(sys.argv) > 2 else './INPUT_ANTIGENS.xlsx'
    report = out_root / '05_report/summary.md'
    report.parent.mkdir(parents=True, exist_ok=True)
    query_rows = load_rows(out_root / '02_queries/query_structure_manifest.csv')
    best_rows = load_rows(out_root / '04_results/snacdb_antigen_best_hits.csv')
    unresolved_rows = load_rows(out_root / '04_results/unresolved_or_failed_targets.csv')
    protein_nodes = load_rows(out_root / '04_results/protein_space_nodes_mds.csv')
    source_txt = out_root / 'reference/REFERENCE_SOURCE.txt'
    lines = [
        '# SNAC-DB antigen comparison summary', '', '## Installed / configured workflow components', '',
        '- Environment spec: `env/environment.yml`.', '- Setup script: `scripts/setup_snacdb.sh`.', '- Execution scripts: `scripts/run_all.sh`, `scripts/run_antigen_hits.sh`.', '',
        '## Data sources used', '', f'- Query workbook path used for this run: `{input_workbook}`.', '- SNAC-DB curated dataset provenance recorded in `reference/REFERENCE_SOURCE.txt`.', '',
        '## Structure selection policy', '', '- Priority order: user-provided experimental PDB hints, alternative experimental PDBs, AlphaFold fallback only when experimental resolution fails.', '- Ambiguous or missing rows are carried into unresolved outputs rather than force-mapped.', '',
        '## Run summary', '', f'- Query structures selected: {sum(1 for r in query_rows if r.get("status") == "selected")}.', f'- Query structures unresolved during selection: {sum(1 for r in query_rows if r.get("status") != "selected")}.', f'- Targets with best-hit output rows: {len(best_rows)}.', f'- Unresolved or failed targets recorded: {len(unresolved_rows)}.', '',
        '## Primary structure-space outputs', ''
    ]
    if protein_nodes:
        query_count = sum(1 for row in protein_nodes if row.get('node_type') == 'query_target')
        ref_count = sum(1 for row in protein_nodes if row.get('node_type') == 'reference_antigen')
        lines.extend([
            f'- Structure maps written from all-vs-all structural similarities across {query_count} workbook proteins and {ref_count} SNAC-DB reference antigens.',
            '- MDS figure: `05_report/protein_space_map_mds.svg`.',
            '- UMAP figure: `05_report/protein_space_map_umap.svg`.',
            '- Backing matrix: `04_results/protein_space_similarity_matrix.csv`.',
            '- Backing coordinates: `04_results/protein_space_nodes_mds.csv` and `04_results/protein_space_nodes_umap.csv`.',
        ])
    else:
        lines.append('- No all-vs-all protein-space report was available in this run, so the structure maps were not generated.')
    lines += ['', '## Per-target nearest SNAC-DB antigen neighbors', '']
    if best_rows:
        for row in best_rows:
            lines.append(f"- **{row['target']}** → best hit `{row['best_hit']}` (`TM-score={row['tm_score']}`); notes: {row['notes']}")
    else:
        lines.append('- No SNAC-DB hit report was available in this run.')
    lines += ['', '## Caveats', '']
    for row in unresolved_rows[:50]:
        lines.append(f"- Target `{row.get('target', '') or 'N/A'}`: {row.get('reason', '')}. {row.get('notes', '')}")
    if source_txt.exists():
        lines += ['', '## Reference dataset provenance snapshot', '']
        lines += [f'- {line}' for line in source_txt.read_text().splitlines() if line.strip()]
    report.write_text('\n'.join(lines) + '\n')
    print(f'Wrote {report}')


if __name__ == '__main__':
    main()
