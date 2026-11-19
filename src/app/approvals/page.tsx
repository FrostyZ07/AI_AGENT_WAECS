import { Suspense } from "react";
import { decideApprovalAction } from "@/app/actions";
import ActionButton from "@/components/ActionButton";
import { Badge, Empty, ErrorNotice, Loading, PageHeader, btnSecondary, btnSuccess } from "@/components/ui";
import { getState } from "@/lib/api";

const flagged = ["payment", "travel", "sensitive"];
const statusTone = { pending: "warning", approved: "success", rejected: "neutral" } as const;

export default function ApprovalsPage() {
  return (
    <Suspense fallback={<Loading />}>
      <Approvals />
    </Suspense>
  );
}

async function Approvals() {
  const { data, error } = await getState();
  if (!data) return <ErrorNotice>{error}</ErrorNotice>;

  // Pending items first, then the rest in their original order.
  const approvals = [...data.approvals].sort((a, b) => (a.status === "pending" ? 0 : 1) - (b.status === "pending" ? 0 : 1));
  const pending = approvals.filter((a) => a.status === "pending").length;

  return (
    <>
      <PageHeader
        title="Approval Inbox"
        description={
          pending > 0
            ? `${pending} item${pending === 1 ? "" : "s"} waiting for your sign-off. Nothing is sent without it.`
            : "Nothing waiting for you. Nothing is sent without your sign-off."
        }
      />

      <div className="max-w-3xl space-y-4">
        {approvals.length === 0 && (
          <Empty>Nothing yet. Run &quot;Process inbox&quot; on the Calendar &amp; Requests page.</Empty>
        )}
        {approvals.map((a) => {
          const isFlagged = flagged.includes(a.type);
          return (
            <article
              key={a.id}
              className={`rounded-xl border border-border bg-surface p-5 shadow-sm ${
                isFlagged ? "border-l-4 border-l-danger" : ""
              } ${a.status !== "pending" ? "opacity-70" : ""}`}
            >
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={isFlagged ? "danger" : "info"}>{a.type}</Badge>
                <Badge tone={statusTone[a.status]}>{a.status}</Badge>
              </div>
              <h3 className="mt-3 font-semibold">{a.summary}</h3>
              {a.draft && (
                <p className="mt-3 whitespace-pre-wrap rounded-lg bg-background p-3 text-sm leading-relaxed text-foreground/80">
                  {a.draft}
                </p>
              )}
              {a.status === "pending" && (
                <div className="mt-4 flex flex-wrap gap-2">
                  <ActionButton
                    action={decideApprovalAction.bind(null, a.id, "approved")}
                    label="Approve"
                    className={btnSuccess}
                  />
                  <ActionButton
                    action={decideApprovalAction.bind(null, a.id, "rejected")}
                    label="Reject"
                    className={btnSecondary}
                  />
                </div>
              )}
            </article>
          );
        })}
      </div>
    </>
  );
}
