import { Suspense } from "react";
import { processInboxAction } from "@/app/actions";
import ActionButton from "@/components/ActionButton";
import { Badge, Card, Empty, ErrorNotice, Loading, PageHeader } from "@/components/ui";
import { getState } from "@/lib/api";
import { dayLabel } from "@/lib/mock-data";

export default function CalendarPage() {
  return (
    <Suspense fallback={<Loading />}>
      <Calendar />
    </Suspense>
  );
}

async function Calendar() {
  const { data, error } = await getState();
  if (!data) return <ErrorNotice>{error}</ErrorNotice>;

  const { meetings, requests } = data;
  const days = [...new Set(meetings.map((m) => m.day))].sort((a, b) => a - b);
  const unprocessed = requests.filter((r) => !r.processed).length;

  return (
    <>
      <PageHeader
        title="Calendar & Requests"
        description="Incoming mail and meeting asks, plus the schedule they affect."
        action={
          <ActionButton
            action={processInboxAction}
            label={unprocessed > 0 ? `Process inbox (${unprocessed})` : "Check inbox"}
            pendingLabel="Processing..."
          />
        }
      />

      <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        <Card title="Incoming requests" aside={<Badge>{requests.length}</Badge>}>
          {requests.length === 0 ? (
            <Empty>No requests yet. Click &quot;Check inbox&quot; to fetch mail.</Empty>
          ) : (
            <ul className="space-y-3">
              {requests.map((r) => (
                <li key={r.id} className="rounded-lg border border-border p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={r.triage === "sensitive" ? "danger" : "success"}>{r.triage}</Badge>
                    <Badge>{r.kind}</Badge>
                    {!r.processed && <Badge tone="info">new</Badge>}
                  </div>
                  <p className="mt-2 font-medium">{r.subject}</p>
                  <p className="mt-0.5 text-sm text-muted">
                    {r.from} · {r.receivedAt}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Schedule">
          {days.length === 0 ? (
            <Empty>No meetings scheduled.</Empty>
          ) : (
            <div className="space-y-6">
              {days.map((d) => (
                <div key={d}>
                  <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">{dayLabel(d)}</h4>
                  <ul className="space-y-2">
                    {meetings
                      .filter((m) => m.day === d)
                      .sort((a, b) => a.start.localeCompare(b.start))
                      .map((m) => (
                        <li key={m.id} className="flex gap-4 rounded-lg border border-border p-3">
                          <span className="w-24 shrink-0 font-mono text-xs tabular-nums text-muted">
                            {m.allDay ? "All day" : `${m.start}–${m.end}`}
                          </span>
                          <span className="text-sm font-medium">{m.title}</span>
                        </li>
                      ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
