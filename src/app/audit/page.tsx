import { AuditExperience } from "@/components/audit-experience";

export default function AuditPage() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(15,23,42,0.08),_transparent_26%),linear-gradient(180deg,_#ffffff_0%,_#f8fafc_100%)] text-slate-950">
      <div className="mx-auto max-w-7xl px-6 py-8 sm:px-8 lg:px-10">
        <header className="mb-10 grid gap-6 border-b border-slate-200 pb-8 lg:grid-cols-[1fr_auto] lg:items-end">
          <div className="space-y-4">
            <div className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">Bradford & Marsh Consulting</div>
            <div className="space-y-3">
              <h1 className="max-w-4xl text-4xl font-semibold tracking-[-0.04em] text-slate-950 sm:text-5xl">
                Recruitment process audit
              </h1>
              <p className="max-w-3xl text-lg leading-8 text-slate-600">
                Complete the audit to score the recruitment process, identify weak points, and generate a client-ready PDF report.
              </p>
            </div>
          </div>
          <div className="rounded-[1.5rem] border border-slate-200 bg-white px-5 py-4 text-sm leading-6 text-slate-500 shadow-[0_16px_44px_rgba(15,23,42,0.05)]">
            One section per step. No gating. No interruptions. Full report at the end.
          </div>
        </header>

        <AuditExperience />
      </div>
    </main>
  );
}
