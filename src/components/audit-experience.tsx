"use client";

import { useState, useTransition } from "react";

import {
  auditSections,
  profileFields,
  scorePalette,
  type AuditAnswers,
  type AuditProfile,
  type AuditSection,
  type NumberQuestion,
  type Question,
  type SelectQuestion,
} from "@/lib/audit-config";
import type { AuditReport, ScoreStatus } from "@/lib/scoring";

type AuditApiResponse = {
  report?: AuditReport;
  error?: string;
};

const initialProfile: AuditProfile = {
  contactName: "",
  contactRole: "",
  companyName: "",
  sector: "",
  location: "",
  companySize: "",
  annualHiringVolume: "",
};

const initialAnswers: AuditAnswers = auditSections.reduce<AuditAnswers>((accumulator, section) => {
  for (const question of section.questions) {
    accumulator[question.id] = "";
  }
  return accumulator;
}, {});

function statusCopy(status: ScoreStatus) {
  if (status === "green") {
    return "Strong";
  }
  if (status === "amber") {
    return "Needs work";
  }
  return "Critical";
}

function sectionColours(status: ScoreStatus) {
  if (status === "green") {
    return scorePalette.green;
  }
  if (status === "amber") {
    return scorePalette.amber;
  }
  return scorePalette.red;
}

function questionValue(question: Question, answers: AuditAnswers) {
  return answers[question.id] ?? "";
}

function completionLabel(step: number) {
  return `${step + 1} of ${auditSections.length + 1}`;
}

function validateProfile(profile: AuditProfile) {
  const missing = profileFields.find((field) => !profile[field.id as keyof AuditProfile].trim());
  return missing ? `Enter ${missing.label.toLowerCase()}.` : "";
}

function validateSection(section: AuditSection, answers: AuditAnswers) {
  const missing = section.questions.find((question) => !answers[question.id]);
  return missing ? `Complete ${missing.label.toLowerCase()}.` : "";
}

function SelectField({
  question,
  value,
  onChange,
}: {
  question: SelectQuestion;
  value: string;
  onChange: (questionId: string, nextValue: string) => void;
}) {
  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <label className="text-sm font-semibold text-slate-900">{question.label}</label>
        <p className="text-sm leading-6 text-slate-500">{question.description}</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {question.options.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(question.id, option.value)}
            className={`rounded-3xl border px-4 py-4 text-left transition ${
              value === option.value
                ? "border-slate-900 bg-slate-950 text-white shadow-[0_20px_45px_rgba(15,23,42,0.16)]"
                : "border-slate-200 bg-white text-slate-900 hover:border-slate-300 hover:shadow-[0_16px_30px_rgba(15,23,42,0.06)]"
            }`}
          >
            <div className="mb-1 text-sm font-semibold">{option.label}</div>
            <div className={`text-sm leading-6 ${value === option.value ? "text-slate-200" : "text-slate-500"}`}>
              {option.description}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function NumberField({
  question,
  value,
  onChange,
}: {
  question: NumberQuestion;
  value: string;
  onChange: (questionId: string, nextValue: string) => void;
}) {
  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <label htmlFor={question.id} className="text-sm font-semibold text-slate-900">
          {question.label}
        </label>
        <p className="text-sm leading-6 text-slate-500">{question.description}</p>
      </div>
      <div className="relative">
        <input
          id={question.id}
          type="number"
          inputMode="decimal"
          min={question.min}
          max={question.max}
          step={question.step}
          value={value}
          onChange={(event) => onChange(question.id, event.target.value)}
          placeholder={question.placeholder}
          className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-4 text-base text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-slate-900"
        />
        {question.unit ? (
          <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-sm font-medium text-slate-400">
            {question.unit}
          </span>
        ) : null}
      </div>
    </div>
  );
}

function SectionQuestions({
  section,
  answers,
  onChange,
}: {
  section: AuditSection;
  answers: AuditAnswers;
  onChange: (questionId: string, nextValue: string) => void;
}) {
  return (
    <div className="space-y-8">
      {section.questions.map((question) =>
        question.type === "select" ? (
          <SelectField key={question.id} question={question} value={questionValue(question, answers)} onChange={onChange} />
        ) : (
          <NumberField key={question.id} question={question} value={questionValue(question, answers)} onChange={onChange} />
        ),
      )}
    </div>
  );
}

function ScorePill({ score, status, large = false }: { score: number; status: ScoreStatus; large?: boolean }) {
  const colours = sectionColours(status);

  return (
    <div
      className={`inline-flex items-center rounded-full font-semibold ${large ? "px-4 py-2 text-base" : "px-3 py-1 text-sm"}`}
      style={{ backgroundColor: colours.soft, color: colours.text }}
    >
      {score}/100
    </div>
  );
}

function ScoreTableRow({ title, score, status }: { title: string; score: number; status: ScoreStatus }) {
  const colours = sectionColours(status);

  return (
    <div className="rounded-[1.25rem] border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between gap-4">
        <div className="text-sm font-semibold text-slate-900">{title}</div>
        <ScorePill score={score} status={status} />
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full" style={{ width: `${score}%`, backgroundColor: colours.line }} />
      </div>
    </div>
  );
}

function SectionReportCard({ section }: { section: AuditReport["sections"][number] }) {
  const colours = sectionColours(section.status);

  return (
    <article className="rounded-[1.75rem] border border-slate-200 bg-white p-7 shadow-[0_18px_50px_rgba(15,23,42,0.05)]">
      <div className="flex flex-col gap-4 border-b border-slate-200 pb-5 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">{section.strapline}</div>
          <h3 className="text-2xl font-semibold tracking-tight text-slate-950">{section.title}</h3>
        </div>
        <div className="flex flex-col items-start gap-2 sm:items-end">
          <ScorePill score={section.score} status={section.status} large />
          <div className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: colours.text }}>
            {statusCopy(section.status)}
          </div>
        </div>
      </div>

      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        <div className="rounded-[1.25rem] bg-slate-50 p-5">
          <div className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Current State</div>
          <p className="text-sm leading-7 text-slate-700">{section.currentState}</p>
        </div>

        <div className="rounded-[1.25rem] bg-slate-50 p-5">
          <div className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Key Risks</div>
          <div className="space-y-2">
            {section.keyRisks.map((risk) => (
              <div key={risk} className="rounded-2xl bg-white px-4 py-3 text-sm leading-6 text-slate-700">
                {risk}
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-[1.25rem] bg-slate-50 p-5">
          <div className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Commercial Impact</div>
          <p className="text-sm leading-7 text-slate-700">{section.commercialImpact}</p>
        </div>

        <div className="rounded-[1.25rem] bg-slate-50 p-5">
          <div className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Actions</div>
          <div className="space-y-2">
            {section.actions.map((action) => (
              <div key={action} className="rounded-2xl bg-white px-4 py-3 text-sm leading-6 text-slate-700">
                {action}
              </div>
            ))}
          </div>
        </div>
      </div>
    </article>
  );
}

function ResultsView({
  report,
  onDownload,
  downloading,
}: {
  report: AuditReport;
  onDownload: () => void;
  downloading: boolean;
}) {
  const overallColours = sectionColours(report.overallStatus);
  const strongestArea = report.strongestAreas[0];
  const weakestArea = report.topIssues[0];

  return (
    <div className="space-y-8">
      <section className="rounded-[2.25rem] border border-slate-200 bg-white p-8 shadow-[0_32px_90px_rgba(15,23,42,0.08)] md:p-10">
        <div className="flex flex-col gap-8 xl:flex-row xl:items-end xl:justify-between">
          <div className="space-y-5">
            <div className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
              Recruitment audit summary
            </div>
            <div>
              <h2 className="max-w-4xl text-4xl font-semibold tracking-[-0.04em] text-slate-950 sm:text-5xl">
                {report.profile.companyName} recruitment audit
              </h2>
              <p className="mt-4 max-w-4xl text-lg leading-8 text-slate-600">{report.executiveSummary}</p>
            </div>
          </div>
          <div className="rounded-[2rem] border border-slate-200 bg-slate-50 px-8 py-7">
            <div className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Overall score</div>
            <div className="mt-3 text-7xl font-semibold tracking-[-0.06em]" style={{ color: overallColours.text }}>
              {report.overallScore}
            </div>
            <div className="mt-3 inline-flex rounded-full px-4 py-2 text-sm font-semibold" style={{ backgroundColor: overallColours.soft, color: overallColours.text }}>
              {statusCopy(report.overallStatus)}
            </div>
          </div>
        </div>

        <div className="mt-10 h-3 overflow-hidden rounded-full bg-slate-100">
          <div className="h-full rounded-full transition-all" style={{ width: `${report.overallScore}%`, backgroundColor: overallColours.line }} />
        </div>
        <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600">{report.scoreMeaning}</p>

        <div className="mt-8 grid gap-4 md:grid-cols-3">
          <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-6">
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Strongest area</div>
            <div className="mt-3 text-lg font-semibold tracking-tight text-slate-950">{strongestArea.title}</div>
            <div className="mt-2 text-sm leading-6 text-slate-600">{strongestArea.score}/100 and operating with the most control.</div>
          </div>
          <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-6">
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Weakest area</div>
            <div className="mt-3 text-lg font-semibold tracking-tight text-slate-950">{weakestArea.title}</div>
            <div className="mt-2 text-sm leading-6 text-slate-600">{weakestArea.score}/100 and the first area that needs tighter operating discipline.</div>
          </div>
          <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-6">
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Audit scope</div>
            <div className="mt-3 text-lg font-semibold tracking-tight text-slate-950">{report.sections.length} sections assessed</div>
            <div className="mt-2 text-sm leading-6 text-slate-600">
              Coverage includes attraction, screening, interview control, conversion quality, cost visibility and manager alignment.
            </div>
          </div>
        </div>

        <div className="mt-8 grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="rounded-[1.75rem] border border-slate-200 bg-white p-7">
            <div className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-500">Key findings</div>
            <div className="mt-5 space-y-4">
              {report.topIssues.map((issue) => {
                return (
                  <div key={issue.id} className="rounded-[1.25rem] border border-slate-200 bg-slate-50 p-5">
                    <div className="flex items-center justify-between gap-4">
                      <h3 className="text-lg font-semibold text-slate-950">{issue.title}</h3>
                      <ScorePill score={issue.score} status={issue.status} />
                    </div>
                    <p className="mt-3 text-sm leading-7 text-slate-600">{issue.currentState}</p>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="space-y-5">
            <div className="rounded-[1.75rem] border border-slate-200 bg-slate-950 p-7 text-white">
              <div className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-300">Priority actions</div>
              <div className="mt-5 space-y-4">
                {report.priorityActions.map((action, index) => (
                  <div key={action} className="rounded-[1.25rem] border border-white/10 bg-white/5 p-4">
                    <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-300">Action {index + 1}</div>
                    <p className="mt-2 text-sm leading-6 text-slate-100">{action}</p>
                  </div>
                ))}
              </div>
              <button
                type="button"
                onClick={onDownload}
                disabled={downloading}
                className="mt-6 inline-flex items-center rounded-full bg-white px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {downloading ? "Preparing PDF..." : "Download PDF report"}
              </button>
            </div>

            <div className="rounded-[1.75rem] border border-slate-200 bg-white p-7">
              <div className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-500">Priority matrix</div>
              <div className="mt-5 grid gap-4 sm:grid-cols-2">
                <div className="rounded-[1.25rem] bg-red-50 p-4">
                  <div className="text-xs font-semibold uppercase tracking-[0.18em] text-red-700">Immediate attention</div>
                  <div className="mt-3 space-y-2">
                    {report.topIssues.slice(0, 2).map((issue) => (
                      <div key={issue.id} className="rounded-2xl bg-white px-4 py-3 text-sm font-medium text-slate-800">
                        {issue.title}
                      </div>
                    ))}
                  </div>
                </div>
                <div className="rounded-[1.25rem] bg-amber-50 p-4">
                  <div className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">Tighten next</div>
                  <div className="mt-3 space-y-2">
                    {report.topIssues.slice(2, 3).map((issue) => (
                      <div key={issue.id} className="rounded-2xl bg-white px-4 py-3 text-sm font-medium text-slate-800">
                        {issue.title}
                      </div>
                    ))}
                    {report.strongestAreas.slice(2, 3).map((issue) => (
                      <div key={issue.id} className="rounded-2xl bg-white px-4 py-3 text-sm font-medium text-slate-800">
                        {issue.title}
                      </div>
                    ))}
                  </div>
                </div>
                <div className="rounded-[1.25rem] bg-slate-50 p-4">
                  <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Watch closely</div>
                  <div className="mt-3 space-y-2">
                    {report.sections
                      .filter((section) => section.score > 70 && section.score < 85)
                      .slice(0, 2)
                      .map((section) => (
                        <div key={section.id} className="rounded-2xl bg-white px-4 py-3 text-sm font-medium text-slate-800">
                          {section.title}
                        </div>
                      ))}
                  </div>
                </div>
                <div className="rounded-[1.25rem] bg-green-50 p-4">
                  <div className="text-xs font-semibold uppercase tracking-[0.18em] text-green-700">Maintain</div>
                  <div className="mt-3 space-y-2">
                    {report.strongestAreas.slice(0, 2).map((area) => (
                      <div key={area.id} className="rounded-2xl bg-white px-4 py-3 text-sm font-medium text-slate-800">
                        {area.title}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-5">
        <div className="rounded-[1.75rem] border border-slate-200 bg-white p-7 shadow-[0_18px_50px_rgba(15,23,42,0.05)]">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-400">Section score overview</div>
              <h3 className="mt-3 text-3xl font-semibold tracking-[-0.03em] text-slate-950">Performance by recruitment area</h3>
            </div>
            <p className="max-w-2xl text-sm leading-7 text-slate-600">
              Each score reflects the current operating position for that part of the process. Lower-scoring sections should be addressed first where they are slowing hiring or weakening conversion.
            </p>
          </div>
          <div className="mt-6 grid gap-3 lg:grid-cols-2">
            {report.sections.map((section) => (
              <ScoreTableRow key={section.id} title={section.title} score={section.score} status={section.status} />
            ))}
          </div>
        </div>

        <div className="grid gap-5">
          {report.sections.map((section) => (
            <SectionReportCard key={section.id} section={section} />
          ))}
        </div>
      </section>

      <section className="rounded-[1.75rem] border border-slate-200 bg-white p-8 shadow-[0_16px_44px_rgba(15,23,42,0.06)]">
        <div className="max-w-4xl">
          <div className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-400">Recommended next step</div>
          <p className="mt-4 text-lg leading-8 text-slate-700">{report.recommendedNextStep}</p>
        </div>
      </section>
    </div>
  );
}

export function AuditExperience() {
  const [profile, setProfile] = useState<AuditProfile>(initialProfile);
  const [answers, setAnswers] = useState<AuditAnswers>(initialAnswers);
  const [step, setStep] = useState(0);
  const [error, setError] = useState("");
  const [report, setReport] = useState<AuditReport | null>(null);
  const [isPending, startTransition] = useTransition();
  const [isDownloading, setIsDownloading] = useState(false);

  const totalSteps = auditSections.length + 1;
  const currentSection = step === 0 ? null : auditSections[step - 1];
  const progress = Math.round(((step + 1) / totalSteps) * 100);

  const updateProfile = (fieldId: keyof AuditProfile, value: string) => {
    setProfile((current) => ({ ...current, [fieldId]: value }));
  };

  const updateAnswer = (questionId: string, value: string) => {
    setAnswers((current) => ({ ...current, [questionId]: value }));
  };

  const nextStep = () => {
    const validationMessage = step === 0 ? validateProfile(profile) : validateSection(currentSection!, answers);
    if (validationMessage) {
      setError(validationMessage);
      return;
    }
    setError("");
    setStep((current) => Math.min(current + 1, totalSteps - 1));
  };

  const previousStep = () => {
    setError("");
    setStep((current) => Math.max(current - 1, 0));
  };

  const generateReport = () => {
    const validationMessage = validateSection(currentSection!, answers);
    if (validationMessage) {
      setError(validationMessage);
      return;
    }

    setError("");
    startTransition(async () => {
      const response = await fetch("/api/audit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile, answers }),
      });

      const payload = (await response.json()) as AuditApiResponse;

      if (!response.ok || !payload.report) {
        setError(payload.error ?? "Unable to generate the audit report.");
        return;
      }

      setReport(payload.report);
    });
  };

  const downloadReport = async () => {
    setIsDownloading(true);
    setError("");

    try {
      const response = await fetch("/api/pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile, answers }),
      });

      if (!response.ok) {
        const payload = (await response.json()) as AuditApiResponse;
        throw new Error(payload.error ?? "Unable to prepare the PDF report.");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${profile.companyName || "recruitment_audit"}_recruitment_audit.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "Unable to prepare the PDF report.");
    } finally {
      setIsDownloading(false);
    }
  };

  if (report) {
    return <ResultsView report={report} onDownload={downloadReport} downloading={isDownloading} />;
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
      <section className="rounded-[2.25rem] border border-slate-200 bg-white p-8 shadow-[0_32px_90px_rgba(15,23,42,0.08)] md:p-10">
        <div className="mb-8 flex flex-col gap-5 border-b border-slate-200 pb-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div className="space-y-3">
              <div className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
                Step {completionLabel(step)}
              </div>
              <div>
                <h2 className="text-4xl font-semibold tracking-[-0.04em] text-slate-950 sm:text-5xl">
                  {step === 0 ? "Company profile" : currentSection?.title}
                </h2>
                <p className="mt-4 max-w-3xl text-lg leading-8 text-slate-600">
                  {step === 0
                    ? "Set the report context first. This information is used in the final audit and PDF output."
                    : currentSection?.summary}
                </p>
              </div>
            </div>
            <div className="min-w-[180px]">
              <div className="mb-2 flex items-center justify-between text-sm text-slate-500">
                <span>Progress</span>
                <span>{progress}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                <div className="h-full rounded-full bg-slate-950 transition-all" style={{ width: `${progress}%` }} />
              </div>
            </div>
          </div>
        </div>

        {step === 0 ? (
          <div className="grid gap-5 sm:grid-cols-2">
            {profileFields.map((field) => (
              <div key={field.id} className={field.id === "companyName" ? "sm:col-span-2" : ""}>
                <label htmlFor={field.id} className="mb-2 block text-sm font-semibold text-slate-900">
                  {field.label}
                </label>
                <input
                  id={field.id}
                  type={field.type ?? "text"}
                  value={profile[field.id as keyof AuditProfile]}
                  onChange={(event) => updateProfile(field.id as keyof AuditProfile, event.target.value)}
                  placeholder={field.placeholder}
                  className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-4 text-base text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-slate-900"
                />
              </div>
            ))}
          </div>
        ) : (
          <SectionQuestions section={currentSection!} answers={answers} onChange={updateAnswer} />
        )}

        {error ? (
          <div className="mt-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">{error}</div>
        ) : null}

        <div className="mt-8 flex flex-col gap-3 border-t border-slate-200 pt-6 sm:flex-row sm:items-center sm:justify-between">
          <button
            type="button"
            onClick={previousStep}
            disabled={step === 0 || isPending}
            className="inline-flex items-center justify-center rounded-full border border-slate-200 px-5 py-3 text-sm font-semibold text-slate-600 transition hover:border-slate-300 hover:text-slate-950 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Back
          </button>
          <button
            type="button"
            onClick={step === totalSteps - 1 ? generateReport : nextStep}
            disabled={isPending}
            className="inline-flex items-center justify-center rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isPending ? "Generating report..." : step === totalSteps - 1 ? "Generate report" : "Continue"}
          </button>
        </div>
      </section>

      <aside className="space-y-6 xl:sticky xl:top-8 xl:self-start">
        <section className="rounded-[2rem] border border-slate-200 bg-slate-950 p-6 text-white shadow-[0_28px_80px_rgba(15,23,42,0.18)]">
          <div className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-300">What you receive</div>
          <h3 className="mt-4 text-2xl font-semibold tracking-tight">A full recruitment audit and PDF report</h3>
          <div className="mt-6 space-y-4 text-sm leading-6 text-slate-300">
            <p>Each of the {auditSections.length} sections is scored out of 100 using hiring inputs tied to speed, conversion, process control and candidate quality.</p>
            <p>The report flags the weakest points, explains business impact and sets out practical actions.</p>
            <p>The PDF is formatted as a client-ready audit document, not a raw export.</p>
          </div>
        </section>

        <section className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-[0_16px_44px_rgba(15,23,42,0.06)]">
          <div className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Audit scope</div>
          <div className="mt-4 space-y-3">
            {auditSections.map((section, index) => (
              <div key={section.id} className="flex items-start gap-3 rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-white text-xs font-semibold text-slate-500">
                  {index + 1}
                </div>
                <div>
                  <div className="text-sm font-semibold text-slate-900">{section.title}</div>
                  <div className="mt-1 text-sm leading-6 text-slate-500">{section.strapline}</div>
                </div>
              </div>
            ))}
          </div>
        </section>
      </aside>
    </div>
  );
}
