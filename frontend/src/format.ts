import type { Cell } from './types'

/** Pick a display format for a whole column:
 *  all dates on Jan 1      -> "2022"     (yearly data)
 *  all dates on the 1st    -> "2024-03"  (monthly data)
 *  anything else           -> as-is */
export function columnFormatter(values: Cell[]): (v: Cell) => string {
  const present = values.filter((v) => v != null)
  const all = (re: RegExp) => present.length > 0 && present.every((v) => typeof v === 'string' && re.test(v))
  if (all(/^\d{4}-01-01/)) return (v) => (v == null ? '—' : String(v).slice(0, 4))
  if (all(/^\d{4}-\d{2}-01/)) return (v) => (v == null ? '—' : String(v).slice(0, 7))
  return (v) => (v == null ? '—' : String(v))
}
