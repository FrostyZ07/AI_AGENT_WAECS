import { ExternalLink, FileSearch } from 'lucide-react'
import { prepMeetingAction } from '@/app/actions'
import ActionButton from '@/components/action-button'
import { NoteBox } from '@/components/dashboard'
import type { Meeting } from '@/lib/types'

// Prep note + linked Drive docs for one meeting, with a button to (re)generate them.
export default function MeetingPrep({ m }: { m: Meeting }) {
  const canPrep = !m.allDay && (m.attendeeEmails?.length ?? 0) > 0
  const docs = m.docs ?? []
  if (!m.prepNote && docs.length === 0 && !canPrep) return null
  return (
    <div className="mt-3 space-y-2">
      {m.prepNote && <NoteBox label={m.prepAt ? `Prep note · ${m.prepAt}` : 'Prep note'}>{m.prepNote}</NoteBox>}
      {docs.length > 0 && (
        <ul aria-label="Linked documents" className="flex flex-wrap gap-1.5">
          {docs.map((d) =>
            d.url ? (
              <li key={d.id}>
                <a
                  href={d.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 rounded-md bg-blue-50 px-2 py-1 text-[11px] font-medium text-blue-700 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 dark:bg-blue-400/10 dark:text-blue-300"
                >
                  {d.name}
                  <ExternalLink aria-hidden="true" className="size-3" />
                </a>
              </li>
            ) : (
              <li key={d.id} className="rounded-md bg-[#efe8d9] px-2 py-1 text-[11px] text-stone-600 dark:bg-zinc-800 dark:text-zinc-400">
                {d.name}
              </li>
            ),
          )}
        </ul>
      )}
      {canPrep && (
        <ActionButton
          action={prepMeetingAction.bind(null, m.id)}
          label={m.prepAt ? 'Refresh prep' : 'Prepare'}
          pendingLabel="Preparing…"
          icon={<FileSearch className="size-3.5" />}
          variant="secondary"
        />
      )}
    </div>
  )
}
