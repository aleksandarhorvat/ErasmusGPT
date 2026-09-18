// Typed client mirroring docs/04-api-contract.md.
// If the contract changes, this file changes in the same commit. Owner: Person B.

const BASE = import.meta.env.VITE_API_BASE ?? '/api/v1'

export type Strategy = 'bm25' | 'dense' | 'hybrid' | 'hybrid+ce'
export type Confidence = 'high' | 'medium' | 'low'

export interface ProgrammeSummary {
  programme_id: string
  institution_name: string
  programme_name: string
  country: string
  level: string
  course_count: number
  total_ects: number | null
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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(body.detail ?? `HTTP ${response.status}`)
  }
  return response.json() as Promise<T>
}

export const api = {
  programmes: () => request<ProgrammeSummary[]>('/programmes'),
  strategies: () => request<StrategyInfo[]>('/strategies'),
  match: (body: {
    home_programme_id: string
    host_programme_id: string
    strategy: Strategy
    top_k: number
  }) => request<MatchResponse>('/match', { method: 'POST', body: JSON.stringify(body) }),
}
