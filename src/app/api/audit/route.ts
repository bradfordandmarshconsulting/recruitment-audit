import { NextResponse } from "next/server";

import { buildAuditReport } from "@/lib/scoring";
import { parseSubmission } from "@/lib/validation";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const submission = parseSubmission(body);
    const report = buildAuditReport(submission);

    return NextResponse.json({ report });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unable to generate the audit report.";
    return NextResponse.json({ error: message }, { status: 400 });
  }
}
