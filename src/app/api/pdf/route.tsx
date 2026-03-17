import React from "react";
import { NextResponse } from "next/server";
import { renderToBuffer } from "@react-pdf/renderer";
import type { DocumentProps } from "@react-pdf/renderer";

import { AuditPdfDocument } from "@/lib/pdf-document";
import { buildAuditReport } from "@/lib/scoring";
import { parseSubmission } from "@/lib/validation";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const submission = parseSubmission(body);
    const report = buildAuditReport(submission);
    const document = AuditPdfDocument({ report }) as React.ReactElement<DocumentProps>;
    const buffer = await renderToBuffer(document);
    const filename = `${report.profile.companyName.replace(/[^a-z0-9]+/gi, "_")}_recruitment_audit.pdf`;

    return new NextResponse(buffer as BodyInit, {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="${filename}"`,
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unable to generate the PDF report.";
    return NextResponse.json({ error: message }, { status: 400 });
  }
}
