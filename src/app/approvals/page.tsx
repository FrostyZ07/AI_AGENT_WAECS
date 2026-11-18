import { Suspense } from "react";
import { decideApprovalAction } from "@/app/actions";
import ActionButton from "@/components/ActionButton";
import { getState } from "@/lib/api";

const flagged = ["payment", "travel", "sensitive"];

export default function ApprovalsPage() {
  return (
    <Suspense fallback={<p className="text-sm">Loading...</p>}>
      <Approvals />
    </Suspense>
  );
}

async function Approvals() {
  const { data, error } = await getState();
  if (!data) return <p className="rounded border border-red-300 p-4 text-sm text-red-800 dark:text-red-400">{error}</p>;

  return (
    <div className="max-w-2xl space-y-4">
      <h2 className="text-xl font-semibold">Approval Inbox</h2>
      {data.approvals.length === 0 && (
        <p className="text-sm text-black/60 dark:text-white/60">Nothing yet. Run &quot;Process inbox&quot; on the Calendar &amp; Requests page.</p>
      )}
      {data.approvals.map((a) => (
        <div key={a.id} className="rounded border p-4">
          <div className="mb-1 flex items-center gap-2">
            <span
              className={`rounded px-2 py-0.5 text-xs ${
                flagged.includes(a.type) ? "bg-red-100 text-red-800" : "bg-blue-100 text-blue-800"
              }`}
            >
              {a.type}
            </span>
            <span className="font-medium">{a.summary}</span>
          </div>
          {a.draft && <p className="mb-2 text-sm text-black/70 dark:text-white/70">{a.draft}</p>}
          {a.status === "pending" ? (
            <div className="flex gap-2">
              <ActionButton
                action={decideApprovalAction.bind(null, a.id, "approved")}
                label="Approve"
                className="rounded bg-green-600 px-3 py-1 text-sm text-white"
              />
              <ActionButton
                action={decideApprovalAction.bind(null, a.id, "rejected")}
                label="Reject"
                className="rounded bg-gray-600 px-3 py-1 text-sm text-white"
              />
            </div>
          ) : (
            <p className="text-sm font-medium">Status: {a.status}</p>
          )}
        </div>
      ))}
    </div>
  );
}
