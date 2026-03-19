#!/usr/bin/env python3
import csv
import sys
import urllib.request
from pathlib import Path


def download(url, dest):
    req = urllib.request.Request(url, headers={'User-Agent': 'snacdb-antigen-compare/1.0'})
    with urllib.request.urlopen(req, timeout=120) as resp, dest.open('wb') as fh:
        fh.write(resp.read())


def main():
    manifest = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('snacdb_antigen_compare/02_queries/query_structure_manifest.csv')
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('snacdb_antigen_compare/02_queries/structures')
    log_file = Path(sys.argv[3]) if len(sys.argv) > 3 else Path('snacdb_antigen_compare/logs/query_structure_downloads.log')
    out_dir.mkdir(parents=True, exist_ok=True)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open('w') as log:
        if not manifest.exists():
            log.write(f'manifest_missing\t{manifest}\n')
            print(f'Manifest missing: {manifest}')
            return
        with manifest.open() as fh:
            for row in csv.DictReader(fh):
                if row.get('status') != 'selected':
                    continue
                structure_id = row['chosen_structure_id']
                dest = out_dir / row['query_filename']
                if row['source_database'] == 'RCSB PDB':
                    url = f'https://files.rcsb.org/download/{structure_id}.cif'
                elif row['source_database'] == 'AlphaFold DB':
                    url = f'https://alphafold.ebi.ac.uk/files/{structure_id}.cif'
                else:
                    log.write(f'unsupported_source\t{structure_id}\t{row["source_database"]}\n')
                    continue
                try:
                    download(url, dest)
                    log.write(f'downloaded\t{structure_id}\t{dest}\t{url}\n')
                except Exception as exc:
                    log.write(f'failed\t{structure_id}\t{dest}\t{url}\t{exc}\n')
    print(f'Wrote {log_file}')


if __name__ == '__main__':
    main()
