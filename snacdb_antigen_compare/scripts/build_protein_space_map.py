#!/usr/bin/env python3
import csv
import sys
from html import escape
from pathlib import Path

import numpy as np
import umap


def load_query_labels(path: Path):
    labels = {}
    if not path.exists():
        return labels
    with path.open() as fh:
        for row in csv.DictReader(fh):
            query_filename = row.get('query_filename', '')
            if not query_filename:
                continue
            stem = Path(query_filename).stem
            labels[stem] = row.get('target_name', stem)
    return labels


def strip_name(value: str):
    return Path(value.strip()).stem


def normalize_node_id(node_id: str):
    if node_id.startswith('query__'):
        prefix, stem = node_id.split('__', 1)
        if '_' in stem:
            stem = stem.rsplit('_', 1)[0]
        return f'{prefix}__{stem}'
    if node_id.startswith('reference__'):
        prefix, stem = node_id.split('__', 1)
        if '_' in stem:
            stem = stem.rsplit('_', 1)[0]
        return f'{prefix}__{stem}'
    return node_id


def classify_node(node_id: str):
    if node_id.startswith('query__'):
        return 'query_target'
    if node_id.startswith('reference__'):
        return 'reference_antigen'
    return 'protein'


def display_label(node_id: str, query_labels):
    if node_id.startswith('query__'):
        query_id = node_id.split('__', 1)[1]
        return query_labels.get(query_id, query_id)
    if node_id.startswith('reference__'):
        return node_id.split('__', 1)[1]
    return node_id


def parse_score(parts):
    if len(parts) >= 3 and parts[2]:
        return float(parts[2])
    qt = float(parts[3]) if len(parts) >= 4 and parts[3] else 0.0
    tt = float(parts[4]) if len(parts) >= 5 and parts[4] else 0.0
    return max(qt, tt)


def load_similarity_rows(path: Path):
    rows = []
    if not path.exists():
        return rows
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t') if '\t' in line else line.split()
            if parts[:3] == ['query', 'target', 'alntmscore']:
                continue
            if len(parts) < 3:
                continue
            query = normalize_node_id(strip_name(parts[0]))
            target = normalize_node_id(strip_name(parts[1]))
            score = parse_score(parts)
            rows.append((query, target, score))
    return rows


def write_matrix(path: Path, node_ids, node_meta, similarity):
    with path.open('w', newline='') as fh:
        writer = csv.writer(fh)
        writer.writerow(['node_id', 'node_type', 'label', *node_ids])
        for node_id in node_ids:
            writer.writerow([
                node_id,
                node_meta[node_id]['node_type'],
                node_meta[node_id]['label'],
                *(f'{similarity[node_id][other]:.5f}' for other in node_ids),
            ])


def write_nodes(path: Path, node_ids, node_meta, coords):
    with path.open('w', newline='') as fh:
        writer = csv.writer(fh)
        writer.writerow(['node_id', 'node_type', 'label', 'x', 'y', 'max_similarity'])
        for node_id, (x, y) in zip(node_ids, coords):
            writer.writerow([
                node_id,
                node_meta[node_id]['node_type'],
                node_meta[node_id]['label'],
                f'{x:.6f}',
                f'{y:.6f}',
                f'{node_meta[node_id]["max_similarity"]:.5f}',
            ])


def write_svg(path: Path, node_ids, node_meta, coords, title: str, subtitle: str):
    xs = [xy[0] for xy in coords]
    ys = [xy[1] for xy in coords]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    def scale(value, lo, hi, out_lo, out_hi):
        if hi == lo:
            return (out_lo + out_hi) / 2
        return out_lo + ((value - lo) / (hi - lo)) * (out_hi - out_lo)

    width, height, margin = 1400, 1000, 85
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<style>',
        'text { font-family: Arial, sans-serif; }',
        '.title { font-size: 24px; font-weight: bold; }',
        '.subtitle { font-size: 14px; fill: #444; }',
        '.ref { fill: #9aa0a6; opacity: 0.45; }',
        '.query { fill: #d62728; }',
        '.query-label { font-size: 11px; fill: #111; }',
        '.frame { fill: white; stroke: #ccc; }',
        '</style>',
        f'<text class="title" x="{margin}" y="38">{escape(title)}</text>',
        f'<text class="subtitle" x="{margin}" y="62">{escape(subtitle)}</text>',
        f'<rect class="frame" x="{margin}" y="{margin}" width="{width - 2 * margin}" height="{height - 2 * margin}" />',
    ]
    for node_id, (x_raw, y_raw) in zip(node_ids, coords):
        meta = node_meta[node_id]
        px = scale(x_raw, min_x, max_x, margin + 18, width - margin - 18)
        py = scale(y_raw, min_y, max_y, height - margin - 18, margin + 18)
        if meta['node_type'] == 'query_target':
            svg.append(f'<circle class="query" cx="{px:.1f}" cy="{py:.1f}" r="6.5" />')
            svg.append(f'<text class="query-label" x="{px + 8:.1f}" y="{py - 7:.1f}">{escape(meta["label"])}</text>')
        else:
            opacity = 0.2 + min(meta['max_similarity'], 1.0) * 0.35
            svg.append(f'<circle class="ref" cx="{px:.1f}" cy="{py:.1f}" r="3.2" opacity="{opacity:.2f}" />')
    legend_x = width - 365
    legend_y = margin + 34
    svg.extend([
        f'<circle class="ref" cx="{legend_x}" cy="{legend_y}" r="4" opacity="0.55" />',
        f'<text x="{legend_x + 14}" y="{legend_y + 4}">SNAC-DB reference antigens</text>',
        f'<circle class="query" cx="{legend_x}" cy="{legend_y + 26}" r="6" />',
        f'<text x="{legend_x + 14}" y="{legend_y + 30}">Workbook proteins (highlighted and labeled)</text>',
        '</svg>',
    ])
    path.write_text('\n'.join(svg) + '\n')


def classical_mds(distance_matrix: np.ndarray):
    n = distance_matrix.shape[0]
    if n == 1:
        return np.array([[0.0, 0.0]])
    squared = distance_matrix ** 2
    identity = np.eye(n)
    ones = np.ones((n, n)) / n
    centered = -0.5 * (identity - ones) @ squared @ (identity - ones)
    eigenvalues, eigenvectors = np.linalg.eigh(centered)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]
    positive = np.maximum(eigenvalues[:2], 0.0)
    coords = eigenvectors[:, :2] * np.sqrt(positive)
    if coords.shape[1] < 2:
        coords = np.pad(coords, ((0, 0), (0, 2 - coords.shape[1])))
    return coords


def umap_embed(distance_matrix: np.ndarray):
    n = distance_matrix.shape[0]
    if n == 1:
        return np.array([[0.0, 0.0]])
    if n == 2:
        return np.array([[0.0, 0.0], [1.0, 0.0]])
    reducer = umap.UMAP(
        n_components=2,
        metric='precomputed',
        n_neighbors=min(15, n - 1),
        min_dist=0.35,
        random_state=42,
    )
    return reducer.fit_transform(distance_matrix)


def main():
    out_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('snacdb_antigen_compare')
    query_manifest = out_root / '02_queries/query_structure_manifest.csv'
    raw_report = out_root / '03_raw_results/protein_space_all_vs_all.tsv'
    results_dir = out_root / '04_results'
    report_dir = out_root / '05_report'
    results_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    query_labels = load_query_labels(query_manifest)
    rows = load_similarity_rows(raw_report)
    if not rows:
        print(f'No protein-space all-vs-all report found at {raw_report}; skipping map export.')
        return

    node_ids = sorted({left for left, _, _ in rows} | {right for _, right, _ in rows})
    node_meta = {}
    similarity = {}
    for node_id in node_ids:
        node_meta[node_id] = {
            'node_type': classify_node(node_id),
            'label': display_label(node_id, query_labels),
            'max_similarity': 0.0,
        }
        similarity[node_id] = {other: (1.0 if other == node_id else 0.0) for other in node_ids}

    for left, right, score in rows:
        score = max(0.0, min(score, 1.0))
        similarity[left][right] = max(similarity[left][right], score)
        similarity[right][left] = max(similarity[right][left], score)
        node_meta[left]['max_similarity'] = max(node_meta[left]['max_similarity'], score)
        node_meta[right]['max_similarity'] = max(node_meta[right]['max_similarity'], score)

    similarity_matrix = np.array([[similarity[left][right] for right in node_ids] for left in node_ids], dtype=float)
    distance_matrix = 1.0 - similarity_matrix

    mds_coords = classical_mds(distance_matrix)
    umap_coords = umap_embed(distance_matrix)

    write_matrix(results_dir / 'protein_space_similarity_matrix.csv', node_ids, node_meta, similarity)
    write_nodes(results_dir / 'protein_space_nodes_mds.csv', node_ids, node_meta, mds_coords)
    write_nodes(results_dir / 'protein_space_nodes_umap.csv', node_ids, node_meta, umap_coords)
    write_nodes(results_dir / 'protein_space_nodes.csv', node_ids, node_meta, mds_coords)
    write_svg(
        report_dir / 'protein_space_map_mds.svg',
        node_ids,
        node_meta,
        mds_coords,
        'Structure map (MDS) across workbook proteins and SNAC-DB reference antigens',
        '2D classical MDS from the all-vs-all structural similarity matrix.',
    )
    write_svg(
        report_dir / 'protein_space_map_umap.svg',
        node_ids,
        node_meta,
        umap_coords,
        'Structure map (UMAP) across workbook proteins and SNAC-DB reference antigens',
        '2D UMAP from the same all-vs-all structural similarity matrix.',
    )
    shutil_path = report_dir / 'protein_space_map.svg'
    shutil_path.write_text((report_dir / 'protein_space_map_mds.svg').read_text())
    print(f'Wrote protein-space outputs to {results_dir} and {report_dir}')


if __name__ == '__main__':
    main()
