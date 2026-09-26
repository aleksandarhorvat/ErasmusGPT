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
import EvaluationPanel from './components/EvaluationPanel'

// Appearance is explicitly not graded (CONTEXT.md section 9). Keep this file readable
// and put the real work in the backend.

type Phase = 'booting' | 'ready' | 'matching' | 'failed'

// The demo case (docs/07-demo-script.md): our bachelor's against Twente TCS.
const DEFAULT_HOME = 'uns-pmf-informatics-bsc'
const DEFAULT_HOST = 'utwente-tcs-bsc'

export default function App() {
  const [programmes, setProgrammes] = useState<ProgrammeSummary[]>([])
  const [strategies, setStrategies] = useState<StrategyInfo[]>([])
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [home, setHome] = useState('')
  const [host, setHost] = useState('')
  // Default changed from hybrid+ce on 2026-09-20: see docs/adr/0005-hybrid-is-the-default.md
  const [strategy, setStrategy] = useState<Strategy>('hybrid')
  const [modules, setModules] = useState<string[]>([])
  const [module, setModule] = useState<string>('')
  const [result, setResult] = useState<MatchResponse | null>(null)
  const [recognition, setRecognition] = useState<RecognitionResponse | null>(null)
  const [phase, setPhase] = useState<Phase>('booting')
  const [error, setError] = useState<string | null>(null)
  const [browsing, setBrowsing] = useState<string | null>(null)
  const [showEval, setShowEval] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [recognising, setRecognising] = useState(false)
  // Bumped whenever the inputs change or a new run starts, so a late answer for an
  // earlier run (the recognition request in particular) is dropped instead of shown.
  const run = useRef(0)
  const timer = useRef<number | null>(null)

  useEffect(() => {
    Promise.all([api.programmes(), api.strategies(), api.health()])
      .then(([p, s, h]) => {
        setProgrammes(p)
        setStrategies(s)
        setHealth(h)
        if (p.length >= 2) {
          // Open on the case the app is for: our own bachelor's against Twente TCS, when
          // both are loaded. Otherwise the first two, which may be two master's programmes.
          const has = (id: string) => p.some((x) => x.programme_id === id)
          const home0 = has(DEFAULT_HOME) ? DEFAULT_HOME : p[0].programme_id
          const host0 = has(DEFAULT_HOST) && DEFAULT_HOST !== home0
            ? DEFAULT_HOST
            : p.find((x) => x.programme_id !== home0)!.programme_id
          setHome(home0)
          setHost(host0)
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
    const id = ++run.current
    setPhase('matching')
    setError(null)
    setResult(null)
    setRecognition(null)
    setRecognising(false)
    setBrowsing(null)
    try {
      const matched = await api.match({
        home_programme_id: home,
        host_programme_id: host,
        strategy,
        top_k: 5,
      })
      if (id !== run.current) return
      setResult(matched)
      setPhase('ready')
    } catch (e) {
      if (id !== run.current) return
      setError((e as Error).message)
      setPhase('ready')
      return
    }
    // The table is the deliverable and is already on screen; the summary follows on its
    // own, without holding the controls or the "Matching" timer.
    setRecognising(true)
    api.recognition({
      home_programme_id: home,
      host_programme_id: host,
      strategy,
      module: module || null,
      ects_budget: programmes.find((p) => p.programme_id === home)?.total_ects ?? null,
    })
      .then((summary) => { if (id === run.current) setRecognition(summary) })
      .catch(() => { if (id === run.current) setRecognition(null) })
      .finally(() => { if (id === run.current) setRecognising(false) })
  }

  function swap() {
    setHome(host)
    setHost(home)
    clear()
  }

  function exportCsv() {
    if (!result) return
    const info = strategies.find((s) => s.id === result.strategy)
    download(`erasmusgpt-${result.home_programme_id}-${result.host_programme_id}.csv`,
             matchesToCsv(result, info))
  }

  const browsed = programmes.find((p) => p.programme_id === browsing) ?? null
  function clear() {
    run.current++
    setResult(null)
    setRecognition(null)
    setRecognising(false)
    setError(null)
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

      {recognising && <p className="hint">Working out the recognition estimate...</p>}
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

      <p className="actions">
        <button type="button" className="chip" onClick={() => setShowEval((v) => !v)}>
          {showEval ? 'hide' : 'how well does this work?'}
        </button>
      </p>
      {showEval && <EvaluationPanel />}

      {health && (
        <footer className="foot">
          backend {health.version} &middot; matcher {health.matcher} &middot; models{' '}
          {health.models_loaded ? 'loaded' : 'not loaded'}
        </footer>
      )}
    </main>
  )
}
