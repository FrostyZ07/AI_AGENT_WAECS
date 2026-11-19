import Link from 'next/link'
import { EmptyState, ErrorNotice, PageHeader, Panel } from '@/components/dashboard'
import { getAudit } from '@/lib/api'

export const metadata = { title: 'Audit log' }

// Details can hold email-derived text, so show only a short preview.
const preview = (d: Record<string, unknown>) => {
  const s = JSON.stringify(d)
  return s.length > 180 ? `${s.slice(0, 180)}…` : s
}

export default async function AuditPage({ searchParams }: { searchParams: Promise<{ event?: string }> }) {
  const { event } = await searchParams
  const { data, error } = await getAudit(event)
  if (!data) return <ErrorNotice>{error}</ErrorNotice>

  const chip = (active: boolean) =>
    `rounded-md px-2 py-1 text-[11px] font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 ${
      active
        ? 'bg-teal-700 text-white dark:bg-indigo-500'
        : 'bg-[#efe8d9] text-stone-600 hover:bg-[#e6dcc8] dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700'
    }`

  return (
    <>
      <PageHeader eyebrow="Accountability" title="Audit log" description="Everything the assistant did or was asked to do, newest first." />

      <nav aria-label="Filter by event" className="mb-4 flex flex-wrap gap-1.5">
        <Link href="/audit" className={chip(!event)}>
          All
        </Link>
        {data.events.map((e) => (
          <Link key={e} href={`/audit?event=${encodeURIComponent(e)}`} className={chip(e === event)} aria-current={e === event ? 'page' : undefined}>
            {e}
          </Link>
        ))}
      </nav>

      <Panel aria-label="Audit entries">
        {data.entries.length === 0 ? (
          <EmptyState message="No entries yet." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[12px]">
              <thead>
                <tr className="text-[10px] font-semibold uppercase tracking-[0.08em] text-stone-500 dark:text-zinc-500">
                  <th className="py-2 pr-4 font-semibold">Time</th>
                  <th className="py-2 pr-4 font-semibold">Event</th>
                  <th className="py-2 font-semibold">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#ece5d6] dark:divide-zinc-800">
                {data.entries.map((e) => (
                  <tr key={e.id} className="align-top">
                    <td className="whitespace-nowrap py-2.5 pr-4 font-mono text-[11px] tabular-nums text-stone-500 dark:text-zinc-400">{e.at}</td>
                    <td className="whitespace-nowrap py-2.5 pr-4 font-medium text-teal-900 dark:text-zinc-100">{e.event}</td>
                    <td className="break-all py-2.5 font-mono text-[11px] text-stone-500 dark:text-zinc-400">{preview(e.details)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </>
  )
}
