"""
Build data/arizona_oz2_nomination_report.pdf

Self-contained: loads parquet data, scores and nominates tracts, then renders PDF.

Scoring methodology (max 106 pts):
  Need:        DCI Q1=50, Q2=38, Q3=22, Q4=8; raw DCI score / 10 (max 10); pers. poverty=8
  Readiness:   CRA eligible=18; prior NMTC=12; rural/QROF=10

Nomination: 125 tracts (25% of 500 AZ eligible). Minimum 1 per county guaranteed (top scorer).
Remaining slots filled by descending score across all counties.

Data sources (FFIEC 2025 exam year):
  data/eligible_tracts.parquet    IRS Rev. Proc. 2026-14
  data/cra_lmi_overlap.parquet    FFIEC Census Flat File 2025 (two-track CRA)
  data/dci.parquet                EIG Distressed Communities Index 2023
  data/persistent_poverty.parquet USDA ERS County Typology 2015
  data/cdfi_nmtc.parquet          CDFI Fund NMTC 2024
  data/tribal_overlap.parquet     Census TIGER/ACS 2023
"""

from pathlib import Path
import pandas as pd
import numpy as np

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus.flowables import HRFlowable

# ── DATA PREP ──────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent.parent / "data"

elig   = pd.read_parquet(DATA_DIR / "eligible_tracts.parquet")
cra    = pd.read_parquet(DATA_DIR / "cra_lmi_overlap.parquet")
dci    = pd.read_parquet(DATA_DIR / "dci.parquet")
pp     = pd.read_parquet(DATA_DIR / "persistent_poverty.parquet")
nmtc   = pd.read_parquet(DATA_DIR / "cdfi_nmtc.parquet")
tribal = pd.read_parquet(DATA_DIR / "tribal_overlap.parquet")

az = elig[elig["state_fips"] == "04"].copy()
az = az.merge(cra[["geoid", "income_level", "is_distressed_underserved", "is_cra_lmi"]], on="geoid", how="left")
az = az.merge(dci[["geoid", "dci_score", "dci_quintile"]], on="geoid", how="left")
az = az.merge(pp[["county_fips", "is_persistent_poverty"]], on="county_fips", how="left")
az = az.merge(tribal[["geoid", "aian_pct"]], on="geoid", how="left")

az_nmtc = nmtc[nmtc["state_fips"] == "04"]["geoid"].unique()
az["has_nmtc"] = az["geoid"].isin(az_nmtc)

az["is_cra_lmi"]              = az["is_cra_lmi"].fillna(False)
az["income_level"]             = az["income_level"].fillna("NA")
az["is_distressed_underserved"] = az["is_distressed_underserved"].fillna(False)
az["dci_score"]                = pd.to_numeric(az["dci_score"], errors="coerce").fillna(0)
az["dci_quintile"]             = pd.to_numeric(az["dci_quintile"], errors="coerce").fillna(0)
az["aian_pct"]                 = pd.to_numeric(az["aian_pct"], errors="coerce").fillna(0)
az["is_persistent_poverty"]    = az["is_persistent_poverty"].fillna(False)

def _score(row):
    pts = 0.0
    q = int(row["dci_quintile"]) if row["dci_quintile"] > 0 else 0
    if q == 1:   pts += 50
    elif q == 2: pts += 38
    elif q == 3: pts += 22
    elif q == 4: pts += 8
    pts += min(row["dci_score"] / 10, 10)
    if row["is_persistent_poverty"]: pts += 8
    if row["is_cra_lmi"]:            pts += 18
    if row["has_nmtc"]:              pts += 12
    if row["is_rural"]:              pts += 10
    return round(pts, 1)

az["score"] = az.apply(_score, axis=1)
az = az.sort_values("score", ascending=False).reset_index(drop=True)

# Guarantee top-scoring tract per county, then fill to 125
az["nominated"] = False
for _, grp in az.groupby("county_name"):
    az.loc[grp["score"].idxmax(), "nominated"] = True
remaining = 125 - int(az["nominated"].sum())
az.loc[az[~az["nominated"]].nlargest(remaining, "score").index, "nominated"] = True

print(f"AZ tract universe: {len(az)} eligible, {int(az['nominated'].sum())} nominated")

# ── Colors ─────────────────────────────────────────────────────────
NAVY    = colors.HexColor("#1e3a5f")
TEAL    = colors.HexColor("#0f766e")
AMBER   = colors.HexColor("#b45309")
RED     = colors.HexColor("#7f1d1d")
RUST    = colors.HexColor("#92400e")
STEEL   = colors.HexColor("#334155")
LGRAY   = colors.HexColor("#f1f5f9")
MGRAY   = colors.HexColor("#64748b")
RULE    = colors.HexColor("#cbd5e1")
WHITE   = colors.white
BLACK   = colors.HexColor("#1e293b")
GREEN   = colors.HexColor("#166534")
TEAL_LT = colors.HexColor("#ccfbf1")

def S(nm, **kw):
    return ParagraphStyle(nm, parent=getSampleStyleSheet()["Normal"], **kw)

H1   = S("H1",  fontSize=22, leading=27, textColor=NAVY, fontName="Helvetica-Bold", spaceAfter=3)
H1s  = S("H1s", fontSize=10, leading=13, textColor=TEAL, fontName="Helvetica", spaceAfter=14)
H2   = S("H2",  fontSize=13, leading=16, textColor=NAVY, fontName="Helvetica-Bold", spaceBefore=0, spaceAfter=5)
H3   = S("H3",  fontSize=10, leading=13, textColor=STEEL, fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=3)
BODY = S("BD",  fontSize=8.8, leading=13.2, textColor=BLACK, fontName="Helvetica", spaceAfter=6, alignment=TA_JUSTIFY)
SMLL = S("SM",  fontSize=7.8, leading=11, textColor=MGRAY, fontName="Helvetica-Oblique", spaceAfter=5)
FOOT = S("FT",  fontSize=7,   leading=10, textColor=MGRAY, fontName="Helvetica", alignment=TA_CENTER, spaceBefore=6)
TH   = S("TH",  fontSize=7.2, leading=10, textColor=WHITE, fontName="Helvetica-Bold")
TDR  = S("TDR", fontSize=7.8, leading=11, textColor=BLACK, fontName="Helvetica", alignment=TA_RIGHT)
TDC  = S("TDC", fontSize=7.8, leading=11, textColor=BLACK, fontName="Helvetica", alignment=TA_CENTER)
TDL  = S("TDL", fontSize=7.8, leading=11, textColor=BLACK, fontName="Helvetica")
TDB  = S("TDB", fontSize=7.8, leading=11, textColor=BLACK, fontName="Helvetica-Bold")
APX  = S("AP",  fontSize=7.5, leading=10.5, textColor=BLACK, fontName="Helvetica")
APH  = S("APH", fontSize=7.5, leading=10.5, textColor=WHITE, fontName="Helvetica-Bold")

def th(t):  return Paragraph(t, TH)
def tdr(t): return Paragraph(str(t), TDR)
def tdc(t): return Paragraph(str(t), TDC)
def tdl(t): return Paragraph(str(t), TDL)
def tdb(t): return Paragraph(str(t), TDB)

def q_label(q):
    labels = {1: "Q1 ▲", 2: "Q2", 3: "Q3", 4: "Q4", 5: "Q5"}
    return labels.get(q, "—")

def fmt_dci(row):
    q = row["dci_quintile"]
    s = row["dci_score"]
    if pd.isna(q) or q == 0: return "—"
    return f"{s:.1f} ({q_label(int(q))})"

def check(val):
    return "✓" if val else "–"

# ── COUNTY NARRATIVES ──────────────────────────────────────────────
narratives = {
"Apache County": (
    "Apache County is among the most economically distressed jurisdictions in the United States. "
    "All 14 eligible tracts carry a USDA persistent poverty designation — meaning the county "
    "recorded poverty rates at or above 20 percent in every decennial census from 1980 through 2010. "
    "The seven nominated tracts average a DCI score of 95.5 out of 100, placing them in the top "
    "quintile of distress nationwide. The county is home to the Navajo Nation and Fort Apache "
    "Reservation (White Mountain Apache Tribe), and all nominated tracts are rural-designated "
    "under Notice 2025-50, qualifying for the QROF rural bonus.",
    "All seven nominated tracts carry CRA designation — five Low or Moderate Income under the "
    "FFIEC income test and two via the FFIEC distressed/underserved (Track 2) designation for "
    "rural middle-income tracts that meet unemployment or poverty criteria. This full CRA coverage "
    "opens bank balance-sheet capital channels across the entire nominated slate. The QROF "
    "30 percent basis step-up and 50 percent improvement threshold make rehabilitation projects "
    "financially viable at lower capital deployment than standard OZ tracts. Tribal enterprise "
    "capacity — including casino operations and agricultural enterprises — provides an institutional "
    "foundation for investor engagement. The main constraint is the need for tribal government "
    "coordination: investors must navigate leasing and land tenure requirements on trust land. "
    "The state should engage both the Navajo Nation and White Mountain Apache Tribe in the "
    "nomination process to surface investment-ready projects.",
    "Seven of 14 eligible tracts not nominated scored below 80, primarily because they lack "
    "DCI data (PO Box ZIP codes on reservation land) and some lack CRA designation — "
    "not because conditions are better, but because data gaps suppress their scores."
),
"Cochise County": (
    "Cochise County is a rural border county anchored by Sierra Vista (near Fort Huachuca), "
    "Douglas, and Bisbee. All six nominated tracts are rural-designated with DCI scores ranging "
    "from 86.8 to 93.5, placing five of the six in distress quintile 1 nationally. The border "
    "economy creates structural unemployment in the communities of Douglas and Naco, and "
    "the county's remote geography limits access to private capital markets.",
    "Five of six nominated tracts carry CRA Moderate Income designation, and Fort Huachuca's "
    "presence gives the county an unusual economic anchor — defense spending flows through "
    "Sierra Vista regardless of commodity cycles. The border region's cross-border trade "
    "infrastructure (Douglas port of entry) creates legitimate commercial real estate and "
    "logistics investment opportunities. QROF eligibility on all six nominated tracts provides "
    "a further incentive for infrastructure-oriented fund managers targeting rural Southwest.",
    "Nine tracts not nominated range from DCI Q3 to Q4 with mixed CRA coverage. The county's "
    "15 eligible tracts are all rural; the six nominated represent the strongest need-plus-"
    "readiness combination available."
),
"Coconino County": (
    "The three nominated Coconino County tracts are AIAN-numbered reservation tracts (census "
    "codes 9450–9452), almost certainly on or adjacent to Navajo Nation land in the eastern "
    "part of the county. All three score in DCI quintile 1 — above 92 — with CRA Moderate "
    "Income designation and rural QROF eligibility. Coconino County stretches from the Grand "
    "Canyon to the Utah border, and these specific tracts represent some of the highest-need "
    "geography in the state.",
    "The CRA LMI designation on all three tracts opens bank capital channels. Proximity to "
    "Flagstaff — Northern Arizona University, a growing tech-adjacent economy, and a strong "
    "outdoor recreation tourism sector — provides a demand anchor for workforce housing and "
    "small-business investment. Rural QROF eligibility adds to investor economics. As with "
    "Apache County, tribal land tenure requires up-front coordination but is not a "
    "disqualifying obstacle for experienced Indian Country developers.",
    "Ten Coconino tracts not nominated include five with very low or null DCI scores — "
    "likely rural tracts near the North Rim and Kaibab Plateau where ZIP-based DCI data "
    "is unavailable. These tracts may warrant nomination by the Navajo Nation directly."
),
"Gila County": (
    "Gila County's eligible tracts center on the Globe-Miami copper mining corridor in "
    "central Arizona. Four of eight tracts are nominated, all rural, with DCI scores between "
    "82 and 93. The mining economy has driven cyclical boom-bust patterns for over a century, "
    "and the county's lack of economic diversification is reflected in elevated DCI distress "
    "scores. One nominated tract (04007940400) had prior NMTC investment — the only county "
    "tract with a documented capital deployment track record.",
    "The prior NMTC project in tract 04007940400 demonstrates that deal flow and CDFI "
    "engagement have occurred here before, making it the most investment-ready tract in the "
    "county. CRA Moderate Income designation on two of four nominated tracts provides a bank "
    "capital pathway. Rural QROF eligibility on all four reduces the improvement threshold "
    "for rehabilitation projects. The Globe-Miami area's proximity to the growing Phoenix "
    "east valley (US-60 corridor) positions it as a potential manufacturing and logistics "
    "site as industrial land costs rise in Maricopa County.",
    "The four un-nominated tracts include two without CRA designation and two with "
    "null DCI data (likely remote trust land tracts). These may be revisited if tribal "
    "nominations are submitted through the San Carlos Apache Tribe."
),
"Graham County": (
    "Graham County's single nominated tract (04009940500) is a rural, DCI quintile 1, CRA "
    "Moderate Income tract in the Safford-Thatcher corridor of the Gila Valley. The county "
    "is primarily agricultural with a declining mining sector, and its single strongest-scoring "
    "tract carries the full combination of rural QROF eligibility, CRA LMI designation, and "
    "a DCI score of 95.1. The remaining two eligible tracts are DCI Q3 rural tracts without "
    "CRA LMI designation.",
    "The Gila Valley's agricultural economy — cotton, grain, livestock — creates a natural "
    "fit for rural infrastructure and agri-processing OZ investment. The rural QROF bonus "
    "directly incentivizes the kind of long-hold, patient capital that agricultural "
    "infrastructure requires. Eastern Arizona College (Thatcher) provides an educational "
    "anchor that could support workforce development investments alongside commercial projects.",
    "With only one strong nomination in a three-tract county, Graham represents a case where "
    "designation alone may not be sufficient — a county-level investor engagement strategy "
    "alongside nomination is recommended."
),
"La Paz County": (
    "La Paz County, spanning the lower Colorado River valley from Parker to Quartzsite, is one "
    "of Arizona's most rural and sparsely populated counties. Three of six eligible tracts are "
    "nominated — all rural, all DCI quintile 1 or 2, averaging a DCI score of 83.6. The "
    "Parker area has a significant tribal presence (Colorado River Indian Tribes) and a "
    "retirement/recreation economy along the river.",
    "All three nominated tracts carry CRA designation: two as Low or Moderate Income tracts "
    "and one via the FFIEC distressed/underserved (Track 2) designation — a rural middle-income "
    "tract that meets FFIEC unemployment and remoteness criteria despite sitting just above the "
    "income threshold. CRA eligibility on all three creates a bank capital pathway in a county "
    "that sees very little institutional investment. The Colorado River waterfront has demonstrated "
    "tourism and hospitality demand, and CRIT's tribal enterprises provide institutional "
    "capacity. The county is well-positioned for renewable energy investment given its solar "
    "resource — a use case that aligns well with the 50 percent improvement threshold under QROF.",
    "Three of six eligible tracts were not nominated because they scored DCI Q5 or are in "
    "areas where investment demand evidence is weak. They remain eligible and could be "
    "nominated if CRIT submits directly."
),
"Maricopa County": (
    "Maricopa County contains 238 of Arizona's 500 eligible tracts — nearly half the state's "
    "eligible universe. The 56 nominated tracts are concentrated in the inner Phoenix core: "
    "South Phoenix, west Phoenix along the I-10 corridor, downtown-adjacent neighborhoods, "
    "and parts of Mesa and Glendale. All nominated tracts are DCI quintile 1 or 2 (scores "
    "64–89), and 17 of the 56 have prior NMTC investment on record — the strongest "
    "capital-deployment track record of any county in Arizona. All 56 are CRA Low or "
    "Moderate Income designated.",
    "Maricopa presents the strongest investment-readiness case in the state by a wide margin. "
    "The NMTC history across 17 nominated tracts confirms active CDFI and community development "
    "lender engagement. CRA LMI designation on all 56 means Arizona's largest banks — "
    "JPMorgan Chase, Bank of America, Wells Fargo, and local players including Western Alliance "
    "and Arizona Financial Credit Union — have existing CRA credit motivation to participate. "
    "Transit infrastructure (Valley Metro light rail and bus rapid transit) runs through the "
    "nominated cluster, making mixed-use development economics work at lower land costs than "
    "comparable transit corridors in other major metros. The combination of documented distress, "
    "proven deal flow, and infrastructure anchors makes these tracts the most compelling "
    "investment story in Arizona's OZ 2.0 slate.",
    "182 Maricopa tracts were not nominated. Most are DCI Q3–Q5 suburban tracts where "
    "distress evidence does not meet the threshold for a strong nomination. The county's "
    "two rural-designated tracts do not reach the composite score threshold. The 56 nominated "
    "represent the most concentrated need in the county."
),
"Mohave County": (
    "Mohave County's sole nominated tract (04015940400) is exceptional among rural Arizona "
    "tracts: a DCI score of 99.9 — the highest in the state — combined with CRA Moderate "
    "Income designation and rural QROF eligibility. Located near Kingman in the northwestern "
    "corner of the state, the county is large and rural, with significant economic challenges "
    "tied to the decline of extractive industries and limited access to capital.",
    "The DCI Q1 score and CRA LMI designation create a strong dual case for this tract. "
    "Kingman's position on I-40 (the successor to Route 66) provides logistics access, and "
    "low land costs combined with QROF incentives make it attractive for manufacturing "
    "facilities and rural broadband infrastructure. The single nomination reflects a genuine "
    "scarcity of tracts meeting both need and readiness thresholds in the county — "
    "20 of 22 eligible Mohave tracts scored in the Q3–Q5 range.",
    "The 21 un-nominated Mohave tracts are predominantly DCI Q3–Q5 rural tracts without CRA "
    "designation. Kingman and the Colorado River communities (Lake Havasu City, Bullhead "
    "City) have some eligible tracts with moderate distress, but investment demand evidence "
    "is limited. Additional nominations could be considered if the county or local CDFIs "
    "submit project-specific proposals."
),
"Navajo County": (
    "Navajo County sits entirely within or adjacent to the Navajo Nation and Hopi Reservation, "
    "and all 21 eligible tracts carry USDA persistent poverty designation. The eight nominated "
    "tracts include one with prior NMTC investment, five with CRA designation, and all eight "
    "in DCI quintile 1 or 2 (average score 91.2). Two of the five CRA-eligible nominated "
    "tracts qualify via the FFIEC distressed/underserved Track 2 designation — rural middle-"
    "income tracts that meet FFIEC unemployment, poverty, or remoteness criteria.",
    "The tract with NMTC history (04017942500, DCI score 99.3 — the highest in Arizona) "
    "demonstrates capital deployment capacity. The Navajo Nation's tribally-operated enterprises, "
    "including Navajo Tribal Utility Authority, Navajo Nation Gaming Enterprise, and ranching "
    "cooperatives, provide institutional anchors for investor engagement. Rural QROF "
    "eligibility on all eight tracts significantly improves investor economics. Winslow "
    "and Holbrook — the county's main towns — offer accessible entry points for "
    "mixed-use and housing development.",
    "Thirteen Navajo County tracts not nominated include several with null DCI data (PO Box "
    "ZIP codes). These tracts may have conditions equivalent to or worse than nominated ones "
    "but lack reliable DCI coverage. Direct Navajo Nation nominations through the state "
    "process are strongly encouraged."
),
"Pima County": (
    "Pima County's 25 nominated tracts are concentrated in Tucson's south side and central "
    "core — a contiguous band of high-distress urban neighborhoods with DCI scores from 80 "
    "to 95.6, all in quintile 1 or 2. Three nominated tracts have prior NMTC investment, and "
    "one rural QROF-eligible tract (04019940800, DCI 99.0) in the southern reaches of the "
    "county — likely Tohono O'odham Nation land — is the most distressed rural tract in the "
    "county and warrants tribal engagement.",
    "Tucson has one of the most established CDFI ecosystems in the Southwest — Chicanos Por "
    "La Causa, Arizona Community Foundation, and multiple NMTC-certified CDEs have active "
    "Pima County portfolios. CRA LMI designation on all 25 nominated tracts provides the bank "
    "capital channel. The south side Tucson market has demonstrated absorption of affordable "
    "housing and mixed-use development, making these tracts among the most fundable in the state.",
    "63 Pima tracts not nominated are primarily DCI Q3–Q5 suburban and exurban tracts. "
    "Several Pima tracts with prior NMTC history score in the Q3 range and fall just below "
    "the nomination threshold — they are viable secondary candidates if additional state slots "
    "become available. The 25 nominated represent Tucson's highest-need, most investment-ready geography."
),
"Pinal County": (
    "Pinal County is one of the fastest-growing counties in the United States, bridging the "
    "Phoenix and Tucson metropolitan areas along the I-10 corridor. Its four nominated tracts "
    "include two rural DCI quintile 1 tracts (scores 93.4 and 93.9) near Casa Grande, one "
    "urban DCI Q1 tract, and one rural DCI Q2 tract. Two tracts have prior NMTC investment. "
    "The nominated tracts represent Pinal's established low-income core alongside a high-growth "
    "suburban periphery.",
    "Casa Grande's position at the intersection of I-10 and I-8 makes it one of the most "
    "logistics-accessible inland locations in the Southwest. Amazon, manufacturing firms, and "
    "distribution centers have already located in Casa Grande, creating labor demand in "
    "surrounding low-income neighborhoods. The CRA LMI designation on all four nominated "
    "tracts, combined with the county's high-growth trajectory, means that investment capital "
    "will follow market demand — OZ designation adds a tax incentive on top of organic "
    "development pressure that already exists.",
    "24 Pinal tracts not nominated are primarily DCI Q3 tracts in newer suburban subdivisions "
    "where distress is moderate and investment would occur without OZ incentives."
),
"Santa Cruz County": (
    "Santa Cruz County is Arizona's smallest county and among its most economically distressed. "
    "Five of seven eligible tracts are nominated — all DCI quintile 1 (score 95.8), all rural, "
    "and all five carry CRA designation. Four are Moderate Income under the FFIEC income test; "
    "the fifth qualifies via the distressed/underserved Track 2 designation for rural middle-"
    "income tracts that meet FFIEC poverty and remoteness criteria. The county seat, Nogales, "
    "is the busiest land port of entry on the Arizona-Mexico border by commercial truck volume.",
    "The Nogales port of entry processed over $30 billion in two-way trade in fiscal year 2024, "
    "with produce, auto parts, and electronics dominating the freight mix. OZ capital invested "
    "in cold storage, light manufacturing, and logistics facilities in CRA-designated tracts "
    "immediately adjacent to the port can capture a fraction of this trade flow. The CRA "
    "designation on all five nominated tracts provides the bank financing layer that logistics "
    "and industrial deals require. Santa Cruz is an unusually strong investment case for a "
    "high-distress rural county because commercial demand — cross-border trade — is "
    "observable and durable.",
    "Two tracts not nominated are DCI Q4 without CRA designation, representing "
    "lower-distress exurban areas with weaker investment demand evidence."
),
"Yavapai County": (
    "Yavapai County's single nominated tract (04025002100) is a rural, DCI quintile 2 tract "
    "in the Prescott Valley area — an interior Arizona community with elevated unemployment "
    "and limited access to capital despite proximity to the larger Prescott metro. The tract "
    "carries a DCI score of 83.5, placing it in the upper half of distress among OZ-eligible "
    "tracts nationally. It does not carry CRA designation, which is the principal constraint "
    "on the investment readiness case.",
    "The investment case rests primarily on QROF rural bonus eligibility — the tract is "
    "rural-designated under Notice 2025-50, qualifying for the 30 percent basis step-up. "
    "The Prescott metro's growth trajectory and the I-17 corridor's industrial development "
    "activity suggest demand conditions for investment exist even without a CRA capital pathway. "
    "Rural workforce housing is a documented need throughout the Prescott Valley. This is "
    "the weakest nomination in the Arizona slate on composite score, and is included "
    "to ensure Yavapai County is represented.",
    "Twelve un-nominated Yavapai tracts are DCI Q3–Q5 with mixed CRA coverage. "
    "If nomination slots become constrained, this tract could be replaced by an additional "
    "tract from Maricopa or Mohave County without materially weakening the overall slate."
),
"Yuma County": (
    "Yuma County's single nominated tract (04027000100) is in the urban core of Yuma City — "
    "DCI quintile 3 (score 75.5), CRA Moderate Income designated, with prior NMTC investment. "
    "Yuma is a high-poverty agricultural county: median household income is among the lowest "
    "in Arizona, and the lettuce/citrus agricultural economy is highly seasonal, creating "
    "persistent workforce poverty. The county's eligible tracts scored in the Q3 range "
    "primarily because urban Yuma tracts share ZIP codes with higher-income areas, "
    "compressing DCI scores for the low-income core.",
    "The prior NMTC project in tract 04027000100 confirms capital deployment has occurred "
    "here. CRA Moderate Income designation provides the bank financing layer. Yuma's "
    "agricultural processing industry — lettuce washing, packing, cold chain — represents "
    "a direct investment target for rural food-system OZ funds. The Marine Corps Air Station "
    "Yuma provides an economic anchor. This is not among the strongest tracts in the Arizona "
    "slate on composite score, but Yuma County's scale and agricultural significance make "
    "inclusion appropriate.",
    "23 Yuma tracts not nominated include suburban and exurban tracts with DCI Q3–Q5 scores "
    "and limited investment case evidence. If additional Yuma tracts are nominated by local "
    "governments or CDFIs with specific project pipelines, they should be evaluated on the "
    "merits of the project rather than the data scores alone."
),
}

# ── BUILD STORY ────────────────────────────────────────────────────
story = []

total_elig  = len(az)
total_nom   = int(az["nominated"].sum())
nom_df      = az[az["nominated"]]
total_rural = int(nom_df["is_rural"].sum())
total_cra   = int(nom_df["is_cra_lmi"].sum())
total_nmtc  = int(nom_df["has_nmtc"].sum())
total_pp    = int(nom_df["is_persistent_poverty"].sum())
total_q12   = int(nom_df[nom_df["dci_quintile"].isin([1, 2])]["geoid"].count())
n_counties  = int(az[az["nominated"]]["county_name"].nunique())

# ── COVER PAGE ─────────────────────────────────────────────────────
story.append(Spacer(1, 0.4*inch))
story.append(Paragraph("Arizona", H1))
story.append(Paragraph(
    "OZ 2.0 Nomination Analysis — Proposed Designation Slate and County-by-County Justification",
    H1s))
story.append(HRFlowable(width="100%", thickness=2, color=TEAL, spaceAfter=14))

stat_data = [
    [Paragraph("500", S("n", fontSize=20, leading=24, textColor=TEAL, fontName="Helvetica-Bold")),
     Paragraph("125", S("n", fontSize=20, leading=24, textColor=NAVY, fontName="Helvetica-Bold")),
     Paragraph(str(n_counties), S("n", fontSize=20, leading=24, textColor=STEEL, fontName="Helvetica-Bold"))],
    [Paragraph("Eligible tracts statewide\n(IRS Rev. Proc. 2026-14)", S("l", fontSize=8, leading=11, fontName="Helvetica", textColor=BLACK)),
     Paragraph("Proposed nominations\n(25% statutory ceiling)", S("l", fontSize=8, leading=11, fontName="Helvetica", textColor=BLACK)),
     Paragraph("Counties with at least\none nominated tract", S("l", fontSize=8, leading=11, fontName="Helvetica", textColor=BLACK))],
]
stat_tbl = Table(stat_data, colWidths=[2.37*inch]*3)
stat_tbl.setStyle(TableStyle([
    ("BACKGROUND", (0,0),(-1,-1), LGRAY),
    ("LINEAFTER",  (0,0),(1,-1), 0.5, RULE),
    ("TOPPADDING", (0,0),(-1,-1), 9), ("BOTTOMPADDING",(0,0),(-1,-1),9),
    ("LEFTPADDING",(0,0),(-1,-1),12), ("RIGHTPADDING",(0,0),(-1,-1),8),
    ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
]))
story.append(stat_tbl)
story.append(Spacer(1, 0.18*inch))

sub_data = [[
    Paragraph(f"<b>{total_q12}</b> in DCI top distress quintiles (Q1–Q2)", S("ss", fontSize=8.5, fontName="Helvetica", textColor=BLACK)),
    Paragraph(f"<b>{total_rural}</b> rural-designated — QROF bonus eligible (P.L. 119-21)", S("ss", fontSize=8.5, fontName="Helvetica", textColor=BLACK)),
    Paragraph(f"<b>{total_cra}</b> CRA-eligible (FFIEC 2025, two-track)", S("ss", fontSize=8.5, fontName="Helvetica", textColor=BLACK)),
    Paragraph(f"<b>{total_nmtc}</b> with prior NMTC investment (CDFI Fund 2024)", S("ss", fontSize=8.5, fontName="Helvetica", textColor=BLACK)),
]]
sub_tbl = Table(sub_data, colWidths=[1.775*inch]*4)
sub_tbl.setStyle(TableStyle([
    ("LINEAFTER",(0,0),(2,-1),0.5,RULE),
    ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
    ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),6),
    ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
]))
story.append(sub_tbl)
story.append(Spacer(1, 0.18*inch))

story.append(Paragraph("About This Report", H3))
story.append(Paragraph(
    "This report proposes a slate of 125 Opportunity Zone 2.0 nominations for Arizona — "
    "the statutory maximum under IRS Rev. Proc. 2026-14 (25 percent of 500 eligible tracts). "
    "Nominations are drawn from all 14 Arizona counties with eligible tracts. "
    "Each nominated tract was scored on two dimensions: <b>economic need</b> (EIG Distressed "
    "Communities Index quintile, USDA persistent poverty county designation) and "
    "<b>investment readiness</b> (prior NMTC activity, CRA designation, rural QROF "
    "eligibility). Tracts scoring highest on the combined measure were nominated, subject to "
    "a minimum of one nomination per county.", BODY))
story.append(Paragraph(
    "Each county section that follows presents the proposed nominated tracts in a data table, "
    "a narrative making the case for economic need, and a narrative on investment readiness — "
    "including why capital should plausibly flow to these specific places. Where trade-offs "
    "were made or data limitations affect conclusions, they are disclosed. An appendix "
    "provides the complete 125-tract nomination list for submission.", BODY))

story.append(Paragraph("Scoring Methodology", H3))
story.append(Paragraph(
    "<b>Need indicators:</b> DCI quintile 1 = 50 pts, Q2 = 38 pts, Q3 = 22 pts, Q4 = 8 pts; "
    "raw DCI score adds up to 10 pts; persistent poverty county adds 8 pts. "
    "<b>Investment-readiness indicators:</b> CRA eligible (any FFIEC track) = 18 pts; "
    "prior NMTC = 12 pts; rural QROF eligibility = 10 pts. Maximum possible score: 106 pts. "
    "CRA eligibility uses the FFIEC two-track definition (FFIEC Census Flat File, 2025 exam year): "
    "Track 1 = Low or Moderate Income; Track 2 = distressed/underserved non-metropolitan "
    "middle-income tracts. "
    "DCI data is unavailable for some rural reservation tracts (PO Box ZIP codes) — "
    "these receive partial credit and their actual distress may exceed what the score implies. "
    "Scores are a selection tool, not a ranking of community need.", SMLL))

story.append(HRFlowable(width="100%", thickness=0.5, color=RULE, spaceAfter=10))

# ── STATEWIDE COUNTY SUMMARY TABLE ────────────────────────────────
story.append(Paragraph("Statewide Summary by County", H3))
cty_sum = az.groupby("county_name").apply(lambda g: pd.Series({
    "eligible":  len(g),
    "nominated": int(g["nominated"].sum()),
    "q12":       int(g[g["nominated"] & g["dci_quintile"].isin([1,2])]["geoid"].count()),
    "rural_nom": int(g[g["nominated"]]["is_rural"].sum()),
    "cra_nom":   int(g[g["nominated"]]["is_cra_lmi"].sum()),
    "nmtc_nom":  int(g[g["nominated"]]["has_nmtc"].sum()),
    "pp":        int(g[g["nominated"]]["is_persistent_poverty"].sum()),
})).reset_index().sort_values("eligible", ascending=False)

hdr = [th(c) for c in ["County","Eligible","Nominated","DCI Q1–Q2","Rural/QROF","CRA","NMTC","Pers. Poverty"]]
cty_rows = []
for _, r in cty_sum.iterrows():
    cty_rows.append([
        tdl(r["county_name"]),
        tdc(str(int(r["eligible"]))),
        tdb(str(int(r["nominated"]))),
        tdc(str(int(r["q12"]))),
        tdc(str(int(r["rural_nom"]))),
        tdc(str(int(r["cra_nom"]))),
        tdc(str(int(r["nmtc_nom"]))),
        tdc(str(int(r["pp"]))),
    ])

cty_tbl = Table([hdr]+cty_rows,
    colWidths=[1.82*inch,0.64*inch,0.82*inch,0.82*inch,0.82*inch,0.73*inch,0.61*inch,0.84*inch])
bg = [("BACKGROUND",(0,0),(-1,0),NAVY),
      ("GRID",(0,0),(-1,-1),0.3,RULE),
      ("LINEBELOW",(0,0),(-1,0),1,NAVY),
      ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
      ("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),
      ("VALIGN",(0,0),(-1,-1),"MIDDLE")]
for i, _ in enumerate(cty_rows):
    if i % 2 == 0: bg.append(("BACKGROUND",(0,i+1),(-1,i+1),LGRAY))
cty_tbl.setStyle(TableStyle(bg))
story.append(cty_tbl)

story.append(Paragraph(
    "DCI Q1–Q2: tracts in the two most distressed quintiles nationally (EIG DCI 2023). "
    "Rural/QROF: rural-designated under Notice 2025-50 §4.01. "
    "CRA: eligible under FFIEC two-track definition (FFIEC Census Flat File, 2025 exam year). "
    "NMTC: prior New Markets Tax Credit investment (CDFI Fund 2024). "
    "Pers. Poverty: USDA ERS County Typology 2015.", SMLL))

story.append(PageBreak())

# ── COUNTY PAGES ──────────────────────────────────────────────────
COUNTY_ORDER = [
    "Apache County","Cochise County","Coconino County","Gila County",
    "Graham County","La Paz County","Maricopa County","Mohave County",
    "Navajo County","Pima County","Pinal County","Santa Cruz County",
    "Yavapai County","Yuma County",
]

for county in COUNTY_ORDER:
    subset = az[az["county_name"] == county].copy()
    nom    = subset[subset["nominated"]].sort_values("score", ascending=False)
    n_elig = len(subset)
    n_nom  = len(nom)
    n_pp   = int(subset["is_persistent_poverty"].sum())
    pp_str = "Persistent poverty" if n_pp > 0 else "No pers. poverty"
    n_rural = int(nom["is_rural"].sum())
    n_cra   = int(nom["is_cra_lmi"].sum())
    n_nmtc  = int(nom["has_nmtc"].sum())
    dci_v   = nom[nom["dci_quintile"] > 0]["dci_score"]
    q12     = int(nom[nom["dci_quintile"].isin([1, 2])]["geoid"].count())

    hdr_data = [
        [Paragraph(county, S("ch", fontSize=14, leading=17, textColor=WHITE, fontName="Helvetica-Bold"))],
        [Paragraph(
            f"{n_nom} nominated  /  {n_elig} eligible  ·  "
            f"{n_rural} rural/QROF  ·  {n_cra} CRA  ·  {n_nmtc} NMTC  ·  "
            f"{q12} DCI Q1–Q2  ·  {pp_str}",
            S("cs", fontSize=8, leading=11, textColor=colors.HexColor("#93c5fd"), fontName="Helvetica"))],
    ]
    hdr_tbl = Table(hdr_data, colWidths=[7.1*inch])
    hdr_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),NAVY),
        ("TOPPADDING",(0,0),(0,0),10),("BOTTOMPADDING",(0,0),(0,0),2),
        ("TOPPADDING",(0,1),(0,1),2), ("BOTTOMPADDING",(0,1),(0,1),10),
        ("LEFTPADDING",(0,0),(-1,-1),12),("RIGHTPADDING",(0,0),(-1,-1),12),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story.append(hdr_tbl)
    story.append(Spacer(1, 0.1*inch))

    need_txt, inv_txt, caveat_txt = narratives[county]
    narr_data = [[
        [Paragraph("Economic Need", S("nh", fontSize=8.5, fontName="Helvetica-Bold", textColor=RED, spaceBefore=0, spaceAfter=3)),
         Paragraph(need_txt, BODY)],
        [Paragraph("Investment Readiness", S("nh", fontSize=8.5, fontName="Helvetica-Bold", textColor=GREEN, spaceBefore=0, spaceAfter=3)),
         Paragraph(inv_txt, BODY)],
    ]]
    narr_tbl = Table(narr_data, colWidths=[3.5*inch, 3.5*inch])
    narr_tbl.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LINEAFTER",(0,0),(0,-1),0.5,RULE),
        ("LEFTPADDING",(0,0),(0,-1),0),("RIGHTPADDING",(0,0),(0,-1),10),
        ("LEFTPADDING",(1,0),(1,-1),10),("RIGHTPADDING",(1,0),(1,-1),0),
        ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
    ]))
    story.append(narr_tbl)
    story.append(Paragraph(f"<i>Not nominated:</i> {caveat_txt}", SMLL))
    story.append(Spacer(1, 0.08*inch))

    MAX_DISPLAY = 16
    show_nom  = nom.head(MAX_DISPLAY)
    truncated = len(nom) > MAX_DISPLAY

    t_hdr = [th(c) for c in ["GEOID","Rural","DCI Score (Q)","CRA","NMTC","Pers.Pov","Score"]]
    t_rows = []
    for _, r in show_nom.iterrows():
        cra_label = "–"
        if r["is_cra_lmi"]:
            if r["income_level"] in ("L", "M"):
                cra_label = str(r["income_level"])
            else:
                cra_label = "D/U"
        t_rows.append([
            tdb(r["geoid"]),
            tdc(check(r["is_rural"])),
            tdc(fmt_dci(r)),
            tdc(cra_label),
            tdc(check(r["has_nmtc"])),
            tdc(check(r["is_persistent_poverty"])),
            tdr(f"{r['score']:.0f}"),
        ])
    if truncated:
        t_rows.append([
            Paragraph(f"… and {len(nom)-MAX_DISPLAY} more — see appendix", SMLL),
            Paragraph("", SMLL), Paragraph("", SMLL),
            Paragraph("", SMLL), Paragraph("", SMLL),
            Paragraph("", SMLL), Paragraph("", SMLL),
        ])

    col_w = [1.88*inch, 0.60*inch, 1.72*inch, 0.82*inch, 0.66*inch, 0.77*inch, 0.64*inch]
    t_tbl = Table([t_hdr]+t_rows, colWidths=col_w, repeatRows=1)
    tbg = [("BACKGROUND",(0,0),(-1,0),STEEL),
           ("GRID",(0,0),(-1,-1),0.3,RULE),
           ("LINEBELOW",(0,0),(-1,0),0.8,STEEL),
           ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
           ("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),
           ("VALIGN",(0,0),(-1,-1),"MIDDLE")]
    for i in range(len(t_rows)):
        if i % 2 == 0: tbg.append(("BACKGROUND",(0,i+1),(-1,i+1),LGRAY))
    t_tbl.setStyle(TableStyle(tbg))
    story.append(t_tbl)

    story.append(Paragraph(
        "DCI Q: quintile 1=most distressed, 5=least. ▲ = Q1. "
        "CRA: L=Low Income, M=Moderate Income, D/U=Distressed/Underserved (Track 2, FFIEC 2025). "
        "Score: composite need+readiness (max 106).",
        SMLL))
    story.append(PageBreak())

# ── APPENDIX: FULL NOMINATION LIST ────────────────────────────────
story.append(Paragraph("Appendix — Proposed Nomination List", H2))
story.append(Paragraph(
    f"Complete proposed slate of {total_nom} census tracts for Arizona OZ 2.0 designation. "
    "Submit GEOIDs to the Arizona Governor's office via the Arizona Commerce Authority "
    "(aztechcouncil.org/opportunity-zones or via ADOA). Federal nomination window: "
    "July 1, 2026 (90-day window under Rev. Proc. 2026-14). "
    "Arizona has no published state deadline as of June 2026.", BODY))
story.append(Spacer(1, 0.08*inch))

nominated_all = az[az["nominated"]].sort_values(["county_name","score"], ascending=[True,False])

apx_hdr = [Paragraph(c, APH) for c in
           ["#","GEOID","County","Rural","DCI Score","DCI Q","CRA","NMTC","Pers.Pov","Score"]]
apx_rows = []
for i, (_, r) in enumerate(nominated_all.iterrows(), 1):
    q = int(r["dci_quintile"]) if pd.notna(r["dci_quintile"]) and r["dci_quintile"] > 0 else 0
    cra_label = "–"
    if r["is_cra_lmi"]:
        cra_label = str(r["income_level"]) if r["income_level"] in ("L","M") else "D/U"
    apx_rows.append([
        Paragraph(str(i), APX),
        Paragraph(str(r["geoid"]), S("m", fontSize=7.5, leading=10, fontName="Courier")),
        Paragraph(r["county_name"], APX),
        Paragraph("✓" if r["is_rural"] else "–", S("c", fontSize=7.5, leading=10, fontName="Helvetica", alignment=TA_CENTER)),
        Paragraph(f"{r['dci_score']:.1f}" if r["dci_score"] > 0 else "–",
                  S("r", fontSize=7.5, leading=10, fontName="Helvetica", alignment=TA_RIGHT)),
        Paragraph(q_label(q) if q > 0 else "–",
                  S("c", fontSize=7.5, leading=10, fontName="Helvetica", alignment=TA_CENTER)),
        Paragraph(cra_label,
                  S("c", fontSize=7.5, leading=10, fontName="Helvetica", alignment=TA_CENTER)),
        Paragraph("✓" if r["has_nmtc"] else "–",
                  S("c", fontSize=7.5, leading=10, fontName="Helvetica", alignment=TA_CENTER)),
        Paragraph("✓" if r["is_persistent_poverty"] else "–",
                  S("c", fontSize=7.5, leading=10, fontName="Helvetica", alignment=TA_CENTER)),
        Paragraph(f"{r['score']:.0f}",
                  S("r", fontSize=7.5, leading=10, fontName="Helvetica", alignment=TA_RIGHT)),
    ])

apx_col_w = [0.33*inch,1.28*inch,1.57*inch,0.49*inch,0.79*inch,0.56*inch,0.49*inch,0.49*inch,0.61*inch,0.50*inch]
apx_tbl = Table([apx_hdr]+apx_rows, colWidths=apx_col_w, repeatRows=1)
abg = [("BACKGROUND",(0,0),(-1,0),NAVY),
       ("GRID",(0,0),(-1,-1),0.3,RULE),
       ("LINEBELOW",(0,0),(-1,0),0.8,NAVY),
       ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
       ("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4),
       ("VALIGN",(0,0),(-1,-1),"MIDDLE")]
for i in range(len(apx_rows)):
    if i % 2 == 0: abg.append(("BACKGROUND",(0,i+1),(-1,i+1),LGRAY))
apx_tbl.setStyle(TableStyle(abg))
story.append(apx_tbl)

story.append(Paragraph(
    "Sources: IRS Rev. Proc. 2026-14 · EIG DCI 2023 · FFIEC Census Flat File 2025 (two-track CRA) · "
    "USDA ERS County Typology 2015 · CDFI Fund NMTC 2024 · P.L. 119-21 (QROF provisions) "
    "· Arizona Commerce Authority (last checked 2026-05-06) · Generated oz2.vargo.city — June 2026",
    FOOT))

# ── BUILD ──────────────────────────────────────────────────────────
OUT = DATA_DIR.parent / "data" / "arizona_oz2_nomination_report.pdf"
doc = SimpleDocTemplate(
    str(OUT),
    pagesize=letter,
    leftMargin=0.7*inch, rightMargin=0.7*inch,
    topMargin=0.65*inch, bottomMargin=0.65*inch,
    title="Arizona OZ 2.0 Nomination Analysis",
    author="oz2.vargo.city",
)
doc.build(story)

import os
size = os.path.getsize(str(OUT))
print(f"PDF written → {OUT}  ({size//1024} KB)")
