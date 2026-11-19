import { CalendarDays, Inbox, Mail } from 'lucide-react'
import { processInboxAction } from '@/app/actions'
import ActionButton from '@/components/action-button'
import { EmptyState, ErrorNotice, PageHeader, Panel, Pill, SectionHeading } from '@/components/dashboard'
import MeetingPrep from '@/components/meeting-prep'
import { getState } from '@/lib/api'
import { dayLabel, formatTime } from '@/lib/format'

export const metadata = { title: 'Calendar & Requests' }

export default async function CalendarPage() {
  const { data, error } = await getState()
  if (!data) return <ErrorNotice>{error}</ErrorNotice>

  const { meetings, requests } = data
  const days = [...new Set(meetings.map((m) => m.day))].sort((a, b) => a - b)
  const unprocessed = requests.filter((r) => !r.processed).length

  return (
    <>
      <PageHeader
        eyebrow="Inbox and schedule"
        title="Calendar & Requests"
        description="Incoming mail and meeting asks, plus the schedule they affect."
        action={
          <ActionButton
            action={processInboxAction}
            label={unprocessed > 0 ? `Process inbox (${unprocessed})` : 'Check inbox'}
            pendingLabel="Processing…"
            icon={<Inbox className="size-4" />}
          />
        }
      />

      <div className="grid items-start gap-5 lg:grid-cols-[1.1fr_1fr]">
        <Panel aria-labelledby="requests-heading">
          <SectionHeading icon={Mail} title="Incoming requests" count={requests.length} id="requests-heading" />
          {requests.length === 0 ? (
            <div className="mt-4"><EmptyState message='No requests yet. Click "Check inbox" to fetch mail.' /></div>
          ) : (
            <ul className="mt-4 divide-y divide-[#ece5d6] dark:divide-zinc-800">
              {requests.map((r) => (
                <li key={r.id} className="py-4 first:pt-0 last:pb-0">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <Pill tone={r.triage === 'sensitive' ? 'danger' : 'success'}>{r.triage}</Pill>
                    <Pill>{r.kind}</Pill>
                    {!r.processed && <Pill tone="accent">new</Pill>}
                  </div>
                  <h3 className="mt-2 text-[14px] font-medium leading-5 text-teal-900 dark:text-zinc-100">{r.subject}</h3>
                  <p className="mt-1 text-[12px] text-[#655e57] dark:text-zinc-400">
                    {r.from} <span className="px-1 text-stone-400 dark:text-zinc-600">·</span> {r.receivedOn ? `${r.receivedOn} ` : ''}{r.receivedAt}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel aria-labelledby="schedule-heading">
          <SectionHeading icon={CalendarDays} title="Schedule" count={meetings.length} id="schedule-heading" />
          {days.length === 0 ? (
            <div className="mt-4"><EmptyState message="No meetings scheduled." /></div>
          ) : (
            <div className="mt-4 space-y-6">
              {days.map((d) => (
                <div key={d}>
                  <h3 className="mb-2 font-mono text-[11px] font-medium uppercase tracking-[0.1em] text-[#655e57] dark:text-zinc-500">{dayLabel(d)}</h3>
                  <ul className="divide-y divide-[#ece5d6] dark:divide-zinc-800">
                    {meetings
                      .filter((m) => m.day === d)
                      .sort((a, b) => a.start.localeCompare(b.start))
                      .map((m) => (
                        <li key={m.id} className="flex gap-4 py-3 first:pt-0 last:pb-0">
                          <div className="w-[76px] shrink-0 pt-0.5 font-mono text-[12px] leading-5 tabular-nums text-[#655e57] dark:text-zinc-400">
                            {m.allDay ? (
                              <span className="font-sans text-[12px] font-medium">All day</span>
                            ) : (
                              <>
                                <span className="block text-teal-900 dark:text-zinc-200">{formatTime(m.start)}</span>
                                <span>{formatTime(m.end)}</span>
                              </>
                            )}
                          </div>
                          <div className="min-w-0 flex-1">
                            <h4 className="text-[14px] font-medium leading-5 text-teal-900 dark:text-zinc-100">{m.title}</h4>
                            <MeetingPrep m={m} />
                          </div>
                        </li>
                      ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </>
  )
}
