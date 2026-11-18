"use client";

import { useState } from "react";
import { saveSettingsAction } from "@/app/actions";
import type { Settings, State } from "@/lib/api";

export default function SettingsForm({
  initial,
  google,
  connectUrl,
  notice,
}: {
  initial: Settings;
  google: State["google"];
  connectUrl: string;
  notice?: string;
}) {
  const [start, setStart] = useState(initial.workingHours.start);
  const [end, setEnd] = useState(initial.workingHours.end);
  const [keywords, setKeywords] = useState(initial.sensitiveKeywords.join(", "));
  const [templates, setTemplates] = useState(initial.replyTemplates.join("\n"));
  const [timezone, setTimezone] = useState(initial.timezone);
  const [briefTime, setBriefTime] = useState(initial.briefTime);
  const [pollMinutes, setPollMinutes] = useState(initial.pollMinutes);
  const [status, setStatus] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const field = "w-full rounded border bg-transparent p-2 text-sm";
  const lines = (s: string, sep: RegExp) => s.split(sep).map((x) => x.trim()).filter(Boolean);

  return (
    <form
      className="max-w-xl space-y-4"
      onSubmit={async (e) => {
        e.preventDefault();
        setSaving(true);
        const err = await saveSettingsAction({
          workingHours: { start, end },
          sensitiveKeywords: lines(keywords, /,/),
          replyTemplates: lines(templates, /\n/),
          timezone: timezone.trim(),
          briefTime,
          pollMinutes: Math.max(1, Number(pollMinutes) || 10),
        });
        setSaving(false);
        setStatus(err ?? "Saved. The agent uses these rules on its next run.");
      }}
      onChange={() => setStatus(null)}
    >
      <h2 className="text-xl font-semibold">Rules &amp; Settings</h2>

      <div className="rounded border p-3 text-sm">
        {google.connected ? (
          <>
            Google: connected as <b>{google.email}</b> (
            <a className="underline" href={connectUrl}>
              reconnect
            </a>
            )
          </>
        ) : (
          <>
            Google is not connected.{" "}
            <a className="underline" href={connectUrl}>
              Connect Google
            </a>
          </>
        )}
        {notice && <div className="mt-1">{notice}</div>}
      </div>

      <label className="block text-sm font-medium">
        Working hours
        <div className="mt-1 flex gap-2">
          <input type="time" value={start} onChange={(e) => setStart(e.target.value)} className={field} />
          <input type="time" value={end} onChange={(e) => setEnd(e.target.value)} className={field} />
        </div>
      </label>

      <label className="block text-sm font-medium">
        Time zone (IANA name)
        <input value={timezone} onChange={(e) => setTimezone(e.target.value)} className={`mt-1 ${field}`} />
      </label>

      <div className="flex gap-2">
        <label className="block flex-1 text-sm font-medium">
          Daily brief email at
          <input type="time" value={briefTime} onChange={(e) => setBriefTime(e.target.value)} className={`mt-1 ${field}`} />
        </label>
        <label className="block flex-1 text-sm font-medium">
          Check inbox every (minutes)
          <input
            type="number"
            min={1}
            value={pollMinutes}
            onChange={(e) => setPollMinutes(Number(e.target.value))}
            className={`mt-1 ${field}`}
          />
        </label>
      </div>

      <label className="block text-sm font-medium">
        Sensitive keywords (comma separated)
        <input value={keywords} onChange={(e) => setKeywords(e.target.value)} className={`mt-1 ${field}`} />
      </label>

      <label className="block text-sm font-medium">
        Reply templates (one per line)
        <textarea rows={5} value={templates} onChange={(e) => setTemplates(e.target.value)} className={`mt-1 ${field}`} />
      </label>

      <button type="submit" disabled={saving} className="rounded bg-foreground px-4 py-2 text-sm text-background disabled:opacity-50">
        {saving ? "Saving..." : "Save"}
      </button>
      {status && <span className="ml-3 text-sm">{status}</span>}
    </form>
  );
}
