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

export interface RuralPartners {
  usda_rd_url: string | null;
  rcap_regional: string | null;
  rural_lisc: string | null;
}

export interface RegionalEdd {
  name: string;
  url: string | null;
  counties_served: string[];
}

export type StatusTier = 'public_process' | 'contact_only' | 'no_public_process';

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
  notes: string | null;
}

let _cache: Record<string, StateMetadata> | null = null;

function load(): Record<string, StateMetadata> {
  if (_cache) return _cache;
  const raw = readFileSync(join(process.cwd(), 'state_metadata.yaml'), 'utf8');
  _cache = yaml.load(raw) as Record<string, StateMetadata>;
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
