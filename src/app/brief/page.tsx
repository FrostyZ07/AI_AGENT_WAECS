import Link from "next/link";
import { Suspense } from "react";
import { generateBriefAction } from "@/app/actions";
import ActionButton from "@/components/ActionButton";
import { Badge, Card, Empty, ErrorNotice, Loading, PageHeader, btnSecondary } from "@/components/ui";
import { getState } from "@/lib/api";

export default function BriefPage() {
  return (
    <Suspense fallback={<Loading />}>
      <Brief />
    </Suspense>
  );
}

async function Brief() {
  const { data, error } = await getState();
  if (!data) return <ErrorNotice>{error}</ErrorNotice>;

  const today = data.meetings.filter((m) => m.day === 0).sort((a, b) => a.start.localeCompare(b.start));
  const open = data.followUps.filter((f) => !f.done);
  const pending = data.approvals.filter((a) => a.status === "pending").length;

  return (
    <>
      <PageHeader
        title="Daily Brief"
        description="Today's meetings, open follow-ups and what needs your sign-off."
        action={<ActionButton action={generateBriefAction} label="Generate brief" pendingLabel="Generating..." />}
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <Stat label="Meetings today" value={today.length} />
        <Stat label="Open follow-ups" value={open.length} />
        <Link href="/approvals" className="block">
          <Stat label="Awaiting approval" value={pending} highlight={pending > 0} hint="Review" />
        </Link>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card title="Assistant's brief" className="lg:col-span-2">
          {data.brief ? (
            <>
              <p className="whitespace-pre-wrap text-sm leading-relaxed">{data.brief.text}</p>
              <p className="mt-4 text-xs text-muted">Generated {data.brief.generatedAt.replace("T", " ")}</p>
            </>
          ) : (
            <Empty>No brief yet. Click &quot;Generate brief&quot; to create one.</Empty>
          )}
        </Card>

        <Card title="Today's meetings" aside={<Badge>{today.length}</Badge>}>
          {today.length === 0 ? (
            <Empty>No meetings today.</Empty>
          ) : (
            <ul className="space-y-3">
              {today.map((m) => (
                <li key={m.id} className="rounded-lg border border-border p-3">
                  <div className="flex flex-wrap items-baseline gap-x-3">
                    <span className="font-mono text-xs tabular-nums text-muted">
                      {m.allDay ? "All day" : `${m.start}–${m.end}`}
                    </span>
                    <span className="text-sm font-medium">{m.title}</span>
                  </div>
                  {m.attendees.length > 0 && <p className="mt-1 text-xs text-muted">{m.attendees.join(", ")}</p>}
                  {m.prepNote && <p className="mt-2 rounded bg-background px-2 py-1 text-xs">Prep: {m.prepNote}</p>}
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Open follow-ups" aside={<Badge>{open.length}</Badge>}>
          {open.length === 0 ? (
            <Empty>Nothing open. Well done.</Empty>
          ) : (
            <ul className="space-y-3">
              {open.map((f) => (
                <li key={f.id} className="flex items-start gap-3">
                  <span aria-hidden className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-accent" />
                  <div className="text-sm">
                    <p className="font-medium">{f.task}</p>
                    <p className="text-xs text-muted">
                      {f.owner} · due {f.due}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <div className="mt-6">
        <Link href="/approvals" className={btnSecondary}>
          Go to approvals
        </Link>
      </div>
    </>
  );
}

function Stat({ label, value, highlight = false, hint }: { label: string; value: number; highlight?: boolean; hint?: string }) {
  return (
    <div
      className={`h-full rounded-xl border bg-surface p-5 shadow-sm transition ${
        highlight ? "border-accent/40 ring-1 ring-accent/20" : "border-border"
      }`}
    >
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-2 text-3xl font-semibold tabular-nums">{value}</p>
      {hint && <p className="mt-1 text-xs text-accent">{hint} →</p>}
    </div>
  );
}
