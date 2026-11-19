"use client";

import { useState } from "react";
import { saveSettingsAction } from "@/app/actions";
import { Badge, Card, btnPrimary, btnSecondary, input } from "@/components/ui";
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
  const [status, setStatus] = useState<{ ok: boolean; text: string } | null>(null);
  const [saving, setSaving] = useState(false);

  const lines = (s: string, sep: RegExp) => s.split(sep).map((x) => x.trim()).filter(Boolean);

  return (
    <form
      className="max-w-2xl space-y-6"
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
        setStatus(err ? { ok: false, text: err } : { ok: true, text: "Saved. The agent uses these rules on its next run." });
      }}
      onChange={() => setStatus(null)}
    >
      <Card
        title="Google account"
        aside={google.connected ? <Badge tone="success">Connected</Badge> : <Badge tone="warning">Not connected</Badge>}
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-muted">
            {google.connected ? (
              <>
                Signed in as <span className="font-medium text-foreground">{google.email}</span>
              </>
            ) : (
              "Connect Google to read mail and manage your calendar."
            )}
          </p>
          <a href={connectUrl} className={google.connected ? btnSecondary : btnPrimary}>
            {google.connected ? "Reconnect" : "Connect Google"}
          </a>
        </div>
        {notice && <p className="mt-3 text-sm">{notice}</p>}
      </Card>

      <Card title="Working time">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block space-y-1.5 text-sm font-medium">
            Working hours start
            <input type="time" value={start} onChange={(e) => setStart(e.target.value)} className={input} />
          </label>
          <label className="block space-y-1.5 text-sm font-medium">
            Working hours end
            <input type="time" value={end} onChange={(e) => setEnd(e.target.value)} className={input} />
          </label>
          <label className="block space-y-1.5 text-sm font-medium sm:col-span-2">
            Time zone (IANA name)
            <input value={timezone} onChange={(e) => setTimezone(e.target.value)} className={input} />
          </label>
          <label className="block space-y-1.5 text-sm font-medium">
            Daily brief email at
            <input type="time" value={briefTime} onChange={(e) => setBriefTime(e.target.value)} className={input} />
          </label>
          <label className="block space-y-1.5 text-sm font-medium">
            Check inbox every (minutes)
            <input
              type="number"
              min={1}
              value={pollMinutes}
              onChange={(e) => setPollMinutes(Number(e.target.value))}
              className={input}
            />
          </label>
        </div>
      </Card>

      <Card title="Mail rules">
        <div className="space-y-5">
          <label className="block space-y-1.5 text-sm font-medium">
            Sensitive keywords
            <span className="block text-xs font-normal text-muted">Comma separated. Mail containing these is escalated to you.</span>
            <input value={keywords} onChange={(e) => setKeywords(e.target.value)} className={input} />
          </label>
          <label className="block space-y-1.5 text-sm font-medium">
            Reply templates
            <span className="block text-xs font-normal text-muted">One per line.</span>
            <textarea rows={5} value={templates} onChange={(e) => setTemplates(e.target.value)} className={input} />
          </label>
        </div>
      </Card>

      <div className="flex flex-wrap items-center gap-3">
        <button type="submit" disabled={saving} className={btnPrimary}>
          {saving ? "Saving..." : "Save changes"}
        </button>
        {status && (
          <span role="status" className={`text-sm ${status.ok ? "text-green-700 dark:text-green-400" : "text-danger"}`}>
            {status.text}
          </span>
        )}
      </div>
    </form>
  );
}
