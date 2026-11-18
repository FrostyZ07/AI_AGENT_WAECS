"use server";

import { revalidatePath } from "next/cache";
import { callApi, type Settings } from "@/lib/api";

// Each action returns an error message (or null on success) so <ActionButton> can display it.
async function run(path: string, method: string, body?: unknown): Promise<string | null> {
  const { error } = await callApi(path, method, body);
  revalidatePath("/", "layout");
  return error ?? null;
}

export async function processInboxAction() {
  return run("/process-inbox", "POST");
}

export async function generateBriefAction() {
  return run("/brief", "POST");
}

export async function decideApprovalAction(id: string, status: "approved" | "rejected") {
  return run(`/approvals/${encodeURIComponent(id)}`, "POST", { status });
}

export async function saveSettingsAction(settings: Settings) {
  return run("/settings", "PUT", settings);
}
