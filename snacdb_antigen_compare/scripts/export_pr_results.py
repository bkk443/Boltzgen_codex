#!/usr/bin/env python3
import csv
import shutil
import sys
from html import escape
from pathlib import Path


def load_rows(path: Path):
    if not path.exists():
        return []
    with path.open() as fh:
        return list(csv.DictReader(fh))


def first_existing(*paths: Path):
    for path in paths:
        if path.exists():
            return path
    return paths[0]


def write_best_hit_bar_chart(best_rows, pr_dir: Path):
    rows = sorted(best_rows, key=lambda row: float(row['tm_score']), reverse=True)
    width = 1400
    row_height = 26
    margin_left = 420
    margin_right = 140
    margin_top = 90
    margin_bottom = 40
    chart_width = width - margin_left - margin_right
    height = margin_top + margin_bottom + row_height * len(rows)

    max_tm = max(float(row['tm_score']) for row in rows) if rows else 1.0

    def bar_color(score: float):
        if score >= 0.5:
            return '#1b9e77'
        if score >= 0.3:
            return '#66a61e'
        if score >= 0.2:
            return '#e6ab02'
        if score >= 0.1:
            return '#e67e22'
        return '#d95f02'

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<style>',
        'text { font-family: Arial, sans-serif; }',
        '.title { font-size: 24px; font-weight: bold; }',
        '.subtitle { font-size: 14px; fill: #444; }',
        '.label { font-size: 12px; fill: #111; }',
        '.score { font-size: 12px; fill: #222; }',
        '.axis { stroke: #888; stroke-width: 1; }',
        '.grid { stroke: #ddd; stroke-width: 1; }',
        '</style>',
        f'<text class="title" x="{margin_left}" y="35">Best-hit TM-scores by workbook target</text>',
        f'<text class="subtitle" x="{margin_left}" y="58">Higher is better. Targets are sorted by their best SNAC-DB structural neighbor.</text>',
        f'<line class="axis" x1="{margin_left}" y1="{margin_top - 10}" x2="{margin_left}" y2="{height - margin_bottom}" />',
    ]

    ticks = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, round(max_tm, 2)]
    ticks = sorted(set(ticks))
    for tick in ticks:
        x = margin_left + (tick / max_tm) * chart_width if max_tm else margin_left
        svg.append(f'<line class="grid" x1="{x:.1f}" y1="{margin_top - 10}" x2="{x:.1f}" y2="{height - margin_bottom}" />')
        svg.append(f'<text class="score" x="{x - 10:.1f}" y="{margin_top - 20}">{tick:.2f}</text>')

    for idx, row in enumerate(rows):
        y = margin_top + idx * row_height
        tm = float(row['tm_score'])
        bar_w = (tm / max_tm) * chart_width if max_tm else 0
        svg.append(f'<text class="label" x="{margin_left - 10}" y="{y + 15}" text-anchor="end">{escape(row["target"])}</text>')
        svg.append(
            f'<rect x="{margin_left}" y="{y}" width="{bar_w:.1f}" height="16" fill="{bar_color(tm)}" rx="2" ry="2" />'
        )
        svg.append(
            f'<text class="score" x="{margin_left + bar_w + 8:.1f}" y="{y + 13}">{tm:.5f} ({escape(row["best_hit"])})</text>'
        )

    svg.append('</svg>')
    (pr_dir / 'best_hit_tm_scores.svg').write_text('\n'.join(svg) + '\n')


def write_top5_heatmap(top5_rows, pr_dir: Path):
    grouped = {}
    for row in top5_rows:
        grouped.setdefault(row['target'], {})[int(row['rank'])] = row

    ordered_targets = sorted(
        grouped,
        key=lambda target: float(grouped[target].get(1, {'tm_score': 0.0})['tm_score']),
        reverse=True,
    )

    matrix_csv = pr_dir / 'top5_tm_heatmap_matrix.csv'
    with matrix_csv.open('w', newline='') as fh:
        writer = csv.writer(fh)
        writer.writerow(['target', 'chosen_query_structure', 'rank_1', 'rank_2', 'rank_3', 'rank_4', 'rank_5'])
        for target in ordered_targets:
            chosen = grouped[target][1]['chosen_query_structure'] if 1 in grouped[target] else ''
            writer.writerow([
                target,
                chosen,
                *(grouped[target].get(rank, {}).get('tm_score', '') for rank in range(1, 6)),
            ])

    width = 1180
    cell_w = 110
    cell_h = 26
    margin_left = 520
    margin_top = 110
    margin_bottom = 40
    margin_right = 70
    height = margin_top + margin_bottom + cell_h * len(ordered_targets)

    def heat(score_text: str):
        if not score_text:
            return '#f5f5f5'
        score = float(score_text)
        intensity = min(max(score / 0.6, 0.0), 1.0)
        red = int(255 - 110 * intensity)
        green = int(255 - 185 * intensity)
        blue = int(255 - 205 * intensity)
        return f'#{red:02x}{green:02x}{blue:02x}'

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<style>',
        'text { font-family: Arial, sans-serif; }',
        '.title { font-size: 24px; font-weight: bold; }',
        '.subtitle { font-size: 14px; fill: #444; }',
        '.label { font-size: 12px; fill: #111; }',
        '.celltext { font-size: 11px; fill: #111; }',
        '.header { font-size: 12px; font-weight: bold; }',
        '</style>',
        f'<text class="title" x="{margin_left}" y="35">Top-5 TM-score heatmap by workbook target</text>',
        f'<text class="subtitle" x="{margin_left}" y="58">Rows are targets sorted by best hit. Columns are hit rank 1–5. Darker cells mean higher TM-scores.</text>',
    ]

    for col in range(5):
        x = margin_left + col * cell_w
        svg.append(f'<text class="header" x="{x + 28}" y="{margin_top - 18}">Rank {col + 1}</text>')

    for row_idx, target in enumerate(ordered_targets):
        y = margin_top + row_idx * cell_h
        svg.append(f'<text class="label" x="{margin_left - 10}" y="{y + 17}" text-anchor="end">{escape(target)}</text>')
        for rank in range(1, 6):
            x = margin_left + (rank - 1) * cell_w
            score_text = grouped[target].get(rank, {}).get('tm_score', '')
            svg.append(f'<rect x="{x}" y="{y}" width="{cell_w - 6}" height="{cell_h - 4}" fill="{heat(score_text)}" stroke="#ddd"/>')
            if score_text:
                svg.append(f'<text class="celltext" x="{x + 24}" y="{y + 17}">{float(score_text):.3f}</text>')

    svg.append('</svg>')
    (pr_dir / 'top5_tm_heatmap.svg').write_text('\n'.join(svg) + '\n')


def main():
    out_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('snacdb_antigen_compare')
    pr_dir = out_root / 'pr_results'
    pr_dir.mkdir(parents=True, exist_ok=True)

    best_hits = first_existing(
        out_root / '04_results/snacdb_antigen_best_hits.csv',
        pr_dir / 'snacdb_antigen_best_hits_pr_snapshot.csv',
    )
    top5_hits = first_existing(
        out_root / '04_results/snacdb_antigen_top5_hits.csv',
        pr_dir / 'snacdb_antigen_top5_hits_pr_snapshot.csv',
    )
    unresolved = first_existing(
        out_root / '04_results/unresolved_or_failed_targets.csv',
        pr_dir / 'unresolved_or_failed_targets_pr_snapshot.csv',
    )
    runtime_summary = first_existing(
        out_root / '05_report/summary.md',
        pr_dir / 'runtime_summary_pr_snapshot.md',
    )

    if best_hits.exists() and best_hits != pr_dir / 'snacdb_antigen_best_hits_pr_snapshot.csv':
        shutil.copyfile(best_hits, pr_dir / 'snacdb_antigen_best_hits_pr_snapshot.csv')
    if top5_hits.exists() and top5_hits != pr_dir / 'snacdb_antigen_top5_hits_pr_snapshot.csv':
        shutil.copyfile(top5_hits, pr_dir / 'snacdb_antigen_top5_hits_pr_snapshot.csv')
    if unresolved.exists() and unresolved != pr_dir / 'unresolved_or_failed_targets_pr_snapshot.csv':
        shutil.copyfile(unresolved, pr_dir / 'unresolved_or_failed_targets_pr_snapshot.csv')
    if runtime_summary.exists() and runtime_summary != pr_dir / 'runtime_summary_pr_snapshot.md':
        shutil.copyfile(runtime_summary, pr_dir / 'runtime_summary_pr_snapshot.md')

    best_rows = load_rows(best_hits)
    top5_rows = load_rows(top5_hits)
    unresolved_rows = load_rows(unresolved)
    best_sorted = sorted(best_rows, key=lambda row: float(row['tm_score']), reverse=True)
    if best_rows:
        write_best_hit_bar_chart(best_rows, pr_dir)
    if top5_rows:
        write_top5_heatmap(top5_rows, pr_dir)

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
        '- `best_hit_tm_scores.svg`: ranked bar chart of best-hit TM-scores.',
        '- `top5_tm_heatmap.svg`: heatmap of TM-scores for ranks 1–5 per target.',
        '- `top5_tm_heatmap_matrix.csv`: numeric matrix behind the heatmap.',
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
