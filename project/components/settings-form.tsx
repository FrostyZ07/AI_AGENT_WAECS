'use client'

import { useState } from 'react'
import { Clock3, Filter, Link2 } from 'lucide-react'
import { disconnectGoogleAction, saveSettingsAction } from '@/app/actions'
import { linkButtonClass } from '@/components/action-button'
import { Panel, Pill, SectionHeading } from '@/components/dashboard'
import type { Settings, State } from '@/lib/api'

const input =
  'w-full rounded-lg border border-[#e4dac6] bg-[#fcfaf5] px-3 py-2 text-[14px] outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 dark:border-zinc-700 dark:bg-zinc-900 dark:focus:border-indigo-400'
const label = 'block space-y-1.5 text-[13px] font-medium text-teal-900 dark:text-zinc-200'
const hint = 'block text-[12px] font-normal text-[#655e57] dark:text-zinc-400'
const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] // index = API value (0 = Monday)

export default function SettingsForm({
  initial,
  google,
  connectUrl,
  notice,
}: {
  initial: Settings
  google: State['google']
  connectUrl: string
  notice?: string
}) {
  const [start, setStart] = useState(initial.workingHours.start)
  const [end, setEnd] = useState(initial.workingHours.end)
  const [keywords, setKeywords] = useState(initial.sensitiveKeywords.join(', '))
  const [templates, setTemplates] = useState(initial.replyTemplates.join('\n'))
  const [timezone, setTimezone] = useState(initial.timezone)
  const [briefTime, setBriefTime] = useState(initial.briefTime)
  const [pollMinutes, setPollMinutes] = useState(initial.pollMinutes)
  const [reminderMinutes, setReminderMinutes] = useState(initial.reminderMinutes)
  const [domains, setDomains] = useState(initial.attendeeAllowDomains.join(', '))
  const [alerts, setAlerts] = useState(initial.escalationAlerts)
  const [workingDays, setWorkingDays] = useState<number[]>(initial.workingDays ?? [0, 1, 2, 3, 4])
  const [minNotice, setMinNotice] = useState(initial.minNoticeMinutes ?? 120)
  const toggleDay = (d: number) =>
    setWorkingDays((cur) => (cur.includes(d) ? cur.filter((x) => x !== d) : [...cur, d].sort((a, b) => a - b)))
  const [status, setStatus] = useState<{ ok: boolean; text: string } | null>(null)
  const [saving, setSaving] = useState(false)
  const [disconnecting, setDisconnecting] = useState(false)

  const lines = (s: string, sep: RegExp) => s.split(sep).map((x) => x.trim()).filter(Boolean)

  return (
    <form
      className="max-w-2xl space-y-5"
      onSubmit={async (e) => {
        e.preventDefault()
        setSaving(true)
        const err = await saveSettingsAction({
          workingHours: { start, end },
          sensitiveKeywords: lines(keywords, /,/),
          replyTemplates: lines(templates, /\n/),
          timezone: timezone.trim(),
          briefTime,
          pollMinutes: Number(pollMinutes) || 10,
          attendeeAllowDomains: lines(domains, /[,\s]+/),
          reminderMinutes: Number(reminderMinutes) || 0,
          escalationAlerts: alerts,
          workingDays,
          minNoticeMinutes: Number.isFinite(minNotice) ? minNotice : 120,
        })
        setSaving(false)
        setStatus(err ? { ok: false, text: err } : { ok: true, text: 'Saved. The agent uses these rules on its next run.' })
      }}
      onChange={() => setStatus(null)}
    >
      <Panel aria-labelledby="google-heading">
        <div className="flex items-center justify-between gap-3">
          <SectionHeading icon={Link2} title="Google account" id="google-heading" />
          {google.connected ? <Pill tone="success">Connected</Pill> : <Pill tone="warning">Not connected</Pill>}
        </div>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <p className="text-[14px] text-[#655e57] dark:text-zinc-400">
            {google.connected ? (
              <>
                Signed in as <span className="font-medium text-teal-900 dark:text-zinc-100">{google.email}</span>
              </>
            ) : (
              'Connect Google to read mail and manage your calendar.'
            )}
          </p>
          <div className="flex items-center gap-2">
            <a href={connectUrl} className={linkButtonClass(google.connected ? 'secondary' : 'primary')}>
              {google.connected ? 'Reconnect' : 'Connect Google'}
            </a>
            {google.connected && (
              <button
                type="button"
                disabled={disconnecting}
                className={linkButtonClass('secondary')}
                onClick={async () => {
                  if (!window.confirm('Disconnect Google? The assistant will stop reading mail and managing your calendar until you reconnect.')) return
                  setDisconnecting(true)
                  const err = await disconnectGoogleAction()
                  setDisconnecting(false)
                  setStatus(err ? { ok: false, text: err } : { ok: true, text: 'Google disconnected.' })
                }}
              >
                {disconnecting ? 'Disconnecting…' : 'Disconnect'}
              </button>
            )}
          </div>
        </div>
        <p className="mt-3 text-[12px] text-[#655e57] dark:text-zinc-400">
          Meeting prep reads (never changes) your Google Drive. If you connected before Drive access was added, click Reconnect once and approve it.
        </p>
        {notice && <p className="mt-3 text-[14px] text-stone-700 dark:text-zinc-300">{notice}</p>}
      </Panel>

      <Panel aria-labelledby="time-heading">
        <SectionHeading icon={Clock3} title="Working time" id="time-heading" />
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <label className={label}>
            Working hours start
            <input type="time" value={start} onChange={(e) => setStart(e.target.value)} className={input} />
          </label>
          <label className={label}>
            Working hours end
            <input type="time" value={end} onChange={(e) => setEnd(e.target.value)} className={input} />
          </label>
          <label className={`${label} sm:col-span-2`}>
            Time zone (IANA name)
            <input value={timezone} onChange={(e) => setTimezone(e.target.value)} className={input} />
          </label>
          <label className={label}>
            Daily brief email at
            <input type="time" value={briefTime} onChange={(e) => setBriefTime(e.target.value)} className={input} />
          </label>
          <label className={label}>
            Check inbox every (minutes)
            <input type="number" min={5} max={240} value={pollMinutes} onChange={(e) => setPollMinutes(Number(e.target.value))} className={input} />
          </label>
          <label className={label}>
            Meeting reminder (minutes before)
            <input type="number" min={0} max={1440} value={reminderMinutes} onChange={(e) => setReminderMinutes(Number(e.target.value))} className={input} />
          </label>
          <label className={label}>
            Minimum notice (minutes)
            <span className={hint}>The assistant never proposes a meeting sooner than this.</span>
            <input type="number" min={0} max={1440} value={minNotice} onChange={(e) => setMinNotice(Number(e.target.value))} className={input} />
          </label>
          <fieldset className="space-y-1.5 sm:col-span-2">
            <legend className="text-[13px] font-medium text-teal-900 dark:text-zinc-200">Working days</legend>
            <span className={hint}>The assistant only proposes meetings on these days. You can still pick any time on the approval card.</span>
            <div className="flex flex-wrap gap-2 pt-1">
              {DAYS.map((name, d) => {
                const on = workingDays.includes(d)
                return (
                  <button
                    key={name}
                    type="button"
                    aria-pressed={on}
                    onClick={() => {
                      toggleDay(d)
                      setStatus(null)
                    }}
                    className={`rounded-lg border px-3 py-1.5 text-[13px] font-medium transition ${
                      on
                        ? 'border-teal-600 bg-teal-600 text-white dark:border-indigo-400 dark:bg-indigo-500'
                        : 'border-[#e4dac6] bg-[#fcfaf5] text-[#655e57] dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-400'
                    }`}
                  >
                    {name}
                  </button>
                )
              })}
            </div>
          </fieldset>
        </div>
      </Panel>

      <Panel aria-labelledby="mail-heading">
        <SectionHeading icon={Filter} title="Mail rules" id="mail-heading" />
        <div className="mt-4 space-y-5">
          <label className={label}>
            Sensitive keywords
            <span className={hint}>Comma separated. Mail containing these is escalated to you.</span>
            <input value={keywords} onChange={(e) => setKeywords(e.target.value)} className={input} />
          </label>
          <label className={label}>
            Reply templates
            <span className={hint}>One per line.</span>
            <textarea rows={5} value={templates} onChange={(e) => setTemplates(e.target.value)} className={input} />
          </label>
          <label className={label}>
            Allowed invite domains
            <span className={hint}>
              The assistant may only invite people on the email thread, you, or anyone at these domains (comma separated, e.g. mycompany.com). You can
              always add other guests yourself on the approval card.
            </span>
            <input value={domains} onChange={(e) => setDomains(e.target.value)} className={input} placeholder="mycompany.com" />
          </label>
          <label className="flex items-start gap-3 text-[13px] font-medium text-teal-900 dark:text-zinc-200">
            <input type="checkbox" checked={alerts} onChange={(e) => setAlerts(e.target.checked)} className="mt-0.5 size-4 accent-teal-600" />
            <span>
              Email me straight away when something needs my sign-off
              <span className={hint}>Payment, travel and sensitive mail. The alert has the sender and subject only, never the message.</span>
            </span>
          </label>
        </div>
      </Panel>

      <div className="flex flex-wrap items-center gap-3">
        <button type="submit" disabled={saving} className={linkButtonClass('primary')}>
          {saving ? 'Saving…' : 'Save changes'}
        </button>
        {status && (
          <span role="status" className={`text-[14px] ${status.ok ? 'text-teal-800 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
            {status.text}
          </span>
        )}
      </div>
    </form>
  )
}
