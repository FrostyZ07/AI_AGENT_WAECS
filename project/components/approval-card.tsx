'use client'

import { useState, useTransition } from 'react'
import { CalendarDays, CircleHelp, IndianRupee, Mail, Plane, ShieldAlert, X, type LucideIcon } from 'lucide-react'
import { decideApprovalAction } from '@/app/actions'
import { linkButtonClass } from '@/components/action-button'
import { NoteBox, Pill, iconTile, panel } from '@/components/dashboard'
import { formatTime } from '@/lib/format'
import type { Approval, ApprovalType } from '@/lib/types'

const flagged: ApprovalType[] = ['payment', 'travel', 'sensitive', 'review']
const typeIcon: Record<ApprovalType, LucideIcon> = {
  payment: IndianRupee,
  travel: Plane,
  sensitive: ShieldAlert,
  review: CircleHelp,
  reply: Mail,
  meeting: CalendarDays,
}
const statusTone = { pending: 'warning', approving: 'warning', approved: 'success', rejected: 'neutral' } as const
const field =
  'w-full rounded-lg border border-[#e4dac6] bg-[#fcfaf5] px-3 py-2 text-[14px] outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 dark:border-zinc-700 dark:bg-zinc-900 dark:focus:border-indigo-400'

export default function ApprovalCard({ a }: { a: Approval }) {
  const isFlagged = flagged.includes(a.type)
  const Icon = typeIcon[a.type]
  const open = a.status === 'pending'

  const [draft, setDraft] = useState(a.draft ?? '')
  const [attendees, setAttendees] = useState<string[]>(a.attendees ?? [])
  const [startTime, setStartTime] = useState(a.start ?? '')
  const [endTime, setEndTime] = useState(a.end ?? '')
  const [newGuest, setNewGuest] = useState('')
  const [rejecting, setRejecting] = useState(false)
  const [note, setNote] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [pending, start] = useTransition()

  function addGuest() {
    const g = newGuest.trim()
    if (g && !attendees.includes(g)) setAttendees([...attendees, g])
    setNewGuest('')
    return g && !attendees.includes(g) ? [...attendees, g] : attendees
  }

  function decide(status: 'approved' | 'rejected') {
    setError(null)
    // A guest typed but not yet added still counts: what you see is what gets invited.
    const guests = a.type === 'meeting' && status === 'approved' ? addGuest() : attendees
    start(async () => {
      const edits =
        status === 'rejected'
          ? { note: note.trim() || undefined }
          : a.type === 'reply'
            ? { draft }
            : a.type === 'meeting'
              ? { attendees: guests, start: startTime, end: endTime }
              : undefined
      const err = await decideApprovalAction(a.id, status, edits)
      if (err) setError(err)
    })
  }

  return (
    <article className={`${panel} min-w-0 ${isFlagged ? 'border-l-4 border-l-red-500 dark:border-l-red-400' : ''} ${!open ? 'opacity-70' : ''}`}>
      <div className="flex items-start gap-3">
        <span className={`mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg ${isFlagged ? iconTile.danger : iconTile.info}`}>
          <Icon aria-hidden="true" className="size-4" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <Pill tone={isFlagged ? 'danger' : 'info'}>{a.type}</Pill>
            <Pill tone={statusTone[a.status]}>{a.status}</Pill>
            {a.edited && <Pill tone="accent">edited by you</Pill>}
          </div>
          <h3 className="mt-2 text-[14px] font-medium leading-5 wrap-anywhere text-teal-900 dark:text-zinc-100">{a.summary}</h3>

          {a.status === 'approving' && (
            <p role="status" className="mt-2 text-[13px] text-amber-700 dark:text-amber-300">
              This is being sent or booked, or was interrupted. Check Gmail or Calendar before doing anything: it will not be sent again.
            </p>
          )}
          {a.type === 'review' && a.status === 'pending' && (
            <p className="mt-2 text-[13px] text-[#655e57] dark:text-zinc-400">
              The assistant could not handle this email. Nothing was drafted or sent. Read it below, deal with it in Gmail, then mark it as handled.
            </p>
          )}
          {a.decisionNote && <p className="mt-2 text-[13px] text-[#655e57] dark:text-zinc-400">Your reason: {a.decisionNote}</p>}

          {a.from && (
            <details className="group mt-3 min-w-0 rounded-lg wrap-anywhere border border-[#ece5d6] px-3 py-2 text-[13px] dark:border-zinc-800">
              <summary className="cursor-pointer select-none text-stone-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 dark:text-zinc-400">
                Original email from <span className="font-medium text-teal-900 dark:text-zinc-200">{a.from}</span>
                {a.receivedAt ? ` · ${a.receivedAt}` : ''}
              </summary>
              <div className="mt-2">
                <NoteBox label={a.subject || '(no subject)'}>{a.body || '(empty)'}</NoteBox>
              </div>
            </details>
          )}

          {a.type === 'meeting' && (
            <div className="mt-3 space-y-2">
              <p className="text-[13px] text-stone-600 dark:text-zinc-400">
                <span className="font-medium text-teal-900 dark:text-zinc-200">{a.meetingDate ?? `In ${a.day} days`}</span>
                {!open && a.start && a.end ? ` · ${formatTime(a.start)} to ${formatTime(a.end)}` : ''}
              </p>
              {open && (
                <div className="flex flex-wrap items-end gap-3">
                  <label className="block font-mono text-[11px] font-medium uppercase tracking-[0.1em] text-[#655e57] dark:text-zinc-500">
                    Start
                    <input type="time" value={startTime} onChange={(e) => setStartTime(e.target.value)} className={`${field} mt-1 w-auto`} />
                  </label>
                  <label className="block font-mono text-[11px] font-medium uppercase tracking-[0.1em] text-[#655e57] dark:text-zinc-500">
                    End
                    <input type="time" value={endTime} onChange={(e) => setEndTime(e.target.value)} className={`${field} mt-1 w-auto`} />
                  </label>
                </div>
              )}
              <div>
                <span className="mb-1 block font-mono text-[11px] font-medium uppercase tracking-[0.1em] text-[#655e57] dark:text-zinc-500">
                  Invite (they get an email when you approve)
                </span>
                <ul className="flex flex-wrap gap-1.5">
                  {attendees.length === 0 && <li className="text-[13px] text-[#655e57]">No guests, just your calendar.</li>}
                  {attendees.map((g) => (
                    <li key={g} className="inline-flex items-center gap-1 rounded-md bg-[#efe8d9] py-0.5 pl-2 pr-1 text-[12px] text-stone-700 dark:bg-zinc-800 dark:text-zinc-300">
                      {g}
                      {open && (
                        <button
                          type="button"
                          aria-label={`Remove ${g}`}
                          onClick={() => setAttendees(attendees.filter((x) => x !== g))}
                          className="grid size-6 place-items-center rounded hover:bg-[#e6dcc8] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 dark:hover:bg-zinc-700"
                        >
                          <X aria-hidden="true" className="size-3" />
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
                {open && (
                  <div className="mt-2 flex gap-2">
                    <input
                      value={newGuest}
                      onChange={(e) => setNewGuest(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault()
                          addGuest()
                        }
                      }}
                      placeholder="Add a guest email"
                      aria-label="Add a guest email"
                      className={field}
                    />
                    <button type="button" onClick={addGuest} className={linkButtonClass('secondary')}>
                      Add
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {a.type === 'reply' &&
            (open ? (
              <label className="mt-3 block space-y-1.5 font-mono text-[12px] font-medium uppercase tracking-[0.1em] text-[#655e57] dark:text-zinc-500">
                Reply (edit before sending)
                <textarea
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  rows={5}
                  className={`${field} text-teal-900 font-sans normal-case tracking-normal dark:text-zinc-100`}
                />
              </label>
            ) : (
              a.draft && (
                <div className="mt-3">
                  <NoteBox label={a.status === 'approved' ? 'Sent' : 'Draft'}>{a.draft}</NoteBox>
                </div>
              )
            ))}

          {open && (
            <div className="mt-4 space-y-3">
              {rejecting && (
                <label className="block space-y-1.5 text-[13px] font-medium text-teal-900 dark:text-zinc-200">
                  Why? {a.type === 'reply' || a.type === 'meeting' ? '(the assistant will try again with your reason)' : '(optional)'}
                  <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2} maxLength={500} className={field} autoFocus />
                </label>
              )}
              <div className="flex flex-wrap gap-2">
                {!rejecting && (
                  <button type="button" disabled={pending} onClick={() => decide('approved')} className={linkButtonClass('success')}>
                    {pending
                      ? 'Working…'
                      : a.type === 'reply'
                        ? 'Approve and send'
                        : a.type === 'meeting'
                          ? 'Approve and invite'
                          : a.type === 'review'
                            ? 'Mark as handled'
                            : 'Sign off'}
                  </button>
                )}
                {rejecting ? (
                  <>
                    <button type="button" disabled={pending} onClick={() => decide('rejected')} className={linkButtonClass('primary')}>
                      {pending ? 'Working…' : 'Confirm reject'}
                    </button>
                    <button type="button" disabled={pending} onClick={() => setRejecting(false)} className={linkButtonClass('secondary')}>
                      Back
                    </button>
                  </>
                ) : (
                  <button type="button" disabled={pending} onClick={() => setRejecting(true)} className={linkButtonClass('secondary')}>
                    Reject
                  </button>
                )}
              </div>
              {error && (
                <p role="alert" className="max-w-xl text-xs text-red-600 dark:text-red-400">
                  {error}
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </article>
  )
}
