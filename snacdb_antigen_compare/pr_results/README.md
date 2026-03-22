# PR-visible SNAC-DB antigen comparison snapshot

This directory intentionally contains a committed text snapshot of the latest generated comparison outputs so the PR shows real results.

## Snapshot contents

- `snacdb_antigen_best_hits_pr_snapshot.csv`: one best SNAC-DB structural neighbor per target.
- `snacdb_antigen_top5_hits_pr_snapshot.csv`: top 5 SNAC-DB neighbors per target.
- `unresolved_or_failed_targets_pr_snapshot.csv`: unresolved or failed targets at postprocessing time.
- `runtime_summary_pr_snapshot.md`: copy of the generated Markdown summary.
- `top5_tm_embedding.svg`: 2D embedding of workbook queries plus top-5 SNAC-DB hits.
- `top5_tm_embedding_nodes.csv`: numeric coordinates behind the SVG embedding.

## Snapshot summary

- Targets with best-hit rows: 28.
- Unresolved or failed targets: 0.

## Strongest best-hit rows in this snapshot

- **MTOR associated protein, LST8 homolog (S. cerevisiae)** → `8ZBI-ASU0-VH_F-VL_F-Ag_B_C` (`TM-score=0.57345`, query `4JSN`)
- **ring-box 1, E3 ubiquitin protein ligase** → `8CAF-ASU0-VH_D-VL_C-Ag_E_G` (`TM-score=0.52546`, query `1LDJ`)
- **cell division cycle 42** → `6SGE-ASU0-VHH_B-Ag_A_C` (`TM-score=0.48236`, query `1A4R`)
- **Ran GTPase activating protein 1** → `8CAF-ASU0-VH_B-VL_A-Ag_F_H` (`TM-score=0.46076`, query `1Z5S`)
- **aminolevulinate dehydratase** → `8RTF-ASU2-VHH_G-Ag_A_F` (`TM-score=0.37865`, query `1E51`)
- **lysyl-tRNA synthetase** → `4DK6-ASU0-VHH_B-Ag_C_D` (`TM-score=0.32942`, query `3BJU`)
- **NUF2, NDC80 kinetochore complex component** → `5TD8-ASU0-VHH_E-Ag_A_C` (`TM-score=0.30054`, query `2VE7`)
- **triosephosphate isomerase 1** → `8RTF-ASU0-VHH_I-Ag_C_D` (`TM-score=0.28926`, query `1HTI`)
- **protein phosphatase 1, regulatory subunit 7** → `8H64-ASU0-VHH_D-Ag_C_E` (`TM-score=0.27775`, query `6HKW`)
- **phosphopantothenoylcysteine synthetase** → `6SGE-ASU0-VHH_B-Ag_A_C` (`TM-score=0.24106`, query `1P9O`)
