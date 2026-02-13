#!/usr/bin/env python3
"""
Search RCSB PDB for (target protein) AND (nanobody/VHH terms) for a list of proteins in an Excel file.

Input:  an Excel file with a column containing gene/protein names (default: Human_Symbol)
Output: two files:
  1) summary CSV: one row per target with hit counts and first N PDB IDs
  2) long CSV:    one row per (target, PDB ID) hit

This uses the RCSB Search API v2 endpoint:
  https://search.rcsb.org/rcsbsearch/v2/query
"""
from __future__ import annotations

import argparse
import json
import time
from typing import Any, Dict, List, Tuple

import pandas as pd
import requests


SEARCH_URL = "https://search.rcsb.org/rcsbsearch/v2/query"
NANOBODY_QUERY = 'nanobody | VHH | "single-domain antibody"'

# For Human_Symbol input, constrain the first pass to human gene annotations to reduce
# false positives for ambiguous symbols (e.g., SARS gene vs SARS coronavirus text hits).
HUMAN_SCIENTIFIC_NAME = "Homo sapiens"


def _entry_query(nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "query": {"type": "group", "logical_operator": "and", "nodes": nodes},
        "return_type": "entry",
        "request_options": {
            "paginate": {"start": 0, "rows": 10000},
            "results_verbosity": "compact",
        },
    }


def _gene_exact_node(target: str) -> Dict[str, Any]:
    return {
        "type": "terminal",
        "service": "text",
        "parameters": {
            "attribute": "rcsb_entity_source_organism.rcsb_gene_name.value",
            "operator": "exact_match",
            "value": target,
            "case_sensitive": True,
        },
    }


def _nanobody_node() -> Dict[str, Any]:
    return {
        "type": "terminal",
        "service": "full_text",
        "parameters": {"value": NANOBODY_QUERY},
    }


def _taxonomy_human_node() -> Dict[str, Any]:
    return {
        "type": "terminal",
        "service": "text",
        "parameters": {
            "attribute": "rcsb_entity_source_organism.scientific_name",
            "operator": "exact_match",
            "value": HUMAN_SCIENTIFIC_NAME
        },
    }


def build_query(target: str, mode: str) -> Dict[str, Any]:
    """
    Build an RCSB Search API query.

    mode:
      - "gene_attr_human": exact gene name + nanobody terms + human taxonomy
      - "gene_attr":       exact gene name + nanobody terms
      - "basic":           broad full-text fallback (opt-in only)
    """
    if mode == "gene_attr_human":
        return _entry_query([_gene_exact_node(target), _taxonomy_human_node(), _nanobody_node()])

    if mode == "gene_attr":
        return _entry_query([_gene_exact_node(target), _nanobody_node()])

    if mode == "basic":
        # Basic-search grammar supports '+' for AND and '|' for OR, plus parentheses.
        basic_value = f'{target} + ( {NANOBODY_QUERY} )'
        return {
            "query": {"type": "terminal", "service": "full_text", "parameters": {"value": basic_value}},
            "return_type": "entry",
            "request_options": {
                "paginate": {"start": 0, "rows": 10000},
                "results_verbosity": "compact",
            },
        }

    raise ValueError(f"Unknown mode: {mode}")


def post_json_with_retries(
    session: requests.Session,
    url: str,
    payload: Dict[str, Any],
    max_retries: int = 6,
    backoff: float = 1.5,
) -> requests.Response:
    """Robust POST with exponential backoff for transient failures (429/5xx)."""
    data = json.dumps(payload)
    headers = {"Content-Type": "application/json"}

    for attempt in range(max_retries):
        resp = session.post(url, data=data, headers=headers, timeout=60)
        if resp.status_code in (200, 204):
            return resp
        if resp.status_code in (429, 500, 502, 503, 504):
            time.sleep(backoff**attempt)
            continue
        resp.raise_for_status()

    resp.raise_for_status()
    return resp  # unreachable


def parse_result_set(resp: requests.Response) -> List[str]:
    if resp.status_code == 204:
        return []

    result_set = resp.json().get("result_set", [])
    pdb_ids: List[str] = []
    for item in result_set:
        if isinstance(item, dict) and "identifier" in item:
            pdb_ids.append(str(item["identifier"]))
        elif isinstance(item, str):
            pdb_ids.append(item)
    return pdb_ids


def run_one_target(
    session: requests.Session,
    target: str,
    *,
    allow_basic_fallback: bool = False,
    delay_s: float = 0.05,
) -> Tuple[str, List[str], str]:
    """
    Use stricter attribute-based modes first to reduce false positives.
    Basic full-text fallback is optional and off by default.
    Returns (target, pdb_ids, used_mode).
    """
    modes = ["gene_attr_human", "gene_attr"]
    if allow_basic_fallback:
        modes.append("basic")

    for mode in modes:
        q = build_query(target, mode)
        resp = post_json_with_retries(session, SEARCH_URL, q)
        pdb_ids = parse_result_set(resp)
        if pdb_ids:
            time.sleep(delay_s)
            return target, pdb_ids, mode

    time.sleep(delay_s)
    return target, [], "none"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("excel", help="Input Excel file (e.g., your_list.xlsx)")
    ap.add_argument("--column", default="Human_Symbol", help="Column containing target names (default: Human_Symbol)")
    ap.add_argument(
        "--allow_basic_fallback",
        action="store_true",
        help="If set, fall back to broad full-text search when attribute-based queries return no hits.",
    )
    ap.add_argument(
        "--max_ids_per_target",
        type=int,
        default=200,
        help="Store up to this many PDB IDs per target in long output (default: 200)",
    )
    ap.add_argument("--out_prefix", default="rcsb_nanobody_hits", help="Output prefix for CSVs")
    args = ap.parse_args()

    df = pd.read_excel(args.excel)
    if args.column not in df.columns:
        raise SystemExit(f"Column '{args.column}' not found. Available: {list(df.columns)}")

    targets = (
        df[args.column].dropna().astype(str).str.strip().replace("", pd.NA).dropna().unique().tolist()
    )

    summary_rows: List[Dict[str, Any]] = []
    long_rows: List[Dict[str, Any]] = []

    with requests.Session() as session:
        for t in targets:
            target, pdb_ids, mode = run_one_target(session, t, allow_basic_fallback=args.allow_basic_fallback)
            summary_rows.append(
                {
                    "target": target,
                    "used_mode": mode,
                    "n_hits": len(pdb_ids),
                    "pdb_ids_first_50": ",".join(pdb_ids[:50]),
                }
            )
            for pid in pdb_ids[: args.max_ids_per_target]:
                long_rows.append({"target": target, "pdb_id": pid, "used_mode": mode})

    summary = pd.DataFrame(summary_rows).sort_values(["n_hits", "target"], ascending=[False, True])
    long_df = pd.DataFrame(long_rows)

    summary_path = f"{args.out_prefix}_summary.csv"
    long_path = f"{args.out_prefix}_long.csv"
    summary.to_csv(summary_path, index=False)
    long_df.to_csv(long_path, index=False)

    print(f"Wrote: {summary_path}")
    print(f"Wrote: {long_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
