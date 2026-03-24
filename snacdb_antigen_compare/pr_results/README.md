# PR-visible SNAC-DB antigen comparison snapshot

This directory intentionally contains a committed text snapshot of the latest generated comparison outputs so the PR shows real results.

## Snapshot contents

- `protein_space_map_mds_pr_snapshot.svg`: MDS structure-space map from the all-vs-all structural similarity matrix.
- `protein_space_map_umap_pr_snapshot.svg`: UMAP structure-space map from the same all-vs-all structural similarity matrix.
- `protein_space_similarity_matrix_pr_snapshot.csv`: full structure-only similarity matrix behind both maps.
- `protein_space_nodes_mds_pr_snapshot.csv`: node metadata and 2D coordinates for the MDS map.
- `protein_space_nodes_umap_pr_snapshot.csv`: node metadata and 2D coordinates for the UMAP map.
- Structure map coverage in this snapshot: 28 workbook proteins and 118 SNAC-DB reference antigens.
- `snacdb_antigen_best_hits_pr_snapshot.csv`: nearest-neighbor summary table for each workbook protein.
- `snacdb_antigen_top5_hits_pr_snapshot.csv`: top 5 SNAC-DB neighbors per workbook protein.
- `unresolved_or_failed_targets_pr_snapshot.csv`: unresolved or failed targets at postprocessing time.
- `runtime_summary_pr_snapshot.md`: copy of the generated Markdown summary.
- `best_hit_tm_scores.svg`: ranked nearest-neighbor TM-score summary.
- `top5_tm_heatmap.svg`: top-5 nearest-neighbor heatmap summary.
- `top5_tm_heatmap_matrix.csv`: numeric matrix behind the top-5 summary heatmap.

## Snapshot summary

- Targets with best-hit rows: 0.
- Protein-space nodes available in this checkout: 146.
- Unresolved or failed targets: 1.

## Strongest nearest-neighbor rows in this snapshot

- No best-hit rows were available when this snapshot was created.
