import type { MatchResponse } from '../lib/api'

export default function ResultsTable({ data }: { data: MatchResponse }) {
  const withNone = data.results.filter((r) => r.matches.length === 0).length

  return (
    <section>
      <p className="hint">
        {data.results.length} courses matched with <code>{data.strategy}</code> in{' '}
        {(data.took_ms / 1000).toFixed(1)}s
        {withNone > 0 && `, ${withNone} with no candidate`}.
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
              <td>{row.home_course.title}</td>
              <td className="num">{row.home_course.ects}</td>
              <td>
                {row.matches.length === 0 ? (
                  <em className="hint">no candidate above threshold</em>
                ) : (
                  <ol className="matches">
                    {row.matches.map((m) => (
                      <li key={m.host_course.course_uid}>
                        <span className={`badge ${m.confidence}`} title={`raw score ${m.score}`}>
                          {m.score_pct}
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
                            <p className="desc">"{m.evidence.home_sentence}"</p>
                            <p className="desc">"{m.evidence.host_sentence}"</p>
                          </details>
                        )}
                      </li>
                    ))}
                  </ol>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
