# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Executive Assistant Agent, built from the spec `../07_executive_assistant_agent.md` (calendar, inbox triage, draft replies, daily brief, principal approvals). Guiding motto: **the easiest method is the best method**, so keep solutions as simple as possible and don't add libraries, services or abstractions that aren't needed yet.

The spec's build steps: 1) scaffold screens with mock data (**done — Phase 1**) → 2) role prompt, tools and guardrails (**done — Phase 2**: Python + Gemini, see `../agent-api/`) → 3) connect systems (**code done — Phase 3**: Google Gmail/Calendar/Tasks via OAuth, Supabase Postgres, APScheduler; credentials not set up and not yet piloted, so the connectors are untested against real accounts), pilot, fix. Guardrails from the spec: nothing is sent or committed on the principal's behalf without approval; payments and travel bookings need sign-off; sensitive mail is escalated.

## Commands

The Python agent API must be running for the UI to show data (see `../agent-api/README.md`):

```
cd ../agent-api && uv run uvicorn app.main:app --reload --port 8000   # needs GEMINI_API_KEY, DATABASE_URL, GOOGLE_* in agent-api/.env
```

```
npm run dev      # dev server at http://localhost:3000
npm run lint     # eslint
npm run build    # production build (also runs TypeScript type-check)
```

Guardrail tests (no network/DB): `cd ../agent-api && uv run pytest`. UI gates: `lint` + `build`.

## Next.js version caveat

This is Next.js 16 with breaking changes from older versions (see `AGENTS.md`). Before using an unfamiliar API, read the matching guide in `node_modules/next/dist/docs/` (App Router docs are under `01-app/`).

## Architecture

- **Two parts.** `../agent-api/` (Python, FastAPI, Gemini via `google-genai`) owns the agent, role prompt, tools, guardrails, a Supabase Postgres store (`store.py`, schema in `schema.sql`) and all Google access (`google_api.py`). Meetings and follow-ups are not stored: Google Calendar / Tasks are the source of truth. A scheduler (`SCHEDULER_ENABLED=1`) polls the inbox and emails the daily brief. This Next app is a thin UI. Prefer Python for new logic (user preference).
- Next side: App Router, TypeScript, Tailwind v4, `src/` dir, `@/*` alias. `cacheComponents` is on, so each page is a sync shell with `<Suspense>` around an async component that calls `getState()` (`src/lib/api.ts`, uncached fetch of `AGENT_API_URL`, default `http://localhost:8000`).
- Mutations are server actions in `src/app/actions.ts` (return an error string or null) run via `src/components/ActionButton.tsx`, which shows pending/error state.
- `src/lib/mock-data.ts` now only holds the shared TS types and the Phase 1 seed (unused by the live app). Keep the types in sync with the API shapes.
- Meeting dates are `day` offsets from today plus `"HH:MM"` strings (rendered via `dayLabel`), so server and client render identically.
- Screens: `/brief` (Generate brief), `/approvals` (Approve/Reject), `/calendar` (Process inbox + schedule), `/settings` (saved to the API; the prompt reads them). `/` redirects to `/brief`.
- Guardrails are enforced in code in `agent-api/app/tools.py` and `agent.py`: no send/book/pay tool exists (real side effects - send reply, create event - happen only in `POST /approvals/{id}` after approval; payment/travel/sensitive only record sign-off, code never pays or books); `classify_sensitive` force-escalates payment/travel/sensitive mail before the model runs and again as a backstop after; `propose_meeting` re-checks clashes and working hours.
- Approval `type` values `payment`, `travel`, `sensitive` are the spec's human-checkpoint cases, styled red.
