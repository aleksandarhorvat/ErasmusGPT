import type { RecognitionResponse } from '../lib/api'

// S6-B4. The one line a student actually wants, over a study path rather than over every
// course the programme offers. The denominator comes from the module filter in
// app/api/routes_recognition.py, not from the whole curriculum file.

export default function RecognitionPanel({ data }: { data: RecognitionResponse }) {
  const pct = Math.round(data.expected_share * 100)
  const bar = (ects: number) => ({ width: `${data.total_ects ? (ects / data.total_ects) * 100 : 0}%` })

  return (
    <section className="recog">
      <h2>
        About <b>{data.expected_recognised_ects}</b> of {data.total_ects} ECTS would likely be
        recognised <span className="hint">({pct} %)</span>
      </h2>

      <div className="stack" role="img" aria-label={
        `${data.likely_ects} ECTS likely, ${data.borderline_ects} borderline, ${data.unlikely_ects} unlikely`
      }>
        <span className="seg likely" style={bar(data.likely_ects)} />
        <span className="seg borderline" style={bar(data.borderline_ects)} />
        <span className="seg unlikely" style={bar(data.unlikely_ects)} />
      </div>
      <ul className="keys">
        <li><span className="dot likely" />likely {data.likely_ects} ECTS</li>
        <li><span className="dot borderline" />borderline {data.borderline_ects} ECTS</li>
        <li><span className="dot unlikely" />unlikely {data.unlikely_ects} ECTS</li>
        {data.ects_shortfall > 0 && (
          <li><span className="dot short" />{data.ects_shortfall} ECTS shortfall, where the host
            course carries fewer credits than yours</li>
        )}
      </ul>

      {!data.calibrated && (
        <p className="warn">
          <code>{data.strategy}</code> has no fitted calibration, so these shares come from a
          display score rather than a probability. Switch to a calibrated strategy for a number
          that means something.
        </p>
      )}
      {data.calibrated && data.provisional && (
        <p className="warn">
          Provisional. The calibration behind these probabilities was fitted on machine labels,
          not on the human-checked gold set. The shape is right, the exact number is not final.
        </p>
      )}
      <p className="hint">
        {data.module ? `Study path: ${data.module}.` : 'Every course the programme offers.'} A
        curriculum lists more courses than any one student takes, so the denominator is the path,
        not the whole file.
      </p>
    </section>
  )
}
