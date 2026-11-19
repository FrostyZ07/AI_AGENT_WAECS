import { Clock3 } from 'lucide-react'
import AppSidebar from '@/components/app-sidebar'
import { getState } from '@/lib/api'

export default async function ConsoleLayout({ children }: { children: React.ReactNode }) {
  const { data } = await getState()
  const pending = data ? data.approvals.filter((a) => a.status === 'pending').length : 0

  return (
    <div className="min-h-screen bg-[#f3eee3] text-teal-900 dark:bg-[#09090b] dark:text-zinc-50">
      <AppSidebar pendingApprovals={pending} />
      <main className="mx-auto min-h-screen max-w-[1320px] px-4 py-8 sm:px-7 sm:py-10 md:ml-[248px] md:px-10 lg:px-12">
        <div className="mx-auto max-w-[1080px]">
          {children}
          <div className="mt-6 flex items-center gap-2 text-[11px] text-stone-500 dark:text-zinc-500">
            <Clock3 aria-hidden="true" className="size-3.5" /> Your assistant prepares actions for review. Nothing is sent without your approval.
          </div>
        </div>
      </main>
    </div>
  )
}
