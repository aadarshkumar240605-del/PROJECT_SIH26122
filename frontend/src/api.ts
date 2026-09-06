const API_BASE = 'http://localhost:8000';

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`);

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function getDashboardStats() {
  return fetchJson<{ tasks: Record<string, number>; reports: Record<string, number> }>(`/dashboard`);
}

export async function getActivities() {
  return fetchJson<Array<{
    id: number;
    task_name: string;
    discipline: string;
    location: string;
    planned_start: string;
    planned_end: string;
    actual_completion_date?: string;
    status: string;
  }>>(`/activities`);
}

export async function getReviewQueue() {
  return fetchJson<Array<{
    id: number;
    raw_text: string;
    extracted_task: string;
    matched_schedule_id: number | null;
    confidence_score: number;
    review_status: string;
  }>>(`/review-queue`);
}

export async function getAuditTrail() {
  return fetchJson<Array<{
    id: number;
    created_at: string;
    raw_text: string;
    extracted_task: string;
    extracted_location?: string;
    extracted_date?: string;
    matched_schedule_id?: number | null;
    confidence_score?: number;
    review_status?: string;
  }>>(`/audit-trail`);
}
