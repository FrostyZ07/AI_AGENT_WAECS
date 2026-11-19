"use client";

import { useActionState } from "react";
import { btnPrimary } from "@/components/ui";

// Runs a server action (which returns an error string or null) and shows the error / pending state.
export default function ActionButton({
  action,
  label,
  pendingLabel = "Working...",
  className = btnPrimary,
}: {
  action: () => Promise<string | null>;
  label: string;
  pendingLabel?: string;
  className?: string;
}) {
  const [error, formAction, pending] = useActionState(async () => action(), null);
  return (
    <form action={formAction} className="inline-block">
      <button type="submit" disabled={pending} className={className}>
        {pending ? pendingLabel : label}
      </button>
      {error && (
        <p role="alert" className="mt-2 text-sm text-danger">
          {error}
        </p>
      )}
    </form>
  );
}
