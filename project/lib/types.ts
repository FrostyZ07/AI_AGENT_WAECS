
export type Triage = "routine" | "sensitive";

export type Request = {
  id: string;
  from: string;
  subject: string;
  receivedAt: string; // HH:MM
  receivedOn?: string; // "19 Nov"
  kind: "mail" | "meeting";
  triage: Triage;
  body?: string; // Phase 2: set by the Python agent API
  processed?: boolean; // Phase 2
  participants?: string[] | null;
  rejectNote?: string | null;
};

export type Doc = {
  id: string;
  name: string;
  url: string | null;
  modified: string; // YYYY-MM-DD
};

export type Meeting = {
  id: string;
  title: string;
  day: number;
  start: string;
  end: string;
  attendees: string[];
  attendeeEmails?: string[];
  prepNote?: string;
  prepAt?: string; // when the AI prep note was generated
  docs?: Doc[]; // Drive documents linked to the meeting
  allDay?: boolean; // Phase 3: set for all-day Google Calendar events
};

export type ApprovalType = "reply" | "meeting" | "payment" | "travel" | "sensitive";
// "approving" = the send/booking is in progress or was interrupted: never offered for approval again.
export type ApprovalStatus = "pending" | "approving" | "approved" | "rejected";

export type Approval = {
  id: string;
  type: ApprovalType;
  summary: string;
  draft?: string | null;
  status: ApprovalStatus;
  requestId?: string | null; // Phase 2: set by the Python agent API
  title?: string | null; // meeting approvals only
  day?: number | null;
  start?: string | null;
  end?: string | null;
  attendees?: string[] | null;
  meetingDate?: string | null; // YYYY-MM-DD, meeting approvals only
  googleRef?: string | null;
  edited?: boolean;
  decisionNote?: string | null;
  createdAt?: string;
  // From the original request, so the card can show who wrote what:
  from?: string | null;
  subject?: string | null;
  body?: string | null;
  receivedAt?: string | null;
};

export type FollowUp = {
  id: string;
  task: string;
  owner: string;
  due: string;
  done: boolean;
  dueDate?: string | null;
  overdue?: boolean;
};

export type Kpis = {
  days: number;
  briefOnTime: { onTime: number; total: number };
  meetings: { booked: number; clashRefusals: number };
  avgReplyMinutes: number | null;
  repliesSent: number;
  followUps: { closed: number; total: number } | null;
};

export type AuditEntry = {
  id: number;
  at: string;
  event: string;
  details: Record<string, unknown>;
};
