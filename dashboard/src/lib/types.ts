export type TaskStatus = "pending" | "in_progress" | "done";
export type TaskSource = "gmail" | "calendar" | "manual" | "debrief";

export type AxionTask = {
  id: string;
  title: string;
  description?: string | null;
  priority: number;
  source: TaskSource;
  status: TaskStatus;
  due_at?: string | null;
  computed_score?: number;
};

export type Commitment = {
  id: string;
  text: string;
  due_at?: string | null;
  direction: "given" | "received";
  status: string;
  context?: Record<string, unknown>;
};

export type CalendarEvent = {
  id: string;
  summary?: string;
  start?: string;
  end?: string;
  status?: string;
  html_link?: string;
};

export type SidebarOverview = {
  status: string;
  generated_at: string;
  briefing: {
    text: string;
    payload?: Record<string, unknown>;
    briefing_date?: string;
    generated_by?: string;
  };
  stats: {
    tasks: number;
    focus_blocks: number;
    commitments: number;
  };
  priority_tasks: AxionTask[];
  calendar: {
    focus_blocks: Array<Record<string, unknown>>;
    next_free_slot?: string | null;
  };
  commitments: {
    i_owe: Commitment[];
    they_owe: Commitment[];
    selected_tab: "i_owe" | "they_owe";
    selected_items: Commitment[];
  };
  empty: boolean;
  latest_run?: {
    id: string;
    status: string;
    started_at?: string;
    finished_at?: string;
    error_message?: string;
    summary?: Record<string, unknown>;
  } | null;
  user: {
    id: string;
    email: string;
    name?: string | null;
  };
};

export type UpcomingEventsResponse = {
  connected: boolean;
  message: string;
  events: CalendarEvent[];
  requested_limit?: number;
  fetched_count?: number;
};

export type TasksResponse = {
  count: number;
  tasks: AxionTask[];
};
