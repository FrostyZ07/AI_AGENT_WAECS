import { Suspense } from "react";
import SettingsForm from "@/components/SettingsForm";
import { BASE, getState } from "@/lib/api";

type Query = Promise<{ connected?: string; google_error?: string }>;

export default function SettingsPage({ searchParams }: { searchParams: Query }) {
  return (
    <Suspense fallback={<p className="text-sm">Loading...</p>}>
      <Settings searchParams={searchParams} />
    </Suspense>
  );
}

async function Settings({ searchParams }: { searchParams: Query }) {
  const [{ data, error }, q] = await Promise.all([getState(), searchParams]);
  if (!data) return <p className="rounded border border-red-300 p-4 text-sm text-red-800 dark:text-red-400">{error}</p>;
  const notice = q.google_error ? `Google connection failed: ${q.google_error}` : q.connected ? "Google connected." : undefined;
  return <SettingsForm initial={data.settings} google={data.google} connectUrl={`${BASE}/oauth/google/start`} notice={notice} />;
}
