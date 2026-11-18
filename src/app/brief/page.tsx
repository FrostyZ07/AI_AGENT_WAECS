import Link from "next/link";
import { Suspense } from "react";
import { generateBriefAction } from "@/app/actions";
import ActionButton from "@/components/ActionButton";
import { getState } from "@/lib/api";

export default function BriefPage() {
  return (
    <Suspense fallback={<p className="text-sm">Loading...</p>}>
      <Brief />
    </Suspense>
  );
}

async function Brief() {
  const { data, error } = await getState();
  if (!data) return <p className="rounded border border-red-300 p-4 text-sm text-red-800 dark:text-red-400">{error}</p>;

  const today = data.meetings.filter((m) => m.day === 0);
  const open = data.followUps.filter((f) => !f.done);
  const pending = data.approvals.filter((a) => a.status === "pending").length;

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Daily Brief</h2>
        <ActionButton action={generateBriefAction} label="Generate brief" pendingLabel="Generating..." />
      </div>

      {data.brief && (
        <section className="rounded border p-4">
          <h3 className="mb-2 font-medium">Assistant&apos;s brief</h3>
          <p className="whitespace-pre-wrap text-sm">{data.brief.text}</p>
          <p className="mt-2 text-xs text-black/50 dark:text-white/50">Generated {data.brief.generatedAt.replace("T", " ")}</p>
        </section>
      )}

      <section className="rounded border p-4">
        <h3 className="mb-2 font-medium">Pending approvals</h3>
        <p className="text-sm">
          {pending} item(s) waiting for your sign-off. <Link href="/approvals" className="underline">Review</Link>
        </p>
      </section>

      <section className="rounded border p-4">
        <h3 className="mb-2 font-medium">Today&apos;s meetings</h3>
        <ul className="space-y-2 text-sm">
          {today.map((m) => (
            <li key={m.id}>
              <span className="font-mono">{m.start}-{m.end}</span> {m.title} ({m.attendees.join(", ")})
              {m.prepNote && <div className="text-black/60 dark:text-white/60">Prep: {m.prepNote}</div>}
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded border p-4">
        <h3 className="mb-2 font-medium">Open follow-ups</h3>
        <ul className="space-y-1 text-sm">
          {open.map((f) => (
            <li key={f.id}>{f.task} - {f.owner}, due {f.due}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
