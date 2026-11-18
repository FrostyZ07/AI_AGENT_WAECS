// Phase 1 seed + the shared TS types. From Phase 2 the live data comes from the Python agent API (agent-api/), see src/lib/api.ts.
// Single source of truth for Phase 1. Later phases swap this for Supabase / Google / M365.
// `day` is an offset from today (0 = today) so the app always looks live and renders identically on server and client.

export type Triage = "routine" | "sensitive";

export type Request = {
  id: string;
  from: string;
  subject: string;
  receivedAt: string; // HH:MM today
  kind: "mail" | "meeting";
  triage: Triage;
  body?: string; // Phase 2: set by the Python agent API
  processed?: boolean; // Phase 2
};

export type Meeting = {
  id: string;
  title: string;
  day: number;
  start: string;
  end: string;
  attendees: string[];
  prepNote?: string;
  allDay?: boolean; // Phase 3: set for all-day Google Calendar events
};

export type ApprovalType = "reply" | "meeting" | "payment" | "travel" | "sensitive";
export type ApprovalStatus = "pending" | "approved" | "rejected";

export type Approval = {
  id: string;
  type: ApprovalType;
  summary: string;
  draft?: string;
  status: ApprovalStatus;
  requestId?: string | null; // Phase 2: set by the Python agent API
  title?: string; // meeting approvals only
  day?: number;
  start?: string;
  end?: string;
};

export type FollowUp = {
  id: string;
  task: string;
  owner: string;
  due: string;
  done: boolean;
};

export const requests: Request[] = [
  { id: "r1", from: "priya@acme.com", subject: "Can we meet Thursday to discuss the Q4 plan?", receivedAt: "08:12", kind: "meeting", triage: "routine" },
  { id: "r2", from: "legal@partnerco.com", subject: "Contract amendment - confidential", receivedAt: "08:40", kind: "mail", triage: "sensitive" },
  { id: "r3", from: "events@conf.io", subject: "Speaker slot confirmation", receivedAt: "09:05", kind: "mail", triage: "routine" },
  { id: "r4", from: "accounts@vendor.com", subject: "Invoice #4821 - payment due Friday", receivedAt: "09:30", kind: "mail", triage: "sensitive" },
  { id: "r5", from: "sam@startup.xyz", subject: "Intro call request", receivedAt: "10:02", kind: "meeting", triage: "routine" },
  { id: "r6", from: "travel@airline.com", subject: "Flight options Mumbai - Delhi", receivedAt: "10:20", kind: "mail", triage: "routine" },
];

export const meetings: Meeting[] = [
  { id: "m1", title: "Team standup", day: 0, start: "09:30", end: "09:45", attendees: ["Product team"] },
  { id: "m2", title: "Investor catch-up", day: 0, start: "11:00", end: "12:00", attendees: ["Rahul Mehta"], prepNote: "Share latest MRR and runway numbers." },
  { id: "m3", title: "Hiring sync", day: 0, start: "15:00", end: "15:30", attendees: ["HR lead"], prepNote: "Review the two shortlisted candidates." },
  { id: "m4", title: "Q4 planning", day: 1, start: "10:00", end: "11:30", attendees: ["Priya", "Leadership team"], prepNote: "Draft OKRs ready in the drive." },
  { id: "m5", title: "Board prep", day: 2, start: "14:00", end: "15:00", attendees: ["CFO"] },
  { id: "m6", title: "Customer demo", day: 3, start: "16:00", end: "16:45", attendees: ["Acme team"], prepNote: "Use the staging demo account." },
];

export const initialApprovals: Approval[] = [
  { id: "a1", type: "reply", summary: "Reply to Speaker slot confirmation", draft: "Hi, thanks for the invite. Confirming the 25-minute slot on Day 2. Please send the AV requirements.", status: "pending" },
  { id: "a2", type: "meeting", summary: "Book Thursday 11:00 with Priya (Acme)", draft: "Invite: Q4 plan discussion, 30 min, video call.", status: "pending" },
  { id: "a3", type: "payment", summary: "Pay invoice #4821 to Vendor Co - Rs 48,000", status: "pending" },
  { id: "a4", type: "travel", summary: "Book flight Mumbai - Delhi, Mon 07:30, Rs 6,200", status: "pending" },
  { id: "a5", type: "sensitive", summary: "Contract amendment from PartnerCo legal - needs your review", status: "pending" },
];

export const followUps: FollowUp[] = [
  { id: "f1", task: "Send deck to Rahul", owner: "Assistant", due: "Today", done: false },
  { id: "f2", task: "Confirm venue for offsite", owner: "Assistant", due: "Tomorrow", done: false },
  { id: "f3", task: "Reply to Sam's intro request", owner: "Principal", due: "Today", done: false },
  { id: "f4", task: "Collect expense receipts", owner: "Assistant", due: "Friday", done: true },
];

export const initialSettings = {
  workingHours: { start: "09:00", end: "18:00" },
  sensitiveKeywords: ["confidential", "contract", "legal", "salary", "invoice", "payment"],
  replyTemplates: [
    "Thanks for reaching out. I'll check the calendar and get back to you shortly.",
    "Thank you for the update. Noted, and we'll follow up by end of week.",
  ],
};

export function dayLabel(day: number): string {
  if (day === 0) return "Today";
  if (day === 1) return "Tomorrow";
  return `In ${day} days`;
}
