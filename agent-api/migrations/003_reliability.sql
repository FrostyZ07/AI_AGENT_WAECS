-- Run once in the Supabase SQL editor on an existing database (fresh installs: schema.sql already has all of this).

-- Failed agent runs per request; at 3 the request becomes a 'review' approval instead of being retried forever.
alter table requests add column if not exists attempts int not null default 0;
