/**
 * Single source of truth for the OZ 2.0 program timeline.
 *
 * Every page that says something date-dependent ("the window is open", "days
 * left", "designations take effect") should derive it from here rather than
 * hardcoding a phrase. Three prior sessions had to sweep the site for stale
 * tense because the dates were scattered across page copy; this module exists
 * so that stops happening.
 *
 * Statutory citations:
 *   IRC § 1400Z-1(b)(1), as amended by P.L. 119-21 (OBBBA) § 70421 —
 *     90-day determination period beginning July 1, 2026; one 30-day extension
 *     available on the Governor's request; Treasury has 30 days to certify,
 *     also extendable by 30 days.
 *   IRC § 1400Z-1(f) — designations take effect January 1, 2027 and remain in
 *     effect for the 10 calendar years through December 31, 2036.
 *   IRS Notice 2026-40 — OZ 1.0 designations expire December 31, 2028
 *     (Puerto Rico: December 31, 2027), creating a 2027–2028 overlap.
 *
 * See references.md §17.
 */

/** ISO date strings. Deadlines resolve to end-of-day, start dates to open-of-day; see dEnd/dStart. */
export const DATES = {
  /** Rev. Proc. 2026-14 eligible-tract appendix published. */
  eligibleListPublished: '2026-04-06',
  /** Determination period opens. */
  windowOpens: '2026-07-01',
  /** Statutory close of the 90-day determination period. */
  windowCloses: '2026-09-28',
  /** Latest close if the Governor requests the single 30-day extension. */
  windowClosesExtended: '2026-10-28',
  /** Comment deadline on REG-116506-25 (OZ information reporting). */
  reportingCommentDeadline: '2026-10-26',
  /** Public hearing on REG-116506-25. */
  reportingHearing: '2026-11-05',
  /** Latest possible Treasury certification (30 + 30 days from a maximally extended filing). */
  certificationLatest: '2026-12-27',
  /** Mandatory OZ 1.0 deferred-gain inclusion date. Cannot itself be re-deferred. */
  oz1GainInclusion: '2026-12-31',
  /** OZ 2.0 designations take effect. */
  designationsEffective: '2027-01-01',
  /** Puerto Rico OZ 1.0 designations expire. */
  oz1ExpiresPuertoRico: '2027-12-31',
  /** All other OZ 1.0 designations expire. */
  oz1Expires: '2028-12-31',
  /** First OZ 2.0 designation period ends. */
  designationsExpire: '2036-12-31',
} as const;

export type Phase =
  | 'pre_window'      // before July 1, 2026
  | 'window_open'     // governors filing
  | 'awaiting_certification' // window closed (or extended), Treasury reviewing
  | 'designated'      // designations in effect
  | 'post_period';    // after 2036

/**
 * Deadline dates are inclusive of the whole day — a September 28 filing deadline
 * is live until 11:59pm on the 28th.
 */
function dEnd(iso: string): Date {
  return new Date(iso + 'T23:59:59.999');
}

/**
 * Start dates take effect at the opening of the day — designations effective
 * January 1, 2027 are in effect at 00:00 on January 1, not at the end of it.
 */
function dStart(iso: string): Date {
  return new Date(iso + 'T00:00:00');
}

/**
 * Whole days from `now` until `iso`. Deadlines count the target day itself, so
 * the last day of a window reads as 1 rather than 0; start dates count to the
 * moment they begin.
 */
export function daysUntil(iso: string, now: Date = asOf(), kind: 'deadline' | 'start' = 'deadline'): number {
  const target = kind === 'start' ? dStart(iso) : dEnd(iso);
  return Math.ceil((target.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
}

/**
 * Build-time "now". Set OZ2_AS_OF=YYYY-MM-DD to render the site as it will look
 * on a future date — used to check phase-dependent copy before a boundary
 * arrives, since a static build freezes whatever `new Date()` returned.
 */
export function asOf(): Date {
  const override = typeof process !== 'undefined' ? process.env?.OZ2_AS_OF : undefined;
  if (override && /^\d{4}-\d{2}-\d{2}$/.test(override)) {
    return new Date(override + 'T12:00:00');
  }
  return new Date();
}

export function currentPhase(now: Date = asOf()): Phase {
  if (now < dStart(DATES.windowOpens)) return 'pre_window';
  if (now <= dEnd(DATES.windowCloses)) return 'window_open';
  if (now < dStart(DATES.designationsEffective)) return 'awaiting_certification';
  if (now <= dEnd(DATES.designationsExpire)) return 'designated';
  return 'post_period';
}

/** Human-readable date, e.g. "September 28, 2026". */
export function fmt(iso: string): string {
  const [y, m, day] = iso.split('-').map(Number);
  return new Date(y, m - 1, day).toLocaleDateString('en-US', {
    month: 'long', day: 'numeric', year: 'numeric',
  });
}

/** Short form, e.g. "Sept. 28". */
export function fmtShort(iso: string): string {
  const [y, m, day] = iso.split('-').map(Number);
  return new Date(y, m - 1, day).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export interface PhaseCopy {
  /** One-line status for the footer and banners. */
  banner: string;
  /** The single most relevant countdown to show in a stat tile. */
  counter: { label: string; value: number | string };
  /** What a local reader should do right now. */
  callToAction: string;
}

export function phaseCopy(now: Date = asOf()): PhaseCopy {
  const phase = currentPhase(now);

  switch (phase) {
    case 'pre_window':
      return {
        banner: `Governors' nomination window opens ${fmt(DATES.windowOpens)}.`,
        counter: { label: 'Days until the window opens', value: daysUntil(DATES.windowOpens, now, 'start') },
        callToAction: 'Get your case in front of the state lead agency before the window opens.',
      };

    case 'window_open': {
      const left = daysUntil(DATES.windowCloses, now);
      return {
        banner: `Governors are filing nominations — the federal window closes ${fmt(DATES.windowCloses)}.`,
        counter: { label: 'Days left in the federal window', value: left },
        callToAction:
          'Most state input windows have closed, but governors can revise their filings until the window shuts. Direct contact with the lead agency still counts.',
      };
    }

    case 'awaiting_certification':
      return {
        banner: `Nominations are with Treasury. Designations take effect ${fmt(DATES.designationsEffective)}.`,
        counter: {
          label: 'Days until designations take effect',
          value: daysUntil(DATES.designationsEffective, now, 'start'),
        },
        callToAction:
          'The map is out of local hands. Shift to readiness: line up the capital stack, the site control, and the community benefit terms you want attached to whatever gets designated.',
      };

    case 'designated':
      return {
        banner: `OZ 2.0 designations are in effect through ${fmt(DATES.designationsExpire)}.`,
        counter: {
          label: 'Years left in the designation period',
          // Calendar-year arithmetic: day-count / 365 rounds up to 11 on day one
          // of a ten-year period because of leap days.
          value: Math.max(0, Number(DATES.designationsExpire.slice(0, 4)) - now.getFullYear() + 1),
        },
        callToAction:
          'Designation is the beginning, not the end. What matters now is which projects get financed and on what terms.',
      };

    case 'post_period':
      return {
        banner: `The first OZ 2.0 designation period ended ${fmt(DATES.designationsExpire)}.`,
        counter: { label: 'Designation period', value: 'Ended' },
        callToAction: 'The next decennial designation cycle governs from here.',
      };
  }
}

/** Milestones for the /whats-next timeline, in order. */
export interface Milestone {
  date: string;
  label: string;
  detail: string;
  /** true when this milestone is not a fixed date but a window or contingency. */
  contingent?: boolean;
}

export const MILESTONES: Milestone[] = [
  {
    date: DATES.windowCloses,
    label: "Governors' filing deadline",
    detail:
      'Close of the 90-day determination period that opened July 1. A governor may request one 30-day extension, moving that state to October 28. States can revise a filing any time before their window shuts; Treasury does not process early filings until the window closes.',
  },
  {
    date: DATES.reportingCommentDeadline,
    label: 'Comments close on the OZ reporting rule',
    detail:
      'REG-116506-25 builds out the § 6039K / § 6039L information-reporting regime and new QOF certification and decertification procedures. A public hearing follows on November 5, 2026. This is the rule that determines how much the public will be able to see about where OZ 2.0 money actually goes.',
  },
  {
    date: DATES.certificationLatest,
    label: 'Latest possible Treasury certification',
    detail:
      'Treasury has 30 days from receipt to certify a state\'s nominations, extendable by another 30. For a state that used the full extension, that pushes certification as late as December 27, 2026. Most states should be certified well before then.',
    contingent: true,
  },
  {
    date: DATES.oz1GainInclusion,
    label: 'OZ 1.0 deferred gains become taxable',
    detail:
      'The mandatory inclusion date for gains deferred under the original program. Notice 2026-40 confirms this inclusion cannot itself be deferred by rolling into a new OZ investment.',
  },
  {
    date: DATES.designationsEffective,
    label: 'OZ 2.0 designations take effect',
    detail:
      'The new map is live for a ten-year period running through December 31, 2036. The QROF rural provisions — the 30% basis step-up at five years and the 50% substantial-improvement threshold — apply to investments from here.',
  },
  {
    date: DATES.oz1ExpiresPuertoRico,
    label: 'Puerto Rico OZ 1.0 designations expire',
    detail:
      'Puerto Rico tracts deemed designated under the original statute expire a year ahead of the rest.',
  },
  {
    date: DATES.oz1Expires,
    label: 'OZ 1.0 designations expire',
    detail:
      'The end of the 2027–2028 overlap. From here, only OZ 2.0 tracts qualify.',
  },
  {
    date: DATES.designationsExpire,
    label: 'First OZ 2.0 designation period ends',
    detail:
      'OBBBA made designation decennial, so a new round of nominations follows rather than the program lapsing.',
  },
];
