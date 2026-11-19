import { Suspense } from "react";
import SettingsForm from "@/components/SettingsForm";
import { ErrorNotice, Loading, PageHeader } from "@/components/ui";
import { BASE, getState } from "@/lib/api";

type Query = Promise<{ connected?: string; google_error?: string }>;

export default function SettingsPage({ searchParams }: { searchParams: Query }) {
  return (
    <Suspense fallback={<Loading />}>
      <Settings searchParams={searchParams} />
    </Suspense>
  );
}

async function Settings({ searchParams }: { searchParams: Query }) {
  const [{ data, error }, q] = await Promise.all([getState(), searchParams]);
  if (!data) return <ErrorNotice>{error}</ErrorNotice>;
  const notice = q.google_error ? `Google connection failed: ${q.google_error}` : q.connected ? "Google connected." : undefined;
  return (
    <>
      <PageHeader title="Rules & Settings" description="These rules shape how the agent triages mail and schedules meetings." />
      <SettingsForm initial={data.settings} google={data.google} connectUrl={`${BASE}/oauth/google/start`} notice={notice} />
    </>
  );
}
