-- Run once in the Supabase SQL editor. Meetings and follow-ups live in Google Calendar / Tasks, not here.

create table if not exists requests (
  id text primary key,                 -- Gmail message id
  thread_id text,
  message_id text,                     -- RFC822 Message-ID header, for threading replies
  from_addr text not null,
  subject text not null default '',
  body text not null default '',
  received_at timestamptz not null default now(),
  kind text not null default 'mail',   -- 'mail' | 'meeting'
  triage text not null default 'routine',
  processed boolean not null default false
);

create table if not exists approvals (
  id serial primary key,
  type text not null,                  -- reply | meeting | payment | travel | sensitive
  summary text not null,
  draft text,
  status text not null default 'pending',
  request_id text,
  title text,
  day int,
  start text,
  "end" text,
  attendees jsonb,
  google_ref text                      -- created event id or sent message id
);

create table if not exists settings (
  id int primary key default 1 check (id = 1),
  data jsonb not null
);

create table if not exists brief (
  id int primary key default 1 check (id = 1),
  text text not null,
  generated_at timestamptz not null default now()
);

create table if not exists audit_log (
  id serial primary key,
  at timestamptz not null default now(),
  event text not null,
  details jsonb not null default '{}'
);

create table if not exists oauth_token (
  id int primary key default 1 check (id = 1),
  token jsonb not null,
  email text
);

insert into settings (id, data) values (1, '{
  "workingHours": {"start": "09:00", "end": "18:00"},
  "sensitiveKeywords": ["confidential", "contract", "legal", "salary", "invoice", "payment"],
  "replyTemplates": [
    "Thanks for reaching out. I''ll check the calendar and get back to you shortly.",
    "Thank you for the update. Noted, and we''ll follow up by end of week."
  ],
  "timezone": "Asia/Kolkata",
  "briefTime": "08:00",
  "pollMinutes": 10
}') on conflict (id) do nothing;
