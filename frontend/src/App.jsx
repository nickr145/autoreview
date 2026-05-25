import { useState, useEffect, useRef } from 'react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const SEVERITY_COLOR = {
  HIGH: '#dc2626',
  MEDIUM: '#d97706',
  LOW: '#2563eb',
}

export default function App() {
  const [repo, setRepo] = useState('')
  const [prNumber, setPrNumber] = useState('')
  const [run, setRun] = useState(null)
  const [error, setError] = useState(null)
  const pollRef = useRef(null)

  async function startReview(e) {
    e.preventDefault()
    setError(null)
    setRun(null)

    const pr = parseInt(prNumber, 10)
    if (!repo.includes('/') || isNaN(pr) || pr < 1) {
      setError('Enter a valid repo (owner/repo) and PR number.')
      return
    }

    try {
      const res = await fetch(`${API}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo, pr_number: pr }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setRun({ run_id: data.run_id, status: 'queued' })
    } catch (err) {
      setError(`Failed to start review: ${err.message}`)
    }
  }

  useEffect(() => {
    if (!run?.run_id) return
    if (run.status === 'complete' || run.status === 'error') return

    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API}/status/${run.run_id}`)
        if (!res.ok) return
        const data = await res.json()
        setRun(prev => ({ ...prev, ...data }))
        if (data.status === 'complete' || data.status === 'error') {
          clearInterval(pollRef.current)
        }
      } catch {
        // network blip — keep polling
      }
    }, 2500)

    return () => clearInterval(pollRef.current)
  }, [run?.run_id, run?.status])

  const isRunning = run && (run.status === 'queued' || run.status === 'running')
  const isDone = run?.status === 'complete'
  const isError = run?.status === 'error'

  return (
    <div className="app">
      <header>
        <h1>AutoReview Agent</h1>
        <p>Autonomous AI code review — security, quality, patches</p>
      </header>

      <form onSubmit={startReview} className="review-form">
        <input
          type="text"
          placeholder="owner/repo"
          value={repo}
          onChange={e => setRepo(e.target.value)}
          disabled={isRunning}
          aria-label="Repository slug"
        />
        <input
          type="number"
          placeholder="PR number"
          value={prNumber}
          onChange={e => setPrNumber(e.target.value)}
          disabled={isRunning}
          min="1"
          aria-label="Pull request number"
        />
        <button type="submit" disabled={isRunning}>
          {isRunning ? 'Reviewing…' : 'Review PR'}
        </button>
      </form>

      {error && <div className="error">{error}</div>}

      {run && (
        <div className="status-bar">
          <span className={`badge badge-${run.status}`}>{run.status.toUpperCase()}</span>
          <span className="run-id">Run: {run.run_id.slice(0, 8)}…</span>
          {isRunning && <span className="spinner" />}
        </div>
      )}

      {isError && (
        <div className="error">Review failed: {run.error}</div>
      )}

      {isDone && (
        <div className="results">
          <div className="stats-grid">
            <StatCard label="Findings" value={run.findings?.length ?? 0} />
            <StatCard label="Patches" value={run.patches ?? 0} />
            <StatCard
              label="Tests"
              value={run.test_passed ? 'PASSED' : 'FAILED'}
              highlight={run.test_passed ? 'green' : 'red'}
            />
            <StatCard label="Iterations" value={run.iterations ?? 0} />
            <StatCard label="Tokens in" value={(run.input_tokens ?? 0).toLocaleString()} />
            <StatCard label="Tokens out" value={(run.output_tokens ?? 0).toLocaleString()} />
          </div>

          {run.findings?.length > 0 ? (
            <>
              <h2>Findings</h2>
              <table className="findings-table">
                <thead>
                  <tr>
                    <th>Severity</th>
                    <th>File</th>
                    <th>Line</th>
                    <th>Description</th>
                    <th>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {run.findings.map((f, i) => (
                    <tr key={i}>
                      <td>
                        <span
                          className="severity-badge"
                          style={{ background: SEVERITY_COLOR[f.severity] ?? '#475569' }}
                        >
                          {f.severity}
                        </span>
                      </td>
                      <td><code>{f.file}</code></td>
                      <td>{f.line}</td>
                      <td>{f.description}</td>
                      <td>{((f.confidence ?? 0) * 100).toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : (
            <div className="no-findings">No security findings detected.</div>
          )}
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value, highlight }) {
  const color =
    highlight === 'green' ? '#16a34a' :
    highlight === 'red'   ? '#dc2626' :
    undefined
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={{ color }}>{value}</div>
    </div>
  )
}
