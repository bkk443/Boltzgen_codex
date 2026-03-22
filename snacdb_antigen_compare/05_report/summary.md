# SNAC-DB antigen comparison summary

## Installed / configured workflow components

- Environment spec: `env/environment.yml`.
- Setup script: `scripts/setup_snacdb.sh`.
- Execution scripts: `scripts/run_all.sh`, `scripts/run_antigen_hits.sh`.

## Data sources used

- Query workbook expected at `./INPUT_ANTIGENS.xlsx`.
- SNAC-DB curated dataset provenance recorded in `reference/REFERENCE_SOURCE.txt`.

## Structure selection policy

- Priority order: user-provided experimental PDB hints, alternative experimental PDBs, AlphaFold fallback only when experimental resolution fails.
- Ambiguous or missing rows are carried into unresolved outputs rather than force-mapped.

## Run summary

- Query structures selected: 0.
- Query structures unresolved during selection: 0.
- Targets with best-hit output rows: 0.
- Unresolved or failed targets recorded: 2.

## Per-target nearest SNAC-DB antigen neighbors

- No SNAC-DB hit report was available in this agent run.

## Caveats

- Target `N/A`: input_workbook_not_found. Missing workbook: /workspace/Boltzgen_codex/INPUT_ANTIGENS.xlsx
- Target `N/A`: snacdb_raw_report_missing. Expected raw report at /workspace/Boltzgen_codex/snacdb_antigen_compare/03_raw_results/foldseek_report.tsv

## Reference dataset provenance snapshot

- Access date (UTC): 2026-03-19T12:33:54.887855+00:00
- Concept DOI: 10.5281/zenodo.15870002
- Versioned DOI: 10.5281/zenodo.18378437
- Title: SNAC-DB: Structural NANOBODY® (VHH) and Antibody (VH-VL) Complex Database
- Publication date: 2026-01-26
- Expected archive: SNAC-DataBase.zip
- Expected size (bytes): 11068449854
- Download URL: https://zenodo.org/api/records/18378437/files/SNAC-DataBase.zip/content
- Note: the archive is large; this helper records exact provenance and can download it when invoked with --download.
