import { useEffect, useRef } from 'react'
import Plotly from 'plotly.js-dist-min'
import type { Cell, ChartSpec } from './types'
import { columnFormatter } from './format'

const isNumericCol = (rows: Cell[][], i: number) =>
  rows.every((r) => typeof r[i] === 'number' || r[i] == null)

/** Decide which columns become x-axis labels and which become plotted series. */
export function chartLayout(columns: string[], rows: Cell[][]) {
  const all = columns.map((_, i) => i)
  const isId = (i: number) => /(^id$|id$)/i.test(columns[i])
  const labelIdxs = all.filter((i) => !isNumericCol(rows, i))
  let xIdxs: number[]
  let yIdxs: number[]
  if (labelIdxs.length) {
    xIdxs = labelIdxs
    yIdxs = all.filter((i) => isNumericCol(rows, i) && !isId(i))
  } else {
    xIdxs = [0]
    yIdxs = all.slice(1).filter((i) => !isId(i))
  }
  return { xIdxs, yIdxs, chartable: rows.length >= 2 && yIdxs.length >= 1 }
}

export default function Chart({ spec, columns, rows }: { spec?: ChartSpec; columns: string[]; rows: Cell[][] }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const { xIdxs, yIdxs } = chartLayout(columns, rows)
    const fmt = new Map(xIdxs.map((i) => [i, columnFormatter(rows.map((r) => r[i]))]))
    const x = rows.map((r) => xIdxs.map((i) => fmt.get(i)!(r[i])).join(' '))
    const kind = spec?.type === 'pie' ? 'pie' : spec?.type === 'line' ? 'line' : 'bar'

    const data: Plotly.Data[] =
      kind === 'pie'
        ? [{ type: 'pie', labels: x, values: rows.map((r) => r[yIdxs[0]] as number) }]
        : yIdxs.map((i) => ({
            type: kind === 'line' ? 'scatter' : 'bar',
            mode: kind === 'line' ? 'lines+markers' : undefined,
            name: columns[i],
            x,
            y: rows.map((r) => r[i] as number),
          }))

    Plotly.react(
      el,
      data,
      {
        title: { text: spec?.title ?? '' },
        xaxis: { title: { text: spec?.x_label ?? '' }, type: 'category' },
        yaxis: { title: { text: spec?.y_label ?? '' } },
        showlegend: yIdxs.length > 1 || kind === 'pie',
        height: 360,
        margin: { t: 48, r: 16, b: 64, l: 72 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#4e331f' },
        colorway: ['#a8692f', '#c98a4b', '#7a5638', '#d9a066', '#3b2616'],
      },
      { displayModeBar: false, responsive: true },
    )
    return () => Plotly.purge(el)
  }, [spec, columns, rows])

  return <div ref={ref} className="w-full" />
}
