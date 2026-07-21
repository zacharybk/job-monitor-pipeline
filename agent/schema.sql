-- job_monitor/agent/schema.sql — tracking spine for the applying engine.
-- Idempotent: safe to re-run.

create table if not exists picks (
  id           uuid primary key default gen_random_uuid(),
  job_id       uuid not null references jobs(id) on delete cascade,
  picked_date  date not null default current_date,
  fit_verdict  text not null,          -- 'apply' | 'apply_with_angle'
  fit_rubric   jsonb,                   -- {stage,comp,remote,scope,ai,domain}
  reasoning    text,
  angle        text,                    -- for apply_with_angle
  rank         int,
  tier         text,                    -- 'top' | 'standard'
  user_decision text,                   -- 'pursue' | 'skip' | 'applied' | null
  decided_at   timestamptz,
  created_at   timestamptz not null default now(),
  unique (job_id)
);

create table if not exists contacts (
  id           uuid primary key default gen_random_uuid(),
  company      text not null,
  name         text not null,
  role         text,
  email        text,
  email_source text,                    -- 'apollo'|'hunter'|'pattern'|'public'
  confidence   text,                    -- 'high'|'medium'|'low'
  linkedin_url text,
  job_id       uuid references jobs(id) on delete set null,
  created_at   timestamptz not null default now(),
  unique (company, name)
);

create table if not exists outreach (
  id            uuid primary key default gen_random_uuid(),
  contact_id    uuid not null references contacts(id) on delete cascade,
  job_id        uuid references jobs(id) on delete set null,
  track         text not null,          -- 'job' | 'network'
  sequence_step int not null default 1, -- 1 initial, 2 +4d, 3 +5d
  subject       text,
  body          text,
  status        text not null default 'drafted',  -- drafted|approved|sent|replied|closed
  drafted_at    timestamptz not null default now(),
  sent_at       timestamptz,
  reply_at      timestamptz,
  unique (contact_id, track, sequence_step)
);

create table if not exists applications (
  id         uuid primary key default gen_random_uuid(),
  job_id     uuid not null references jobs(id) on delete cascade,
  status     text not null default 'drafted', -- drafted|applied|interviewing|rejected|offer
  cover_letter_path text,
  applied_at timestamptz,
  notes      text,
  created_at timestamptz not null default now(),
  unique (job_id)
);

create table if not exists network_targets (
  id            uuid primary key default gen_random_uuid(),
  target_type   text not null,          -- 'vc_firm' | 'yc_founder'
  org           text not null,
  focus         text,
  why_target    text,
  funding_signal text,
  tier          int,                    -- 1..3
  best_person   text,
  status        text not null default 'queued', -- queued|researched|contacted|in_network|closed
  notes         text,
  created_at    timestamptz not null default now(),
  unique (target_type, org)
);

create table if not exists activity_log (
  day               date primary key default current_date,
  jobs_reviewed     int default 0,
  picks_made        int default 0,
  emails_drafted    int default 0,
  emails_sent       int default 0,
  applications_sent int default 0,
  replies           int default 0,
  agent_ran_at      timestamptz,
  discovery_notes   jsonb,              -- {query: picks_produced}
  summary           text
);

create table if not exists draft_feedback (
  id           uuid primary key default gen_random_uuid(),
  outreach_id  uuid references outreach(id) on delete cascade,
  edited_body  text,
  feedback_note text,
  created_at   timestamptz not null default now()
);

-- RLS on: service key (the agent) bypasses; anon/authenticated denied until the
-- dashboard adds explicit policies (plan 2). Keeps contacts/drafts private.
alter table picks enable row level security;
alter table contacts enable row level security;
alter table outreach enable row level security;
alter table applications enable row level security;
alter table network_targets enable row level security;
alter table activity_log enable row level security;
alter table draft_feedback enable row level security;
