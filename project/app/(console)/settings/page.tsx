import SettingsForm from '@/components/settings-form'
import { ErrorNotice, PageHeader } from '@/components/dashboard'
import { getState } from '@/lib/api'

export const metadata = { title: 'Settings' }

export default async function SettingsPage({
  searchParams,
}: {
  searchParams: Promise<{ connected?: string; google_error?: string }>
}) {
  const [{ data, error }, q] = await Promise.all([getState(), searchParams])
  if (!data) return <ErrorNotice>{error}</ErrorNotice>
  const notice = q.google_error ? `Google connection failed: ${q.google_error}` : q.connected ? 'Google connected.' : undefined

  return (
    <>
      <PageHeader eyebrow="Preferences" title="Settings" description="These rules shape how the agent triages mail and schedules meetings." />
      <SettingsForm initial={data.settings} google={data.google} connectUrl="/connect/google" notice={notice} />
    </>
  )
}
