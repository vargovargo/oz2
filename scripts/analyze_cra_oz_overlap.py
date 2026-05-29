"""
Analyze overlap between OZ 2.0-eligible tracts and CRA LMI, rural, tribal,
and persistent poverty designations. Outputs summary stats and a two-panel
figure saved to docs/figures/oz_cra_overlap.png.

Usage: python3 scripts/analyze_cra_oz_overlap.py
"""

from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

FIGURES_DIR = Path("docs/figures")
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
tracts = pd.read_parquet("data/eligible_tracts.parquet")
cra = pd.read_parquet("data/cra_lmi_overlap.parquet")
tribal = pd.read_parquet("data/tribal_overlap.parquet")
pp = pd.read_parquet("data/persistent_poverty.parquet")

df = (
    tracts
    .merge(cra[["geoid", "income_level", "is_cra_lmi"]], on="geoid", how="left")
    .merge(tribal[["geoid", "is_tribal_overlap"]], on="geoid", how="left")
    .merge(pp[["county_fips", "is_persistent_poverty"]], on="county_fips", how="left")
)
df["is_cra_lmi"] = df["is_cra_lmi"].fillna(False)
df["is_tribal_overlap"] = df["is_tribal_overlap"].fillna(False)
df["is_persistent_poverty"] = df["is_persistent_poverty"].fillna(False)

n = len(df)

# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------
n_cra = df["is_cra_lmi"].sum()
n_low = (df["income_level"] == "L").sum()
n_mod = (df["income_level"] == "M").sum()
n_rural = df["is_rural"].sum()
n_tribal = df["is_tribal_overlap"].sum()
n_pp = df["is_persistent_poverty"].sum()

n_cra_rural = (df["is_cra_lmi"] & df["is_rural"]).sum()
n_cra_tribal = (df["is_cra_lmi"] & df["is_tribal_overlap"]).sum()
n_cra_rural_tribal = (df["is_cra_lmi"] & df["is_rural"] & df["is_tribal_overlap"]).sum()

urban = df[~df["is_rural"]]
rural = df[df["is_rural"]]
pct_urban_cra = urban["is_cra_lmi"].mean() * 100
pct_rural_cra = rural["is_cra_lmi"].mean() * 100

print("=" * 60)
print("OZ 2.0 × CRA ELIGIBILITY OVERLAP — SUMMARY STATISTICS")
print("=" * 60)
print(f"Total OZ 2.0-eligible tracts:           {n:>7,}")
print(f"CRA LMI (L or M):                       {n_cra:>7,}  ({n_cra/n*100:.1f}%)")
print(f"  — Low income (<50% area MFI):          {n_low:>7,}  ({n_low/n*100:.1f}%)")
print(f"  — Moderate income (50–80% area MFI):   {n_mod:>7,}  ({n_mod/n*100:.1f}%)")
print(f"Rural-eligible (QROF):                  {n_rural:>7,}  ({n_rural/n*100:.1f}%)")
print(f"Tribal area overlap:                    {n_tribal:>7,}  ({n_tribal/n*100:.1f}%)")
print(f"Persistent poverty counties:            {n_pp:>7,}  ({n_pp/n*100:.1f}%)")
print()
print(f"CRA LMI + Rural:                        {n_cra_rural:>7,}  ({n_cra_rural/n*100:.1f}%)")
print(f"CRA LMI + Tribal:                       {n_cra_tribal:>7,}  ({n_cra_tribal/n*100:.1f}%)")
print(f"CRA LMI + Rural + Tribal (triple):      {n_cra_rural_tribal:>7,}  ({n_cra_rural_tribal/n*100:.1f}%)")
print()
print(f"Urban OZ tracts that are CRA LMI:       {pct_urban_cra:.1f}%")
print(f"Rural OZ tracts that are CRA LMI:       {pct_rural_cra:.1f}%")

# ---------------------------------------------------------------------------
# State-level table (51 states + DC + territories)
# ---------------------------------------------------------------------------
def state_cra_rural(grp):
    return (grp["is_cra_lmi"] & grp["is_rural"]).sum()

by_state = df.groupby("state_name").agg(
    total=("geoid", "count"),
    cra_lmi=("is_cra_lmi", "sum"),
    rural=("is_rural", "sum"),
    tribal=("is_tribal_overlap", "sum"),
    persistent_poverty=("is_persistent_poverty", "sum"),
).reset_index()

cra_rural_counts = (
    df[df["is_cra_lmi"] & df["is_rural"]]
    .groupby("state_name")["geoid"]
    .count()
    .rename("cra_lmi_rural")
)
by_state = by_state.merge(cra_rural_counts, on="state_name", how="left")
by_state["cra_lmi_rural"] = by_state["cra_lmi_rural"].fillna(0).astype(int)
by_state["cra_pct"] = (by_state["cra_lmi"] / by_state["total"] * 100).round(1)
by_state = by_state.sort_values("total", ascending=False).reset_index(drop=True)

print("\n" + "=" * 60)
print("STATE-LEVEL TABLE (sorted by total OZ tracts)")
print("=" * 60)
print(
    by_state[["state_name", "total", "cra_lmi", "cra_pct", "rural",
               "cra_lmi_rural", "tribal", "persistent_poverty"]].to_string(index=False)
)

# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------

# Segment counts for Panel A
seg_cra_urban = int((df["is_cra_lmi"] & ~df["is_rural"] & ~df["is_tribal_overlap"]).sum())
seg_cra_rural = int((df["is_cra_lmi"] & df["is_rural"] & ~df["is_tribal_overlap"]).sum())
seg_cra_tribal = int((df["is_cra_lmi"] & df["is_tribal_overlap"]).sum())  # rural+urban
seg_non_cra_rural = int((~df["is_cra_lmi"] & df["is_rural"]).sum())
seg_non_cra_urban = int((~df["is_cra_lmi"] & ~df["is_rural"]).sum())

# Palette — blues for CRA, muted reds/tans for non-CRA
C_CRA_URBAN  = "#2E6DA4"   # deep blue
C_CRA_RURAL  = "#71A8D1"   # mid blue
C_CRA_TRIBAL = "#A8C8E8"   # light blue
C_NON_RURAL  = "#D97F5A"   # rust / non-CRA rural
C_NON_URBAN  = "#E8C4AD"   # tan / non-CRA urban

fig, axes = plt.subplots(1, 2, figsize=(13, 5),
                          gridspec_kw={"width_ratios": [2, 1]})
fig.patch.set_facecolor("white")

# ---- Panel A: composition bar ----
ax = axes[0]
ax.set_facecolor("white")

segs = [
    (seg_cra_urban,  C_CRA_URBAN,  f"CRA LMI, urban\n{seg_cra_urban:,}  ({seg_cra_urban/n*100:.0f}%)"),
    (seg_cra_rural,  C_CRA_RURAL,  f"CRA LMI, rural/QROF\n{seg_cra_rural:,}  ({seg_cra_rural/n*100:.0f}%)"),
    (seg_cra_tribal, C_CRA_TRIBAL, f"CRA LMI, tribal\n{seg_cra_tribal:,}  ({seg_cra_tribal/n*100:.0f}%)"),
    (seg_non_cra_rural, C_NON_RURAL, f"Not CRA LMI, rural/QROF\n{seg_non_cra_rural:,}  ({seg_non_cra_rural/n*100:.0f}%)"),
    (seg_non_cra_urban, C_NON_URBAN, f"Not CRA LMI, urban\n{seg_non_cra_urban:,}  ({seg_non_cra_urban/n*100:.0f}%)"),
]

left = 0
bar_y = 0.5
bar_h = 0.35
for count, color, label in segs:
    ax.barh(bar_y, count, left=left, height=bar_h, color=color, edgecolor="white", linewidth=0.8)
    if count / n > 0.06:
        ax.text(left + count / 2, bar_y, f"{count/n*100:.0f}%",
                ha="center", va="center", fontsize=9, color="white", fontweight="bold")
    left += count

legend_patches = [mpatches.Patch(color=c, label=l) for _, c, l in segs]
ax.legend(handles=legend_patches, loc="lower center", bbox_to_anchor=(0.5, -0.45),
          ncol=2, fontsize=8.5, frameon=False)

ax.set_xlim(0, n)
ax.set_ylim(0, 1)
ax.set_yticks([])
ax.set_xlabel("Number of OZ 2.0-eligible census tracts", fontsize=9)
ax.set_title(f"A.  All {n:,} OZ 2.0-eligible tracts by CRA LMI and rural/tribal status",
             fontsize=10, fontweight="bold", loc="left")
ax.spines[["top", "right", "left"]].set_visible(False)
ax.tick_params(axis="x", labelsize=8)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x):,}"))

# ---- Panel B: urban vs rural CRA share ----
ax2 = axes[1]
ax2.set_facecolor("white")

categories = ["Urban OZ\n(non-QROF)", "Rural OZ\n(QROF-eligible)"]
cra_vals = [
    urban["is_cra_lmi"].sum(),
    rural["is_cra_lmi"].sum(),
]
non_cra_vals = [
    (~urban["is_cra_lmi"]).sum(),
    (~rural["is_cra_lmi"]).sum(),
]
totals = [len(urban), len(rural)]
x = np.arange(len(categories))
w = 0.5

bars_cra = ax2.bar(x, cra_vals, width=w, color=C_CRA_URBAN, label="CRA LMI")
bars_non = ax2.bar(x, non_cra_vals, width=w, bottom=cra_vals, color=C_NON_RURAL, label="Not CRA LMI")

for i, (cv, tot) in enumerate(zip(cra_vals, totals)):
    pct = cv / tot * 100
    ax2.text(i, cv / 2, f"{pct:.0f}%", ha="center", va="center",
             fontsize=11, fontweight="bold", color="white")
    non_cv = tot - cv
    ax2.text(i, cv + non_cv / 2, f"{(non_cv/tot*100):.0f}%", ha="center", va="center",
             fontsize=11, fontweight="bold", color="white")

ax2.set_xticks(x)
ax2.set_xticklabels(categories, fontsize=9)
ax2.set_ylabel("Number of tracts", fontsize=9)
ax2.set_title("B.  CRA LMI share:\nurban vs. rural OZ tracts", fontsize=10,
              fontweight="bold", loc="left")
ax2.legend(fontsize=8.5, frameon=False, loc="upper right")
ax2.spines[["top", "right"]].set_visible(False)
ax2.tick_params(axis="y", labelsize=8)
ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x):,}"))

for i, (cv, tot) in enumerate(zip(cra_vals, totals)):
    ax2.text(i, tot + 150, f"n={tot:,}", ha="center", va="bottom", fontsize=7.5, color="#555")

plt.tight_layout(rect=[0, 0, 1, 1])
plt.subplots_adjust(bottom=0.22, wspace=0.35)

out = FIGURES_DIR / "oz_cra_overlap.png"
plt.savefig(out, dpi=180, bbox_inches="tight", facecolor="white")
print(f"\nFigure saved to {out}")
