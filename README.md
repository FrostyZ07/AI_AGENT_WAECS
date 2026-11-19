# Executive Assistant Agent

An AI assistant for a busy principal. It triages the inbox, drafts replies, proposes meetings, preps for calls and sends a daily brief. **Nothing is sent, booked or paid without the principal's approval.**

Built from the spec in `../07_executive_assistant_agent.md`.

## What it does

- **Inbox triage**: reads Gmail, skips newsletters and auto-mail, drafts replies and flags anything sensitive.
- **Scheduling**: checks Google Calendar for clashes and working hours, then proposes invites.
- **Daily brief**: emails today's meetings, pending approvals and follow-ups.
- **Meeting prep**: pulls context from Google Drive (read-only).
- **Approvals**: the principal reviews, edits, approves or rejects every action. Payment, travel and sensitive mail are escalated for sign-off only; the agent never pays or books.

## Structure

| Folder | What it is |
| --- | --- |
| [agent-api/](agent-api/) | Python backend (FastAPI + Gemini), Google access, Supabase Postgres, scheduler |
| [project/](project/) | The UI (Next.js 16, Tailwind v4, shadcn): brief, approvals, calendar, settings |

The `src/` app that older notes mention is the Phase 1/2 prototype and is no longer wired up. Use `project/`.

## Quick start

You need Python 3.12+, [uv](https://docs.astral.sh/uv/), Node and pnpm.

1. **Set up the API.** Follow the one-time setup in [agent-api/README.md](agent-api/README.md) (Google Cloud OAuth, Supabase, `.env`).
2. **Run the API:**
   ```bash
   cd agent-api
   uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
3. **Run the UI:**
   ```bash
   cd project
   cp .env.example .env.local   # set AGENT_API_KEY, UI_PASSWORD, SESSION_SECRET
   pnpm install
   pnpm dev
   ```
4. Open http://localhost:3000, sign in, go to **Settings** and click **Connect Google**.

`AGENT_API_KEY` must be the same value in both `.env` files.

## Tests

```bash
cd agent-api && uv run pytest     # guardrail tests, no network or database
cd project && pnpm lint && pnpm build
```

## Status

Code is complete through the connect-your-systems phase. The Google connectors have not yet been piloted against real accounts.
