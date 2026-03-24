#!/usr/bin/env python3
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

STRUCTURE_SUFFIXES = {'.pdb', '.cif', '.ent', '.gz'}


def parse_reference_source(path: Path):
    data = {}
    if not path.exists():
        return data
    for line in path.read_text().splitlines():
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        data[key.strip()] = value.strip()
    return data


def find_archive(source_info, reference_parent: Path):
    downloaded = source_info.get('Downloaded archive to')
    if downloaded:
        candidate = Path(downloaded)
        if candidate.exists():
            return candidate
    expected_name = source_info.get('Expected archive')
    if expected_name:
        candidate = reference_parent / expected_name
        if candidate.exists():
            return candidate
    return None


def is_structure_member(name: str):
    member = Path(name)
    if member.name.startswith('._') or '__MACOSX' in member.parts:
        return False
    if member.name.startswith('.'):
        return False
    suffixes = member.suffixes
    return any(suffix.lower() in STRUCTURE_SUFFIXES for suffix in suffixes)


def count_reference_files(reference_dir: Path):
    return sum(1 for path in reference_dir.iterdir() if path.is_file() and is_structure_member(path.name))


def count_archive_members(archive_path: Path, reference_basename: str):
    with zipfile.ZipFile(archive_path) as zf:
        named = [
            info.filename for info in zf.infolist()
            if not info.is_dir()
            and Path(info.filename).parent.name == reference_basename
            and is_structure_member(info.filename)
        ]
        if named:
            return len(named)
        fallback = [info.filename for info in zf.infolist() if not info.is_dir() and is_structure_member(info.filename)]
        return len(fallback)


def validate_reference(reference_dir: Path, source_txt: Path):
    info = parse_reference_source(source_txt)
    result = {
        'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'reference_dir': str(reference_dir),
        'reference_source': str(source_txt),
        'status': 'invalid',
        'reason': '',
        'extracted_structure_count': 0,
        'archive_structure_count': 0,
        'archive_path': None,
    }
    if not reference_dir.exists():
        result['reason'] = f'Reference directory is missing: {reference_dir}'
        return result
    if not reference_dir.is_dir():
        result['reason'] = f'Reference path is not a directory: {reference_dir}'
        return result
    if not source_txt.exists():
        result['reason'] = (
            f'Reference provenance file is missing: {source_txt}. '
            'Run download_snacdb_reference.py first so the workflow records the Zenodo archive metadata.'
        )
        return result

    archive_path = find_archive(info, source_txt.parent / 'snacdb_curated')
    if archive_path is None:
        result['reason'] = (
            'Downloaded SNAC-DB archive is not available for validation. '
            'Keep the full SNAC-DataBase.zip beside the extracted reference tree or preserve the exact '
            'download path recorded in REFERENCE_SOURCE.txt before generating protein-space outputs.'
        )
        return result
    result['archive_path'] = str(archive_path)

    expected_size_text = info.get('Expected size (bytes)')
    expected_size = int(expected_size_text) if expected_size_text and re.fullmatch(r'\d+', expected_size_text) else None
    if expected_size is not None:
        actual_size = archive_path.stat().st_size
        result['archive_size_bytes'] = actual_size
        result['archive_expected_size_bytes'] = expected_size
        if actual_size != expected_size:
            result['reason'] = (
                f'Archive size mismatch for {archive_path}: expected {expected_size} bytes, found {actual_size} bytes.'
            )
            return result

    extracted_count = count_reference_files(reference_dir)
    archive_count = count_archive_members(archive_path, reference_dir.name)
    result['extracted_structure_count'] = extracted_count
    result['archive_structure_count'] = archive_count
    if extracted_count == 0:
        result['reason'] = f'Reference directory is empty or contains no recognized structure files: {reference_dir}'
        return result
    if archive_count == 0:
        result['reason'] = (
            f'Could not identify structure members for {reference_dir.name} inside archive {archive_path}. '
            'Inspect the archive layout before running the protein-space workflow.'
        )
        return result
    if extracted_count != archive_count:
        result['reason'] = (
            'Extracted reference file count does not match the downloaded archive: '
            f'{extracted_count} extracted vs {archive_count} archived structure files. '
            'Refusing to treat this as the complete SNAC-DB antigen reference.'
        )
        return result

    result['status'] = 'complete'
    result['reason'] = (
        'Extracted all_complexes directory matches the downloaded Zenodo archive and is eligible '
        'for full protein-space generation.'
    )
    return result


def main():
    reference_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('snacdb_antigen_compare/reference/snacdb_curated/all_complexes')
    source_txt = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('snacdb_antigen_compare/reference/REFERENCE_SOURCE.txt')
    out_json = Path(sys.argv[3]) if len(sys.argv) > 3 else Path('snacdb_antigen_compare/03_raw_results/protein_space_reference_validation.json')
    out_json.parent.mkdir(parents=True, exist_ok=True)
    result = validate_reference(reference_dir, source_txt)
    out_json.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(f'Wrote {out_json}')
    if result['status'] != 'complete':
        print(f"ERROR: {result['reason']}", file=sys.stderr)
        raise SystemExit(1)
    print(result['reason'])


if __name__ == '__main__':
    main()
