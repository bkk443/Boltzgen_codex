#!/usr/bin/env python3
import csv
import shutil
import sys
from html import escape
from pathlib import Path

import numpy as np


def load_rows(path: Path):
    if not path.exists():
        return []
    with path.open() as fh:
        return list(csv.DictReader(fh))


def write_embedding(top5_rows, pr_dir: Path):
    query_labels = sorted({row['target'] for row in top5_rows})
    hit_labels = sorted({row['best_hit'] for row in top5_rows})
    nodes = [('query', label) for label in query_labels] + [('hit', label) for label in hit_labels]
    node_index = {node: idx for idx, node in enumerate(nodes)}

    matrix = np.zeros((len(nodes), len(nodes)), dtype=float)
    best_weight = {node: 0.0 for node in nodes}
    for row in top5_rows:
        query_node = ('query', row['target'])
        hit_node = ('hit', row['best_hit'])
        weight = float(row['tm_score'])
        i = node_index[query_node]
        j = node_index[hit_node]
        matrix[i, j] = max(matrix[i, j], weight)
        matrix[j, i] = max(matrix[j, i], weight)
        best_weight[query_node] = max(best_weight[query_node], weight)
        best_weight[hit_node] = max(best_weight[hit_node], weight)

    centered = matrix - matrix.mean(axis=0, keepdims=True)
    u, s, _ = np.linalg.svd(centered, full_matrices=False)
    coords = u[:, :2] * s[:2]
    if coords.shape[1] < 2:
        coords = np.pad(coords, ((0, 0), (0, 2 - coords.shape[1])))

    min_x, max_x = coords[:, 0].min(), coords[:, 0].max()
    min_y, max_y = coords[:, 1].min(), coords[:, 1].max()
    width, height, margin = 1400, 1000, 80

    def scale(value, lo, hi, out_lo, out_hi):
        if hi == lo:
            return (out_lo + out_hi) / 2
        return out_lo + ((value - lo) / (hi - lo)) * (out_hi - out_lo)

    csv_path = pr_dir / 'top5_tm_embedding_nodes.csv'
    with csv_path.open('w', newline='') as fh:
        writer = csv.writer(fh)
        writer.writerow(['node_type', 'label', 'x', 'y', 'max_tm_score'])
        for (node_type, label), (x, y) in zip(nodes, coords):
            writer.writerow([node_type, label, f'{x:.6f}', f'{y:.6f}', f'{best_weight[(node_type, label)]:.5f}'])

    labeled_hits = sorted(
        ((best_weight[node], node[1]) for node in nodes if node[0] == 'hit'),
        reverse=True,
    )[:12]
    labeled_hit_names = {label for _, label in labeled_hits}

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<style>',
        'text { font-family: Arial, sans-serif; }',
        '.title { font-size: 24px; font-weight: bold; }',
        '.subtitle { font-size: 14px; fill: #444; }',
        '.query { fill: #d62728; }',
        '.hit { fill: #1f77b4; opacity: 0.7; }',
        '.query-label { font-size: 11px; fill: #111; }',
        '.hit-label { font-size: 10px; fill: #1f3b73; }',
        '</style>',
        f'<text class="title" x="{margin}" y="40">PCA-style embedding of query targets and top-5 SNAC-DB hits</text>',
        f'<text class="subtitle" x="{margin}" y="65">Built from the top-5 Foldseek TM-score relationship matrix exported for PR review.</text>',
        f'<rect x="{margin}" y="{margin}" width="{width - 2 * margin}" height="{height - 2 * margin}" fill="white" stroke="#ccc"/>',
    ]

    for (node_type, label), (x, y) in zip(nodes, coords):
        px = scale(x, min_x, max_x, margin + 20, width - margin - 20)
        py = scale(y, min_y, max_y, height - margin - 20, margin + 20)
        if node_type == 'query':
            svg_lines.append(f'<circle class="query" cx="{px:.1f}" cy="{py:.1f}" r="5"/>')
            svg_lines.append(f'<text class="query-label" x="{px + 7:.1f}" y="{py - 7:.1f}">{escape(label)}</text>')
        else:
            svg_lines.append(f'<circle class="hit" cx="{px:.1f}" cy="{py:.1f}" r="3.5"/>')
            if label in labeled_hit_names:
                svg_lines.append(f'<text class="hit-label" x="{px + 5:.1f}" y="{py + 10:.1f}">{escape(label)}</text>')

    legend_x = width - 320
    legend_y = margin + 30
    svg_lines += [
        f'<circle class="query" cx="{legend_x}" cy="{legend_y}" r="5"/>',
        f'<text x="{legend_x + 12}" y="{legend_y + 4}">Workbook query targets</text>',
        f'<circle class="hit" cx="{legend_x}" cy="{legend_y + 24}" r="4"/>',
        f'<text x="{legend_x + 12}" y="{legend_y + 28}">SNAC-DB hit structures (top 5 per query)</text>',
        '</svg>',
    ]

    (pr_dir / 'top5_tm_embedding.svg').write_text('\n'.join(svg_lines) + '\n')


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
    top5_rows = load_rows(top5_hits)
    unresolved_rows = load_rows(unresolved)
    best_sorted = sorted(best_rows, key=lambda row: float(row['tm_score']), reverse=True)
    if top5_rows:
        write_embedding(top5_rows, pr_dir)

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
        '- `top5_tm_embedding.svg`: 2D embedding of workbook queries plus top-5 SNAC-DB hits.',
        '- `top5_tm_embedding_nodes.csv`: numeric coordinates behind the SVG embedding.',
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
