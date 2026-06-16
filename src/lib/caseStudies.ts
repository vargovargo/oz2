import { readFileSync } from 'fs';
import { join } from 'path';
import yaml from 'js-yaml';

export type SectorTag =
  | 'affordable_housing'
  | 'small_business'
  | 'broadband'
  | 'healthcare'
  | 'manufacturing'
  | 'mixed_use'
  | 'anchor_institution'
  | 'rural_development';

export type SizeTag = 'small' | 'medium' | 'large';

export type SourceType = 'press_release' | 'aggregator_writeup' | 'news';

export interface CaseStudy {
  id: string;
  title: string;
  state: string;
  state_slug: string | null;
  location: string;
  sector_tags: SectorTag[];
  size_tag: SizeTag;
  investment_amount_usd: number | null;
  year: number;
  rural: boolean;
  summary: string;
  source_name: string;
  source_url: string;
  source_type: SourceType;
  last_checked: string;
}

let _cache: CaseStudy[] | null = null;

function load(): CaseStudy[] {
  if (_cache) return _cache;
  const raw = readFileSync(join(process.cwd(), 'data/case_studies.yaml'), 'utf8');
  _cache = yaml.load(raw) as CaseStudy[];
  return _cache;
}

export function getAllCaseStudies(): CaseStudy[] {
  return [...load()].sort((a, b) => a.title.localeCompare(b.title));
}

export function getAllSectorTags(): SectorTag[] {
  const tags = new Set<SectorTag>();
  for (const study of load()) {
    for (const tag of study.sector_tags) tags.add(tag);
  }
  return [...tags].sort();
}
