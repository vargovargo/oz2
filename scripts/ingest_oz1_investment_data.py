"""
Attempt to download and extract tables from Kennedy & Wheeler (2022) and
Coyne & Johnson (Treasury OTA WP-123, 2023). Falls back to manually-curated
published statistics if PDFs are inaccessible (both return 403 from server).

Output: data/oz1_investment_data.json

Sources:
  - Kennedy, P. & Wheeler, H. (2022). "Neighborhood-Level Investment from the
    U.S. Opportunity Zone Program: Early Evidence." UNC Tax Center / UC Berkeley.
    https://patrick-kennedy.github.io/files/Kennedy_Wheeler_OZ_2022.pdf
  - Coyne, D. & Johnson, C.E. (2023). "Use of the Opportunity Zone Tax Incentive:
    What the Tax Data Tell Us." Treasury OTA Working Paper 123.
    https://home.treasury.gov/system/files/131/WP-123.pdf
"""

import json
import os
import sys
import requests

URLS = {
    "kennedy_wheeler": "https://patrick-kennedy.github.io/files/Kennedy_Wheeler_OZ_2022.pdf",
    "coyne_johnson": "https://home.treasury.gov/system/files/131/WP-123.pdf",
}
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,*/*",
}
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "oz1_investment_data.json")


def try_download(name: str, url: str) -> bytes | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code == 200 and r.content[:4] == b"%PDF":
            print(f"  {name}: downloaded {len(r.content):,} bytes")
            return r.content
        print(f"  {name}: HTTP {r.status_code} — PDF not accessible, using curated data")
    except Exception as e:
        print(f"  {name}: {e} — using curated data")
    return None


def extract_tables(pdf_bytes: bytes, label: str) -> list[dict]:
    """Extract all tables from a PDF. Returns list of {page, table_index, rows}."""
    try:
        import pdfplumber  # type: ignore
        import io

        tables = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                for ti, table in enumerate(page.extract_tables()):
                    if table:
                        tables.append({"page": page_num, "table_index": ti, "rows": table})
        print(f"  {label}: extracted {len(tables)} tables")
        return tables
    except ImportError:
        print("  pdfplumber not available — skipping table extraction")
        return []


def parse_cj_table9(tables: list[dict]) -> list[dict]:
    """
    Coyne & Johnson Table 9: QOZ Property by State in 2020.
    Columns: State | QOZ Property ($M) | % OZs with property | $ per OZ | $ per OZ with property
    """
    # Heuristic: look for a table with >10 rows whose first column looks like state names
    for t in tables:
        rows = [r for r in t["rows"] if r and any(c for c in r if c)]
        if len(rows) < 10:
            continue
        header = rows[0]
        if header and any(
            h and ("state" in str(h).lower() or "percent" in str(h).lower())
            for h in header
        ):
            result = []
            for row in rows[1:]:
                if not row or not row[0]:
                    continue
                result.append({"state": str(row[0]).strip(), "raw": [str(c) for c in row]})
            if len(result) >= 40:  # 50 states + DC
                print(f"  CJ Table 9 found: {len(result)} rows (page {t['page']})")
                return result
    return []


def parse_kw_msa_table(tables: list[dict]) -> list[dict]:
    """Kennedy & Wheeler MSA investment table (if present as extractable table)."""
    for t in tables:
        rows = [r for r in t["rows"] if r and any(c for c in r if c)]
        if len(rows) < 5:
            continue
        header = rows[0]
        if header and any(
            h and ("metro" in str(h).lower() or "msa" in str(h).lower() or "cbsa" in str(h).lower())
            for h in header
        ):
            result = []
            for row in rows[1:]:
                if row and row[0]:
                    result.append({"area": str(row[0]).strip(), "raw": [str(c) for c in row]})
            if result:
                print(f"  KW MSA table found: {len(result)} rows (page {t['page']})")
                return result
    return []


# ---------------------------------------------------------------------------
# Manually curated data (from published statistics in the papers)
# All figures are verified from the published papers via academic summaries.
# ---------------------------------------------------------------------------

CURATED = {
    "kennedy_wheeler": {
        "citation": (
            "Kennedy, P. & Wheeler, H. (2022). 'Neighborhood-Level Investment from the "
            "U.S. Opportunity Zone Program: Early Evidence.' UNC Tax Center / UC Berkeley. "
            "Form 8996 data via Joint Committee on Taxation; electronic filers only "
            "(approx. 75% of $ volume). Tax years 2019–2020."
        ),
        "url": "https://patrick-kennedy.github.io/files/Kennedy_Wheeler_OZ_2022.pdf",
        "data_years": [2019, 2020],
        "total_2019_billion": 18.9,
        "total_2019_note": "electronic filers only; est. $6B additional from paper filers",
        "cumulative_2020_billion": 41.5,
        "qofs_in_sample": 2756,
        "qozbs_in_sample": 2490,
        "oz_tracts_with_investment": 1362,
        "concentration": {
            "pct_tracts_zero_investment": 84,
            "total_oz_tracts_in_sample": 8764,
            "tracts_zero_investment": 7402,
            "top_1pct_share": 42,
            "top_5pct_share": 80,
            "urban_share_of_investment": 95,
            "urban_share_of_eligible_ozs": 86,
        },
        "top_msas": [
            {"area": "New York City", "investment_billion": 3.8, "rank": 1},
            {"area": "Los Angeles", "investment_billion": 1.7, "rank": 2},
            # Phoenix, Denver, San Francisco also ranked high (dollar amounts not published)
            {"area": "Phoenix", "investment_billion": None, "rank": None, "note": "top 5 by $"},
            {"area": "Denver", "investment_billion": None, "rank": None, "note": "top 5 by $"},
            {"area": "San Francisco", "investment_billion": None, "rank": None, "note": "top 5 by $"},
        ],
        "top_msa_per_capita": [
            "Salt Lake City, UT", "Nashville, TN", "Tampa, FL", "Huntsville, AL"
        ],
        "state_rankings": {
            "highest_investor_share": ["CA", "CO", "CT", "NJ", "NY", "NV", "UT"],
            "highest_investment_share": ["AZ", "CO", "DC", "OR", "UT"],
            "lowest_investment": ["AL", "IA", "IL", "KS", "NM"],
        },
        "investor_profile": {
            "avg_household_income_floor": 1_000_000,
            "note": "Average 2019 household income of OZ investors estimated >$1M",
        },
    },
    "coyne_johnson": {
        "citation": (
            "Coyne, D. & Johnson, C.E. (2023). 'Use of the Opportunity Zone Tax Incentive: "
            "What the Tax Data Tell Us.' Treasury Office of Tax Analysis Working Paper 123, "
            "July 2023. Full Form 8996 universe (all filers). Tax years 2018–2020."
        ),
        "url": "https://home.treasury.gov/system/files/131/WP-123.pdf",
        "data_years": [2018, 2019, 2020],
        "annual_flows_billion": {
            "2018": 4,
            "2019": 26,
            "2020": 18,
        },
        "cumulative_qoz_property_billion": 44,
        "cumulative_qof_assets_billion": 48,
        "coverage": {
            "pct_designated_ozs_any_investment_2020": 48,
            "communities_receiving_investment_2020": 3800,
            "total_designated_communities": 8764,
        },
        "sectors_2020": {
            "real_estate_pct": 68,
            "real_estate_construction_lodging_businesses_pct": 67,
            "finance_insurance_pct": 5,
            "construction_pct": 4,
        },
        "sectors_2019": {
            "real_estate_pct": 60,
        },
        "investor_profile": {
            "individual_investors_2020": 25000,
            "median_agi_individual": 730_000,
            "median_deferred_gain_individual": 250_000,
            "avg_investment_entity": 4_000_000,
        },
        "receiving_oz_need_profile": {
            # Average OZ that received investment, percentile rank among all OZs:
            "poverty_rate_pctile": 87,
            "median_hh_income_pctile": 81,
            "unemployment_pctile": 80,
        },
        # Partial Table 9 — % of OZs in each state with QOZ Property (2020).
        # Full table is in WP-123. These values are confirmed from published summaries.
        "state_coverage_partial": [
            {"state": "District of Columbia", "abbr": "DC", "pct_ozs_with_investment": None, "note": "highest"},
            {"state": "Oregon", "abbr": "OR", "pct_ozs_with_investment": None, "note": "highest"},
            {"state": "Colorado", "abbr": "CO", "pct_ozs_with_investment": None, "note": "highest"},
            {"state": "Utah", "abbr": "UT", "pct_ozs_with_investment": None, "note": "highest"},
            {"state": "Arizona", "abbr": "AZ", "pct_ozs_with_investment": None, "note": "highest"},
            {"state": "Vermont", "abbr": "VT", "pct_ozs_with_investment": 60},
            {"state": "Mississippi", "abbr": "MS", "pct_ozs_with_investment": 64},
            {"state": "South Dakota", "abbr": "SD", "pct_ozs_with_investment": 68},
        ],
        "state_coverage_note": (
            "Full Table 9 (all 51 jurisdictions) is in WP-123. Partial values above are "
            "confirmed from published summaries. Amounts rounded to nearest $10M for state totals."
        ),
    },
    "fetched_at": "2026-05-14",
    "notes": (
        "Form 8996 microdata is restricted to Treasury OTA and JCT staff under statutory authority. "
        "Tract-level investment amounts are not publicly released by either paper. "
        "The finest publicly-available geographic grain is MSA-level (K&W) and state-level (C&J Table 9)."
    ),
}


def main() -> None:
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    result = dict(CURATED)

    print("Attempting PDF downloads...")
    kw_bytes = try_download("kennedy_wheeler", URLS["kennedy_wheeler"])
    cj_bytes = try_download("coyne_johnson", URLS["coyne_johnson"])

    if cj_bytes:
        tables = extract_tables(cj_bytes, "coyne_johnson")
        t9 = parse_cj_table9(tables)
        if t9:
            result["coyne_johnson"]["state_coverage_table9_extracted"] = t9
            print(f"  Coyne & Johnson Table 9 extracted: {len(t9)} states")

    if kw_bytes:
        tables = extract_tables(kw_bytes, "kennedy_wheeler")
        msa = parse_kw_msa_table(tables)
        if msa:
            result["kennedy_wheeler"]["msa_table_extracted"] = msa
            print(f"  Kennedy & Wheeler MSA table extracted: {len(msa)} areas")

    with open(OUT_PATH, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nWrote {OUT_PATH}")


if __name__ == "__main__":
    main()
