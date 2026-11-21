# The 2027 designations through the lens of Native lands (2026-11-21)

Companion to `designation-postmortem-2026-11.md`. Site: `/designations#native-lands` and the
"Native lands and communities" section of each state page (`#native`).

Pipeline (after the main designation pipeline):
`ingest_native_lands.py` → `data/native_lands.parquet`;
`ingest_native_cdfis.py` → `data/cdfis_certified.parquet`;
`analyze_designations.py`; `analyze_native_lands.py` → `data/native_lands_analysis.json`;
`patch_geo_native.py` (map). Thresholds live in `scripts/native_rules.py` and nowhere else.

## Two lenses

| Lens | Rule | Eligible | Designated |
|---|---|---:|---:|
| Land | ≥50% of 2020 residents live on federally recognized reservation / off-reservation trust land; Hawaii: ≥10% on Hawaiian Home Land | 201 | 67 |
| Land, area basis (sensitivity) | ≥50% of tract area | 184 | 60 |
| People | Native residents ≥20% (AIAN alone; Hawaii adds NHPI alone) | 326 | 101 |
| — majority | Native residents ≥50% | 177 | 52 |
| Both | | 174 | 54 |
| Either | | 353 | 114 |

Choices and why:
- **Population-weighted land share** (added in the second pass). From the 2020 PL 94-171 block file:
  each block carries its AIANNH code, so the share is "residents living on reservation or trust land,"
  not area. It mostly agrees with area share (r = 0.97), but 14 tracts enter and
  3 leave. The entrants are largely the Navajo checkerboard in New Mexico, where
  people live on trust allotments that are a minority of the land. The leavers are tracts that are
  mostly reservation by area while the population sits in an off-reservation town (two in Navajo
  County, AZ). Tracts with no 2020 residents fall back to area. Population is 2020 decennial; ACS
  columns are 2020–24.
- **Statistical areas kept out of "land."** OTSAs (plus a few TDSAs, e.g. Cayuga Nation), ANVSAs and
  SDTSAs are tabulation areas, not land held by or for a tribe. Reported separately. Oklahoma caveat:
  since *McGirt v. Oklahoma* (2020) and 2021 OCCA rulings, the Muscogee, Cherokee, Chickasaw, Choctaw,
  Seminole and Quapaw reservations are recognized as never disestablished; Census still tabulates them
  as OTSAs.
- **AIAN alone, not alone-or-in-combination,** as the primary population measure; AOIC in the parquet.
- **Hawaii** uses NHPI. The Island Areas are not in the ACS; they designated every eligible tract.

## Findings

1. **Raw within-state lift:** land 1.05 (area basis 1.02), people 0.96,
   majority-Native 0.88. Other rural tracts 1.18.
2. **With controls** (main post-mortem logit + both lenses; n = 22,904): land OR 1.2
   (0.65–2.19, p = 0.56); people OR 0.59
   (0.38–0.93, p = 0.023), AME -8.8 pp.
   Tracts with substantial Native populations are rural, poor and often ex-OZ 1.0 — traits that raised
   the odds elsewhere — yet were picked only at the expected rate. Robustness:

   | Specification | Land OR | People OR |
   |---|---:|---:|
| without residents of color | 1.06 | 0.53 (p = 0.0066) |
| population lens only | — | 0.65 (p = 0.015) |
| population lens only, without residents of color | — | 0.55 (p = 0.00045) |
| land lens only | 0.79 | — (p = —) |

   In the first pass (area-based land lens) the people OR was 0.65, p = 0.077; moving to the
   population-weighted land lens sharpened it. It is robust to dropping the residents-of-color control.
   Descriptive, not causal: county spreading or tribes declining nomination would produce it too.
3. **Incumbency:** 32 of 67 former-OZ-1.0 land tracts redesignated; 35 of 134 others.
   35 reservation/trust tracts stop being OZs after 2028-12-31 — case-study leads.
4. **Residents:** 28.7% of Native residents of eligible tracts live in a designated tract
   (all residents 26.1%). 142,615 of 432,013 Native residents living on
   reservation/trust land in eligible tracts (2020) are in a designated tract.
5. **Reservation level:** 80 reservations; 48 with ≥1 designated tract; 32 in
   selection states with none. Navajo Nation AZ 6/26, NM 3/25, UT 0/2. Hopi, Zuni, Crow 0 of 3.
6. **QROF:** 59 of 67 designated land tracts are rural.
7. **Consultation:** states with a published tribal consultation framework (`tribal_consultation.framework`
   in YAML: KS, MS, NC, NM, OR, WA) designated Native tracts at
   1.06× expected; others 1.0×. The YAML field is uneven
   (some entries are notes, not frameworks) — treat as a weak descriptive.
8. **Native CDFIs:** 65 certified (list of 2026-11-16); 27 HQ on reservation/trust/Home Land,
   14 HQ in a designated tract. Reservations with a locally based Native CDFI got ≥1 designated
   tract 12/19; without, 35/60 — no difference.
   NMTC record does matter: 21 of 42 land tracts with an NMTC project were designated
   ($324M across 60 projects). Native-affiliated CDEs with NMTC deals in eligible
   tracts: Alaska Growth Capital BIDCO, Inc.; Chickasaw Nation Community Development Endeavor LLC; National Tribal Development Association (21 projects, $114M).
   Geocoding: {'Place': 31, 'Exact': 20, 'Non_Exact': 11, 'ZIP': 3}. "Place" = PO box placed at the town's Census point. Headquarters only —
   not service areas. Quirks worth knowing: Lower Brule CDE is listed in Reston, VA; Yurok Alliance
   places outside the reservation by town point.

## Reservations with ≥3 eligible tracts

| Reservation | State | Designated / eligible | Native CDFIs headquartered on it |
|---|---|---:|---|
| Navajo Nation | AZ, NM, UT | 9 / 53 | Navajo community Development Financial Institution Inc Non Profit |
| Pine Ridge | SD | 1 / 5 | Lakota Federal Credit Union; Lakota Fund, Inc., The; Mazaska Owecaso Otipi Financial, Inc |
| Yakama Nation | WA | 4 / 5 |  |
| Fort Apache | AZ | 1 / 4 |  |
| Standing Rock | ND, SD | 1 / 4 |  |
| Cheyenne River | SD | 1 / 3 | Akiptan, Inc.; Four Bands Community Fund, Incorporated |
| Colorado River | AZ, CA | 1 / 3 |  |
| Colville | WA | 2 / 3 | Northwest Native Development Fund |
| Crow | MT | 0 / 3 |  |
| Flathead | MT | 1 / 3 |  |
| Fort Berthold | ND | 2 / 3 |  |
| Fort Hall | ID | 1 / 3 |  |
| Gila River | AZ | 1 / 3 |  |
| Hopi | AZ | 0 / 3 | Hopi Credit Association |
| Osage | OK | 1 / 3 |  |
| Puyallup | WA | 2 / 3 |  |
| Tohono O'odham Nation | AZ | 1 / 3 |  |
| White Earth | MN | 1 / 3 | White Earth Investment Initiative |
| Wind River | WY | 3 / 3 | Wind River Development Fund |
| Zuni | NM | 0 / 3 |  |

## States with ≥3 Native land or community tracts

| State | Overall rate | Land | People ≥20% | Either (expected) | Native share of residents, eligible → designated |
|---|---:|---:|---:|---:|---:|
| New Mexico | 25.2% | 9 / 39 | 12 / 55 | 15 / 58 (14.6) | 15.6% → 12.6% |
| Arizona | 25.1% | 13 / 46 | 15 / 52 | 15 / 52 (13.1) | 10.2% → 10.6% |
| Oklahoma | 25.1% | 1 / 3 | 8 / 37 | 8 / 39 (9.8) | 8.3% → 8.9% |
| Hawaii | 28.1% | 1 / 6 | 9 / 25 | 9 / 25 (7.0) | 17.3% → 18.4% |
| North Carolina | 25.1% | 0 / 0 | 2 / 25 | 2 / 25 (6.3) | 2.4% → 1.7% |
| South Dakota | 48.1% | 7 / 18 | 10 / 23 | 10 / 23 (11.1) | 28.7% → 27.0% |
| Montana | 43.1% | 5 / 15 | 5 / 16 | 5 / 17 (7.3) | 21.4% → 19.7% |
| Alaska | 75.8% | 0 / 0 | 13 / 16 | 13 / 16 (12.1) | 38.8% → 36.2% |
| Washington | 25.0% | 9 / 16 | 5 / 10 | 9 / 16 (4.0) | 2.2% → 3.2% |
| California | 25.0% | 3 / 8 | 4 / 8 | 5 / 13 (3.3) | 1.9% → 1.9% |
| New York | 25.0% | 2 / 9 | 0 / 10 | 2 / 12 (3.0) | 1.0% → 1.1% |
| North Dakota | 67.6% | 5 / 9 | 5 / 10 | 5 / 10 (6.8) | 17.2% → 14.8% |
| Minnesota | 25.1% | 2 / 8 | 2 / 8 | 2 / 9 (2.3) | 2.4% → 3.5% |
| Idaho | 30.9% | 1 / 4 | 0 / 2 | 1 / 4 (1.2) | 2.1% → 1.2% |
| Wisconsin | 25.0% | 1 / 4 | 1 / 4 | 1 / 4 (1.0) | 1.3% → 1.8% |
| Colorado | 25.1% | 0 / 2 | 1 / 2 | 1 / 3 (0.8) | 1.8% → 2.3% |
| Michigan | 25.0% | 0 / 2 | 1 / 1 | 1 / 3 (0.8) | 0.6% → 0.7% |
| Mississippi | 25.1% | 1 / 1 | 1 / 3 | 1 / 3 (0.8) | 0.7% → 1.4% |
| Nevada | 25.1% | 1 / 2 | 2 / 3 | 2 / 3 (0.8) | 1.9% → 2.6% |
| Utah | 25.2% | 1 / 3 | 0 / 2 | 1 / 3 (0.8) | 2.4% → 1.0% |
| Wyoming | 100.0% | 3 / 3 | 2 / 2 | 3 / 3 (all) | 8.2% → 8.2% |

## Quality-gate reviews (2026-11-21)

Run with the three project skills as reviewers on `/designations#native-lands` and the state-page
`#native` section (AZ, NM, SD, OK, HI checked).

**oz2-local-planner — Refine → Ship after fixes.** Works: state-specific counts; Native CDFIs named
and linked; reservation table. Gaps fixed: added a "What this means for projects" paragraph per state
(designated reservation tracts, QROF status, OZ 1.0 reservation tracts losing status with dates from
`timeline.ts`, and the transition-rules link); removed a hardcoded "after 2028". Not fixed: no named
tribal contacts per reservation (the YAML has none beyond `tribal_consultation`; adding them is a
research task).

**oz2-impact-investor — Refine → Ship after fixes.** Works: NMTC track-record signal; Native CDFI
presence; land-tenure note. Gaps fixed: QROF share of designated reservation tracts stated with the
30%/50% mechanics; leasehold-vs-fee note; HEARTH Act leasing (BIA or tribal approval); explicit
statement that OZ 1.0 equity reaching reservation tracts cannot be measured. Not fixed: Native CDFI
specialties beyond institution type (would need each CDFI's product data).

**oz2-community-matchmaker — Refine → Ship after fixes.** Works: sovereignty framing ("the tribal
government is a principal"); statistical-area / *McGirt* handling; Native CDFIs as structuring
partners; the "tribes may decline nomination" caveat on the model. Gaps fixed: named the Cherokee
Nation tribe-led program as an alternative to state designation; added the consultation-framework
comparison. Not fixed: no tribe-by-tribe record of whether tribes sought or declined nomination —
that is primary research with tribal governments, not a data join.

## Not done

- Tribal contacts per reservation; tribe-by-tribe nomination positions.
- Native CDFI service areas (CDFI Fund target-market data) instead of HQ points.
- `references.md` HEARTH Act entry is from knowledge; confirm with a fetch (law.cornell.edu not allowed here).
