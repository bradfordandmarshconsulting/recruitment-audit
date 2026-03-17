import Link from "next/link";

const valueAreas = [
  {
    title: "What is analysed",
    body: "The audit reviews 12 areas across the hiring model, including job definition, advertising, source effectiveness, application friction, screening, interviews, candidate experience, offer control, time to hire, cost visibility, conversion quality and hiring manager alignment.",
  },
  {
    title: "What you receive",
    body: "Each area is scored, diagnosed and translated into practical recommendations. The finished output is a polished PDF report suitable for internal leadership discussion.",
  },
  {
    title: "Who it is for",
    body: "This is designed for founders, hiring managers, directors and leadership teams who need a clear view of where hiring is losing pace, control or candidate quality.",
  },
];

export default function HomePage() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(31,42,64,0.08),_transparent_26%),linear-gradient(180deg,_#fbf8f2_0%,_#f3f4f6_100%)] text-slate-950">
      <div className="mx-auto max-w-7xl px-6 py-8 sm:px-8 lg:px-10">
        <header className="flex flex-col gap-6 border-b border-[#d9d4cb] pb-8 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.28em] text-[#b5935a]">Bradford & Marsh Consulting</div>
            <div className="mt-3 text-sm text-slate-500">Recruitment operating model assessment and consulting-grade report output.</div>
          </div>
          <Link
            href="/audit"
            className="inline-flex items-center justify-center rounded-full px-5 py-3 text-sm font-semibold text-white transition"
            style={{ backgroundColor: "#1f2a40" }}
          >
            Start free audit
          </Link>
        </header>

        <section className="grid gap-10 py-16 lg:grid-cols-[1.15fr_0.85fr] lg:items-end">
          <div className="space-y-8">
            <div className="inline-flex rounded-full border border-[#d9d4cb] bg-white px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-500 shadow-[0_16px_40px_rgba(15,23,42,0.04)]">
              Recruitment audit application
            </div>
            <div className="space-y-5">
              <h1 className="max-w-4xl text-5xl font-semibold tracking-[-0.04em] text-slate-950 sm:text-6xl lg:text-7xl">
                Your hiring process is leaking time, money, and candidates
              </h1>
              <p className="max-w-2xl text-lg leading-8 text-slate-600 sm:text-xl">
                This audit shows you exactly where and how to fix it.
              </p>
            </div>
            <div className="flex flex-col gap-4 sm:flex-row">
              <Link
                href="/audit"
                className="inline-flex items-center justify-center rounded-full px-6 py-4 text-base font-semibold text-white transition"
                style={{ backgroundColor: "#1f2a40" }}
              >
                Start free audit
              </Link>
              <div className="inline-flex items-center rounded-full border border-[#d9d4cb] bg-white px-5 py-4 text-sm font-medium text-slate-500">
                Multi-step audit, instant results, professional PDF report
              </div>
            </div>
          </div>

          <div className="rounded-[2rem] border border-[#d9d4cb] bg-white p-8 shadow-[0_24px_80px_rgba(15,23,42,0.08)]">
            <div className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">What the audit covers</div>
            <div className="mt-6 grid gap-4">
              {[
                "Role definition and brief quality",
                "Advertising and channel effectiveness",
                "Application friction and candidate drop-off",
                "Screening, interview and offer discipline",
                "Time to hire, cost awareness and conversion quality",
                "Hiring manager alignment and process ownership",
              ].map((item) => (
                <div key={item} className="rounded-2xl border border-slate-100 bg-[#f7f5f1] px-4 py-4 text-sm leading-6 text-slate-700">
                  {item}
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="grid gap-5 py-6 lg:grid-cols-3">
          {valueAreas.map((area) => (
            <article key={area.title} className="rounded-[1.75rem] border border-[#d9d4cb] bg-white p-8 shadow-[0_16px_44px_rgba(15,23,42,0.05)]">
              <div className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-400">{area.title}</div>
              <p className="mt-4 text-base leading-7 text-slate-600">{area.body}</p>
            </article>
          ))}
        </section>
      </div>
    </main>
  );
}
