'use client'

import { useSyncExternalStore } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { CalendarDays, Check, LayoutDashboard, LogOut, ScrollText, Settings2, Sparkles } from 'lucide-react'
import { logoutAction } from '@/app/login/actions'
import Brand from '@/components/brand'

const navigation = [
  { label: 'Daily Brief', href: '/brief', icon: LayoutDashboard },
  { label: 'Approvals', href: '/approvals', icon: Check },
  { label: 'Calendar & Requests', href: '/calendar', icon: CalendarDays },
  { label: 'Audit log', href: '/audit', icon: ScrollText },
  { label: 'Settings', href: '/settings', icon: Settings2 },
]

const active = 'bg-teal-50 text-teal-700 dark:bg-indigo-400/10 dark:text-indigo-300'

const noop = () => () => {}

export default function AppSidebar({ pendingApprovals }: { pendingApprovals: number }) {
  // The prerendered shell doesn't know the URL, so the first client render must match it (no active link);
  // the active link is applied right after hydration. Avoids a hydration mismatch on aria-current/className.
  const hydrated = useSyncExternalStore(noop, () => true, () => false)
  const pathname = usePathname()
  const current = hydrated ? pathname : null
  return (
    <>
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-[248px] flex-col border-r border-[#e4dac6] bg-[#fcfaf5] px-4 py-6 dark:border-zinc-800 dark:bg-[#111114] md:flex">
        <Link href="/brief" className="mb-9 flex items-center gap-3 rounded-lg px-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500">
          <Brand />
        </Link>
        <nav aria-label="Main navigation" className="flex flex-col gap-1">
          {navigation.map(({ label, href, icon: Icon }) => {
            const isActive = current === href
            return (
              <Link
                key={href}
                href={href}
                aria-current={isActive ? 'page' : undefined}
                className={`group flex items-center gap-3 rounded-lg px-3 py-2.5 font-nav text-[14px] font-medium tracking-[0.01em] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 ${isActive ? active : 'text-stone-600 hover:bg-[#efe8d9] hover:text-teal-900 dark:text-zinc-400 dark:hover:bg-zinc-800/70 dark:hover:text-zinc-100'}`}
              >
                <Icon aria-hidden="true" className="size-[17px]" strokeWidth={1.8} />
                {label}
                {href === '/approvals' && pendingApprovals > 0 && (
                  <span className="ml-auto rounded-md bg-[#fcfaf5] px-1.5 py-0.5 text-[12px] tabular-nums text-stone-600 ring-1 ring-[#e4dac6] dark:bg-zinc-900 dark:text-zinc-300 dark:ring-zinc-700">
                    {pendingApprovals}
                  </span>
                )}
              </Link>
            )
          })}
        </nav>
        <div className="mt-auto rounded-xl border border-[#e4dac6] bg-[#f8f4ea] p-3.5 dark:border-zinc-800 dark:bg-zinc-900/60">
          <div className="mb-1.5 flex items-center gap-2 text-xs font-medium text-teal-900 dark:text-zinc-200">
            <Sparkles aria-hidden="true" className="size-3.5 text-teal-700 dark:text-indigo-400" />
            Always in control
          </div>
          <p className="text-[12px] leading-relaxed text-[#655e57] dark:text-zinc-400">Nothing is sent or paid without your approval.</p>
          <form action={logoutAction} className="mt-3 border-t border-[#e4dac6] pt-3 dark:border-zinc-800">
            <button
              type="submit"
              className="flex min-h-8 items-center gap-2 rounded-md text-[13px] font-medium text-stone-600 hover:text-teal-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 dark:text-zinc-400 dark:hover:text-zinc-100"
            >
              <LogOut aria-hidden="true" className="size-3.5" /> Sign out
            </button>
          </form>
        </div>
      </aside>

      <div className="sticky top-0 z-10 border-b border-[#e4dac6] bg-[#fcfaf5]/95 px-4 py-3 backdrop-blur dark:border-zinc-800 dark:bg-[#111114]/95 md:hidden">
        <div className="mb-3">
          <Brand size="sm" />
        </div>
        <nav aria-label="Main navigation" className="flex gap-1 overflow-x-auto pb-0.5">
          {navigation.map(({ label, href, icon: Icon }) => {
            const isActive = current === href
            return (
              <Link
                key={href}
                href={href}
                aria-current={isActive ? 'page' : undefined}
                className={`flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 font-nav text-[14px] font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 ${isActive ? active : 'text-stone-600 hover:bg-[#efe8d9] dark:text-zinc-400 dark:hover:bg-zinc-800'}`}
              >
                <Icon aria-hidden="true" className="size-3.5" />
                {label}
              </Link>
            )
          })}
        </nav>
      </div>
    </>
  )
}
