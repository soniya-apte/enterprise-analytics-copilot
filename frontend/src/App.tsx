import { useEffect, useState } from 'react'

export default function App() {
  const [status, setStatus] = useState('checking...')

  useEffect(() => {
    fetch('/api/health')
      .then((r) => r.json())
      .then((d) => setStatus(`${d.status}: ${d.message}`))
      .catch(() => setStatus('backend not reachable'))
  }, [])

  return (
    <main className="min-h-screen bg-slate-50 flex items-center justify-center">
      <div className="rounded-xl bg-white p-8 shadow">
        <h1 className="text-2xl font-semibold text-slate-800">Enterprise Analytics Copilot</h1>
        <p className="mt-2 text-slate-600">Backend: {status}</p>
      </div>
    </main>
  )
}
