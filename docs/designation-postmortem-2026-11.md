# The 2027 designations: post-mortem

*Generated from `data/designation_analysis.json` on 2026-11-05. Rendered for the public at `/designations`.
Regenerate the numbers with `python3 scripts/analyze_designations.py`; this narrative is hand-written around them.*

## The question

Treasury published the final OZ 2.0 list on October 30, 2026. Of 25,462 eligible tracts,
6,576 were designated (2,594 rural). What distinguished the chosen tracts from the
18,886 passed over?

## Data

| Input | Source | Script |
|---|---|---|
| Designations, eligibility, poverty, MFI ratio | Treasury OTP files dated 2026-10-30 (references.md §18) | `ingest_designated_tracts.py` |
| Race/ethnicity, education, employment, housing | ACS 2020–2024 5-year Summary File | `ingest_acs_tract_demographics.py` |
| OZ 1.0 status | Notice 2018-48 / 2019-42 + Census 2020↔2010 relationship file | `ingest_oz1_tracts.py` |
| CRA, DCI, Urban Institute, NMTC, persistent poverty, tribal | Existing site overlays | — |
| Analysis | | `analyze_designations.py` |

## Method

Selection happens within a state, against a fixed cap. All comparisons are therefore within-state:

- **Lift** (yes/no traits): designated tracts with the trait ÷ the count expected if each state picked
  at its own overall rate.
- **Within-state percentile** (continuous traits): mean percentile rank of designated tracts among
  their own state's eligible tracts; 50 = no preference. Decile curves show the shape.
- **Logit** with state fixed effects and county-clustered SEs, continuous terms per SD.

Six jurisdictions designated every eligible tract (VT, WY, AS, GU, MP, VI) and are
excluded from the selection analysis (50 jurisdictions remain).

## Findings

1. **Incumbency.** Former OZ 1.0 tracts were designated 42.6% of the time vs
   19.2% (lift 1.67; logit OR 2.72,
   +16.9 pp). 45.2% of the new map was on the old one.
2. **Deal history.** Prior NMTC investment: lift 1.62, OR 1.79.
3. **Rural tilt.** Lift 1.17; rural share 32.8% of eligible →
   39.4% of designated.
4. **Investability.** Urban Institute Tier 1 lift 1.28, Tier 3 0.86.
5. **Distress did not matter.** EIG DCI percentile 50.3; CRA lift
   1.01; persistent-poverty counties 0.91. Poverty rate tilted
   slightly upward (percentile 54.0).
6. **Shape.** Mid-to-low density favored over the densest cores (density percentile
   44.8); renter-heavy tracts favored (54.6).
   MFI ratio is a shallow U. Education, unemployment, home value: flat.
7. **Race and ethnicity.** Designated tracts had a somewhat smaller share of residents of color than
   passed-over tracts in the same state (percentile 48.1; logit
   -2.7 pp per SD after controls). Partly the rural tilt (rural eligible tracts
   average 39% residents of color vs 72% non-rural), but it survives controls. Black and Hispanic shares
   separately show no consistent pattern. This describes the selected set, not intent.
8. **Most of the choice is unexplained by tract data** — pseudo-R² 0.089. Local advocacy,
   project pipelines, political geography and county spreading are not in the census.

## OZ 1.0 handoff

9,950 2020 tracts were ≥50% inside a 2018 QOZ; 6,882 remain eligible;
2,974 were redesignated; **6,976 were not**. Under Notice 2026-40 those generally cannot take
new capital after 2026 except under a working capital safe harbor plan adopted by 2026-12-31. Listed per
county on each state page. This is the population for the "transition-affected projects" case-study
priority.

## Late additions

130 tracts were added to the eligible list in October under the missing-data rules;
15 were designated (11.5%). No designated tract is outside the eligible list.

## Tables

### Lift by trait

| Trait | Eligible with trait | Designated | Rate with | Rate without | Lift |
|---|---:|---:|---:|---:|---:|
| Was an OZ 1.0 tract | 6,808 | 2,900 | 42.6% | 19.2% | 1.67 |
| Prior NMTC investment | 3,187 | 1,335 | 41.9% | 23.1% | 1.62 |
| Urban Institute Tier 1 | 5,684 | 1,845 | 32.5% | 23.5% | 1.28 |
| Rural (QROF) | 8,249 | 2,481 | 30.1% | 23.3% | 1.17 |
| CRA-eligible | 18,871 | 4,860 | 25.8% | 24.7% | 1.01 |
| Tribal overlap | 1,064 | 296 | 27.8% | 25.4% | 1.01 |
| Persistent-poverty county | 3,136 | 722 | 23.0% | 25.8% | 0.91 |
| Urban Institute Tier 3 (low probability) | 14,825 | 3,262 | 22.0% | 30.4% | 0.86 |
| Added in October (missing-data rule) | 130 | 15 | 11.5% | 25.6% | 0.45 |

### Within-state percentile and decile curve (designation rate % by tenth, lowest → highest)

| Trait | Percentile | Deciles |
|---|---:|---|
| Poverty rate | 54.0 | 18.8 · 22.1 · 21.8 · 24.8 · 25.9 · 26.0 · 26.9 · 28.3 · 30.3 · 29.8 |
| Median family income, % of area | 48.7 | 30.5 · 27.5 · 26.8 · 23.8 · 24.8 · 22.6 · 25.1 · 21.6 · 25.1 · 27.0 |
| Population | 51.2 | 24.9 · 23.7 · 25.5 · 25.2 · 24.1 · 24.4 · 25.4 · 26.8 · 25.5 · 29.1 |
| Population density | 44.8 | 26.8 · 33.4 · 31.8 · 29.7 · 28.5 · 24.6 · 23.9 · 20.6 · 18.3 · 17.2 |
| Unemployment rate | 50.5 | 24.8 · 25.0 · 25.2 · 25.8 · 24.5 · 26.6 · 26.3 · 24.8 · 25.8 · 26.2 |
| Adults with a BA or more | 50.4 | 25.4 · 26.3 · 24.7 · 25.0 · 25.3 · 25.6 · 24.3 · 24.9 · 25.6 · 27.6 |
| Renter-occupied share | 54.6 | 18.4 · 21.7 · 23.6 · 23.8 · 23.5 · 25.7 · 26.5 · 27.8 · 31.0 · 33.0 |
| Housing vacancy rate | 52.3 | 22.9 · 22.6 · 23.3 · 23.5 · 26.6 · 26.2 · 26.4 · 29.4 · 28.2 · 26.1 |
| Renters cost-burdened | 49.1 | 24.3 · 26.7 · 26.9 · 26.3 · 26.5 · 26.3 · 26.7 · 25.2 · 25.2 · 20.9 |
| Median home value | 49.6 | 26.3 · 24.3 · 26.7 · 26.4 · 25.4 · 26.6 · 23.6 · 24.1 · 23.3 · 26.1 |
| Residents of color | 48.1 | 24.9 · 28.4 · 28.0 · 28.1 · 26.5 · 25.8 · 25.3 · 24.3 · 22.1 · 21.5 |
| Black residents | 50.5 | 21.7 · 24.0 · 27.2 · 25.4 · 26.0 · 29.0 · 26.3 · 28.4 · 23.7 · 23.1 |
| Hispanic residents | 49.8 | 24.2 · 25.9 · 27.0 · 25.2 · 26.7 · 25.8 · 25.8 · 25.2 · 25.4 · 23.7 |
| EIG distress score (higher = more distressed) | 50.3 | 25.2 · 25.5 · 25.0 · 24.9 · 26.1 · 25.9 · 24.9 · 27.0 · 25.9 · 25.1 |

### Logit (state FE, county-clustered SE; n = 22,904, pseudo-R² 0.089)

| Term | AME (pp) | OR | p |
|---|---:|---:|---:|
| `is_oz1` | +16.9 | 2.72 | 4.4e-48 |
| `has_nmtc` | +9.8 | 1.79 | 1e-29 |
| `pct_renter_z` | +6.5 | 1.47 | 1.5e-44 |
| `log_density_z` | -5.4 | 0.72 | 3.7e-19 |
| `is_rural` | +5.2 | 1.36 | 1.5e-06 |
| `ui_tier1` | +4.1 | 1.27 | 0.023 |
| `ui_tier3` | -4.0 | 0.79 | 0.0011 |
| `pct_nonwhite_z` | -2.7 | 0.85 | 1.2e-06 |
| `pop_z` | +2.1 | 1.14 | 4.5e-10 |
| `median_home_value_z` | -1.6 | 0.91 | 0.03 |
| `poverty_rate_z` | +1.2 | 1.07 | 0.006 |
| `vacancy_rate_z` | -0.9 | 0.95 | 0.023 |
| `unemp_rate_z` | -0.7 | 0.96 | 0.04 |
| `is_cra_lmi` | -0.7 | 0.96 | 0.36 |
| `mfi_ratio_z` | +0.4 | 1.02 | 0.35 |
| `pct_ba_plus_z` | +0.3 | 1.02 | 0.48 |

### By state (eligible → designated)

| State | Designated / eligible | Rural % | OZ 1.0 % | Median poverty | Largest differences |
|---|---:|---:|---:|---:|---|
| AK | 25/33 | 63.6 → 68.0 | 39.4 → 44.0 | 13.6 → 17.3 | favored less dense tracts; favored less populous tracts; passed over tracts with prior NMTC deals |
| AL | 141/563 | 53.6 → 46.1 | 24.0 → 51.1 | 25.8 → 28.4 | favored former OZ 1.0 tracts; favored renter-heavy tracts; favored Urban Institute Tier 1 tracts |
| AR | 78/310 | 69.7 → 62.8 | 24.5 → 48.7 | 25.4 → 25.4 | favored former OZ 1.0 tracts; favored tracts with prior NMTC deals; favored renter-heavy tracts |
| AS | 16/16 | 100.0 → 100.0 | 100.0 → 100.0 | None → 53.8 | all eligible designated |
| AZ | 127/506 | 27.7 → 31.5 | 24.1 → 52.0 | 23.0 → 25.2 | favored former OZ 1.0 tracts; favored less dense tracts; favored tracts with prior NMTC deals |
| CA | 620/2479 | 14.0 → 17.1 | 30.6 → 37.4 | 21.0 → 23.3 | favored Urban Institute Tier 1 tracts; favored higher-poverty tracts; favored tracts with prior NMTC deals |
| CO | 91/362 | 28.2 → 30.8 | 23.2 → 50.5 | 16.6 → 20.7 | favored former OZ 1.0 tracts; favored less dense tracts; favored tracts with prior NMTC deals |
| CT | 61/243 | 12.3 → 21.3 | 25.1 → 60.7 | 21.0 → 24.3 | favored former OZ 1.0 tracts; favored renter-heavy tracts; favored Urban Institute Tier 1 tracts |
| DC | 25/69 | 0.0 → 0.0 | 29.0 → 68.0 | 29.5 → 28.3 | favored former OZ 1.0 tracts; favored tracts with prior NMTC deals; favored less dense tracts |
| DE | 25/61 | 36.1 → 48.0 | 31.1 → 72.0 | 20.0 → 23.5 | favored former OZ 1.0 tracts; favored renter-heavy tracts; favored higher-poverty tracts |
| FL | 342/1367 | 20.8 → 28.7 | 26.0 → 36.3 | 22.3 → 23.4 | favored former OZ 1.0 tracts; favored tracts with prior NMTC deals; favored less dense tracts |
| GA | 238/949 | 44.4 → 49.6 | 27.7 → 32.8 | 23.8 → 23.7 | favored renter-heavy tracts; favored tracts with prior NMTC deals; favored Urban Institute Tier 1 tracts |
| GU | 20/20 | 100.0 → 100.0 | 50.0 → 50.0 | None → 25.7 | all eligible designated |
| HI | 25/89 | 40.4 → 32.0 | 16.9 → 48.0 | 18.9 → 20.2 | favored former OZ 1.0 tracts; favored renter-heavy tracts; favored higher-poverty tracts |
| IA | 44/175 | 33.1 → 47.7 | 21.1 → 45.5 | 22.3 → 23.0 | favored former OZ 1.0 tracts; favored tracts with prior NMTC deals; favored less dense tracts |
| ID | 25/81 | 40.7 → 36.0 | 12.3 → 20.0 | 20.4 → 20.9 | favored Urban Institute Tier 1 tracts; favored renter-heavy tracts; favored former OZ 1.0 tracts |
| IL | 240/957 | 22.2 → 32.5 | 29.0 → 31.7 | 23.2 → 24.4 | favored tracts with prior NMTC deals; favored less dense tracts; favored rural tracts |
| IN | 126/503 | 23.9 → 33.3 | 22.3 → 53.2 | 24.3 → 25.2 | favored former OZ 1.0 tracts; favored tracts with prior NMTC deals; favored rural tracts |
| KS | 53/211 | 36.0 → 50.9 | 18.5 → 35.8 | 22.2 → 23.5 | favored former OZ 1.0 tracts; favored rural tracts; favored tracts with fewer residents of color |
| KY | 137/546 | 70.0 → 65.7 | 24.9 → 38.7 | 25.5 → 25.3 | favored more populous tracts; favored former OZ 1.0 tracts; favored tracts with prior NMTC deals |
| LA | 156/621 | 49.9 → 52.6 | 20.9 → 39.7 | 28.8 → 30.3 | favored former OZ 1.0 tracts; favored less dense tracts; favored tracts with prior NMTC deals |
| MA | 104/414 | 14.3 → 21.2 | 24.4 → 56.7 | 20.5 → 24.3 | favored former OZ 1.0 tracts; favored tracts with prior NMTC deals; favored renter-heavy tracts |
| MD | 114/454 | 17.0 → 25.4 | 24.4 → 50.9 | 16.8 → 21.1 | favored former OZ 1.0 tracts; favored Urban Institute Tier 1 tracts; favored higher-poverty tracts |
| ME | 25/78 | 94.9 → 88.0 | 17.9 → 32.0 | 20.2 → 23.2 | favored renter-heavy tracts; favored higher-poverty tracts; favored lower-vacancy tracts |
| MI | 215/860 | 29.2 → 27.9 | 22.8 → 47.0 | 26.8 → 27.6 | favored former OZ 1.0 tracts; favored tracts with prior NMTC deals; favored renter-heavy tracts |
| MN | 73/291 | 36.8 → 39.7 | 29.9 → 58.9 | 17.2 → 20.2 | favored former OZ 1.0 tracts; favored tracts with prior NMTC deals; favored renter-heavy tracts |
| MO | 131/523 | 42.1 → 51.9 | 25.4 → 40.5 | 22.4 → 25.4 | favored former OZ 1.0 tracts; favored renter-heavy tracts; favored tracts with fewer residents of color |
| MP | 19/19 | 100.0 → 100.0 | 94.7 → 94.7 | None → 38.7 | all eligible designated |
| MS | 102/406 | 79.3 → 76.5 | 20.7 → 53.9 | 28.0 → 29.3 | favored former OZ 1.0 tracts; favored tracts with prior NMTC deals; favored renter-heavy tracts |
| MT | 25/58 | 63.8 → 60.0 | 29.3 → 40.0 | 24.2 → 23.8 | favored Urban Institute Tier 1 tracts; favored tracts with prior NMTC deals; favored renter-heavy tracts |
| NC | 204/814 | 52.9 → 61.8 | 24.0 → 41.7 | 23.4 → 23.1 | favored former OZ 1.0 tracts; favored less dense tracts; favored tracts with prior NMTC deals |
| ND | 25/37 | 48.6 → 44.0 | 40.5 → 44.0 | 25.8 → 23.8 | favored more populous tracts; favored lower-vacancy tracts; favored tracts with fewer residents of color |
| NE | 28/112 | 25.0 → 42.9 | 23.2 → 46.4 | 21.0 → 22.1 | favored former OZ 1.0 tracts; favored rural tracts; favored more populous tracts |
| NH | 25/53 | 67.9 → 68.0 | 35.8 → 56.0 | 12.5 → 21.1 | favored higher-poverty tracts; favored former OZ 1.0 tracts; favored renter-heavy tracts |
| NJ | 130/518 | 7.1 → 10.0 | 25.7 → 53.8 | 20.7 → 22.6 | favored former OZ 1.0 tracts; favored less dense tracts; favored tracts with prior NMTC deals |
| NM | 65/258 | 63.6 → 55.4 | 20.5 → 24.6 | 28.1 → 29.7 | favored tracts with prior NMTC deals; favored Urban Institute Tier 1 tracts; favored renter-heavy tracts |
| NV | 49/195 | 12.8 → 28.6 | 21.5 → 38.8 | 22.6 → 25.2 | favored less dense tracts; favored rural tracts; favored former OZ 1.0 tracts |
| NY | 430/1717 | 17.8 → 28.8 | 25.1 → 50.5 | 23.8 → 27.8 | favored former OZ 1.0 tracts; favored tracts with prior NMTC deals; favored rural tracts |
| OH | 260/1040 | 26.9 → 36.9 | 22.7 → 45.4 | 26.5 → 27.5 | favored former OZ 1.0 tracts; favored less dense tracts; favored tracts with prior NMTC deals |
| OK | 104/414 | 45.4 → 54.8 | 19.6 → 42.3 | 24.3 → 25.7 | favored former OZ 1.0 tracts; favored less dense tracts; favored renter-heavy tracts |
| OR | 58/229 | 46.3 → 55.2 | 23.6 → 48.3 | 21.0 → 21.8 | favored former OZ 1.0 tracts; favored tracts with prior NMTC deals; favored renter-heavy tracts |
| PA | 218/871 | 31.6 → 34.9 | 26.3 → 43.6 | 23.6 → 25.7 | favored former OZ 1.0 tracts; favored renter-heavy tracts; favored tracts with prior NMTC deals |
| PR | 178/712 | 34.1 → 46.1 | 99.4 → 99.4 | 46.2 → 47.7 | favored less dense tracts; favored rural tracts; favored more populous tracts |
| RI | 25/55 | 1.8 → 4.0 | 29.1 → 56.0 | 23.8 → 22.9 | favored former OZ 1.0 tracts; favored less dense tracts; favored tracts with prior NMTC deals |
| SC | 113/449 | 73.1 → 75.2 | 23.4 → 46.0 | 24.1 → 26.5 | favored former OZ 1.0 tracts; favored renter-heavy tracts; favored more populous tracts |
| SD | 25/52 | 67.3 → 72.0 | 38.5 → 72.0 | 28.3 → 23.0 | favored former OZ 1.0 tracts; favored lower-poverty tracts; favored less dense tracts |
| TN | 128/509 | 43.6 → 56.2 | 23.4 → 46.1 | 24.9 → 26.7 | favored former OZ 1.0 tracts; favored tracts with prior NMTC deals; favored rural tracts |
| TX | 608/2431 | 21.7 → 30.3 | 20.7 → 33.4 | 24.6 → 25.8 | favored former OZ 1.0 tracts; favored less dense tracts; favored rural tracts |
| UT | 37/147 | 20.4 → 27.0 | 22.4 → 37.8 | 18.2 → 20.3 | favored former OZ 1.0 tracts; passed over Urban Institute Tier 1 tracts; favored rural tracts |
| VA | 153/611 | 47.1 → 50.3 | 26.2 → 47.1 | 18.4 → 20.8 | favored former OZ 1.0 tracts; favored tracts with prior NMTC deals; favored higher-poverty tracts |
| VI | 18/18 | 100.0 → 100.0 | 72.2 → 72.2 | None → 27.9 | all eligible designated |
| VT | 24/24 | 100.0 → 100.0 | 37.5 → 37.5 | None → 17.0 | all eligible designated |
| WA | 99/396 | 37.1 → 36.4 | 23.5 → 49.5 | 16.7 → 20.4 | favored former OZ 1.0 tracts; favored tracts with prior NMTC deals; favored higher-poverty tracts |
| WI | 77/308 | 21.8 → 31.2 | 28.2 → 63.6 | 22.0 → 23.6 | favored former OZ 1.0 tracts; favored tracts with prior NMTC deals; favored less dense tracts |
| WV | 52/208 | 100.0 → 100.0 | 20.2 → 44.2 | 26.0 → 24.5 | favored former OZ 1.0 tracts; favored tracts with more residents of color; favored renter-heavy tracts |
| WY | 20/20 | 80.0 → 80.0 | 40.0 → 40.0 | None → 23.1 | all eligible designated |

## Caveats

- Descriptive, not causal. The logit describes the selected set; it is not a model of governors' intent.
- OZ 1.0 status is itself correlated with tract traits from 2018; incumbency here means "was chosen before."
- Overlays (CRA, DCI, Urban, NMTC) were joined to the April eligible list; the 130 October additions lack them.
- Island Areas are not in the ACS; they are all full-designation jurisdictions and excluded anyway.
- NMTC CDE names are from the CDFI Fund public release and show past activity, not current allocation.
