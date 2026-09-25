import { useState } from 'react'
import {
  api,
  type MatchCandidate,
  type MatchResponse,
  type MatchRow,
  type Strategy,
  type StrategyInfo,
} from '../lib/api'
import { badgeClass, noSuitableMatch, scoreKind, scoreText, scoreTitle } from '../lib/score'

interface Props {
  data: MatchResponse
  strategies: StrategyInfo[]
  hostProgrammeId: string
}

function Candidate({
  m,
  info,
}: {
  m: MatchCandidate
  info: StrategyInfo | undefined
}) {
  const kind = scoreKind(info)
  return (
    <li>
      <span
        className={`badge ${badgeClass(kind, m.score_pct, m.confidence)}`}
        title={scoreTitle(kind, m.score_pct, info?.provisional ?? false)}
      >
        {scoreText(kind, m.score_pct)}
      </span>{' '}
      {m.host_course.url ? (
        <a href={m.host_course.url} target="_blank" rel="noreferrer">
          {m.host_course.title}
        </a>
      ) : (
        m.host_course.title
      )}{' '}
      <small>
        {m.host_course.ects} ECTS ({m.ects_delta >= 0 ? '+' : ''}
        {m.ects_delta})
      </small>
      {m.evidence && (
        <details>
          <summary>why</summary>
          <p className="desc">{m.evidence.home_sentence}</p>
          <p className="desc">{m.evidence.host_sentence}</p>
        </details>
      )}
    </li>
  )
}

/** S3-B3 and S4-B2: re-run one course under another strategy, shown next to the first. */
function Compare({
  row,
  hostProgrammeId,
  current,
  strategies,
}: {
  row: MatchRow
  hostProgrammeId: string
  current: Strategy
  strategies: StrategyInfo[]
}) {
  const other = strategies.find((s) => s.id !== current)?.id ?? 'dense'
  const [against, setAgainst] = useState<Strategy>(other)
  const [result, setResult] = useState<MatchCandidate[] | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function run(strategy: Strategy) {
    setAgainst(strategy)
    setBusy(true)
    setError(null)
    try {
      setResult(
        await api.matchCourse({
          home_course_uid: row.home_course.course_uid,
          host_programme_id: hostProgrammeId,
          strategy,
          top_k: 5,
        }),
      )
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="compare">
      <div className="compare-head">
        <label>
          compare against
          <select value={against} onChange={(e) => run(e.target.value as Strategy)} disabled={busy}>
            {strategies.filter((s) => s.id !== current).map((s) => (
              <option key={s.id} value={s.id}>{s.label}</option>
            ))}
          </select>
        </label>
        <button type="button" onClick={() => run(against)} disabled={busy}>
          {busy ? 'running...' : result ? 'run again' : 'run'}
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      {result && (
        <ol className="matches">
          {result.length === 0 && <li><em className="hint">no candidate</em></li>}
          {result.map((m) => (
            <Candidate key={m.host_course.course_uid} m={m} info={strategies.find((s) => s.id === against)} />
          ))}
        </ol>
      )}
    </div>
  )
}

export default function ResultsTable({ data, strategies, hostProgrammeId }: Props) {
  const [open, setOpen] = useState<string | null>(null)
  const info = strategies.find((s) => s.id === data.strategy)
  const withNone = data.results.filter((r) => r.matches.length === 0).length
  const kind = scoreKind(info)
  const weak = (row: MatchRow) => noSuitableMatch(kind, row.matches.map((m) => m.score_pct))
  const withWeak = data.results.filter(weak).length

  return (
    <section>
      <p className="hint">
        {data.results.length} courses matched with <code>{data.strategy}</code> in{' '}
        {(data.took_ms / 1000).toFixed(1)}s
        {withNone > 0 && `, ${withNone} with no candidate`}
        {withWeak > 0 && `, ${withWeak} with no suitable match`}.{' '}
        {info?.calibrated
          ? 'Scores are estimated probabilities of recognition.'
          : 'Scores are relative to the best hit for each course, not probabilities.'}
      </p>
      <table className="results">
        <thead>
          <tr>
            <th>My course</th>
            <th className="num">ECTS</th>
            <th>Best matches abroad</th>
          </tr>
        </thead>
        <tbody>
          {data.results.map((row) => (
            <tr key={row.home_course.course_uid}>
              <td>
                {row.home_course.title}
                <br />
                <button
                  type="button"
                  className="linkish"
                  onClick={() =>
                    setOpen(open === row.home_course.course_uid ? null : row.home_course.course_uid)
                  }
                >
                  {open === row.home_course.course_uid ? 'hide compare' : 'compare'}
                </button>
              </td>
              <td className="num">{row.home_course.ects}</td>
              <td>
                {row.matches.length === 0 ? (
                  <em className="hint">no candidate above threshold</em>
                ) : weak(row) ? (
                  <>
                    <span className="nomatch">no suitable match</span>{' '}
                    <span className="hint">
                      (best candidate {Math.max(...row.matches.map((m) => m.score_pct))}%)
                    </span>
                    <details>
                      <summary>show the {row.matches.length} candidates anyway</summary>
                      <ol className="matches">
                        {row.matches.map((m) => (
                          <Candidate key={m.host_course.course_uid} m={m} info={info} />
                        ))}
                      </ol>
                    </details>
                  </>
                ) : (
                  <ol className="matches">
                    {row.matches.map((m) => (
                      <Candidate key={m.host_course.course_uid} m={m} info={info} />
                    ))}
                  </ol>
                )}
                {open === row.home_course.course_uid && (
                  <Compare
                    row={row}
                    hostProgrammeId={hostProgrammeId}
                    current={data.strategy}
                    strategies={strategies}
                  />
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
