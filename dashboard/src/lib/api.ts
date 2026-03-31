import type {
  AxionTask,
  SidebarOverview,
  TaskSource,
  TaskStatus,
  TasksResponse,
  UpcomingEventsResponse,
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8000";
const AXION_API_KEY = process.env.NEXT_PUBLIC_AXION_API_KEY;

type FetchOptions = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
};

async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (AXION_API_KEY) {
    headers["x-api-key"] = AXION_API_KEY;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
    cache: "no-store",
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `API request failed (${response.status})`);
  }

  return (await response.json()) as T;
}

export async function getOAuthUrl() {
  return apiFetch<{ authorization_url: string }>("/api/v1/auth/google/url");
}

export async function getSidebarOverview(email: string, tab: "i_owe" | "they_owe" = "i_owe") {
  const query = new URLSearchParams({ email, commitments_tab: tab });
  return apiFetch<SidebarOverview>(`/api/v1/sidebar/overview?${query.toString()}`);
}

export async function runSidebarSync(email: string, resume = true) {
  const query = new URLSearchParams({ email, resume: String(resume) });
  return apiFetch<{ synced: boolean; pipeline: { run_id: string; status: string }; overview: SidebarOverview }>(
    `/api/v1/sidebar/sync?${query.toString()}`,
    { method: "POST" },
  );
}

export async function askSidebar(email: string, question: string) {
  const query = new URLSearchParams({ email });
  return apiFetch<{ answer: string; mode: string; fallback_reason?: string }>(`/api/v1/sidebar/ask?${query.toString()}`, {
    method: "POST",
    body: { question },
  });
}

export async function listTasks(email: string) {
  const query = new URLSearchParams({ email });
  return apiFetch<TasksResponse>(`/api/v1/tasks?${query.toString()}`);
}

export async function createTask(input: {
  email: string;
  title: string;
  description?: string | null;
  priority: number;
  source?: TaskSource;
  due_at?: string | null;
}) {
  return apiFetch<{ created: boolean; task: AxionTask }>("/api/v1/tasks/", {
    method: "POST",
    body: {
      source: "manual",
      ...input,
    },
  });
}

export async function updateTaskStatus(taskId: string, email: string, status: TaskStatus) {
  return apiFetch<{ updated: boolean; task: AxionTask }>(`/api/v1/tasks/${taskId}`, {
    method: "PATCH",
    body: { email, status },
  });
}

export async function deleteTask(taskId: string, email: string) {
  const query = new URLSearchParams({ email });
  return apiFetch<{ deleted: boolean; task_id: string }>(`/api/v1/tasks/${taskId}?${query.toString()}`, {
    method: "DELETE",
  });
}

export async function getUpcomingEvents(email: string, limit = 10) {
  const query = new URLSearchParams({ email, limit: String(limit) });
  return apiFetch<UpcomingEventsResponse>(`/api/v1/integrations/calendar/upcoming?${query.toString()}`);
}

export async function createCalendarTestEvent(email: string) {
  const query = new URLSearchParams({ email });
  return apiFetch<{ created: boolean; message: string; event?: Record<string, unknown> }>(
    `/api/v1/integrations/calendar/test-event?${query.toString()}`,
    { method: "POST" },
  );
}

export async function getLatestRun(email: string) {
  const query = new URLSearchParams({ email });
  return apiFetch<{ exists: boolean; run?: Record<string, unknown> }>(`/api/v1/orchestrator/runs/latest?${query.toString()}`);
}

export async function listOverdueCommitments(email: string) {
  const query = new URLSearchParams({ email });
  return apiFetch<{ count: number; commitments: Array<Record<string, unknown>> }>(
    `/api/v1/tasks/commitments/overdue?${query.toString()}`,
  );
}

export async function triggerOrchestrator(email: string, resume = true, maxFocusBlocks = 2) {
  const query = new URLSearchParams({
    email,
    resume: String(resume),
    max_focus_blocks: String(maxFocusBlocks),
  });
  return apiFetch<{ run_id: string; status: string; resumed: boolean }>(`/api/v1/orchestrator/run?${query.toString()}`, {
    method: "POST",
  });
}
