import { readFileSync } from 'fs';
import { join } from 'path';
import yaml from 'js-yaml';

export interface LeadAgency {
  name: string | null;
  url: string | null;
  contact_email: string | null;
  contact_phone: string | null;
}

export interface County {
  fips: string;
  name: string;
  eligible_count: number;
}

export interface TribalConsultation {
  framework: string | null;
  citation: string | null;
}

export interface PartnerOrg {
  name: string;
  url: string;
}

export interface RuralPartners {
  usda_rd_url: string | null;
  rcap_regional: PartnerOrg | null;
  rural_lisc: PartnerOrg | null;
}

export interface RegionalEdd {
  name: string;
  url: string | null;
  counties_served: string[];
}

export type StatusTier = 'public_process' | 'contact_only' | 'no_public_process';

/**
 * How the state's *federal* filing stands — a different question from
 * `status_tier`, which describes its own public input process.
 *
 *   filed_confirmed — the state publicly confirmed what it sent Treasury
 *   filed_assumed   — window closed, presumed filed, nothing published
 *   unknown         — no information either way
 *   certified       — Treasury published the state's designations (Oct 30, 2026);
 *                     tract_count is now the certified count
 */
export type NominationStatus = 'certified' | 'filed_confirmed' | 'filed_assumed' | 'unknown';

export interface Nomination {
  status: NominationStatus;
  submitted_date: string | null;
  tract_count: number | null;
  off_list_count: number | null;
  list_published_url: string | null;
  source_url: string | null;
  source_note: string | null;
  last_checked: string;
}

/** Treasury's final 2027 QOZ designations. See scripts/patch_designation_status.py. */
export interface Designation {
  published: string;
  eligible_final: number;
  designated: number;
  designated_rural: number;
  cap: number;
  oz1_redesignated: number;
  oz1_lost: number;
  counties_designated: number;
  source_url: string;
}

export interface StateMetadata {
  name: string;
  fips: string;
  slug: string;
  total_eligible: number;
  rural_eligible: number;
  pct_rural: number;
  max_designations: number;
  top10_counties: County[];
  status_tier: StatusTier;
  last_checked: string;
  lead_agency: LeadAgency;
  process: string | null;
  scoring_rubric_url: string | null;
  state_deadline: string | null;
  application_portal_url: string | null;
  tribal_consultation: TribalConsultation;
  regional_edds: RegionalEdd[];
  rural_partners: RuralPartners;
  state_cdfi_count: number | null;
  dci_q1_tracts: number | null;
  pp_county_count: number | null;
  nmtc_projects: number | null;
  cra_lmi_tracts: number | null;
  ui_invest_q1_tracts: number | null;
  nomination: Nomination;
  designation: Designation;
  notes: string | null;
}

let _cache: Record<string, StateMetadata> | null = null;

function load(): Record<string, StateMetadata> {
  if (_cache) return _cache;
  const raw = readFileSync(join(process.cwd(), 'state_metadata.yaml'), 'utf8');
  _cache = yaml.load(raw) as Record<string, StateMetadata>;
  // PyYAML writes FIPS codes like 08 and 09 unquoted (they are not valid YAML 1.1 octal),
  // and js-yaml (YAML 1.2) reads them back as the numbers 8 and 9. Normalize so lookups by
  // FIPS — GeoJSON paths, designation data — work for Colorado and Connecticut.
  for (const s of Object.values(_cache)) {
    s.fips = String(s.fips).padStart(2, '0');
    for (const c of s.top10_counties ?? []) c.fips = String(c.fips).padStart(5, '0');
  }
  return _cache;
}

export function getAllStates(): StateMetadata[] {
  return Object.values(load()).sort((a, b) => a.name.localeCompare(b.name));
}

export function getState(slug: string): StateMetadata | undefined {
  return load()[slug];
}

export function getStateSlugs(): string[] {
  return Object.keys(load());
}

// ---------------------------------------------------------------------------
// Designation detail (data/designations_by_state.json, from analyze_designations.py)
// ---------------------------------------------------------------------------

export type TractTag =
  | 'qrof' | 'oz1' | 'nmtc' | 'cra' | 'tribal' | 'housing' | 'vacancy' | 'sweetspot' | 'ppov' | 'added';

export interface DesignatedTract {
  geoid: string;
  county: string;
  place: string | null;
  rural: boolean;
  pov: number | null;      // poverty rate, %
  mfi: number | null;      // median family income, % of area median
  pop: number | null;
  renter: number | null;   // %
  vac: number | null;      // %
  unemp: number | null;    // %
  hv: number | null;       // median home value
  ui: number | null;       // Urban Institute tier 1–3
  nmtc_n: number;
  nmtc_usd: number;
  cdes: string[];
  tribal: string | null;
  tags: TractTag[];
}

export interface DesignationCounty {
  fips: string;
  name: string;
  eligible: number;
  designated: number;
  rural: number;
  oz1_kept: number;
  oz1_lost: number;
  pop: number;
  cdes: string[];
}

export interface StateDesignationDetail {
  tracts: DesignatedTract[];
  counties: DesignationCounty[];
  oz1_lost: number;
}

let _detail: Record<string, StateDesignationDetail> | null = null;

export function getDesignationDetail(fips: string): StateDesignationDetail {
  if (!_detail) {
    _detail = JSON.parse(readFileSync(join(process.cwd(), 'data', 'designations_by_state.json'), 'utf8'));
  }
  return _detail![fips] ?? { tracts: [], counties: [], oz1_lost: 0 };
}

let _analysis: any = null;

/** National and per-state post-mortem output (data/designation_analysis.json). */
export function getDesignationAnalysis(): any {
  if (!_analysis) {
    _analysis = JSON.parse(readFileSync(join(process.cwd(), 'data', 'designation_analysis.json'), 'utf8'));
  }
  return _analysis;
}

export const TAG_LABELS: Record<TractTag, string> = {
  qrof: 'Rural / QROF',
  oz1: 'Former OZ 1.0',
  nmtc: 'NMTC track record',
  cra: 'CRA-eligible',
  tribal: 'Tribal',
  housing: 'Housing pressure',
  vacancy: 'High vacancy',
  sweetspot: 'UI Tier 1',
  ppov: 'Persistent poverty',
  added: 'Added Oct. 2026',
};
