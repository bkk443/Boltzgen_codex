#!/usr/bin/env python3
import csv
import shutil
import sys
from pathlib import Path


def load_rows(path: Path):
    if not path.exists():
        return []
    with path.open() as fh:
        return list(csv.DictReader(fh))


def main():
    out_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('snacdb_antigen_compare')
    pr_dir = out_root / 'pr_results'
    pr_dir.mkdir(parents=True, exist_ok=True)

    best_hits = out_root / '04_results/snacdb_antigen_best_hits.csv'
    top5_hits = out_root / '04_results/snacdb_antigen_top5_hits.csv'
    unresolved = out_root / '04_results/unresolved_or_failed_targets.csv'
    runtime_summary = out_root / '05_report/summary.md'

    if best_hits.exists():
        shutil.copyfile(best_hits, pr_dir / 'snacdb_antigen_best_hits_pr_snapshot.csv')
    if top5_hits.exists():
        shutil.copyfile(top5_hits, pr_dir / 'snacdb_antigen_top5_hits_pr_snapshot.csv')
    if unresolved.exists():
        shutil.copyfile(unresolved, pr_dir / 'unresolved_or_failed_targets_pr_snapshot.csv')
    if runtime_summary.exists():
        shutil.copyfile(runtime_summary, pr_dir / 'runtime_summary_pr_snapshot.md')

    best_rows = load_rows(best_hits)
    unresolved_rows = load_rows(unresolved)
    best_sorted = sorted(best_rows, key=lambda row: float(row['tm_score']), reverse=True)

    lines = [
        '# PR-visible SNAC-DB antigen comparison snapshot',
        '',
        'This directory intentionally contains a committed text snapshot of the latest generated comparison outputs so the PR shows real results.',
        '',
        '## Snapshot contents',
        '',
        '- `snacdb_antigen_best_hits_pr_snapshot.csv`: one best SNAC-DB structural neighbor per target.',
        '- `snacdb_antigen_top5_hits_pr_snapshot.csv`: top 5 SNAC-DB neighbors per target.',
        '- `unresolved_or_failed_targets_pr_snapshot.csv`: unresolved or failed targets at postprocessing time.',
        '- `runtime_summary_pr_snapshot.md`: copy of the generated Markdown summary.',
        '',
        '## Snapshot summary',
        '',
        f'- Targets with best-hit rows: {len(best_rows)}.',
        f'- Unresolved or failed targets: {len(unresolved_rows)}.',
        '',
        '## Strongest best-hit rows in this snapshot',
        '',
    ]

    if best_sorted:
        for row in best_sorted[:10]:
            lines.append(
                f"- **{row['target']}** → `{row['best_hit']}` (`TM-score={row['tm_score']}`, query `{row['chosen_query_structure']}`)"
            )
    else:
        lines.append('- No best-hit rows were available when this snapshot was created.')

    (pr_dir / 'README.md').write_text('\n'.join(lines) + '\n')
    print(f'Wrote PR snapshot files to {pr_dir}')


if __name__ == '__main__':
    main()
