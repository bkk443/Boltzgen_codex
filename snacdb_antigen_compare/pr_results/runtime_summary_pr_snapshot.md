# SNAC-DB antigen comparison summary

## Installed / configured workflow components

- Environment spec: `env/environment.yml`.
- Setup script: `scripts/setup_snacdb.sh`.
- Execution scripts: `scripts/run_all.sh`, `scripts/run_antigen_hits.sh`.

## Data sources used

- Query workbook path used for this run: `snacdb_antigen_compare/top_kandidati_intracelularne_tarce_ARIS.xlsx`.
- SNAC-DB curated dataset provenance recorded in `reference/REFERENCE_SOURCE.txt`.

## Structure selection policy

- Priority order: user-provided experimental PDB hints, alternative experimental PDBs, AlphaFold fallback only when experimental resolution fails.
- Ambiguous or missing rows are carried into unresolved outputs rather than force-mapped.

## Run summary

- Query structures selected: 40.
- Query structures unresolved during selection: 1.
- Targets with best-hit output rows: 28.
- Unresolved or failed targets recorded: 0.

## Per-target nearest SNAC-DB antigen neighbors

- **GTP cyclohydrolase 1** → best hit `7K7I-ASU0-VH_J-VL_K-Ag_B_E` (`TM-score=0.15159`); notes: Parsed from SNAC-DB Foldseek report.
- **MTOR associated protein, LST8 homolog (S. cerevisiae)** → best hit `8ZBI-ASU0-VH_F-VL_F-Ag_B_C` (`TM-score=0.57345`); notes: Parsed from SNAC-DB Foldseek report.
- **NUF2, NDC80 kinetochore complex component** → best hit `5TD8-ASU0-VHH_E-Ag_A_C` (`TM-score=0.30054`); notes: Parsed from SNAC-DB Foldseek report.
- **O-sialoglycoprotein endopeptidase** → best hit `6GKD-ASU0-VHH_G-Ag_F_T` (`TM-score=0.14203`); notes: Parsed from SNAC-DB Foldseek report.
- **Ran GTPase activating protein 1** → best hit `8CAF-ASU0-VH_B-VL_A-Ag_F_H` (`TM-score=0.46076`); notes: Parsed from SNAC-DB Foldseek report.
- **Thymidylate synthase** → best hit `8J7U-ASU0-VH_E-VL_C-Ag_A_B` (`TM-score=0.08797`); notes: Parsed from SNAC-DB Foldseek report.
- **UDP-glucose pyrophosphorylase 2** → best hit `5BOP-ASU0-VHH_A-Ag_B_D` (`TM-score=0.19294`); notes: Parsed from SNAC-DB Foldseek report.
- **adenylosuccinate lyase** → best hit `8DJM-ASU0-VH_H-VL_L-Ag_A_B` (`TM-score=0.13754`); notes: Parsed from SNAC-DB Foldseek report.
- **aminolevulinate dehydratase** → best hit `8RTF-ASU2-VHH_G-Ag_A_F` (`TM-score=0.37865`); notes: Parsed from SNAC-DB Foldseek report.
- **cell division cycle 42** → best hit `6SGE-ASU0-VHH_B-Ag_A_C` (`TM-score=0.48236`); notes: Parsed from SNAC-DB Foldseek report.
- **cytochrome P450, family 51, subfamily A, polypeptide 1** → best hit `4DKF-ASU0-VH_H-VL_L-Ag_A_B` (`TM-score=0.13097`); notes: Parsed from SNAC-DB Foldseek report.
- **deoxyuridine triphosphatase** → best hit `3ZHD-ASU1-VHH_E-Ag_C_D` (`TM-score=0.16115`); notes: Parsed from SNAC-DB Foldseek report.
- **glutamate-ammonia ligase** → best hit `8IM1-ASU0-VHH_H-Ag_C_G` (`TM-score=0.09487`); notes: Parsed from SNAC-DB Foldseek report.
- **glutaminyl-tRNA synthetase** → best hit `9MGB-ASU0-VH_k-VL_k-Ag_J_L` (`TM-score=0.12751`); notes: Parsed from SNAC-DB Foldseek report.
- **hydroxymethylbilane synthase** → best hit `8TME-ASU0-VH_H-VL_L-Ag_A_B` (`TM-score=0.08472`); notes: Parsed from SNAC-DB Foldseek report.
- **leucyl-tRNA synthetase** → best hit `6OL7-ASU0-VH_C-VL_B-Ag_D_E` (`TM-score=0.10798`); notes: Parsed from SNAC-DB Foldseek report.
- **lysyl-tRNA synthetase** → best hit `4DK6-ASU0-VHH_B-Ag_C_D` (`TM-score=0.32942`); notes: Parsed from SNAC-DB Foldseek report.
- **mevalonate (diphospho) decarboxylase** → best hit `5UDD-ASU0-VH_J-VL_P-Ag_A_E` (`TM-score=0.07685`); notes: Parsed from SNAC-DB Foldseek report.
- **mevalonate kinase** → best hit `4PLK-ASU0-VH_D-VL_C-Ag_A_B` (`TM-score=0.08082`); notes: Parsed from SNAC-DB Foldseek report.
- **peptidylprolyl cis/trans isomerase, NIMA-interacting 1** → best hit `2IAM-ASU0-VH_D-VL_C-Ag_A_B_P` (`TM-score=0.10311`); notes: Parsed from SNAC-DB Foldseek report.
- **phosphopantothenoylcysteine synthetase** → best hit `6SGE-ASU0-VHH_B-Ag_A_C` (`TM-score=0.24106`); notes: Parsed from SNAC-DB Foldseek report.
- **protein phosphatase 1, regulatory subunit 7** → best hit `8H64-ASU0-VHH_D-Ag_C_E` (`TM-score=0.27775`); notes: Parsed from SNAC-DB Foldseek report.
- **ring-box 1, E3 ubiquitin protein ligase** → best hit `8CAF-ASU0-VH_D-VL_C-Ag_E_G` (`TM-score=0.52546`); notes: Parsed from SNAC-DB Foldseek report.
- **seryl-tRNA synthetase** → best hit `6BPE-ASU0-VH_B-VL_C-Ag_A_D` (`TM-score=0.10968`); notes: Parsed from SNAC-DB Foldseek report.
- **superkiller viralicidic activity 2-like 2 (S. cerevisiae)** → best hit `8RTF-ASU2-VHH_G-Ag_A_F` (`TM-score=0.12441`); notes: Parsed from SNAC-DB Foldseek report.
- **tRNA nucleotidyl transferase, CCA-adding, 1** → best hit `8TEA-ASU0-VH_F-VL_I-Ag_C_D` (`TM-score=0.09858`); notes: Parsed from SNAC-DB Foldseek report.
- **thiamin pyrophosphokinase 1** → best hit `5BOP-ASU0-VHH_A-Ag_B_D` (`TM-score=0.23447`); notes: Parsed from SNAC-DB Foldseek report.
- **triosephosphate isomerase 1** → best hit `8RTF-ASU0-VHH_I-Ag_C_D` (`TM-score=0.28926`); notes: Parsed from SNAC-DB Foldseek report.

## Caveats


## Reference dataset provenance snapshot

- Access date (UTC): 2026-03-22T11:40:02.088067+00:00
- Concept DOI: 10.5281/zenodo.15870002
- Versioned DOI: 10.5281/zenodo.18378437
- Title: SNAC-DB: Structural NANOBODY® (VHH) and Antibody (VH-VL) Complex Database
- Publication date: 2026-01-26
- Expected archive: SNAC-DataBase.zip
- Expected size (bytes): 11068449854
- Download URL: https://zenodo.org/api/records/18378437/files/SNAC-DataBase.zip/content
- Note: the archive is large; this helper records exact provenance and can download it when invoked with --download.
