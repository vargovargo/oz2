import { readFileSync } from 'fs';
import { join } from 'path';
import yaml from 'js-yaml';

export type ModuleId =
  | 'tax-incentive'
  | 'capital-stacks'
  | 'banks-and-cra'
  | 'cdfis'
  | 'deal-economics'
  | 'evidence-check';

export interface StudyModule {
  id: ModuleId;
  number: number;
  title: string;
  short: string;
}

export interface StudyPrompt {
  id: string;
  module: ModuleId;
  prompt: string;
  why: string;
  followups?: string[];
}

export interface GlossaryTerm {
  term: string;
  expansion: string | null;
  definition: string;
  see_also: string[];
  site_link: string | null;
}

/**
 * Module order and titles. The ids double as section anchors on /learn and as
 * the `module` values in data/study_prompts.yaml.
 */
const MODULES: StudyModule[] = [
  {
    id: 'tax-incentive',
    number: 1,
    title: 'How the tax incentive actually works',
    short: 'Tax incentive',
  },
  {
    id: 'capital-stacks',
    number: 2,
    title: 'Reading a capital stack',
    short: 'Capital stacks',
  },
  {
    id: 'banks-and-cra',
    number: 3,
    title: 'Banks and the Community Reinvestment Act',
    short: 'Banks & CRA',
  },
  {
    id: 'cdfis',
    number: 4,
    title: 'CDFIs',
    short: 'CDFIs',
  },
  {
    id: 'deal-economics',
    number: 5,
    title: 'Deal economics',
    short: 'Deal economics',
  },
  {
    id: 'evidence-check',
    number: 6,
    title: 'The evidence check',
    short: 'Evidence check',
  },
];

let _prompts: StudyPrompt[] | null = null;
let _glossary: GlossaryTerm[] | null = null;

function loadPrompts(): StudyPrompt[] {
  if (_prompts) return _prompts;
  const raw = readFileSync(join(process.cwd(), 'data/study_prompts.yaml'), 'utf8');
  _prompts = yaml.load(raw) as StudyPrompt[];
  return _prompts;
}

function loadGlossary(): GlossaryTerm[] {
  if (_glossary) return _glossary;
  const raw = readFileSync(join(process.cwd(), 'data/glossary.yaml'), 'utf8');
  _glossary = yaml.load(raw) as GlossaryTerm[];
  return _glossary;
}

export function getModules(): StudyModule[] {
  return MODULES;
}

export function getModule(id: ModuleId): StudyModule | undefined {
  return MODULES.find(m => m.id === id);
}

export function getStudyPrompts(): StudyPrompt[] {
  return loadPrompts();
}

export function getPromptsByModule(id: ModuleId): StudyPrompt[] {
  return loadPrompts().filter(p => p.module === id);
}

/** Sort key ignoring leading symbols, so "§ 6039K" files under 6 rather than ahead of everything. */
function sortKey(term: string): string {
  return term.replace(/^[^0-9a-z]+/i, '');
}

export function getGlossary(): GlossaryTerm[] {
  return [...loadGlossary()].sort((a, b) =>
    sortKey(a.term).localeCompare(sortKey(b.term), 'en', { sensitivity: 'base' })
  );
}
