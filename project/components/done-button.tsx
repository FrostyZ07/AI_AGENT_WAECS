'use client'

import { useState, useTransition } from 'react'
import { completeFollowUpAction } from '@/app/actions'

// Marks a follow-up done in the principal's own task list (no approval needed).
export default function DoneButton({ id }: { id: string }) {
  const [pending, start] = useTransition()
  const [error, setError] = useState<string | null>(null)
  return (
    <span className="shrink-0">
      <button
        type="button"
        disabled={pending}
        onClick={() => start(async () => setError(await completeFollowUpAction(id)))}
        className="inline-flex min-h-8 items-center rounded-md border border-[#e4dac6] px-3 text-[13px] font-medium text-stone-600 transition hover:bg-[#f8f4ea] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 disabled:opacity-60 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
      >
        {pending ? 'Saving…' : 'Mark done'}
      </button>
      {error && (
        <span role="alert" className="mt-1 block max-w-[160px] text-[12px] text-red-600 dark:text-red-400">
          {error}
        </span>
      )}
    </span>
  )
}
