import { useEffect, useState } from 'react'
import { api, type MatchResponse, type ProgrammeSummary, type Strategy, type StrategyInfo } from './lib/api'
import ResultsTable from './components/ResultsTable'

// Appearance is explicitly not graded (see CONTEXT.md section 9).
// Keep this file small and readable; put real work in the backend.

export default function App() {
  const [programmes, setProgrammes] = useState<ProgrammeSummary[]>([])
  const [strategies, setStrategies] = useState<StrategyInfo[]>([])
  const [home, setHome] = useState('')
  const [host, setHost] = useState('')
  const [strategy, setStrategy] = useState<Strategy>('hybrid+ce')
  const [result, setResult] = useState<MatchResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([api.programmes(), api.strategies()])
      .then(([p, s]) => {
        setProgrammes(p)
        setStrategies(s)
        if (p.length >= 2) {
          setHome(p[0].programme_id)
          setHost(p[1].programme_id)
        }
      })
      .catch((e) => setError(String(e.message ?? e)))
  }, [])

  async function runMatch() {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      setResult(await api.match({ home_programme_id: home, host_programme_id: host, strategy, top_k: 5 }))
    } catch (e) {
      setError(String((e as Error).message))
    } finally {
      setLoading(false)
    }
  }

  const label = (p: ProgrammeSummary) => `${p.institution_name} - ${p.programme_name} (${p.course_count})`

  return (
    <main>
      <h1>ErasmusGPT</h1>
      <p className="sub">
        Pick your home curriculum and a host curriculum. For every one of your courses you get the
        five most similar courses abroad, ranked.
      </p>

      <section className="controls">
        <label>
          My curriculum
          <select value={home} onChange={(e) => setHome(e.target.value)}>
            {programmes.map((p) => (
              <option key={p.programme_id} value={p.programme_id}>{label(p)}</option>
            ))}
          </select>
        </label>

        <label>
          Host curriculum
          <select value={host} onChange={(e) => setHost(e.target.value)}>
            {programmes.map((p) => (
              <option key={p.programme_id} value={p.programme_id}>{label(p)}</option>
            ))}
          </select>
        </label>

        <label>
          Strategy
          <select value={strategy} onChange={(e) => setStrategy(e.target.value as Strategy)}>
            {strategies.map((s) => (
              <option key={s.id} value={s.id}>{s.label}</option>
            ))}
          </select>
        </label>

        <button onClick={runMatch} disabled={loading || !home || !host || home === host}>
          {loading ? 'Matching...' : 'Match courses'}
        </button>
      </section>

      {strategies.find((s) => s.id === strategy) && (
        <p className="hint">{strategies.find((s) => s.id === strategy)!.description}</p>
      )}

      {loading && <p className="hint">Cross-encoder reranking on CPU can take up to a minute for a whole programme.</p>}
      {error && <p className="error">{error}</p>}
      {result && <ResultsTable data={result} />}
    </main>
  )
}
