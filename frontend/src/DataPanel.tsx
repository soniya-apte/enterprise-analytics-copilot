import type { AskResponse, Cell } from './types'

function fmt(v: Cell) {
  if (v == null) return '—'
  if (typeof v === 'number') {
    if (Number.isInteger(v) && v >= 1900 && v <= 2100) return String(v) // looks like a year
    return v.toLocaleString(undefined, { maximumFractionDigits: 2 })
  }
  return String(v)
}

export default function DataPanel({ result }: { result: AskResponse }) {
  const { columns, rows, row_count } = result.data
  const shown = rows.slice(0, 50)
  return (
    <details className="mt-5 rounded-lg border border-slate-200">
      <summary className="cursor-pointer select-none px-4 py-2 text-sm font-medium text-slate-700">
        Show SQL &amp; data ({row_count ?? rows.length} rows)
      </summary>
      <div className="border-t border-slate-200 p-4">
        {result.sql.explanation && <p className="text-sm text-slate-600">{result.sql.explanation}</p>}
        <pre className="mt-2 overflow-x-auto whitespace-pre-wrap rounded bg-slate-900 p-3 text-xs text-slate-100">
          {result.sql.query}
        </pre>
        {columns.length > 0 && (
          <div className="mt-3 max-h-80 overflow-auto">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 bg-slate-100 text-slate-600">
                <tr>{columns.map((c) => <th key={c} className="px-3 py-2 font-medium">{c}</th>)}</tr>
              </thead>
              <tbody>
                {shown.map((r, i) => (
                  <tr key={i} className="border-t border-slate-100">
                    {r.map((v, j) => (
                      <td key={j} className={`px-3 py-1.5 ${typeof v === 'number' ? 'text-right tabular-nums' : ''}`}>{fmt(v)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {rows.length > shown.length && <p className="mt-2 text-xs text-slate-500">Showing first {shown.length} rows.</p>}
          </div>
        )}
      </div>
    </details>
  )
}
