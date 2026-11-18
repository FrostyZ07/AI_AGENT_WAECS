"use client";

import { useActionState } from "react";

// Runs a server action (which returns an error string or null) and shows the error / pending state.
export default function ActionButton({
  action,
  label,
  pendingLabel = "Working...",
  className = "rounded bg-foreground px-4 py-2 text-sm text-background",
}: {
  action: () => Promise<string | null>;
  label: string;
  pendingLabel?: string;
  className?: string;
}) {
  const [error, formAction, pending] = useActionState(async () => action(), null);
  return (
    <form action={formAction} className="inline-block">
      <button type="submit" disabled={pending} className={`${className} disabled:opacity-50`}>
        {pending ? pendingLabel : label}
      </button>
      {error && <p className="mt-2 text-sm text-red-700 dark:text-red-400">{error}</p>}
    </form>
  );
}
