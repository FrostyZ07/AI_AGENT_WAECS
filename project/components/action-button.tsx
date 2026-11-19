'use client'

import { useActionState } from 'react'
import type { ReactNode } from 'react'

const base =
  'inline-flex min-h-10 items-center justify-center gap-2 rounded-lg px-4 font-nav text-[14px] font-medium tracking-[0.01em] shadow-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-2 disabled:cursor-wait disabled:opacity-75 dark:focus-visible:ring-offset-[#09090b]'
const variants = {
  primary: 'bg-teal-700 text-white hover:bg-teal-800 dark:bg-indigo-500 dark:hover:bg-indigo-400',
  success: 'bg-[#c2410c] text-white hover:bg-[#9a3412] dark:bg-orange-500 dark:hover:bg-orange-400',
  secondary:
    'border border-[#e4dac6] bg-[#fcfaf5] text-stone-700 hover:bg-[#f8f4ea] dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200 dark:hover:bg-zinc-800',
}

export const linkButtonClass = (variant: keyof typeof variants = 'primary') => `${base} ${variants[variant]}`

// Runs a server action (returns an error string or null) and shows pending/error state.
export default function ActionButton({
  action,
  label,
  pendingLabel = 'Working…',
  icon,
  variant = 'primary',
}: {
  action: () => Promise<string | null>
  label: string
  pendingLabel?: string
  icon?: ReactNode // an element (e.g. <Inbox className="size-4" />): components can't cross the server/client boundary
  variant?: keyof typeof variants
}) {
  const [error, formAction, pending] = useActionState(async () => action(), null)
  return (
    <form action={formAction} className="inline-block self-start sm:self-auto">
      <button type="submit" disabled={pending} className={linkButtonClass(variant)}>
        {icon && (
          <span aria-hidden="true" className={`inline-flex ${pending ? 'animate-pulse motion-reduce:animate-none' : ''}`}>
            {icon}
          </span>
        )}
        {pending ? pendingLabel : label}
      </button>
      {error && (
        <p role="alert" className="mt-2 max-w-sm text-xs text-red-600 dark:text-red-400">
          {error}
        </p>
      )}
    </form>
  )
}
