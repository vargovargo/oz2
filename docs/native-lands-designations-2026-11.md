# The 2027 designations through the lens of Native lands (2026-11-21)

Companion to `designation-postmortem-2026-11.md`. Site: `/designations#native-lands` and the
"Native lands and communities" section of each state page. Data: `data/native_lands.parquet`
(`scripts/ingest_native_lands.py`) → `data/native_lands_analysis.json`
(`scripts/analyze_native_lands.py`).

## Two lenses

| Lens | Rule | Eligible | Designated |
|---|---|---:|---:|
| Land | ≥50% of tract area in a federally recognized reservation or off-reservation trust land; Hawaii: ≥10% Hawaiian Home Land | 193 | 62 |
| People | Native residents ≥20% (AIAN alone; Hawaii adds NHPI alone) | 326 | 101 |
| — majority | Native residents ≥50% | 177 | 52 |
| Both | | 167 | 50 |
| Either | | 352 | 113 |

Why these choices:
- **Area share, not "any overlap".** The old `tribal_overlap.parquet` flagged any tract touching any
  AIANNH polygon (1,064 tracts), which picked up border slivers and all of eastern Oklahoma. Area is
  computed in EPSG:6933 on shoreline-clipped cartographic tracts. It is still an area share, not a
  population share: a big rural tract can be mostly reservation by area while most residents live in
  an off-reservation town. Shares are in the parquet, so other thresholds are one line away
  (≥1%: 299 tracts; ≥90%: 157 — lift is ~1.0 at every threshold).
- **Statistical areas kept out of "land".** OTSAs (plus a few TDSAs, e.g. Cayuga Nation), ANVSAs and
  SDTSAs are tabulation areas, not land held by or for a tribe. Reported separately. Oklahoma caveat:
  since *McGirt v. Oklahoma* (2020) and 2021 OCCA rulings, the Muscogee, Cherokee, Chickasaw, Choctaw,
  Seminole and Quapaw reservations are recognized as never disestablished for criminal jurisdiction;
  Census still tabulates them as OTSAs.
- **AIAN alone, not alone-or-in-combination**, as the primary measure; the 2020 jump in multiracial
  AIAN reporting makes AOIC less comparable. AOIC is in the parquet; lifts barely move (≥20% AOIC:
  0.98; ≥50%: 0.91).
- **Hawaii** uses NHPI. Elsewhere NHPI is not counted as Native to the place (e.g. Marshallese
  communities in Arkansas). The Island Areas are not in the ACS; AS, GU, MP, VI designated every
  eligible tract anyway.

## Findings

1. **Neutral on average.** Within-state lift: land 1.01, people 0.96,
   majority-Native 0.88. Other rural tracts: 1.18. Land tracts
   are 92.2% rural, so they did *not* share in the rural preference.
2. **With controls** (same logit as the main post-mortem plus both lenses; n = 22,904):
   land OR 1.01 (95% CI 0.52–1.95, p = 0.98);
   people OR 0.65 (0.4–1.05, p = 0.077).
   The people lens leans negative but is not significant at 0.05. Note the model also controls for
   share of residents of color, which these tracts score high on.
3. **Incumbency held:** 32 of 62 former-OZ-1.0 land tracts were redesignated;
   30 of 131 others.
   So 30 reservation/trust tracts lose OZ status after 2028 — a starting list for the
   transition-affected case studies.
4. **Residents:** 28.7% of Native residents of eligible tracts live in a designated tract,
   vs 26.1% of all residents.
5. **Reservation level:** 76 reservations have an eligible tract ≥50% inside them; 44 got at least one
   designated; 32 in states that had to choose got none. Navajo Nation: 7 of 49 — all 7 in Arizona (7/28);
   New Mexico designated none of its 19 and Utah none of its 2. Hopi, Zuni, Crow: 0 of 3 each.
6. **Statistical areas:** OK OTSAs 65/252 (≈ state rate). SDTSAs
   25/119, mostly North Carolina's Lumbee area (14/74, against a 25% state rate).

## Reservations with ≥3 eligible tracts

| Reservation | State | Designated / eligible |
|---|---|---:|
| Navajo Nation | AZ, NM, UT | 7 / 49 |
| Pine Ridge | SD | 1 / 5 |
| Yakama Nation | WA | 4 / 5 |
| Fort Apache | AZ | 1 / 4 |
| Standing Rock | ND, SD | 1 / 4 |
| Cheyenne River | SD | 1 / 3 |
| Colorado River | AZ, CA | 1 / 3 |
| Colville | WA | 2 / 3 |
| Crow | MT | 0 / 3 |
| Flathead | MT | 1 / 3 |
| Fort Berthold | ND | 2 / 3 |
| Gila River | AZ | 1 / 3 |
| Hopi | AZ | 0 / 3 |
| Osage | OK | 1 / 3 |
| Puyallup | WA | 2 / 3 |
| Tohono O'odham Nation | AZ | 1 / 3 |
| White Earth | MN | 1 / 3 |
| Wind River | WY | 3 / 3 |
| Zuni | NM | 0 / 3 |

Wind River (WY) was designated in full because Wyoming designated every eligible tract.

## States with ≥3 Native land or community tracts

| State | Overall rate | Land | People ≥20% | Either (expected) | Native share of residents, eligible → designated |
|---|---:|---:|---:|---:|---:|
| New Mexico | 25.2% | 6 / 34 | 12 / 55 | 15 / 58 (14.6) | 15.6% → 12.6% |
| Arizona | 25.1% | 14 / 48 | 15 / 52 | 15 / 52 (13.1) | 10.2% → 10.6% |
| Oklahoma | 25.1% | 1 / 3 | 8 / 37 | 8 / 39 (9.8) | 8.3% → 8.9% |
| Hawaii | 28.1% | 2 / 9 | 9 / 25 | 9 / 27 (7.6) | 17.3% → 18.4% |
| North Carolina | 25.1% | 0 / 0 | 2 / 25 | 2 / 25 (6.3) | 2.4% → 1.7% |
| South Dakota | 48.1% | 7 / 18 | 10 / 23 | 10 / 23 (11.1) | 28.7% → 27.0% |
| Montana | 43.1% | 5 / 14 | 5 / 16 | 5 / 17 (7.3) | 21.4% → 19.7% |
| Alaska | 75.8% | 0 / 0 | 13 / 16 | 13 / 16 (12.1) | 38.8% → 36.2% |
| Washington | 25.0% | 9 / 16 | 5 / 10 | 9 / 16 (4.0) | 2.2% → 3.2% |
| California | 25.0% | 2 / 6 | 4 / 8 | 5 / 12 (3.0) | 1.9% → 1.9% |
| New York | 25.0% | 2 / 9 | 0 / 10 | 2 / 12 (3.0) | 1.0% → 1.1% |
| North Dakota | 67.6% | 5 / 8 | 5 / 10 | 5 / 10 (6.8) | 17.2% → 14.8% |
| Minnesota | 25.1% | 2 / 7 | 2 / 8 | 2 / 8 (2.0) | 2.4% → 3.5% |
| Wisconsin | 25.0% | 1 / 4 | 1 / 4 | 1 / 4 (1.0) | 1.3% → 1.8% |
| Colorado | 25.1% | 0 / 2 | 1 / 2 | 1 / 3 (0.8) | 1.8% → 2.3% |
| Idaho | 30.9% | 0 / 3 | 0 / 2 | 0 / 3 (0.9) | 2.1% → 1.2% |
| Michigan | 25.0% | 0 / 2 | 1 / 1 | 1 / 3 (0.8) | 0.6% → 0.7% |
| Mississippi | 25.1% | 1 / 1 | 1 / 3 | 1 / 3 (0.8) | 0.7% → 1.4% |
| Nevada | 25.1% | 0 / 1 | 2 / 3 | 2 / 3 (0.8) | 1.9% → 2.6% |
| Utah | 25.2% | 1 / 3 | 0 / 2 | 1 / 3 (0.8) | 2.4% → 1.0% |
| Wyoming | 100.0% | 3 / 3 | 2 / 2 | 3 / 3 (all) | 8.2% → 8.2% |

## Site changes

- `analyze_designations.py`: the "Tribal overlap" lift row is replaced by the two lenses; the
  `tribal` tag now means ≥10% reservation/trust/Home Land or ≥20% Native residents (381 tracts,
  was 1,064); the national CSV gains `federal_share`, `native_pct`, `native_land`, `native_pop`.
- `patch_geo_native.py`: map GeoJSON `is_tribal_overlap`, `tribal_area_name`, `aian_pct` refreshed;
  `native_land_share`, `hhl_share` added. Popup reworded. Run after any geo patch that appends tracts.
- `/designations#native-lands`, state pages `#native`.

## Not done

- Population-weighted land shares (needs 2020 block populations + Block Assignment Files).
- Native CDFIs and tribal enterprises active in designated tracts (the CDFI Fund's NACA awardee
  list would join on the same pattern as the NMTC CDE list).
- Quality-gate pass with the three project skills.
