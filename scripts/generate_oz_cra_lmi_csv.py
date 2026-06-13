"""
Generate data/oz_cra_lmi_tracts.csv — all OZ 2.0-eligible tracts with CRA designation.

Two-track definition (FFIEC Census Flat File, 2025 exam year):
  Track 1 — LMI: income_level in ('L', 'M')
  Track 2 — Distressed/Underserved: is_distressed_underserved == True (non-LMI middle-income)

Output columns:
  geoid, state_fips, state_name, county_fips, county_name,
  is_rural_qrof, income_level, cra_track, cra_label
"""

from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data"

elig = pd.read_parquet(DATA_DIR / "eligible_tracts.parquet")
cra  = pd.read_parquet(DATA_DIR / "cra_lmi_overlap.parquet")

merged = elig[["geoid", "state_fips", "state_name", "county_fips", "county_name", "is_rural"]].merge(
    cra[["geoid", "income_level", "is_distressed_underserved", "is_cra_lmi"]],
    on="geoid", how="inner"
)

merged = merged[merged["is_cra_lmi"] == True].copy()

INCOME_LABELS = {"L": "Low Income", "M": "Moderate Income", "Middle": "Middle Income (D/U)"}

def _track(row):
    if row["income_level"] in ("L", "M"):
        return 1
    return 2

def _label(row):
    if row["income_level"] == "L":
        return "Low Income"
    if row["income_level"] == "M":
        return "Moderate Income"
    return "Middle Income — Distressed/Underserved"

merged["cra_track"] = merged.apply(_track, axis=1)
merged["cra_label"] = merged.apply(_label, axis=1)

out = merged.rename(columns={"is_rural": "is_rural_qrof"})[[
    "geoid", "state_fips", "state_name", "county_fips", "county_name",
    "is_rural_qrof", "income_level", "cra_track", "cra_label"
]].sort_values("geoid").reset_index(drop=True)

out.to_csv(DATA_DIR / "oz_cra_lmi_tracts.csv", index=False)

track1 = (out["cra_track"] == 1).sum()
track2 = (out["cra_track"] == 2).sum()
print(f"Written: {len(out):,} CRA-eligible OZ tracts")
print(f"  Track 1 (LMI):                   {track1:,}")
print(f"    Low Income:                     {(out['income_level']=='L').sum():,}")
print(f"    Moderate Income:                {(out['income_level']=='M').sum():,}")
print(f"  Track 2 (D/U non-LMI):           {track2:,}")
print(f"  Rural/QROF:                       {out['is_rural_qrof'].sum():,}")
