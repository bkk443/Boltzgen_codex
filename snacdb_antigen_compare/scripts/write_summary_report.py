#!/usr/bin/env python3
import csv
from pathlib import Path


def count_rows(path):
    if not path.exists():
        return 0
    with path.open() as fh:
        return max(sum(1 for _ in fh) - 1, 0)


def load_rows(path):
    if not path.exists():
        return []
    with path.open() as fh:
        return list(csv.DictReader(fh))


def main():
    out_root = Path('snacdb_antigen_compare')
    report = out_root / '05_report/summary.md'
    report.parent.mkdir(parents=True, exist_ok=True)
    query_rows = load_rows(out_root / '02_queries/query_structure_manifest.csv')
    best_rows = load_rows(out_root / '04_results/snacdb_antigen_best_hits.csv')
    unresolved_rows = load_rows(out_root / '04_results/unresolved_or_failed_targets.csv')
    source_txt = out_root / 'reference/REFERENCE_SOURCE.txt'
    lines = [
        '# SNAC-DB antigen comparison summary',
        '',
        '## Installed / configured workflow components',
        '',
        '- Environment spec: `env/environment.yml`.',
        '- Setup script: `scripts/setup_snacdb.sh`.',
        '- Execution scripts: `scripts/run_all.sh`, `scripts/run_antigen_hits.sh`.',
        '',
        '## Data sources used',
        '',
        '- Query workbook expected at `./INPUT_ANTIGENS.xlsx`.',
        '- SNAC-DB curated dataset provenance recorded in `reference/REFERENCE_SOURCE.txt`.',
        '',
        '## Structure selection policy',
        '',
        '- Priority order: user-provided experimental PDB hints, alternative experimental PDBs, AlphaFold fallback only when experimental resolution fails.',
        '- Ambiguous or missing rows are carried into unresolved outputs rather than force-mapped.',
        '',
        '## Run summary',
        '',
        f'- Query structures selected: {sum(1 for r in query_rows if r.get("status") == "selected")}.',
        f'- Query structures unresolved during selection: {sum(1 for r in query_rows if r.get("status") != "selected")}.',
        f'- Targets with best-hit output rows: {len(best_rows)}.',
        f'- Unresolved or failed targets recorded: {len(unresolved_rows)}.',
        '',
        '## Per-target nearest SNAC-DB antigen neighbors',
        '',
    ]
    if best_rows:
        for row in best_rows:
            lines.append(f"- **{row['target']}** → best hit `{row['best_hit']}` (`TM-score={row['tm_score']}`); notes: {row['notes']}")
    else:
        lines.append('- No SNAC-DB hit report was available in this agent run.')
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
