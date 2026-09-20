// S3-B1: the one place that decides how a score is shown.
//
// `score_pct` does not mean the same thing for every strategy. Where
// eval/fit_calibration.py has fitted one (S6-A4) it is a probability of recognition.
// For `dense` it is a stretched cosine, and for `bm25` and `hybrid` it is relative to
// the best hit for that home course, so the top row always reads 100. Printing
// "87 % chance" over the last two would be a lie, so nothing outside this file is
// allowed to format a score.

import type { Confidence, StrategyInfo } from './api'

export type ScoreKind = 'probability' | 'relative'
export type Band = 'likely' | 'borderline' | 'unlikely'

// Same thresholds as backend/app/matching/aggregate.py, deliberately.
const LIKELY = 70
const BORDERLINE = 40

export function scoreKind(info: StrategyInfo | undefined): ScoreKind {
  return info?.calibrated ? 'probability' : 'relative'
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
    ? `${base} Fitted on machine labels so far, not on checked ones.`
    : base
}

export function bandLabel(band: Band): string {
  return band === 'likely' ? 'likely' : band === 'borderline' ? 'borderline' : 'unlikely'
}
