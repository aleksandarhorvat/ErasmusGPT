import type { ProgrammeSummary, Strategy, StrategyInfo } from '../lib/api'

interface Props {
  programmes: ProgrammeSummary[]
  home: string
  host: string
  strategy: Strategy
  strategies: StrategyInfo[]
  modules: string[]
  module: string
  busy: boolean
  onHome: (id: string) => void
  onHost: (id: string) => void
  onStrategy: (s: Strategy) => void
  onModule: (m: string) => void
  onSwap: () => void
  onMatch: () => void
}

function label(p: ProgrammeSummary): string {
  return `${p.institution_name} - ${p.programme_name} (${p.course_count})`
}

export default function ProgrammePicker(props: Props) {
  const { programmes, home, host, strategy, strategies, modules, module, busy } = props
  const sameProgramme = home !== '' && home === host
  const active = strategies.find((s) => s.id === strategy)

  return (
    <section className="controls-block">
      <div className="controls">
        <label htmlFor="home">
          My curriculum
          <select id="home" value={home} onChange={(e) => props.onHome(e.target.value)} disabled={busy}>
            {programmes.map((p) => (
              <option key={p.programme_id} value={p.programme_id}>{label(p)}</option>
            ))}
          </select>
        </label>

        <button type="button" className="swap" onClick={props.onSwap} disabled={busy} title="Swap the two curricula">
          swap
        </button>

        <label htmlFor="host">
          Host curriculum
          <select id="host" value={host} onChange={(e) => props.onHost(e.target.value)} disabled={busy}>
            {programmes.map((p) => (
              <option key={p.programme_id} value={p.programme_id}>{label(p)}</option>
            ))}
          </select>
        </label>

        <label htmlFor="strategy">
          Strategy
          <select
            id="strategy"
            value={strategy}
            onChange={(e) => props.onStrategy(e.target.value as Strategy)}
            disabled={busy}
          >
            {strategies.map((s) => (
              <option key={s.id} value={s.id}>{s.label}</option>
            ))}
          </select>
        </label>

        {modules.length > 0 && (
          <label htmlFor="module">
            My study path
            <select id="module" value={module} onChange={(e) => props.onModule(e.target.value)} disabled={busy}>
              <option value="">every course offered</option>
              {modules.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </label>
        )}

        <button type="button" className="primary" onClick={props.onMatch} disabled={busy || sameProgramme}>
          {busy ? 'Matching...' : 'Match courses'}
        </button>
      </div>

      {active && <p className="hint">{active.description}</p>}
      {sameProgramme && (
        <p className="warn">Pick two different curricula. Matching a programme against itself tells you nothing.</p>
      )}
    </section>
  )
}
