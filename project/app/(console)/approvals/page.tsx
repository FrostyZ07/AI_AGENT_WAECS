import ApprovalCard from '@/components/approval-card'
import { EmptyState, ErrorNotice, PageHeader } from '@/components/dashboard'
import { getState } from '@/lib/api'

export const metadata = { title: 'Approvals' }

export default async function ApprovalsPage() {
  const { data, error } = await getState()
  if (!data) return <ErrorNotice>{error}</ErrorNotice>

  // Pending first (and interrupted "approving" items next, so they are not missed), then the rest in original order.
  const rank = (s: string) => (s === 'pending' ? 0 : s === 'approving' ? 1 : 2)
  const approvals = [...data.approvals].sort((a, b) => rank(a.status) - rank(b.status))
  const pending = approvals.filter((a) => a.status === 'pending').length

  return (
    <>
      <PageHeader
        eyebrow="Approval inbox"
        title="Approvals"
        description={
          pending > 0
            ? `${pending} item${pending === 1 ? '' : 's'} waiting for your sign-off. Nothing is sent without it.`
            : 'Nothing waiting for you. Nothing is sent without your sign-off.'
        }
      />

      <div className="max-w-3xl space-y-4">
        {approvals.length === 0 && <EmptyState message='Nothing yet. Run "Process inbox" on the Calendar & Requests page.' />}
        {approvals.map((a) => (
          // key includes the status so the card's local edit state resets once it is decided
          <ApprovalCard key={`${a.id}-${a.status}`} a={a} account={data.google.email} />
        ))}
      </div>
    </>
  )
}
