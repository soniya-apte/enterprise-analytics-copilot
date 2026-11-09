// Shapes of the JSON returned by the FastAPI backend (backend/api/service.py)

export interface ChartSpec {
  type: string // "bar" | "line" | "pie"
  title?: string
  x_label?: string
  y_label?: string
  data_description?: string
}

export type Cell = string | number | boolean | null

export interface AskResponse {
  id?: number
  question: string
  answer: {
    summary: string | null
    key_takeaways: string[] | null
    recommendations: string[] | null
    chart_specs: ChartSpec[] | null
    confidence_note: string | null
  }
  data: { columns: string[]; rows: Cell[][]; row_count: number | null }
  sql: { query: string | null; explanation: string | null; attempts: number | null; success: boolean | null }
  routing: { analysis_type: string | null; uses_live_stream: boolean | null; data_science: string | null }
  analysis?: unknown
  data_science?: unknown
  evaluation: { overall_score: number | null; summary?: string; [key: string]: unknown } | null
  diagnostics: { errors: string[]; llm_calls: number; cost_usd: number; duration_ms: number }
}

export interface HistoryItem {
  id: number
  asked_at: string
  question: string
  analysis_type: string | null
  uses_live_stream: boolean | null
  sql_success: boolean | null
  overall_score: number | null
  cost_usd: number | null
  duration_ms: number | null
}
