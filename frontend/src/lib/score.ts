// S3-B1: the one place that decides how a score is shown.
//
// `score_pct` does not mean the same thing for every strategy. Where
// eval/fit_calibration.py has fitted one (S6-A4; today `hybrid` and `hybrid+ce`) it is a
// probability of recognition. Otherwise it is a display number: a stretched cosine for
// `dense`, and for `bm25` a value relative to the best hit for that home course, so the
// top row always reads 100. Printing "87 % chance" over those would be a lie, so nothing
// outside this file is allowed to format a score. The split is read from /strategies,
// never hardcoded here.

import type { Confidence, StrategyInfo } from './api'

export type ScoreKind = 'probability' | 'relative'
export type Band = 'likely' | 'borderline' | 'unlikely'

// Same thresholds as backend/app/matching/aggregate.py, deliberately.
const LIKELY = 70
const BORDERLINE = 40

export function scoreKind(info: StrategyInfo | undefined): ScoreKind {
  return info?.calibrated ? 'probability' : 'relative'
}

// S3-B1's floor. When even the most probable candidate for a course is below this, the
// honest answer is "no suitable match", not a weak top hit in amber. Only applies to
// calibrated scores: a relative score of 12 says nothing about whether the match is good.
export const NO_MATCH_BELOW = 20

export function noSuitableMatch(kind: ScoreKind, pcts: number[]): boolean {
  return kind === 'probability' && pcts.length > 0 && Math.max(...pcts) < NO_MATCH_BELOW
}

export function bandOf(pct: number): Band {
  if (pct >= LIKELY) return 'likely'
  if (pct >= BORDERLINE) return 'borderline'
  return 'unlikely'
}

/** The class that colours a badge. Calibrated scores get the recognition bands; the
 *  others fall back to the contract's own confidence field, which is relative. */
export function badgeClass(kind: ScoreKind, pct: number, confidence: Confidence): string {
  return kind === 'probability' ? bandOf(pct) : `rel-${confidence}`
}

export function scoreText(kind: ScoreKind, pct: number): string {
  return kind === 'probability' ? `${pct}%` : String(pct)
}

export function scoreTitle(kind: ScoreKind, pct: number, provisional: boolean): string {
  if (kind !== 'probability') {
    return `Relative score ${pct} of 100, comparable only within this course and this strategy. Not a probability.`
  }
  const base = `Estimated ${pct}% chance a coordinator would recognise this pair.`
  return provisional
    ? `${base} Fitted on a gold set that is partly model-labelled, so provisional.`
    : base
}

export function bandLabel(band: Band): string {
  return band === 'likely' ? 'likely' : band === 'borderline' ? 'borderline' : 'unlikely'
}
