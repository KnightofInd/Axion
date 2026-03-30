-- AXION Phase 3 orchestration checkpoint schema

create table if not exists public.pipeline_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  pipeline_date date not null,
  status text not null default 'running' check (status in ('running', 'completed', 'failed')),
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  last_error text,
  summary jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(user_id, pipeline_date)
);

create table if not exists public.pipeline_steps (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.pipeline_runs(id) on delete cascade,
  step_name text not null,
  status text not null default 'pending' check (status in ('pending', 'running', 'completed', 'failed', 'skipped')),
  output jsonb not null default '{}'::jsonb,
  error text,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(run_id, step_name)
);

create index if not exists idx_pipeline_runs_user_date on public.pipeline_runs(user_id, pipeline_date desc);
create index if not exists idx_pipeline_runs_status on public.pipeline_runs(status);
create index if not exists idx_pipeline_steps_run_status on public.pipeline_steps(run_id, status);

-- Reuse existing trigger function for updated_at.
drop trigger if exists trg_pipeline_runs_updated_at on public.pipeline_runs;
create trigger trg_pipeline_runs_updated_at before update on public.pipeline_runs
for each row execute function public.set_updated_at();

drop trigger if exists trg_pipeline_steps_updated_at on public.pipeline_steps;
create trigger trg_pipeline_steps_updated_at before update on public.pipeline_steps
for each row execute function public.set_updated_at();
