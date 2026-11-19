'use client'

import { useActionState } from 'react'
import { loginAction } from '@/app/login/actions'
import Brand from '@/components/brand'
import { linkButtonClass } from '@/components/action-button'

const input =
  'w-full rounded-lg border border-[#e4dac6] bg-[#fcfaf5] px-3 py-2 text-[13px] outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 dark:border-zinc-700 dark:bg-zinc-900 dark:focus:border-indigo-400'

export default function LoginPage() {
  const [error, formAction, pending] = useActionState(loginAction, null)
  return (
    <main className="grid min-h-screen place-items-center bg-[#f3eee3] px-4 text-teal-900 dark:bg-[#09090b] dark:text-zinc-50">
      <form
        action={formAction}
        className="w-full max-w-sm space-y-5 rounded-xl border border-[#e4dac6] bg-[#fcfaf5] p-6 shadow-[0_1px_2px_rgba(0,0,0,0.035)] dark:border-zinc-800 dark:bg-[#111114]"
      >
        <div className="space-y-2">
          <h1><Brand /></h1>
          <p className="text-[11px] text-stone-500 dark:text-zinc-400">Sign in to review approvals</p>
        </div>
        <label className="block space-y-1.5 text-[12px] font-medium text-teal-900 dark:text-zinc-200">
          Password
          <input name="password" type="password" autoComplete="current-password" required autoFocus className={input} />
        </label>
        {error && (
          <p role="alert" className="text-[12px] text-red-600 dark:text-red-400">
            {error}
          </p>
        )}
        <button type="submit" disabled={pending} className={`${linkButtonClass('primary')} w-full`}>
          {pending ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </main>
  )
}
