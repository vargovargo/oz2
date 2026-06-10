# CRA Eligibility Overlap Analysis — OZ 2.0 Eligible Tracts

**Branch:** `claude/cra-eligibility-overlap-2srcf8`
**Date:** 2026-06-10
**Data source:** FFIEC Census Flat File, 2025 exam year (`CensusFlatFile2025.csv`)
**Tract universe:** 25,332 IRS Rev. Proc. 2026-14 eligible tracts

---

## Finding

**74.9% of OZ 2.0-eligible tracts carry CRA designation** — 18,968 of 25,332.

This corrects an earlier single-track estimate of 68.6% (LMI only). The full two-track CRA definition adds 1,590 tracts that are not LMI but are officially designated distressed or underserved by FFIEC.

---

## Two-Track CRA Eligibility

The FFIEC defines CRA-eligible census tracts on two independent tracks:

**Track 1 — Low- or Moderate-Income (LMI)**
A tract qualifies if its median family income (MFI) is below 80% of the area MFI, where "area" means the MSA/MD for metro tracts, or the statewide non-MSA figure for rural tracts.
- Low Income (LMI-L): tract MFI < 50% of area MFI
- Moderate Income (LMI-M): tract MFI 50–80% of area MFI

**Track 2 — Distressed or Underserved (non-metropolitan middle-income tracts only)**
A non-metro tract with MFI of 80–120% of the statewide non-metro median qualifies if it meets **at least one** of:
1. Unemployment rate ≥ 1.5× the national average
2. Poverty rate ≥ 20%
3. Population loss ≥ 10% between the 2010 and 2020 Census, or net migration loss ≥ 5%
4. USDA urban influence code of 7, 10, 11, or 12 (very remote geography)

Track 2 is expressly for rural middle-income communities that are distressed or isolated but don't meet the income threshold. The FFIEC publishes this designation annually; the 2025 exam-year file includes a one-year lag period, so tracts designated in either the current or prior year are flagged.

---

## National Summary

| Metric | Tracts | % of OZ universe |
|--------|--------|-----------------|
| OZ-eligible (total) | 25,332 | 100% |
| Track 1 — LMI (L+M) | 17,378 | 68.6% |
| — Low Income (L) | 5,260 | 20.8% |
| — Moderate Income (M) | 12,118 | 47.8% |
| Track 2 — D/U only (non-LMI) | 1,590 | 6.3% |
| **CRA-eligible (any track)** | **18,968** | **74.9%** |
| Middle income, not D/U | 5,530 | 21.8% |
| Upper income | 798 | 3.1% |
| Not classified (zero MFI) | 834 | 3.3% |

**Track 2 adds meaningful coverage.** The 1,590 Track 2 tracts represent rural non-metro communities that are economically distressed despite sitting just above the LMI threshold. Without Track 2, bank capital seeking CRA credit would overlook these tracts entirely.

**Rural vs. urban split.** Despite common assumptions that OZ tracts are primarily urban, 8,334 of 25,332 eligible tracts (32.9%) are IRS-flagged rural (Rev. Proc. 2026-14 rural designation). Rural CRA eligibility rate is 69.7% vs. 77.4% for non-rural tracts. The lower rural rate reflects the larger share of rural tracts that are middle income relative to the non-metro median — still not LMI — but Track 2 captures a meaningful subset of those.

---

## State-Level CRA Counts

States with the highest absolute CRA-eligible OZ tract counts (ordered by CRA count):

| State | OZ eligible | CRA eligible | CRA % | Track 2 only |
|-------|-------------|--------------|-------|--------------|
| California | 2,469 | 1,944 | 78.7% | 24 |
| Texas | 2,420 | 1,836 | 75.9% | 108 |
| New York | 1,702 | 1,186 | 69.7% | 17 |
| Florida | 1,360 | 1,010 | 74.3% | 38 |
| Ohio | 1,032 | 805 | 78.0% | 23 |
| Illinois | 950 | 804 | 84.6% | 63 |
| Georgia | 942 | 710 | 75.4% | 104 |
| Michigan | 856 | 645 | 75.4% | 42 |
| Pennsylvania | 866 | 617 | 71.2% | 8 |
| North Carolina | 807 | 597 | 74.0% | 73 |
| Virginia | 607 | 472 | 77.8% | 90 |
| Louisiana | 620 | 431 | 69.5% | 60 |
| New Jersey | 516 | 428 | 82.9% | 0 |
| Missouri | 523 | 402 | 76.9% | 63 |
| Kentucky | 545 | 402 | 73.8% | 101 |

States with notable Track 2 contributions (rural distressed/underserved adding ≥ 60 tracts):
- **Texas:** 108 Track 2 tracts — the most of any state, reflecting its large number of remote rural counties above the income threshold
- **Kentucky:** 101 Track 2 tracts
- **Georgia:** 104 Track 2 tracts
- **Virginia:** 90 Track 2 tracts
- **North Carolina:** 73 Track 2 tracts

Territories (Guam, USVI, American Samoa, CNMI) show very high CRA rates (78–100%) driven mostly by Track 2 — their tracts often have middle-income designations relative to non-metro medians but meet unemployment or poverty thresholds.

---

## Implication for Capital Stacking

**The two-track definition expands the bankable deal universe.** A rural middle-income tract that has lost population or has high unemployment is now in-scope for CRA community-development credit, even though its MFI ratio looks "healthy" relative to the non-metro median. Local planners working in these communities should not assume that a middle-income income designation removes CRA as a capital-stack ingredient — they should check the FFIEC's current designation directly.

**Practical check:** The FFIEC tract search tool at [ffiec.cfpb.gov/tools/tract-search](https://ffiec.cfpb.gov/tools/tract-search) returns the current income designation and distressed/underserved flag for any GEOID. Use this to confirm eligibility before structuring a CRA-linked deal.

---

## Data and Methodology Notes

- **Source file:** `data/raw/CensusFlatFile2025.csv` — FFIEC Census Flat File, 2025 exam year (87,276 rows, no header, positional column format). Data dictionary: `data/raw/FFIEC_Census_File_Definitions_10JULY25.xlsx`.
- **Income indicator:** column 14 (0-indexed), values 1=Low, 2=Moderate, 3=Middle, 4=Upper, 0=N/A.
- **D/U flag:** column 21, `X` = meets at least one current or prior-year distressed/underserved criterion (includes FFIEC one-year lag period).
- **Script:** `scripts/ingest_cra_lmi.py` — prefers the flat CSV over the XLSX (XLSX has income levels only, no D/U column). Output: `data/cra_lmi_overlap.parquet`.
- **OZ tract universe:** `data/eligible_tracts.parquet`, 25,332 tracts from IRS Rev. Proc. 2026-14.
- **Note on earlier 83–84% estimate:** The earlier estimate attributed to another analysis used a different or looser definition of CRA eligibility and does not match the FFIEC two-track definition. 74.9% is the figure derived from the FFIEC's own classification.
