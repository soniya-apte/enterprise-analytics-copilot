import type { AskResponse, HistoryItem } from './types'

// All requests go to /api/..., which Vite's proxy forwards to the FastAPI backend.
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init)
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      // response was not JSON - keep the status text
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export const askQuestion = (question: string) =>
  request<AskResponse>('/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })

export const getHistory = (limit = 10) => request<HistoryItem[]>(`/history?limit=${limit}`)

export const getAnswer = (id: number) => request<AskResponse>(`/history/${id}`)
