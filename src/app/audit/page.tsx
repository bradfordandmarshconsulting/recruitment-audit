import Image from "next/image";

import { AuditExperience } from "@/components/audit-experience";

export default function AuditPage() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(31,42,64,0.08),_transparent_26%),linear-gradient(180deg,_#fbf8f2_0%,_#f3f4f6_100%)] text-slate-950">
      <div className="mx-auto max-w-7xl px-6 py-8 sm:px-8 lg:px-10">
        <header className="mb-10 grid gap-6 border-b border-[#d9d4cb] pb-8 lg:grid-cols-[1fr_auto] lg:items-end">
          <div className="space-y-4">
            <Image src="/brand/bradford-marsh-logo.png" alt="Bradford & Marsh Consulting" width={278} height={56} priority />
            <div className="space-y-3">
              <h1 className="max-w-4xl text-4xl font-semibold tracking-[-0.04em] text-slate-950 sm:text-5xl">
                Recruitment Operating Model Audit
              </h1>
              <p className="max-w-3xl text-lg leading-8 text-slate-600">
                Complete the audit to generate a branded Bradford & Marsh recruitment report with leadership summary, section findings and roadmap.
              </p>
            </div>
          </div>
          <div className="rounded-[1.5rem] border border-[#d9d4cb] bg-white px-5 py-4 text-sm leading-6 text-slate-500 shadow-[0_16px_44px_rgba(15,23,42,0.05)]">
            One section per step. Bradford & Marsh branding from form through to final PDF.
          </div>
        </header>

        <AuditExperience />
      </div>
    </main>
  );
}
