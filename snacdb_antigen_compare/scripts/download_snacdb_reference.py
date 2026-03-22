#!/usr/bin/env python3
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_URL = 'https://zenodo.org/api/records/15870002'


def main():
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('snacdb_antigen_compare/reference/snacdb_curated')
    source_txt = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('snacdb_antigen_compare/reference/REFERENCE_SOURCE.txt')
    out_dir.mkdir(parents=True, exist_ok=True)
    source_txt.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(API_URL, headers={'User-Agent': 'snacdb-antigen-compare/1.0'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        record = json.loads(resp.read().decode('utf-8'))
    files = record.get('files', [])
    target = next((f for f in files if f.get('key') == 'SNAC-DataBase.zip'), None)
    lines = [
        f'Access date (UTC): {datetime.now(timezone.utc).isoformat()}',
        f'Concept DOI: {record.get("conceptdoi")}',
        f'Versioned DOI: {record.get("doi")}',
        f'Title: {record.get("metadata", {}).get("title")}',
        f'Publication date: {record.get("metadata", {}).get("publication_date")}',
        f'Expected archive: {target.get("key") if target else "N/A"}',
        f'Expected size (bytes): {target.get("size") if target else "N/A"}',
        f'Download URL: {target.get("links", {}).get("self") if target else "N/A"}',
        'Note: the archive is large; this helper records exact provenance and can download it when invoked with --download.',
    ]
    download = '--download' in sys.argv[1:]
    if download and target:
        zip_path = out_dir / target['key']
        with urllib.request.urlopen(target['links']['self'], timeout=120) as resp, zip_path.open('wb') as fh:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                fh.write(chunk)
        lines.append(f'Downloaded archive to: {zip_path}')
    source_txt.write_text('\n'.join(lines) + '\n')
    print(f'Wrote {source_txt}')


if __name__ == '__main__':
    main()
