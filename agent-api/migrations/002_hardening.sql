-- Run once in the Supabase SQL editor on an existing database (fresh installs: schema.sql already has all of this).

alter table requests  add column if not exists participants jsonb;        -- From/To/Cc addresses of the mail
alter table requests  add column if not exists reject_note text;          -- principal's reason when a proposal was rejected

alter table approvals add column if not exists meeting_date date;         -- absolute date (day offsets go stale)
alter table approvals add column if not exists created_at timestamptz not null default now();
alter table approvals add column if not exists decided_at timestamptz;
alter table approvals add column if not exists decision_note text;
alter table approvals add column if not exists edited boolean not null default false;

-- Pending meeting proposals were stored as day offsets: pin them to a date (relative to today, as before).
update approvals
   set meeting_date = (now() at time zone 'Asia/Kolkata')::date + day
 where type = 'meeting' and meeting_date is null and day is not null and status = 'pending';

-- Reject duplicate *pending* proposals so the unique index below can be created.
-- (If two rows for the same request+type are already 'approved', resolve that by hand first.)
update approvals a set status = 'rejected'
 where status = 'pending' and request_id is not null and exists (
   select 1 from approvals b
    where b.request_id = a.request_id and b.type = a.type and b.id < a.id
      and b.status in ('pending', 'approving', 'approved'));

create unique index if not exists approvals_one_open_per_request
  on approvals (request_id, type)
  where request_id is not null and status in ('pending', 'approving', 'approved');

create table if not exists meeting_prep (
  event_id text primary key,            -- Google Calendar event id
  meeting_date date,
  note text not null default '',
  docs jsonb not null default '[]',     -- [{id, name, url, modified}]
  generated_at timestamptz not null default now()
);

-- New settings fields (the API also fills these defaults in when they are missing).
update settings set data = data
  || jsonb_build_object('attendeeAllowDomains', coalesce(data->'attendeeAllowDomains', '[]'::jsonb))
  || jsonb_build_object('reminderMinutes', coalesce(data->'reminderMinutes', '15'::jsonb))
  || jsonb_build_object('escalationAlerts', coalesce(data->'escalationAlerts', 'true'::jsonb))
 where id = 1;
