import { useEffect, useState } from 'react'
import { api, type CourseSummary, type ProgrammeSummary } from '../lib/api'

// S1-B3. Exists so that data problems show up before anyone runs a match: the whole
// pipeline reads the description field, and a curriculum with empty descriptions loads
// without complaint and then matches badly.

export default function CourseBrowser({ programme }: { programme: ProgrammeSummary }) {
  const [courses, setCourses] = useState<CourseSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [open, setOpen] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    setCourses(null)
    setError(null)
    api
      .courses(programme.programme_id)
      .then((c) => live && setCourses(c))
      .catch((e: Error) => live && setError(e.message))
    return () => {
      live = false
    }
  }, [programme.programme_id])

  if (error) return <p className="error">{error}</p>
  if (!courses) return <p className="hint">Loading courses...</p>

  const empty = courses.filter((c) => c.description.trim() === '')
  const ects = courses.reduce((sum, c) => sum + c.ects, 0)

  return (
    <div className="browser">
      <p className="hint">
        {courses.length} courses, {ects} ECTS in total.
      </p>
      {empty.length > 0 && (
        <p className="warn">
          {empty.length} course{empty.length === 1 ? ' has' : 's have'} no description. Matching runs on
          the description text, so these will score poorly whatever the strategy does:{' '}
          {empty.map((c) => c.code).join(', ')}
        </p>
      )}
      <table>
        <thead>
          <tr>
            <th>Code</th>
            <th>Title</th>
            <th>ECTS</th>
            <th>Year</th>
            <th>Module</th>
          </tr>
        </thead>
        <tbody>
          {courses.map((c) => (
            <tr key={c.course_uid}>
              <td className="mono">{c.code}</td>
              <td>
                <button
                  type="button"
                  className="linkish"
                  onClick={() => setOpen(open === c.course_uid ? null : c.course_uid)}
                >
                  {c.title}
                </button>
                {open === c.course_uid && (
                  <p className="desc">
                    {c.description.trim() === '' ? <em>No description published.</em> : c.description}
                  </p>
                )}
              </td>
              <td className="num">{c.ects}</td>
              <td className="num">{c.year ?? '-'}</td>
              <td>{c.module ?? '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
