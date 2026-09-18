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

export interface StrategyInfo {
  id: Strategy
  label: string
  description: string
}

export interface MatchBody {
  home_programme_id: string
  host_programme_id: string
  strategy: Strategy
  top_k: number
}

/** Matching a whole programme with a cross-encoder takes tens of seconds on CPU. */
const MATCH_TIMEOUT_MS = 150_000

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
      const body = (await response.json().catch(() => null)) as { detail?: string } | null
      throw new Error(body?.detail ?? `HTTP ${response.status} ${response.statusText}`)
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
  match: (body: MatchBody) =>
    request<MatchResponse>('/match', { method: 'POST', body: JSON.stringify(body) }, MATCH_TIMEOUT_MS),
}
