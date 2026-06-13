"""
Build data/shoshone_bannock_oz2_brief.pdf

A 3-page practitioner brief on OZ 2.0 designation opportunities for the
Shoshone-Bannock Tribes (Fort Hall Reservation, Idaho).

Data sources:
  data/eligible_tracts.parquet    IRS Rev. Proc. 2026-14
  data/cra_lmi_overlap.parquet    FFIEC Census Flat File 2025 (two-track CRA)
  data/dci.parquet                EIG Distressed Communities Index 2023
  data/tribal_overlap.parquet     Census TIGER/ACS 2023
  data/persistent_poverty.parquet USDA ERS County Typology 2015
  data/cdfi_nmtc.parquet          CDFI Fund NMTC 2024
"""

from pathlib import Path
import pandas as pd

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

# ── DATA PREP ──────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent.parent / "data"

elig   = pd.read_parquet(DATA_DIR / "eligible_tracts.parquet")
cra    = pd.read_parquet(DATA_DIR / "cra_lmi_overlap.parquet")
dci    = pd.read_parquet(DATA_DIR / "dci.parquet")
tribal = pd.read_parquet(DATA_DIR / "tribal_overlap.parquet")
pp     = pd.read_parquet(DATA_DIR / "persistent_poverty.parquet")
nmtc   = pd.read_parquet(DATA_DIR / "cdfi_nmtc.parquet")

FORT_HALL_GEOIDS = ["16005940000", "16011940000", "16011950502", "16077960100"]

id_elig = elig[elig["state_fips"] == "16"].copy()
id_elig = id_elig.merge(cra[["geoid","income_level","is_distressed_underserved","is_cra_lmi"]], on="geoid", how="left")
id_elig = id_elig.merge(dci[["geoid","dci_score","dci_quintile"]], on="geoid", how="left")
id_elig = id_elig.merge(tribal[["geoid","aian_pct","tribal_area_name"]], on="geoid", how="left")
id_elig = id_elig.merge(pp[["county_fips","is_persistent_poverty"]], on="county_fips", how="left")
id_elig["has_nmtc"] = id_elig["geoid"].isin(nmtc[nmtc["state_fips"]=="16"]["geoid"].unique())
id_elig["is_cra_lmi"]               = id_elig["is_cra_lmi"].fillna(False)
id_elig["is_distressed_underserved"] = id_elig["is_distressed_underserved"].fillna(False)
id_elig["income_level"]              = id_elig["income_level"].fillna("NA")
id_elig["dci_score"]                 = pd.to_numeric(id_elig["dci_score"], errors="coerce").fillna(0)
id_elig["dci_quintile"]              = pd.to_numeric(id_elig["dci_quintile"], errors="coerce").fillna(0)
id_elig["aian_pct"]                  = pd.to_numeric(id_elig["aian_pct"], errors="coerce").fillna(0)

sb = id_elig[id_elig["geoid"].isin(FORT_HALL_GEOIDS)].copy()

# ── Colors ─────────────────────────────────────────────────────────
NAVY  = colors.HexColor("#1e3a5f")
TEAL  = colors.HexColor("#0f766e")
STEEL = colors.HexColor("#334155")
MGRAY = colors.HexColor("#64748b")
LGRAY = colors.HexColor("#f1f5f9")
RULE  = colors.HexColor("#cbd5e1")
WHITE = colors.white
BLACK = colors.HexColor("#1e293b")
AMBER = colors.HexColor("#b45309")
RED   = colors.HexColor("#7f1d1d")
GREEN = colors.HexColor("#166534")

def S(nm, **kw):
    return ParagraphStyle(nm, parent=getSampleStyleSheet()["Normal"], **kw)

H1   = S("H1",  fontSize=20, leading=25, textColor=NAVY, fontName="Helvetica-Bold", spaceAfter=3)
H1s  = S("H1s", fontSize=10, leading=13, textColor=TEAL, fontName="Helvetica", spaceAfter=14)
H2   = S("H2",  fontSize=12, leading=15, textColor=NAVY, fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=5)
H3   = S("H3",  fontSize=9.5, leading=12, textColor=STEEL, fontName="Helvetica-Bold", spaceBefore=7, spaceAfter=3)
BODY = S("BD",  fontSize=8.8, leading=13.2, textColor=BLACK, fontName="Helvetica", spaceAfter=5, alignment=TA_JUSTIFY)
SMLL = S("SM",  fontSize=7.8, leading=11, textColor=MGRAY, fontName="Helvetica-Oblique", spaceAfter=5)
FOOT = S("FT",  fontSize=7, leading=10, textColor=MGRAY, fontName="Helvetica", alignment=TA_CENTER, spaceBefore=6)
TH   = S("TH",  fontSize=7.5, leading=10, textColor=WHITE, fontName="Helvetica-Bold")
TDC  = S("TDC", fontSize=8, leading=11, textColor=BLACK, fontName="Helvetica", alignment=TA_CENTER)
TDL  = S("TDL", fontSize=8, leading=11, textColor=BLACK, fontName="Helvetica")
TDB  = S("TDB", fontSize=8, leading=11, textColor=BLACK, fontName="Helvetica-Bold")
CALL = S("CL",  fontSize=11, leading=14, textColor=NAVY, fontName="Helvetica-Bold", spaceAfter=2)
CALS = S("CS",  fontSize=7.5, leading=10, textColor=STEEL, fontName="Helvetica", spaceAfter=0)

def th(t):  return Paragraph(t, TH)
def tdc(t): return Paragraph(str(t), TDC)
def tdl(t): return Paragraph(str(t), TDL)
def tdb(t): return Paragraph(str(t), TDB)
def check(v): return "✓" if v else "–"

def cra_label(row):
    if not row["is_cra_lmi"]: return "–"
    if row["income_level"] == "L": return "Low Income"
    if row["income_level"] == "M": return "Moderate Income"
    return "Distressed/Underserved"

def dci_str(row):
    s, q = row["dci_score"], int(row["dci_quintile"]) if row["dci_quintile"] > 0 else 0
    if s == 0 and q == 0: return "N/A*"
    labels = {1:"Q1 ▲",2:"Q2",3:"Q3",4:"Q4",5:"Q5"}
    return f"{s:.1f} ({labels.get(q,'—')})"

# ── STORY ──────────────────────────────────────────────────────────
story = []

# ── COVER ──────────────────────────────────────────────────────────
story.append(Spacer(1, 0.3*inch))
story.append(Paragraph("Shoshone-Bannock Tribes", H1))
story.append(Paragraph(
    "Opportunity Zone 2.0 Designation Brief — Fort Hall Reservation, Idaho",
    H1s))
story.append(HRFlowable(width="100%", thickness=2, color=TEAL, spaceAfter=12))

# Callout boxes
n_rural = int(sb["is_rural"].sum())
n_cra   = int(sb["is_cra_lmi"].sum())
n_qrof  = n_rural

call_data = [
    [Paragraph("4",       CALL), Paragraph("3",       CALL), Paragraph("4",       CALL)],
    [Paragraph("OZ 2.0-eligible\ntracts on Fort Hall\nReservation", CALS),
     Paragraph("rural-designated\n(QROF bonus eligible\nunder P.L. 119-21)", CALS),
     Paragraph("carry CRA\ndesignation\n(FFIEC 2025)", CALS)],
]
call_tbl = Table(call_data, colWidths=[2.37*inch]*3)
call_tbl.setStyle(TableStyle([
    ("BACKGROUND",(0,0),(-1,-1),LGRAY),
    ("LINEAFTER",(0,0),(1,-1),0.5,RULE),
    ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
    ("LEFTPADDING",(0,0),(-1,-1),12),("RIGHTPADDING",(0,0),(-1,-1),8),
    ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
]))
story.append(call_tbl)
story.append(Spacer(1, 0.15*inch))

story.append(Paragraph("Overview", H2))
story.append(Paragraph(
    "The Shoshone-Bannock Tribes govern the Fort Hall Reservation in southeastern Idaho, "
    "home to approximately 5,800 tribal members. The reservation spans Bannock, Bingham, "
    "and Power counties along the Snake River Plain. Under IRS Rev. Proc. 2026-14, four "
    "census tracts on or adjacent to Fort Hall are eligible for OZ 2.0 designation. "
    "Three are rural-designated under Notice 2025-50 §4.01, qualifying for the QROF rural "
    "bonus: a 30 percent basis step-up on deferred gains and a 50 percent improvement "
    "threshold under P.L. 119-21 (One Big Beautiful Bill Act, 2026).", BODY))
story.append(Paragraph(
    "All four tracts carry CRA designation under the FFIEC two-track definition: three as "
    "Moderate Income tracts (Track 1) and one — the Power County tract (16077960100) — via "
    "the FFIEC distressed/underserved designation (Track 2) for non-metropolitan middle-income "
    "tracts that meet unemployment or remoteness criteria. CRA eligibility on all four tracts "
    "creates a pathway for bank community development loans and equity-equivalent investments "
    "that can be layered with Opportunity Fund equity and QROF rural incentives.", BODY))

# ── TRACT TABLE ────────────────────────────────────────────────────
story.append(Paragraph("Tract Detail", H2))

hdr = [th(c) for c in ["GEOID","County","AIAN %","Rural/QROF","CRA Designation","DCI Score","Pers. Pov."]]
rows = []
for _, r in sb.sort_values("is_rural", ascending=False).iterrows():
    rows.append([
        tdb(r["geoid"]),
        tdl(r["county_name"].replace(" County","")),
        tdc(f"{r['aian_pct']*100:.0f}%"),
        tdc("✓" if r["is_rural"] else "–"),
        tdl(cra_label(r)),
        tdc(dci_str(r)),
        tdc(check(r["is_persistent_poverty"])),
    ])

col_w = [1.38*inch, 0.90*inch, 0.65*inch, 0.78*inch, 1.65*inch, 0.98*inch, 0.75*inch]
tbl = Table([hdr]+rows, colWidths=col_w)
tbg = [("BACKGROUND",(0,0),(-1,0),NAVY),
       ("GRID",(0,0),(-1,-1),0.3,RULE),
       ("LINEBELOW",(0,0),(-1,0),0.8,NAVY),
       ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
       ("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),
       ("VALIGN",(0,0),(-1,-1),"MIDDLE")]
for i in range(len(rows)):
    if i % 2 == 0: tbg.append(("BACKGROUND",(0,i+1),(-1,i+1),LGRAY))
tbl.setStyle(TableStyle(tbg))
story.append(tbl)

story.append(Paragraph(
    "* EIG DCI scores based on ZIP code-level data; reservation tracts using PO Box ZIP codes "
    "may show suppressed or missing scores regardless of actual economic conditions. Q5 scores "
    "for these tracts likely reflect data unavailability, not better conditions. "
    "AIAN %: share of tract population identifying as American Indian/Alaska Native (ACS 2020).",
    SMLL))

story.append(PageBreak())

# ── PAGE 2: INVESTMENT LANDSCAPE ──────────────────────────────────
story.append(Paragraph("Investment Landscape", H2))
story.append(Paragraph(
    "Fort Hall has no prior New Markets Tax Credit investment on record for these tracts. "
    "The reservation's existing economic infrastructure — Shoshone-Bannock Casino Hotel, "
    "Fort Hall Business Council enterprises, and the Fort Hall Industrial Park on I-15 — "
    "provides an institutional foundation that many rural tribal OZ contexts lack. The "
    "industrial park, positioned on I-15 at the Fort Hall exit, is an established commercial "
    "site with existing tenants and demonstrable demand for expansion. This is a material "
    "advantage: OZ capital can supplement an active economic development program rather than "
    "creating one from scratch.", BODY))
story.append(Paragraph(
    "The three rural QROF-eligible tracts benefit from both the standard 10-year gain "
    "exclusion and the QROF rural step-up: investors who hold a qualifying rural OZ investment "
    "for five or more years receive a 30 percent basis step-up on the original deferred gain, "
    "permanently excluding that portion from tax. The 50 percent improvement threshold (versus "
    "100 percent for non-rural QOZB properties) meaningfully reduces the equity requirement "
    "for rehabilitation projects — workforce housing, light industrial, agri-processing — "
    "that form the realistic investment pipeline on the reservation.", BODY))

story.append(Paragraph("CRA Capital Pathway", H3))
story.append(Paragraph(
    "CRA designation on all four tracts is a strategic asset for tribal economic development "
    "staff approaching banks in the Pocatello-Idaho Falls market. Idaho's major CRA-regulated "
    "institutions — U.S. Bank, Banner Bank, Idaho Central Credit Union (state-chartered, "
    "not CRA-covered, but community-oriented), and regional community banks — have CRA "
    "examination incentives to make community development loans and investments in these "
    "tracts. The FFIEC distressed/underserved designation on tract 16077960100 (Power County) "
    "means it qualifies for CRA credit even though its income ratio sits just above the LMI "
    "threshold.", BODY))
story.append(Paragraph(
    "The most effective use of CRA designation for tribal projects is typically through "
    "a tribal CDFI intermediary: a bank provides a CRA-eligible community development loan "
    "to a tribal CDFI, which on-lends to the OZ project on terms negotiated with the tribe. "
    "This structure resolves the bank's concerns about trust land titling and BIA leasing "
    "requirements while maintaining the CRA credit and keeping deal terms under tribal "
    "control. Identifying or capitalizing a Fort Hall-affiliated CDFI — or engaging an "
    "existing regional Native CDFI such as the Northwest Native Development Fund — should "
    "be a near-term priority alongside the nomination process.", BODY))

story.append(Paragraph("Land and Jurisdictional Considerations", H3))
story.append(Paragraph(
    "Investors unfamiliar with Indian Country require early education on the legal structure "
    "of deals on trust land. BIA leasing regulations (25 CFR Part 162) govern surface leases "
    "on trust land; HEARTH Act authorizations — if the Shoshone-Bannock Tribes have adopted "
    "one — allow the Business Council to approve leases directly without BIA approval, "
    "substantially reducing transaction time. Tribal sovereignty means that investment "
    "structures must be negotiated with and approved by the Fort Hall Business Council. "
    "These are not disqualifying obstacles for experienced Indian Country developers; "
    "they are front-loaded transaction costs that should be reflected in deal timelines "
    "and investor expectations.", BODY))

story.append(PageBreak())

# ── PAGE 3: RECOMMENDATIONS ────────────────────────────────────────
story.append(Paragraph("Recommended Actions", H2))

actions = [
    ("Engage Idaho's Governor's office for tribal nomination",
     "Idaho has not published a public OZ 2.0 nomination process as of June 2026. The Shoshone-"
     "Bannock Tribes should submit a direct request to the Governor's office identifying the four "
     "Fort Hall tracts and documenting economic need, tribal sovereignty, and investment readiness. "
     "The Fort Hall Business Council should sign the letter. Sovereign tribal nations have standing "
     "to engage governor's offices directly; do not wait for a public process."),
    ("Lead with the QROF rural bonus and CRA dual designation",
     "In any investor or bank conversation, lead with the combination of facts: rural QROF "
     "eligibility (30% basis step-up, 50% improvement threshold) on three tracts, CRA "
     "designation on all four, and the existing Fort Hall Industrial Park as proof of "
     "commercial viability. The CRA + QROF combination is unusual in rural tribal contexts "
     "and will differentiate Fort Hall from comparable reservation OZ opportunities."),
    ("Prioritize the industrial park tract for the first OZ deal",
     "The Fort Hall Industrial Park is on or adjacent to one of the QROF-eligible tracts. "
     "A deal in an active commercial park — even a relatively small expansion or new tenant "
     "buildout — demonstrates the OZ mechanism to tribal leadership and investors before "
     "attempting more complex housing or infrastructure projects. First deals shape "
     "perceptions of the program for the community."),
    ("Engage a regional Native CDFI as CRA intermediary",
     "The Northwest Native Development Fund (Nez Perce Tribe-affiliated) and the Native "
     "CDFI Network directory are starting points for identifying a CDFI that can bridge "
     "bank CRA capital and Fort Hall trust land projects. A formal relationship with a "
     "tribal CDFI should be established before approaching banks for CRA community "
     "development loans, not after."),
    ("Document the DCI data gap as part of the nomination case",
     "The Q5 DCI scores for Fort Hall tracts likely reflect ZIP code-level data suppression "
     "on reservation land, not actual economic conditions. The nomination letter should include "
     "reservation-level economic data (BIA Labor Force Report, tribal unemployment rate, "
     "per-capita income from ACS) to supplement the DCI scores and make the economic need "
     "case independently of the national distress index."),
]

for i, (title, body) in enumerate(actions, 1):
    story.append(Paragraph(f"{i}. {title}", H3))
    story.append(Paragraph(body, BODY))

story.append(HRFlowable(width="100%", thickness=0.5, color=RULE, spaceAfter=8))
story.append(Paragraph(
    "Sources: IRS Rev. Proc. 2026-14 · FFIEC Census Flat File 2025 (two-track CRA) · "
    "EIG DCI 2023 · Census TIGER/ACS 2023 (AIAN population) · P.L. 119-21 (QROF provisions) · "
    "CDFI Fund NMTC 2024 · Shoshone-Bannock Tribes (shoshonebannocktribes.com) · "
    "Generated oz2.vargo.city — June 2026",
    FOOT))

# ── BUILD ──────────────────────────────────────────────────────────
OUT = DATA_DIR / "shoshone_bannock_oz2_brief.pdf"
doc = SimpleDocTemplate(
    str(OUT),
    pagesize=letter,
    leftMargin=0.75*inch, rightMargin=0.75*inch,
    topMargin=0.65*inch, bottomMargin=0.65*inch,
    title="Shoshone-Bannock Tribes OZ 2.0 Brief",
    author="oz2.vargo.city",
)
doc.build(story)

import os
size = os.path.getsize(str(OUT))
print(f"PDF written → {OUT}  ({size//1024} KB)")
