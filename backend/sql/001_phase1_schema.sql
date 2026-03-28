-- AXION Phase 1 base schema
create extension if not exists vector;

create table if not exists public.users (
  id uuid primary key default gen_random_uuid(),
  google_user_id text unique not null,
  email text unique not null,
  full_name text,
  refresh_token text,
  access_token text,
  token_expires_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.tasks (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  source text not null check (source in ('gmail', 'calendar', 'manual', 'debrief')),
  title text not null,
  description text,
  status text not null default 'pending' check (status in ('pending', 'in_progress', 'done')),
  priority int not null default 3,
  due_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  embedding vector(768),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.commitments (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  direction text not null check (direction in ('given', 'received')),
  counterpart text,
  text text not null,
  due_at timestamptz,
  status text not null default 'open' check (status in ('open', 'fulfilled', 'overdue')),
  source_message_id text,
  metadata jsonb not null default '{}'::jsonb,
  embedding vector(768),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.briefings (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  briefing_date date not null,
  payload jsonb not null,
  generated_by text not null default 'gemini-1.5-pro',
  created_at timestamptz not null default now(),
  unique (user_id, briefing_date)
);

create index if not exists idx_tasks_user_status on public.tasks(user_id, status);
create index if not exists idx_tasks_due_at on public.tasks(due_at);
create index if not exists idx_commitments_user_status on public.commitments(user_id, status);
create index if not exists idx_commitments_due_at on public.commitments(due_at);
create index if not exists idx_briefings_user_date on public.briefings(user_id, briefing_date desc);

create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_users_updated_at on public.users;
create trigger trg_users_updated_at before update on public.users
for each row execute function public.set_updated_at();

drop trigger if exists trg_tasks_updated_at on public.tasks;
create trigger trg_tasks_updated_at before update on public.tasks
for each row execute function public.set_updated_at();

drop trigger if exists trg_commitments_updated_at on public.commitments;
create trigger trg_commitments_updated_at before update on public.commitments
for each row execute function public.set_updated_at();
