import { Suspense } from "react";
import { processInboxAction } from "@/app/actions";
import ActionButton from "@/components/ActionButton";
import { getState } from "@/lib/api";
import { dayLabel } from "@/lib/mock-data";

export default function CalendarPage() {
  return (
    <Suspense fallback={<p className="text-sm">Loading...</p>}>
      <Calendar />
    </Suspense>
  );
}

async function Calendar() {
  const { data, error } = await getState();
  if (!data) return <p className="rounded border border-red-300 p-4 text-sm text-red-800 dark:text-red-400">{error}</p>;

  const { meetings, requests } = data;
  const days = [...new Set(meetings.map((m) => m.day))].sort((a, b) => a - b);
  const unprocessed = requests.filter((r) => !r.processed).length;

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-xl font-semibold">Incoming requests</h2>
          <ActionButton
            action={processInboxAction}
            label={unprocessed > 0 ? `Process inbox (${unprocessed})` : "Check inbox"}
            pendingLabel="Processing..."
          />
        </div>
        <ul className="space-y-2">
          {requests.map((r) => (
            <li key={r.id} className="rounded border p-3 text-sm">
              <div className="flex items-center gap-2">
                <span
                  className={`rounded px-2 py-0.5 text-xs ${
                    r.triage === "sensitive" ? "bg-red-100 text-red-800" : "bg-green-100 text-green-800"
                  }`}
                >
                  {r.triage}
                </span>
                <span className="text-black/60 dark:text-white/60">
                  {r.kind} &middot; {r.receivedAt} &middot; {r.processed ? "processed" : "new"}
                </span>
              </div>
              <div className="mt-1 font-medium">{r.subject}</div>
              <div className="text-black/60 dark:text-white/60">{r.from}</div>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="mb-3 text-xl font-semibold">Schedule</h2>
        {days.map((d) => (
          <div key={d} className="mb-4">
            <h3 className="mb-1 font-medium">{dayLabel(d)}</h3>
            <ul className="space-y-1 text-sm">
              {meetings
                .filter((m) => m.day === d)
                .sort((a, b) => a.start.localeCompare(b.start))
                .map((m) => (
                  <li key={m.id} className="rounded border p-2">
                    <span className="font-mono">{m.start}-{m.end}</span> {m.title}
                  </li>
                ))}
            </ul>
          </div>
        ))}
      </section>
    </div>
  );
}
