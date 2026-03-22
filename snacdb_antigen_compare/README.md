# SNAC-DB antigen comparison workflow

This directory contains a rerunnable workflow for comparing user antigen target structures against SNAC-DB antigen structures with SNAC-DB's `antigen` hit-finding mode.

## What this workflow does

1. Inspect `INPUT_ANTIGENS.xlsx` and normalize likely antigen-identifying columns.
2. Resolve one representative structure per antigen conservatively.
3. Download query structures into a standard directory layout.
4. Set up SNAC-DB and required tooling reproducibly.
5. Record provenance for the curated SNAC-DB reference dataset and optionally download it.
6. Run SNAC-DB structural hit finding in antigen mode.
7. Postprocess raw outputs into user-friendly CSV summaries and a Markdown report.

## Important assumptions and current agent-run caveats

- The workflow expects the workbook at `./INPUT_ANTIGENS.xlsx` relative to the repository root.
- During this agent run, that workbook file was **not present** in `/workspace/Boltzgen_codex`, so the generated manifests intentionally record the missing-input condition instead of fabricating antigen mappings.
- The SNAC-DB curated dataset archive advertised by the upstream repository is currently ~11 GB on Zenodo. The helper script records exact provenance and can download it when explicitly invoked with `--download`, but the agent did not pull the full archive automatically.
- AlphaFold is only used as a labeled fallback when no experimental structure can be resolved automatically from the manifest row.

## Required software

- One of: `conda`, `mamba`, or `micromamba`
- `git`
- Internet access for dependency installation, structure downloads, and the SNAC-DB reference dataset
- Enough disk space for the SNAC-DB curated archive (roughly 11+ GB compressed, more after extraction)

## Environment setup

```bash
bash snacdb_antigen_compare/scripts/setup_snacdb.sh
conda activate snacdb_antigen_compare
```

## Rerun the full workflow

```bash
bash snacdb_antigen_compare/scripts/run_all.sh
```

## Optional: download the curated SNAC-DB reference archive

```bash
python snacdb_antigen_compare/scripts/download_snacdb_reference.py \
  snacdb_antigen_compare/reference/snacdb_curated \
  snacdb_antigen_compare/reference/REFERENCE_SOURCE.txt \
  --download
```

After download, extract the archive under `snacdb_antigen_compare/reference/snacdb_curated/` so that `run_antigen_hits.sh` can point SNAC-DB at the curated structure directory.

## Optional: run the SNAC-DB hit-finding step directly

```bash
bash snacdb_antigen_compare/scripts/run_antigen_hits.sh \
  snacdb_antigen_compare/reference/snacdb_curated \
  snacdb_antigen_compare/02_queries/structures
```

## Output layout

- `01_manifest/`: workbook schema summary plus normalized/unresolved manifests
- `02_queries/`: selected structure manifest and downloaded query structures
- `03_raw_results/`: copied raw SNAC-DB/Foldseek outputs
- `04_results/`: all hits, best hits, top-5 hits, unresolved/failed targets
- `05_report/summary.md`: short interpretation report
- `env/environment.yml`: reproducible environment spec
- `logs/`: terminal-style logs for each workflow stage
- `scripts/`: all custom workflow code

## Selection policy

The structure-selection step is intentionally conservative:

1. Prefer experimental PDB IDs explicitly supplied in the workbook.
2. Otherwise try to find another experimental PDB entry by exact UniProt accession search.
3. Use AlphaFold only as a clearly labeled fallback.
4. Leave ambiguous rows unresolved rather than force matching names to structures.

## Notes on SNAC-DB integration

- Upstream SNAC-DB repo: `external/SNAC-DB` after setup.
- Upstream `finding_hits.sh` is used in `antigen` mode.
- The environment spec includes Foldseek, HMMER, MMseqs2, and the Python dependencies SNAC-DB documents.
- ANARCI is installed from GitHub and patched with `snacdb-patch-anarci` per upstream instructions.
