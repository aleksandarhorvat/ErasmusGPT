// S3-B2: the table as a file a student can send to a coordinator.

import type { MatchResponse, StrategyInfo } from './api'
import { noSuitableMatch, scoreKind, scoreText } from './score'

function cell(value: string | number | null | undefined): string {
  const text = value === null || value === undefined ? '' : String(value)
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

export function matchesToCsv(data: MatchResponse, info: StrategyInfo | undefined): string {
  const kind = scoreKind(info)
  const header = [
    'home_uid', 'home_course', 'home_ects',
    'rank', 'host_uid', 'host_course', 'host_ects', 'ects_delta',
    'score', 'score_meaning', 'confidence', 'host_url', 'no_suitable_match',
  ]
  const lines = [header.join(',')]
  for (const row of data.results) {
    if (row.matches.length === 0) {
      lines.push([
        cell(row.home_course.course_uid), cell(row.home_course.title), cell(row.home_course.ects),
        '', '', cell('no candidate above threshold'), '', '', '', cell(kind), '', '', 'yes',
      ].join(','))
      continue
    }
    // Same rule as the table: a calibrated best candidate under the floor is not a match,
    // and a coordinator reading the file should see that, not a plain rank-1 row.
    const weak = noSuitableMatch(kind, row.matches.map((m) => m.score_pct)) ? 'yes' : 'no'
    for (const m of row.matches) {
      lines.push([
        cell(row.home_course.course_uid), cell(row.home_course.title), cell(row.home_course.ects),
        cell(m.rank), cell(m.host_course.course_uid), cell(m.host_course.title),
        cell(m.host_course.ects), cell(m.ects_delta),
        cell(scoreText(kind, m.score_pct)), cell(kind), cell(m.confidence),
        cell(m.host_course.url), weak,
      ].join(','))
    }
  }
  return lines.join('\n') + '\n'
}

export function download(filename: string, text: string): void {
  const blob = new Blob([text], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
