export const API_BASE = process.env.EXPO_PUBLIC_API_URL ?? 'http://127.0.0.1:8001'

export type ScheduleItem = {
  id: number
  task_name: string
  discipline: string | null
  location: string | null
  planned_start: string | null
  planned_end: string | null
  actual_completion_date: string | null
  status: 'pending' | 'in_progress' | 'done' | 'flagged'
}
export type Dashboard = {
  tasks: Record<string, number>
  reports: Record<string, number>
}

export type MatchResult = {
  matched_activity_id: string
  matched_activity_name: string
  confidence_score: number
  match_status: 'auto_linked' | 'review_queue' | 'unplanned'
  rejection_reason: string | null
}

export type SubmitResponse = {
  results: MatchResult[]
  issues: string[]
}

export type ReviewItem = {
  id: number
  raw_text: string
  extracted_task: string | null
  matched_activity_code: string | null
  confidence_score: number | null
  review_status: string
  created_at: string
  candidate_task: string | null
  candidate_location: string | null
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Request failed with ${response.status}`)
  }

  return response.json() as Promise<T>
}

export const api = {
  ping: () => request<{ status: string; message: string }>('/ping'),
  dashboard: () => request<Dashboard>('/dashboard'),
  schedule: () => request<ScheduleItem[]>('/schedule'),
  reviewQueue: () => request<ReviewItem[]>('/review-queue'),
  submit: (reportText: string) =>
    request<SubmitResponse>('/submit', {
      method: 'POST',
      body: JSON.stringify({ report_text: reportText }),
    }),
}

