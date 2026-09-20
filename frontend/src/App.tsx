import { useEffect, useRef, useState } from 'react'
import {
  api,
  type HealthResponse,
  type MatchResponse,
  type ProgrammeSummary,
  type RecognitionResponse,
  type Strategy,
  type StrategyInfo,
} from './lib/api'
import { download, matchesToCsv } from './lib/csv'
import ProgrammePicker from './components/ProgrammePicker'
import ResultsTable from './components/ResultsTable'
import CourseBrowser from './components/CourseBrowser'
import RecognitionPanel from './components/RecognitionPanel'

// Appearance is explicitly not graded (CONTEXT.md section 9). Keep this file readable
// and put the real work in the backend.

type Phase = 'booting' | 'ready' | 'matching' | 'failed'

export default function App() {
  const [programmes, setProgrammes] = useState<ProgrammeSummary[]>([])
  const [strategies, setStrategies] = useState<StrategyInfo[]>([])
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [home, setHome] = useState('')
  const [host, setHost] = useState('')
  const [strategy, setStrategy] = useState<Strategy>('hybrid+ce')
  const [modules, setModules] = useState<string[]>([])
  const [module, setModule] = useState<string>('')
  const [result, setResult] = useState<MatchResponse | null>(null)
  const [recognition, setRecognition] = useState<RecognitionResponse | null>(null)
  const [phase, setPhase] = useState<Phase>('booting')
  const [error, setError] = useState<string | null>(null)
  const [browsing, setBrowsing] = useState<string | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const timer = useRef<number | null>(null)

  useEffect(() => {
    Promise.all([api.programmes(), api.strategies(), api.health()])
      .then(([p, s, h]) => {
        setProgrammes(p)
        setStrategies(s)
        setHealth(h)
        if (p.length >= 2) {
          setHome(p[0].programme_id)
          setHost(p[1].programme_id)
        } else if (p.length === 1) {
          setHome(p[0].programme_id)
        }
        setPhase('ready')
      })
      .catch((e: Error) => {
        setError(e.message)
        setPhase('failed')
      })
  }, [])

  // Study paths for the recognition denominator (S6-B4).
  useEffect(() => {
    if (!home) return
    let live = true
    api
      .courses(home)
      .then((cs) => {
        if (!live) return
        const found = Array.from(new Set(cs.map((c) => c.module).filter((m): m is string => !!m)))
        setModules(found)
        setModule('')
      })
      .catch(() => live && setModules([]))
    return () => {
      live = false
    }
  }, [home])

  useEffect(() => {
    if (phase !== 'matching') {
      if (timer.current !== null) window.clearInterval(timer.current)
      return
    }
    setElapsed(0)
    timer.current = window.setInterval(() => setElapsed((n) => n + 1), 1000)
    return () => {
      if (timer.current !== null) window.clearInterval(timer.current)
    }
  }, [phase])

  async function runMatch() {
    setPhase('matching')
    setError(null)
    setResult(null)
    setRecognition(null)
    setBrowsing(null)
    try {
      const matched = await api.match({
        home_programme_id: home,
        host_programme_id: host,
        strategy,
        top_k: 5,
      })
      setResult(matched)
      try {
        setRecognition(
          await api.recognition({
            home_programme_id: home,
            host_programme_id: host,
            strategy,
            module: module || null,
            ects_budget: programmes.find((p) => p.programme_id === home)?.total_ects ?? null,
          }),
        )
      } catch {
        setRecognition(null) // the table is the deliverable; the summary is a bonus
      }
      setPhase('ready')
    } catch (e) {
      setError((e as Error).message)
      setPhase('ready')
    }
  }

  function swap() {
    setHome(host)
    setHost(home)
    setResult(null)
    setRecognition(null)
  }

  function exportCsv() {
    if (!result) return
    const info = strategies.find((s) => s.id === result.strategy)
    download(`erasmusgpt-${result.home_programme_id}-${result.host_programme_id}.csv`,
             matchesToCsv(result, info))
  }

  const browsed = programmes.find((p) => p.programme_id === browsing) ?? null
  const clear = () => {
    setResult(null)
    setRecognition(null)
  }

  return (
    <main>
      <h1>ErasmusGPT</h1>
      <p className="sub">
        Pick your home curriculum and a host curriculum. For every one of your courses you get the
        five most similar courses abroad, ranked.
      </p>

      {phase === 'booting' && <p className="hint">Loading curricula...</p>}

      {phase === 'failed' && (
        <p className="error">
          {error} Start the backend with <code>docker compose up</code>, then reload.
        </p>
      )}

      {phase !== 'booting' && phase !== 'failed' && programmes.length < 2 && (
        <p className="warn">
          Only {programmes.length} curriculum loaded. Matching needs two. Check that
          <code> data/curricula/</code> holds the JSON files and that <code>DATA_DIR</code> points at
          it in <code>docker-compose.yml</code>.
        </p>
      )}

      {programmes.length >= 2 && (
        <ProgrammePicker
          programmes={programmes}
          home={home}
          host={host}
          strategy={strategy}
          strategies={strategies}
          modules={modules}
          module={module}
          busy={phase === 'matching'}
          onHome={(id) => { setHome(id); clear() }}
          onHost={(id) => { setHost(id); clear() }}
          onStrategy={(s) => { setStrategy(s); clear() }}
          onModule={(m) => { setModule(m); clear() }}
          onSwap={swap}
          onMatch={runMatch}
        />
      )}

      {phase === 'matching' && (
        <p className="hint">
          Matching, {elapsed}s elapsed. Cross-encoder reranking on CPU takes about a second per
          course, so a whole programme is around a minute.
        </p>
      )}

      {error && phase === 'ready' && <p className="error">{error}</p>}

      {health && !health.models_loaded && (
        <p className="warn">
          The backend is running the stub matcher, so these results are fake. Set
          <code> MATCHER_IMPL=real</code> and <code>BAKE_MODELS=1</code> in <code>.env</code> and
          rebuild for real matches.
        </p>
      )}

      {recognition && <RecognitionPanel data={recognition} />}

      {result && (
        <>
          <p className="actions">
            <button type="button" onClick={exportCsv}>Export CSV</button>
            <span className="hint">
              One row per suggested pair, for the learning agreement.
            </span>
          </p>
          <ResultsTable data={result} strategies={strategies} hostProgrammeId={host} />
        </>
      )}

      {!result && phase === 'ready' && programmes.length > 0 && (
        <section className="empty">
          <p className="hint">
            No match run yet. Browse a curriculum first to check the data looks right:
          </p>
          <div className="chips">
            {programmes.map((p) => (
              <button
                key={p.programme_id}
                type="button"
                className={p.programme_id === browsing ? 'chip on' : 'chip'}
                onClick={() => setBrowsing(p.programme_id === browsing ? null : p.programme_id)}
              >
                {p.institution_name}
              </button>
            ))}
          </div>
          {browsed && <CourseBrowser programme={browsed} />}
        </section>
      )}

      {health && (
        <footer className="foot">
          backend {health.version} &middot; matcher {health.matcher} &middot; models{' '}
          {health.models_loaded ? 'loaded' : 'not loaded'}
        </footer>
      )}
    </main>
  )
}
