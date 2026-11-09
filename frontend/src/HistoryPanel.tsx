import type { HistoryItem } from './types'

function ago(iso: string) {
  const s = (Date.now() - new Date(iso).getTime()) / 1000
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)} min ago`
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`
  return `${Math.floor(s / 86400)} d ago`
}

export default function HistoryPanel({ items, activeId, onSelect, disabled }: {
  items: HistoryItem[]
  activeId?: number
  onSelect: (id: number) => void
  disabled: boolean
}) {
  return (
    <aside className="lg:sticky lg:top-10 lg:self-start">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-cocoa-500">Recent questions</h2>
      {items.length === 0 ? (
        <p className="mt-3 text-sm text-cocoa-500">No questions yet.</p>
      ) : (
        <ul className="mt-3 space-y-2">
          {items.map((h) => (
            <li key={h.id}>
              <button
                type="button"
                disabled={disabled}
                onClick={() => onSelect(h.id)}
                className={`w-full rounded-lg border px-3 py-2 text-left text-sm transition hover:border-caramel-500 disabled:opacity-50 ${
                  h.id === activeId ? 'border-caramel-600 bg-cream' : 'border-cocoa-200 bg-cream/60'
                }`}
              >
                <p className="line-clamp-2 text-cocoa-800">{h.question}</p>
                <p className="mt-1 text-xs text-cocoa-500">
                  {ago(h.asked_at)} · {h.overall_score != null ? `score ${h.overall_score}` : 'not scored'}
                  {h.uses_live_stream ? ' · stream' : ''}
                </p>
              </button>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-3 text-xs text-cocoa-500">Reopening a past answer is free: no agents run.</p>
    </aside>
  )
}
