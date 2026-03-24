# SNAC-DB antigen comparison workflow

This directory contains a rerunnable workflow for comparing user antigen target structures against SNAC-DB antigen structures with SNAC-DB's `antigen` hit-finding mode.

## What this workflow does

1. Inspect `INPUT_ANTIGENS.xlsx` and normalize likely antigen-identifying columns.
2. Resolve one representative structure per antigen conservatively.
3. Download query structures into a standard directory layout.
4. Set up SNAC-DB and required tooling reproducibly.
5. Record provenance for the curated SNAC-DB reference dataset and optionally download it.
6. Run SNAC-DB structural searches in antigen mode, including an all-vs-all protein-space search over workbook proteins plus reference antigens.
7. Postprocess raw outputs into user-friendly CSV summaries, separate MDS and UMAP structure-space maps, and a Markdown report.

## Important assumptions

- By default, `run_all.sh` looks for `./INPUT_ANTIGENS.xlsx` at the repository root, but you should usually pass the workbook path explicitly.
- Local input workbooks are intentionally not committed to git; provide the `.xlsx` file locally when you run the workflow.
- The SNAC-DB curated dataset archive advertised by the upstream repository is currently ~11 GB on Zenodo. The helper script records exact provenance and can download it when explicitly invoked with `--download`, but the agent did not pull the full archive automatically.
- AlphaFold is only used as a labeled fallback when no experimental structure can be resolved automatically from the manifest row.
- Most files under `01_manifest/`, `02_queries/`, `03_raw_results/`, `04_results/`, `05_report/`, `logs/`, and `reference/` are generated at runtime and are intentionally ignored by git.

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

Default workbook location:

```bash
bash snacdb_antigen_compare/scripts/run_all.sh
```

Override the workbook path explicitly if the file is stored under a different name/location:

```bash
bash snacdb_antigen_compare/scripts/run_all.sh /absolute/or/relative/path/to/workbook.xlsx
```

## Optional: download the curated SNAC-DB reference archive

```bash
python snacdb_antigen_compare/scripts/download_snacdb_reference.py \
  snacdb_antigen_compare/reference/snacdb_curated \
  snacdb_antigen_compare/reference/REFERENCE_SOURCE.txt \
  --download
```

After download, extract the archive under `snacdb_antigen_compare/reference/snacdb_curated/` so that the merged curated-complex directory is available at `snacdb_antigen_compare/reference/snacdb_curated/all_complexes`.
Keep the downloaded `SNAC-DataBase.zip` in that directory as well; the workflow now validates the extracted `all_complexes/` tree against the archive before it will generate protein-space outputs or export PR-visible MDS/UMAP figures.

## Optional: run the SNAC-DB hit-finding step directly

```bash
bash snacdb_antigen_compare/scripts/run_antigen_hits.sh \
  snacdb_antigen_compare/reference/snacdb_curated/all_complexes \
  snacdb_antigen_compare/02_queries/structures
```

## Output layout

- `01_manifest/`: generated workbook schema summary plus normalized/unresolved manifests
- `02_queries/`: generated structure manifest and downloaded query structures
- `03_raw_results/`: copied raw SNAC-DB/Foldseek outputs, including `protein_space_all_vs_all.tsv` for the structure map
- `04_results/`: generated all hits, best hits, top-5 hits, unresolved/failed targets, and the protein-space matrix / node table
- `05_report/summary.md`, `05_report/protein_space_map_mds.svg`, and `05_report/protein_space_map_umap.svg`: generated interpretation report plus paired MDS/UMAP structure-space figures
- `pr_results/`: optional committed text snapshots of result files for PR review
- `env/environment.yml`: reproducible environment spec
- `logs/`: terminal-style logs for each workflow stage
- `scripts/`: all custom workflow code

## Selection policy

The structure-selection step is intentionally conservative:

1. Prefer experimental PDB IDs explicitly supplied in the workbook.
2. Otherwise try to find another experimental PDB entry by exact UniProt accession search.
3. Use AlphaFold only as a clearly labeled fallback.
4. Leave ambiguous rows unresolved rather than force matching names to structures.

The workbook parser now infers likely columns from both headers and sample values, so unlabeled or weakly labeled UniProt-accession columns (for example a second column populated with UniProt codes) are detected without relying on the header text alone.

## Notes on SNAC-DB integration

- Upstream SNAC-DB repo: `external/SNAC-DB` after setup.
- The workflow prepares antigen-chain reference inputs with upstream SNAC-DB utilities, runs Foldseek multimer search for nearest-neighbor summaries, and also runs a Foldseek all-vs-all single-chain structure search over workbook proteins plus prepared reference antigens for the primary structure-space map.
- The environment spec includes Foldseek, HMMER, MMseqs2, and the Python dependencies SNAC-DB documents.
- ANARCI is installed from GitHub and patched with `snacdb-patch-anarci` per upstream instructions.

## PR-visible result snapshots

If you want text results to appear directly in a pull request, export the latest generated outputs into `pr_results/`:

```bash
python snacdb_antigen_compare/scripts/export_pr_results.py snacdb_antigen_compare
```

When the workflow has produced `03_raw_results/protein_space_all_vs_all.tsv` and the downstream `build_protein_space_map.py` outputs from a real full run against the complete prepared SNAC-DB antigen reference, the exporter copies the MDS and UMAP structure maps into `pr_results/` as the primary PR figures, along with the backing structure-only similarity matrix and node tables.
The generated runtime UMAP lives at `05_report/protein_space_map_umap.svg`, and the PR-visible exported copy lives at `pr_results/protein_space_map_umap_pr_snapshot.svg`.
The full-reference guard writes `03_raw_results/protein_space_reference_validation.json`; if that marker is missing or invalid, the map builder and PR exporter will refuse to treat protein-space artifacts as complete.
