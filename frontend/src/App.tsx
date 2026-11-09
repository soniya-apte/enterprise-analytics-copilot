import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { askQuestion } from './api'
import Chart, { chartLayout } from './Chart'
import DataPanel from './DataPanel'
import type { AskResponse } from './types'

const EXAMPLES = [
  'What was total revenue by year?',
  'Which product category had the highest revenue in 2024?',
  'Who are the top 5 salespeople by total sales revenue?',
  'Were there any unusual sales days recently?',
]

const STAGES = ['Plan the analysis', 'Retrieve schema + write SQL', 'Analyze results',
  'Run data-science models (if needed)', 'Write the report', 'Evaluate the answer']

function ScoreBadge({ score }: { score: number | null | undefined }) {
  if (score == null) return <span className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-500">Not scored</span>
  const color = score >= 80 ? 'bg-emerald-100 text-emerald-800' : score >= 60 ? 'bg-amber-100 text-amber-800' : 'bg-rose-100 text-rose-800'
  return <span className={`rounded-full px-3 py-1 text-sm font-medium ${color}`}>Quality score {score}/100</span>
}

function BulletList({ title, items }: { title: string; items: string[] | null | undefined }) {
  if (!items?.length) return null
  return (
    <section className="mt-5">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">{title}</h3>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-slate-700">
        {items.map((t, i) => <li key={i}>{t}</li>)}
      </ul>
    </section>
  )
}

export default function App() {
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState<AskResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [elapsed, setElapsed] = useState(0)

  // Elapsed-seconds counter while a question is running
  useEffect(() => {
    if (!loading) return
    setElapsed(0)
    const timer = setInterval(() => setElapsed((s) => s + 1), 1000)
    return () => clearInterval(timer)
  }, [loading])

  async function submit(q: string) {
    if (q.trim().length < 3 || loading) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      setResult(await askQuestion(q.trim()))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    submit(question)
  }

  const d = result?.diagnostics
  return (
    <main className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-4xl px-4 py-10">
        <header>
          <h1 className="text-3xl font-semibold text-slate-900">Enterprise Analytics Copilot</h1>
          <p className="mt-1 text-slate-600">Ask a business question in plain English. Six AI agents plan, query, analyze, report and self-evaluate.</p>
        </header>

        <form onSubmit={onSubmit} className="mt-6 flex gap-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. Which sales territory had the most orders in 2023?"
            maxLength={500}
            className="flex-1 rounded-lg border border-slate-300 bg-white px-4 py-3 text-slate-800 shadow-sm focus:border-indigo-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={loading || question.trim().length < 3}
            className="rounded-lg bg-indigo-600 px-5 py-3 font-medium text-white shadow-sm hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {loading ? 'Working...' : 'Ask'}
          </button>
        </form>

        <div className="mt-3 flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button key={ex} type="button" disabled={loading}
              onClick={() => { setQuestion(ex); submit(ex) }}
              className="rounded-full border border-slate-300 bg-white px-3 py-1 text-sm text-slate-700 hover:border-indigo-400 hover:text-indigo-700 disabled:opacity-50">
              {ex}
            </button>
          ))}
        </div>

        {loading && (
          <div className="mt-8 rounded-xl bg-white p-6 shadow">
            <p className="font-medium text-slate-800">Running the agent pipeline... {elapsed}s</p>
            <p className="mt-1 text-sm text-slate-500">This usually takes 20-30 seconds. The pipeline will:</p>
            <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm text-slate-600">
              {STAGES.map((s) => <li key={s}>{s}</li>)}
            </ol>
          </div>
        )}

        {error && (
          <div className="mt-8 rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-800">
            <p className="font-medium">Something went wrong</p>
            <p className="mt-1 text-sm">{error}</p>
          </div>
        )}

        {result && (
          <article className="mt-8 rounded-xl bg-white p-6 shadow">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <h2 className="text-lg font-semibold text-slate-900">{result.question}</h2>
              <ScoreBadge score={result.evaluation?.overall_score} />
            </div>
            <p className="mt-4 leading-relaxed text-slate-800">{result.answer.summary ?? 'No summary was produced.'}</p>
            {chartLayout(result.data.columns, result.data.rows).chartable && (
              <div className="mt-5">
                <Chart spec={result.answer.chart_specs?.[0]} columns={result.data.columns} rows={result.data.rows} />
              </div>
            )}
            <BulletList title="Key takeaways" items={result.answer.key_takeaways} />
            <BulletList title="Recommendations" items={result.answer.recommendations} />
            {result.answer.confidence_note && (
              <p className="mt-5 rounded-lg bg-slate-50 p-3 text-sm text-slate-600">
                <span className="font-medium">Confidence: </span>{result.answer.confidence_note}
              </p>
            )}
            <DataPanel result={result} />
            {d && (
              <p className="mt-5 border-t border-slate-100 pt-3 text-xs text-slate-500">
                {result.routing.analysis_type ?? 'unknown'} question
                {result.routing.uses_live_stream ? ' · live stream' : ''}
                {' · '}{d.llm_calls} LLM calls · ${d.cost_usd.toFixed(4)} · {(d.duration_ms / 1000).toFixed(1)}s
                {' · '}SQL attempts: {result.sql.attempts ?? '-'}
              </p>
            )}
          </article>
        )}
      </div>
    </main>
  )
}
