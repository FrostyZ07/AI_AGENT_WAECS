import Link from 'next/link'
import {
  ArrowUpRight,
  CalendarCheck,
  CalendarDays,
  ChevronRight,
  IndianRupee,
  FileText,
  Inbox,
  ListChecks,
  ListTodo,
  Mail,
  Reply,
  Sparkles,
  Timer,
  Users,
} from 'lucide-react'
import { generateBriefAction } from '@/app/actions'
import ActionButton from '@/components/action-button'
import { EmptyState, ErrorNotice, PageHeader, Panel, SectionHeading, StatCard, Pill, iconTile } from '@/components/dashboard'
import DoneButton from '@/components/done-button'
import MeetingPrep from '@/components/meeting-prep'
import { getKpis, getState } from '@/lib/api'
import { formatTime } from '@/lib/format'

export const metadata = { title: 'Daily Brief' }

function minutesLabel(m: number | null) {
  if (m === null) return '–'
  return m < 60 ? `${Math.round(m)} min` : `${(m / 60).toFixed(1)} h`
}

export default async function BriefPage() {
  const [{ data, error }, { data: kpis }] = await Promise.all([getState(), getKpis()])
  if (!data) return <ErrorNotice>{error}</ErrorNotice>

  const today = data.meetings.filter((m) => m.day === 0).sort((a, b) => a.start.localeCompare(b.start))
  // Overdue first, so they are not buried.
  const openFollowUps = data.followUps.filter((f) => !f.done).sort((a, b) => Number(!!b.overdue) - Number(!!a.overdue))
  const pendingApprovals = data.approvals.filter((a) => a.status === 'pending')
  const dueToday = openFollowUps.filter((f) => f.due === 'Today').length
  const brief = data.brief

  return (
    <>
      <PageHeader
        eyebrow="Today's schedule"
        title="Daily Brief"
        description="A clear view of what needs your attention today."
        action={<ActionButton action={generateBriefAction} label="Generate brief" pendingLabel="Generating…" icon={<Sparkles className="size-4" />} />}
      />

      <section aria-label="Today's overview" className="mb-6 grid gap-3 sm:grid-cols-3">
        <StatCard icon={CalendarDays} label="Meetings today" value={today.length} detail="On your calendar" />
        <StatCard icon={ListTodo} label="Open follow-ups" value={openFollowUps.length} detail={`${dueToday} due today`} />
        <Link
          href="/approvals"
          className="group rounded-xl border border-teal-200 bg-teal-50/70 p-4 shadow-[0_1px_2px_rgba(0,0,0,0.03)] transition hover:border-teal-300 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 dark:border-indigo-400/30 dark:bg-indigo-400/[0.07] dark:hover:border-indigo-300/50"
        >
          <div className="mb-4 flex items-center justify-between">
            <span className="text-[13px] font-medium text-teal-800 dark:text-indigo-200">Awaiting approval</span>
            <span className="grid size-8 place-items-center rounded-lg bg-[#fcfaf5]/80 text-teal-700 dark:bg-indigo-300/10 dark:text-indigo-300">
              <Inbox aria-hidden="true" className="size-4" />
            </span>
          </div>
          <div className="flex items-baseline justify-between">
            <span className="font-heading text-[32px] font-medium leading-none tracking-tight tabular-nums text-teal-950 dark:text-indigo-100">{pendingApprovals.length}</span>
            <span className="inline-flex items-center gap-1 text-[12px] font-medium text-teal-700 group-hover:underline dark:text-indigo-300">
              Review queue <ArrowUpRight aria-hidden="true" className="size-3" />
            </span>
          </div>
        </Link>
      </section>

      {kpis && (
        <section aria-labelledby="kpi-heading" className="mb-6">
          <h2 id="kpi-heading" className="mb-3 font-heading text-[16px] font-medium text-teal-900 dark:text-zinc-200">
            Last {kpis.days} days
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              icon={Timer}
              label="Brief on time"
              value={kpis.briefOnTime.total ? `${kpis.briefOnTime.onTime}/${kpis.briefOnTime.total}` : '–'}
              detail="within 15 min of set time"
            />
            <StatCard icon={CalendarCheck} label="Meetings booked" value={kpis.meetings.booked} detail={`${kpis.meetings.clashRefusals} clash refusals`} />
            <StatCard icon={Reply} label="Avg reply time" value={minutesLabel(kpis.avgReplyMinutes)} detail={`${kpis.repliesSent} replies sent`} />
            <StatCard
              icon={ListChecks}
              label="Follow-ups closed"
              value={kpis.followUps ? `${kpis.followUps.closed}/${kpis.followUps.total}` : '–'}
              detail="done vs. all"
            />
          </div>
        </section>
      )}

      <Panel aria-labelledby="assistant-brief" className="mb-6">
        <div className="mb-3 flex items-center gap-2">
          <span className="grid size-7 place-items-center rounded-lg bg-teal-50 text-teal-700 dark:bg-indigo-400/10 dark:text-indigo-300">
            <FileText aria-hidden="true" className="size-3.5" />
          </span>
          <h2 id="assistant-brief" className="font-heading text-[18px] font-medium tracking-tight">Assistant&apos;s brief</h2>
        </div>
        {brief ? (
          <>
            <p className="max-w-[760px] whitespace-pre-wrap font-reading text-[17px] leading-[1.65] text-stone-700 dark:text-zinc-300">{brief.text}</p>
            <p className="mt-3 text-[12px] text-[#655e57] dark:text-zinc-500">Generated {brief.generatedAt.replace('T', ' ')}</p>
          </>
        ) : (
          <EmptyState message="Generate your brief to see a summary of today." />
        )}
      </Panel>

      <div className="grid items-start gap-5 lg:grid-cols-2">
        <Panel aria-labelledby="meetings-heading">
          <SectionHeading icon={CalendarDays} title="Today's meetings" count={today.length} id="meetings-heading" />
          {today.length > 0 ? (
            <ol className="mt-4 divide-y divide-[#ece5d6] dark:divide-zinc-800">
              {today.map((m) => (
                <li key={m.id} className="flex gap-4 py-4 first:pt-0 last:pb-0">
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
                    <h3 className="text-[14px] font-medium leading-5 text-teal-900 dark:text-zinc-100">{m.title}</h3>
                    {m.attendees.length > 0 && (
                      <p className="mt-1 flex items-center gap-1.5 text-[12px] text-[#655e57] dark:text-zinc-400">
                        <Users aria-hidden="true" className="size-3" />
                        {m.attendees.join(', ')}
                      </p>
                    )}
                    <MeetingPrep m={m} />
                  </div>
                  <ChevronRight aria-hidden="true" className="mt-1 size-4 shrink-0 text-stone-400 dark:text-zinc-600" />
                </li>
              ))}
            </ol>
          ) : (
            <div className="mt-4"><EmptyState message="No meetings on the calendar today." /></div>
          )}
        </Panel>

        <Panel aria-labelledby="followups-heading">
          <SectionHeading icon={ListTodo} title="Open follow-ups" count={openFollowUps.length} id="followups-heading" />
          {openFollowUps.length > 0 ? (
            <ul className="mt-4 divide-y divide-[#ece5d6] dark:divide-zinc-800">
              {openFollowUps.map((f) => (
                <li key={f.id} className="flex items-start gap-3 py-4 first:pt-0 last:pb-0">
                  <span
                    aria-hidden="true"
                    className={`mt-[6px] size-2 shrink-0 rounded-full ring-4 ${f.overdue ? 'bg-red-500 ring-red-50 dark:bg-red-400 dark:ring-red-400/10' : 'bg-teal-500 ring-teal-50 dark:bg-indigo-400 dark:ring-indigo-400/10'}`}
                  />
                  <div className="min-w-0 flex-1">
                    <h3 className="text-[14px] font-medium leading-5 text-teal-900 dark:text-zinc-100">{f.task}</h3>
                    <p className="mt-1 text-[12px] text-[#655e57] dark:text-zinc-400">
                      {f.owner} <span className="px-1 text-stone-400 dark:text-zinc-600">·</span>{' '}
                      {f.overdue ? <span className="font-medium text-red-600 dark:text-red-400">Overdue, due {f.due}</span> : <>Due {f.due}</>}
                    </p>
                  </div>
                  <DoneButton id={f.id} />
                </li>
              ))}
            </ul>
          ) : (
            <div className="mt-4"><EmptyState message="You're all caught up. No open follow-ups." /></div>
          )}

          <div className="mt-6 border-t border-[#ece5d6] pt-5 dark:border-zinc-800">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-[13px] font-semibold text-teal-900 dark:text-zinc-200">Needs your approval</h3>
              <Link href="/approvals" className="inline-flex min-h-6 items-center text-[13px] font-medium text-teal-700 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 dark:text-indigo-400">
                View all
              </Link>
            </div>
            {pendingApprovals.length > 0 ? (
              <ul className="flex flex-col gap-2">
                {pendingApprovals.slice(0, 4).map((a) => {
                  const flagged = ['payment', 'travel', 'sensitive', 'review'].includes(a.type)
                  return (
                    <li key={a.id} className="flex items-start gap-3 rounded-lg border border-[#e4dac6]/80 px-3 py-3 dark:border-zinc-800">
                      <span className={`mt-0.5 grid size-7 shrink-0 place-items-center rounded-md ${flagged ? iconTile.danger : iconTile.info}`}>
                        {a.type === 'payment' ? <IndianRupee aria-hidden="true" className="size-4" /> : <Mail aria-hidden="true" className="size-4" />}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="text-[13px] font-medium leading-5 text-teal-900 dark:text-zinc-200">{a.summary}</p>
                        <span className="mt-1 inline-block"><Pill tone={flagged ? 'danger' : 'info'}>{a.type} · Pending</Pill></span>
                      </div>
                      <ArrowUpRight aria-hidden="true" className="mt-1 size-3.5 shrink-0 text-[#655e57]" />
                    </li>
                  )
                })}
              </ul>
            ) : (
              <EmptyState message="Nothing is waiting for your approval." />
            )}
          </div>
        </Panel>
      </div>
    </>
  )
}
