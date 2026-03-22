#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from tqdm import tqdm

MYGENE_BASE = "https://mygene.info/v3/gene"
OT_URL = "https://api.platform.opentargets.org/api/v4/graphql"

OT_QUERY = """
query TargetDiseases($ensemblId: String!, $size: Int!) {
  target(ensemblId: $ensemblId) {
    id
    approvedSymbol
    approvedName
    associatedDiseases(page: { index: 0, size: $size }, orderByScore: \"score desc\") {
      count
      rows {
        score
        disease { id name }
        datatypeScores { id score }
        datasourceScores { id score }
      }
    }
  }
}
"""


class RateLimiter:
    def __init__(self, max_per_sec: float) -> None:
        self.min_interval = 1.0 / max_per_sec
        self.last = 0.0

    def wait(self) -> None:
        now = time.time()
        wait_s = self.min_interval - (now - self.last)
        if wait_s > 0:
            time.sleep(wait_s)
        self.last = time.time()


def request_with_retry(
    session: requests.Session,
    method: str,
    url: str,
    *,
    rate_limiter: RateLimiter,
    runlog: list[str],
    max_retries: int = 6,
    **kwargs: Any,
) -> requests.Response:
    backoff = 1.5
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            rate_limiter.wait()
            resp = session.request(method, url, timeout=60, **kwargs)
            if resp.status_code in (429, 500, 502, 503, 504):
                sleep_s = backoff**attempt
                runlog.append(f"RETRY {method} {url} status={resp.status_code} attempt={attempt+1} sleep={sleep_s:.2f}s")
                time.sleep(sleep_s)
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            sleep_s = backoff**attempt
            runlog.append(f"ERROR {method} {url} attempt={attempt+1} exc={exc} sleep={sleep_s:.2f}s")
            time.sleep(sleep_s)
    raise RuntimeError(f"Failed request after retries: {method} {url}; last_exc={last_exc}")


def parse_ensembl_gene_id(mygene_json: dict[str, Any]) -> str | None:
    ensembl = mygene_json.get("ensembl")
    if isinstance(ensembl, dict):
        gene = ensembl.get("gene")
        if isinstance(gene, str) and gene.startswith("ENSG"):
            return gene
    elif isinstance(ensembl, list):
        for item in ensembl:
            if isinstance(item, dict):
                gene = item.get("gene")
                if isinstance(gene, str) and gene.startswith("ENSG"):
                    return gene
    return None




def parse_subcellular_localisation(mygene_json: dict[str, Any]) -> str:
    go = mygene_json.get("go")
    if not isinstance(go, dict):
        return ""

    cc = go.get("CC")
    terms: list[str] = []
    entries = cc if isinstance(cc, list) else [cc]
    for entry in entries:
        if isinstance(entry, dict):
            term = entry.get("term")
            if isinstance(term, str) and term.strip():
                terms.append(term.strip())

    # Deduplicate while preserving order and keep the string compact for CSV.
    seen = set()
    uniq = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return "; ".join(uniq[:5])


def parse_pdb_codes(mygene_json: dict[str, Any], max_codes: int = 30) -> str:
    pdb = mygene_json.get("pdb")
    codes: list[str] = []
    if isinstance(pdb, str) and pdb.strip():
        codes = [pdb.strip()]
    elif isinstance(pdb, list):
        for item in pdb:
            if isinstance(item, str) and item.strip():
                codes.append(item.strip())

    seen = set()
    uniq = []
    for c in codes:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    return "; ".join(uniq[:max_codes])

def pick_top_scores(items: list[dict[str, Any]], top_n: int = 2) -> list[tuple[str, float]]:
    vals: list[tuple[str, float]] = []
    for d in items or []:
        i = d.get("id")
        s = d.get("score")
        if isinstance(i, str) and isinstance(s, (int, float)) and not math.isnan(float(s)):
            vals.append((i, float(s)))
    vals.sort(key=lambda x: x[1], reverse=True)
    return vals[:top_n]


def fmt_pairs(pairs: list[tuple[str, float]]) -> str:
    return "; ".join([f"{name} ({score:.3f})" for name, score in pairs])


def build_paragraph(symbol: str, top_rows: list[dict[str, Any]]) -> tuple[str, str, str, str]:
    if not top_rows:
        text = f"Open Targets does not report target–disease associations for {symbol} in the queried dataset."
        return text, "", "", ""

    disease_pairs = []
    for r in top_rows[:3]:
        disease = r.get("disease") or {}
        dname = disease.get("name") if isinstance(disease.get("name"), str) else "Unknown disease"
        score = float(r.get("score", 0.0))
        disease_pairs.append((dname, score))

    if len(disease_pairs) >= 2:
        sent1 = (
            f"{symbol} shows the strongest Open Targets disease associations with "
            f"{disease_pairs[0][0]} (score {disease_pairs[0][1]:.3f}) and "
            f"{disease_pairs[1][0]} (score {disease_pairs[1][1]:.3f})."
        )
    else:
        sent1 = (
            f"{symbol} shows the strongest Open Targets disease association with "
            f"{disease_pairs[0][0]} (score {disease_pairs[0][1]:.3f})."
        )

    datatype_agg: dict[str, float] = {}
    datasource_agg: dict[str, float] = {}
    for r in top_rows[:3]:
        for d in (r.get("datatypeScores") or []):
            if isinstance(d, dict) and isinstance(d.get("id"), str) and isinstance(d.get("score"), (int, float)):
                datatype_agg[d["id"]] = datatype_agg.get(d["id"], 0.0) + float(d["score"])
        for d in (r.get("datasourceScores") or []):
            if isinstance(d, dict) and isinstance(d.get("id"), str) and isinstance(d.get("score"), (int, float)):
                datasource_agg[d["id"]] = datasource_agg.get(d["id"], 0.0) + float(d["score"])

    top_dt = sorted(datatype_agg.items(), key=lambda x: x[1], reverse=True)[:2]
    top_ds = sorted(datasource_agg.items(), key=lambda x: x[1], reverse=True)[:2]

    sentences = [sent1]
    if top_dt:
        joined = " and ".join([t[0] for t in top_dt])
        sentences.append(f"Evidence is driven primarily by {joined}.")
    if top_ds:
        joined = " and ".join([t[0] for t in top_ds])
        sentences.append(f"Top contributing sources include {joined}.")

    return " ".join(sentences), fmt_pairs(disease_pairs), fmt_pairs(top_dt), fmt_pairs(top_ds)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "excel",
        nargs="?",
        default="aaa0769_1to1_replaceable_pairs_complementing_ChEMBL_SINGLE_PROTEIN_sweep_candidates.xlsx",
    )
    args = ap.parse_args()

    in_path = Path(args.excel)
    if not in_path.exists():
        fallback = Path("aaa0769_1to1_replaceable_pairs_complementing.xlsx")
        if fallback.exists():
            in_path = fallback
        else:
            raise SystemExit(f"Input file not found: {args.excel}")

    cache_mygene = Path("cache/mygene")
    cache_ot = Path("cache/opentargets")
    cache_mygene.mkdir(parents=True, exist_ok=True)
    cache_ot.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(in_path)
    required = ["Human_Entrez", "Human_Symbol"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise SystemExit(f"Missing required columns: {missing}")

    runlog: list[str] = []
    long_rows: list[dict[str, Any]] = []

    new_cols = {
        "resolved_ensembl_gene_id": [],
        "mapping_status": [],
        "opentargets_status": [],
        "ot_n_associated_diseases_total": [],
        "ot_top_diseases": [],
        "ot_top_datatypes": [],
        "ot_top_datasources": [],
        "disease_relevance_paragraph": [],
        "opentargets_target_url": [],
        "mapping_source_url": [],
        "subcellular_localisation": [],
        "pdb_codes": [],
        "opentargets_query_ok": [],
        "notes": [],
    }

    mygene_rl = RateLimiter(5.0)
    ot_rl = RateLimiter(3.0)

    with requests.Session() as session:
        for idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing genes"):
            symbol = str(row.get("Human_Symbol", "")).strip() or "UNKNOWN"
            notes: list[str] = []

            # defaults
            ensg = ""
            mapping_status = "ERROR"
            ot_status = "NOT_QUERIED"
            ot_count: int | None = None
            ot_top_diseases = ""
            ot_top_datatypes = ""
            ot_top_datasources = ""
            paragraph = ""
            ot_ok = False

            source_url = ""
            subcellular_localisation = ""
            pdb_codes = ""

            entrez_raw = row.get("Human_Entrez")
            try:
                if pd.isna(entrez_raw):
                    raise ValueError("Human_Entrez is null")
                entrez = int(entrez_raw)
                source_url = f"{MYGENE_BASE}/{entrez}"
                mygene_cache_file = cache_mygene / f"{entrez}.json"

                if mygene_cache_file.exists():
                    mygene_json = json.loads(mygene_cache_file.read_text())
                else:
                    resp = request_with_retry(session, "GET", source_url, rate_limiter=mygene_rl, runlog=runlog)
                    mygene_json = resp.json()
                    mygene_cache_file.write_text(json.dumps(mygene_json, ensure_ascii=False, indent=2))

                if mygene_json.get("notfound") is True:
                    mapping_status = "MYGENE_NOT_FOUND"
                    notes.append("MyGene returned notfound=true")
                else:
                    subcellular_localisation = parse_subcellular_localisation(mygene_json)
                    pdb_codes = parse_pdb_codes(mygene_json)
                    gene = parse_ensembl_gene_id(mygene_json)
                    if gene:
                        ensg = gene
                        mapping_status = "OK"
                    else:
                        mapping_status = "NO_ENSEMBL"
                        notes.append("No ENSG found under ensembl.gene")
            except Exception as exc:
                mapping_status = "ERROR"
                notes.append(f"mapping_error={exc}")
                runlog.append(f"ROW {idx} {symbol}: mapping error: {exc}")

            if mapping_status == "OK" and ensg:
                ot_cache_file = cache_ot / f"{ensg}.json"
                payload = {"query": OT_QUERY, "variables": {"ensemblId": ensg, "size": 10}}
                try:
                    if ot_cache_file.exists():
                        ot_json = json.loads(ot_cache_file.read_text())
                    else:
                        resp = request_with_retry(
                            session,
                            "POST",
                            OT_URL,
                            rate_limiter=ot_rl,
                            runlog=runlog,
                            json=payload,
                            headers={"Content-Type": "application/json"},
                        )
                        ot_json = resp.json()
                        ot_cache_file.write_text(json.dumps(ot_json, ensure_ascii=False, indent=2))

                    if ot_json.get("errors"):
                        ot_status = "OT_ERROR"
                        ot_ok = False
                        notes.append("Open Targets GraphQL errors present")
                        runlog.append(f"ROW {idx} {symbol}: OT errors={ot_json.get('errors')}")
                    else:
                        target = ((ot_json.get("data") or {}).get("target"))
                        if not target:
                            ot_status = "OT_NO_DATA"
                            paragraph, ot_top_diseases, ot_top_datatypes, ot_top_datasources = build_paragraph(symbol, [])
                        else:
                            ad = target.get("associatedDiseases") or {}
                            rows = ad.get("rows") or []
                            ot_count = ad.get("count") if isinstance(ad.get("count"), int) else None
                            ot_ok = True
                            if rows:
                                ot_status = "OK"
                                top_rows = rows[:3]
                                paragraph, ot_top_diseases, ot_top_datatypes, ot_top_datasources = build_paragraph(symbol, top_rows)
                                for r in rows:
                                    disease = r.get("disease") or {}
                                    long_rows.append(
                                        {
                                            "Human_Symbol": symbol,
                                            "Human_Entrez": int(entrez_raw),
                                            "resolved_ensembl_gene_id": ensg,
                                            "disease_id": disease.get("id", ""),
                                            "disease_name": disease.get("name", ""),
                                            "association_score": r.get("score", None),
                                            "datatypeScores_json": json.dumps(r.get("datatypeScores") or [], separators=(",", ":"), ensure_ascii=False),
                                            "datasourceScores_json": json.dumps(r.get("datasourceScores") or [], separators=(",", ":"), ensure_ascii=False),
                                        }
                                    )
                            else:
                                ot_status = "OT_NO_DATA"
                                paragraph, ot_top_diseases, ot_top_datatypes, ot_top_datasources = build_paragraph(symbol, [])
                except Exception as exc:
                    ot_status = "OT_ERROR"
                    ot_ok = False
                    notes.append(f"opentargets_error={exc}")
                    runlog.append(f"ROW {idx} {symbol}: OT error: {exc}")
            else:
                ot_status = "OT_NOT_QUERIED"
                paragraph = f"Open Targets does not report target–disease associations for {symbol} in the queried dataset."

            new_cols["resolved_ensembl_gene_id"].append(ensg)
            new_cols["mapping_status"].append(mapping_status)
            new_cols["opentargets_status"].append(ot_status)
            new_cols["ot_n_associated_diseases_total"].append(ot_count)
            new_cols["ot_top_diseases"].append(ot_top_diseases)
            new_cols["ot_top_datatypes"].append(ot_top_datatypes)
            new_cols["ot_top_datasources"].append(ot_top_datasources)
            new_cols["disease_relevance_paragraph"].append(paragraph)
            new_cols["opentargets_target_url"].append(f"https://platform.opentargets.org/target/{ensg}" if ensg else "")
            new_cols["mapping_source_url"].append(source_url)
            new_cols["subcellular_localisation"].append(subcellular_localisation)
            new_cols["pdb_codes"].append(pdb_codes)
            new_cols["opentargets_query_ok"].append(bool(ot_ok))
            new_cols["notes"].append("; ".join(notes))

    out_df = df.copy()
    for c, values in new_cols.items():
        out_df[c] = values

    out_xlsx = Path("disease_relevance_opentargets.xlsx")
    out_csv = Path("disease_relevance_opentargets.csv")
    out_long = Path("disease_relevance_opentargets_long.csv")
    out_log = Path("disease_relevance_opentargets_runlog.txt")

    out_df.to_excel(out_xlsx, index=False)
    out_df.to_csv(out_csv, index=False)
    pd.DataFrame(long_rows).to_csv(out_long, index=False)
    out_log.write_text("\n".join(runlog) + ("\n" if runlog else ""))

    total = len(out_df)
    mapped = int((out_df["mapping_status"] == "OK").sum())
    ot_success = int((out_df["opentargets_status"] == "OK").sum())
    ot_no_data = int((out_df["opentargets_status"] == "OT_NO_DATA").sum())
    errors = int(((out_df["mapping_status"] == "ERROR") | (out_df["opentargets_status"] == "OT_ERROR")).sum())

    print(f"Input file: {in_path}")
    print(f"Wrote: {out_xlsx}")
    print(f"Wrote: {out_csv}")
    print(f"Wrote: {out_long}")
    print(f"Wrote: {out_log}")
    print("--- Summary ---")
    print(f"total genes: {total}")
    print(f"mapped ENSG count: {mapped}")
    print(f"OT success count: {ot_success}")
    print(f"OT no-data count: {ot_no_data}")
    print(f"error count: {errors}")
    print("--- Preview (first 10) ---")
    preview_cols = [
        "Human_Symbol",
        "resolved_ensembl_gene_id",
        "ot_top_diseases",
        "disease_relevance_paragraph",
    ]
    print(out_df[preview_cols].head(10).to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
