-- Run once in the Supabase SQL editor on an existing database (fresh installs: schema.sql already has all of this).

-- Failed agent runs per request; at 3 the request becomes a 'review' approval instead of being retried forever.
alter table requests add column if not exists attempts int not null default 0;

-- Attachment file names: "INV-0042.pdf" under a bland subject must still be escalated as a payment.
alter table requests add column if not exists attachments jsonb;
