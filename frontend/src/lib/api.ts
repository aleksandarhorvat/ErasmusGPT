// Typed client mirroring docs/04-api-contract.md.
// If the contract changes, this file changes in the same commit. Owner: Person B.

const BASE = import.meta.env.VITE_API_BASE ?? '/api/v1'

export type Strategy = 'bm25' | 'dense' | 'hybrid' | 'hybrid+ce'
export type Confidence = 'high' | 'medium' | 'low'

export interface HealthResponse {
  status: string
  matcher: string
  models_loaded: boolean
  version: string
}

export interface ProgrammeSummary {
  programme_id: string
  institution_name: string
  programme_name: string
  country: string
  level: string
  course_count: number
  total_ects: number | null
}

export interface CourseSummary {
  course_uid: string
  code: string
  title: string
  ects: number
  year: number | null
  semester: number | null
  mandatory: boolean
  module: string | null
  url: string | null
  description: string
}

export interface CourseRef {
  course_uid: string
  title: string
  ects: number
  url: string | null
}

export interface Evidence {
  home_sentence: string
  host_sentence: string
  similarity: number
}

export interface MatchCandidate {
  host_course: CourseRef
  score: number
  score_pct: number
  confidence: Confidence
  ects_delta: number
  rank: number
  evidence: Evidence | null
}

export interface MatchRow {
  home_course: CourseRef
  matches: MatchCandidate[]
}

export interface MatchResponse {
  home_programme_id: string
  host_programme_id: string
  strategy: Strategy
  took_ms: number
  results: MatchRow[]
}

export interface EvaluationResponse {
  available: boolean
  provisional: boolean
  gold_checked: number
  gold_total: number
  gold_human: number
  gold_model: number
  columns: string[]
  rows: Record<string, string>[]
  reports: string[]
}

export interface StrategyInfo {
  id: Strategy
  label: string
  description: string
  calibrated: boolean
  provisional: boolean
}

export type Bucket = 'likely' | 'borderline' | 'unlikely'

export interface CourseOutcome {
  course_uid: string
  title: string
  ects: number
  probability: number
  bucket: Bucket
  best_match_uid: string | null
  best_match_title: string | null
  ects_shortfall: number
}

export interface RecognitionResponse {
  home_programme_id: string
  host_programme_id: string
  strategy: Strategy
  module: string | null
  calibrated: boolean
  provisional: boolean
  took_ms: number
  total_ects: number
  expected_recognised_ects: number
  expected_share: number
  likely_ects: number
  borderline_ects: number
  unlikely_ects: number
  ects_shortfall: number
  courses: CourseOutcome[]
}

export interface MatchBody {
  home_programme_id: string
  host_programme_id: string
  strategy: Strategy
  top_k: number
}

/** Matching a whole programme with a cross-encoder takes tens of seconds on CPU. */
const MATCH_TIMEOUT_MS = 150_000

/** FastAPI sends a string for our own errors and a list of {loc, msg} for 422s. */
function detailText(detail: unknown): string | null {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const parts = detail.map((d) =>
      d && typeof d === 'object' && 'msg' in d
        ? `${Array.isArray((d as { loc?: unknown }).loc) ? (d as { loc: unknown[] }).loc.slice(1).join('.') + ': ' : ''}${String((d as { msg: unknown }).msg)}`
        : String(d))
    return parts.length ? `Invalid request. ${parts.join('; ')}` : null
  }
  return null
}

async function request<T>(path: string, init?: RequestInit, timeoutMs = 20_000): Promise<T> {
  const abort = new AbortController()
  const timer = setTimeout(() => abort.abort(), timeoutMs)
  try {
    const response = await fetch(`${BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      signal: abort.signal,
      ...init,
    })
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: unknown } | null
      throw new Error(detailText(body?.detail) ?? `HTTP ${response.status} ${response.statusText}`)
    }
    return (await response.json()) as T
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') {
      throw new Error(`The request took longer than ${Math.round(timeoutMs / 1000)}s and was cancelled.`)
    }
    if (e instanceof TypeError) {
      throw new Error('Cannot reach the backend. Is it running on port 8000?')
    }
    throw e
  } finally {
    clearTimeout(timer)
  }
}

export const api = {
  health: () => request<HealthResponse>('/health'),
  programmes: () => request<ProgrammeSummary[]>('/programmes'),
  courses: (programmeId: string) =>
    request<CourseSummary[]>(`/programmes/${encodeURIComponent(programmeId)}/courses`),
  strategies: () => request<StrategyInfo[]>('/strategies'),
  evaluation: () => request<EvaluationResponse>('/evaluation'),
  match: (body: MatchBody) =>
    request<MatchResponse>('/match', { method: 'POST', body: JSON.stringify(body) }, MATCH_TIMEOUT_MS),
  matchCourse: (body: {
    home_course_uid: string
    host_programme_id: string
    strategy: Strategy
    top_k: number
  }) =>
    request<MatchCandidate[]>(
      '/match/course',
      { method: 'POST', body: JSON.stringify(body) },
      MATCH_TIMEOUT_MS,
    ),
  recognition: (body: {
    home_programme_id: string
    host_programme_id: string
    strategy: Strategy
    module: string | null
    ects_budget: number | null
  }) =>
    request<RecognitionResponse>(
      '/recognition',
      { method: 'POST', body: JSON.stringify(body) },
      MATCH_TIMEOUT_MS,
    ),
}
