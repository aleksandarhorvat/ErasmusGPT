import { useEffect, useState } from 'react'
import { api, type EvaluationResponse } from '../lib/api'

// S5-B3. "How well does this work" needs to be one click away at the defence, and it
// has to be honest: until the gold set is checked by a human, every number in
// eval/report/ was computed against labels a model wrote about its own retrieval.

export default function EvaluationPanel() {
  const [data, setData] = useState<EvaluationResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.evaluation().then(setData).catch((e: Error) => setError(e.message))
  }, [])

  if (error) return <p className="error">{error}</p>
  if (!data) return <p className="hint">Loading evaluation...</p>

  const done = data.gold_total ? Math.round((data.gold_checked / data.gold_total) * 100) : 0

  return (
    <section className="eval">
      <h2>How well does this work</h2>

      <p className="hint">
        Gold set: <b>{data.gold_checked}</b> of {data.gold_total} pairs checked by a human
        ({done} %).
      </p>

      {data.provisional && (
        <p className="warn">
          No measured results yet. The numbers in <code>eval/report/</code> were computed
          against labels a model wrote about our own retrieval, so they can choose between
          settings but cannot be reported as results. They become real when the human pass
          (<code>S5-A1</code>) lands and the harness is re-run.
        </p>
      )}

      {data.available ? (
        <div className="tablewrap">
          <table>
            <thead>
              <tr>{data.columns.map((c) => <th key={c}>{c}</th>)}</tr>
            </thead>
            <tbody>
              {data.rows.map((row, i) => (
                <tr key={i}>{data.columns.map((c) => <td key={c}>{row[c]}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="hint">
          <code>eval/report/results.csv</code> does not exist yet, so there is no table to
          show. That is the truthful state, not an error.
        </p>
      )}

      {data.reports.length > 0 && (
        <p className="hint">
          Written up in the repository: {data.reports.map((r) => <code key={r}>{r} </code>)}
        </p>
      )}

      <p className="hint">
        The headline finding so far: cross-encoder reranking, which this project set out to
        show would win, measures worse than plain hybrid retrieval and costs about 500 times
        more per query. See <code>ablations.md</code> and ADR-0005.
      </p>
    </section>
  )
}
