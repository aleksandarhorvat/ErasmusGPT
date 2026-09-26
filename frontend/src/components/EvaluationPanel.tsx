import { useEffect, useState } from 'react'
import { api, type EvaluationResponse } from '../lib/api'

// S5-B3. "How well does this work" needs to be one click away at the defence, and it
// has to be honest about who wrote the labels behind the numbers: a person, or a model.

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

      {data.gold_model > 0 ? (
        <p className="hint">
          Gold set: all {data.gold_checked} of {data.gold_total} pairs labelled.{' '}
          <b>{data.gold_human}</b> were checked by a person, <b>{data.gold_model}</b> were
          labelled by a second model (Claude) and not checked by a person.
        </p>
      ) : (
        <p className="hint">
          Gold set: <b>{data.gold_checked}</b> of {data.gold_total} pairs checked by a human
          ({done} %).
        </p>
      )}

      {!data.provisional && data.gold_model > 0 && (
        <p className="warn">
          Partly model-labelled. For lack of time, {data.gold_model} of {data.gold_total} gold
          labels come from a second model instead of a human check, so the table below measures
          agreement with people on {data.gold_human} rows and with a model on the rest. The
          reports in <code>eval/report/</code> state the same split, and{' '}
          <code>kappa.md</code> gives how often that model and a person agree.
        </p>
      )}

      {data.provisional && data.gold_checked > 0 && (
        <p className="warn">
          Human pass in progress. Any table below scores only the {data.gold_checked} checked
          rows, which cover whichever home courses were labelled first, so it is not yet the
          number the report will quote. It becomes final when all {data.gold_total} rows are
          checked and the harness is re-run.
        </p>
      )}

      {data.provisional && data.gold_checked === 0 && (
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
        The headline finding: cross-encoder reranking, which this project set out to show
        would win, only helps when it is fused with the other two rankings instead of
        replacing them. Fused, it is level with plain hybrid retrieval and costs about 300
        times more per query, so hybrid is the default. The one significant gain is hybrid
        over the MiniLM baseline on Recall@5 against Twente Applied Mathematics. See{' '}
        <code>results.md</code> and ADR-0005.
      </p>
    </section>
  )
}
