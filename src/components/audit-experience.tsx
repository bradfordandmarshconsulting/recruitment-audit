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
import type { AuditReport, ScoreStatus, SectionReport } from "@/lib/scoring";

type AuditApiResponse = {
  report?: AuditReport;
  error?: string;
};

const BRAND_NAVY = "#1f2a40";
const BRAND_GOLD = "#b5935a";

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

function MatrixCard({
  title,
  items,
  tone,
}: {
  title: string;
  items: string[];
  tone: "red" | "amber" | "green" | "slate";
}) {
  const toneClasses =
    tone === "red"
      ? "bg-red-50 text-red-800"
      : tone === "amber"
        ? "bg-amber-50 text-amber-800"
        : tone === "green"
          ? "bg-green-50 text-green-800"
          : "bg-slate-50 text-slate-700";

  return (
    <div className={`rounded-[1.25rem] p-4 ${toneClasses}`}>
      <div className="text-xs font-semibold uppercase tracking-[0.18em]">{title}</div>
      <div className="mt-3 space-y-2">
        {items.map((item) => (
          <div key={item} className="rounded-2xl bg-white px-4 py-3 text-sm font-medium text-slate-800">
            {item}
          </div>
        ))}
      </div>
    </div>
  );
}

function ScoreSummaryTable({ rows }: { rows: AuditReport["scoreSummary"] }) {
  return (
    <div className="overflow-hidden rounded-[1.5rem] border border-slate-200 bg-white">
      <div className="grid grid-cols-[1fr_120px] bg-slate-950 px-4 py-3 text-xs font-semibold uppercase tracking-[0.18em] text-white">
        <div>Area</div>
        <div className="text-right">Score</div>
      </div>
      {rows.map((row, index) => {
        const colours = sectionColours(row.status);
        return (
          <div
            key={row.title}
            className={`grid grid-cols-[1fr_120px] items-center px-4 py-3 text-sm ${
              index % 2 === 1 ? "bg-slate-50" : "bg-white"
            }`}
          >
            <div className="pr-4 font-medium text-slate-800">{row.title}</div>
            <div className="text-right font-semibold" style={{ color: colours.text }}>
              {row.score}/100
            </div>
          </div>
        );
      })}
    </div>
  );
}

function MethodologyTable({ rows }: { rows: AuditReport["scoringMethodology"] }) {
  return (
    <div className="overflow-hidden rounded-[1.5rem] border border-slate-200 bg-white">
      <div className="grid grid-cols-[140px_1fr_1.3fr] bg-slate-950 px-4 py-3 text-xs font-semibold uppercase tracking-[0.18em] text-white">
        <div>Band</div>
        <div>Interpretation</div>
        <div>Typical implication</div>
      </div>
      {rows.map((row, index) => (
        <div
          key={row.band}
          className={`grid grid-cols-[140px_1fr_1.3fr] gap-4 px-4 py-3 text-sm ${
            index % 2 === 1 ? "bg-slate-50" : "bg-white"
          }`}
        >
          <div className="font-semibold text-slate-900">{row.band}</div>
          <div className="text-slate-700">{row.interpretation}</div>
          <div className="text-slate-700">{row.implication}</div>
        </div>
      ))}
    </div>
  );
}

function BenchmarkTable({ rows }: { rows: AuditReport["benchmarkSnapshot"] }) {
  return (
    <div className="overflow-hidden rounded-[1.5rem] border border-slate-200 bg-white">
      <div className="grid grid-cols-[1.1fr_120px_120px_1.2fr] bg-slate-950 px-4 py-3 text-xs font-semibold uppercase tracking-[0.18em] text-white">
        <div>Metric</div>
        <div>Client</div>
        <div>Target</div>
        <div>Comment</div>
      </div>
      {rows.map((row, index) => {
        const colours = sectionColours(row.status);
        return (
          <div
            key={row.metric}
            className={`grid grid-cols-[1.1fr_120px_120px_1.2fr] gap-4 px-4 py-3 text-sm ${
              index % 2 === 1 ? "bg-slate-50" : "bg-white"
            }`}
          >
            <div className="font-semibold text-slate-900">{row.metric}</div>
            <div style={{ color: colours.text }} className="font-semibold">
              {row.client}
            </div>
            <div className="text-slate-700">{row.target}</div>
            <div className="text-slate-700">{row.comment}</div>
          </div>
        );
      })}
    </div>
  );
}

function ScoreBars({ sections }: { sections: SectionReport[] }) {
  return (
    <div className="rounded-[1.5rem] border border-slate-200 bg-white p-6">
      <div className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-400">Section score profile</div>
      <div className="mt-5 space-y-4">
        {sections.map((section) => {
          const colours = sectionColours(section.status);
          return (
            <div key={section.id}>
              <div className="mb-2 flex items-center justify-between gap-4 text-sm">
                <div className="font-medium text-slate-800">{section.title}</div>
                <div className="font-semibold text-slate-800">{section.score}/100</div>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                <div className="h-full rounded-full" style={{ width: `${section.score}%`, backgroundColor: colours.line }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function DistributionChart({ sections }: { sections: SectionReport[] }) {
  const distribution = [
    {
      label: "Green sections",
      value: sections.filter((section) => section.status === "green").length,
      status: "green" as ScoreStatus,
    },
    {
      label: "Amber sections",
      value: sections.filter((section) => section.status === "amber").length,
      status: "amber" as ScoreStatus,
    },
    {
      label: "Red sections",
      value: sections.filter((section) => section.status === "red").length,
      status: "red" as ScoreStatus,
    },
  ];

  return (
    <div className="rounded-[1.5rem] border border-slate-200 bg-white p-6">
      <div className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-400">Score distribution</div>
      <div className="mt-5 space-y-4">
        {distribution.map((item) => {
          const colours = sectionColours(item.status);
          return (
            <div key={item.label}>
              <div className="mb-2 flex items-center justify-between gap-4 text-sm">
                <div className="font-medium text-slate-800">{item.label}</div>
                <div className="font-semibold text-slate-800">
                  {item.value} of {sections.length}
                </div>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${(item.value / sections.length) * 100}%`, backgroundColor: colours.line }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function FindingsCard({ section }: { section: SectionReport }) {
  const colours = sectionColours(section.status);

  return (
    <article className="rounded-[1.75rem] border border-slate-200 bg-white p-7 shadow-[0_18px_50px_rgba(15,23,42,0.05)]">
      <div className="flex flex-col gap-4 border-b border-slate-200 pb-5 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">{section.strapline}</div>
          <h3 className="text-2xl font-semibold tracking-tight text-slate-950">{section.title}</h3>
          <p className="text-sm font-semibold leading-6" style={{ color: BRAND_NAVY }}>
            {section.headlineDiagnosis}
          </p>
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
          <div className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Immediate Actions</div>
          <div className="space-y-2">
            {section.immediateActions.map((action) => (
              <div key={action} className="rounded-2xl bg-white px-4 py-3 text-sm leading-6 text-slate-700">
                {action}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-5 rounded-[1.25rem] border border-slate-200 px-5 py-4">
        <div className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Structural Improvements</div>
        <div className="space-y-2">
          {section.structuralImprovements.map((item) => (
            <div key={item} className="rounded-2xl bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-700">
              {item}
            </div>
          ))}
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
  const watchAreas = report.sections.filter((section) => section.score > 70 && section.score < 85).slice(0, 2).map((section) => section.title);

  return (
    <div className="space-y-8">
      <section className="overflow-hidden rounded-[2.25rem] border border-[#d9d4cb] bg-white shadow-[0_32px_90px_rgba(15,23,42,0.08)]">
        <div className="border-b border-[#d9d4cb] bg-[linear-gradient(135deg,#1f2a40_0%,#26344d_100%)] px-8 py-8 text-white md:px-10">
          <div className="inline-flex rounded-full border border-white/15 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-200">
            Bradford &amp; Marsh Consulting
          </div>
          <div className="mt-6 grid gap-8 xl:grid-cols-[1.15fr_0.85fr] xl:items-end">
            <div>
              <div className="text-sm uppercase tracking-[0.22em] text-[#d8c29b]">Recruitment Operating Model Audit</div>
              <h2 className="mt-3 max-w-4xl text-4xl font-semibold tracking-[-0.04em] sm:text-5xl">
                {report.profile.companyName}
              </h2>
              <p className="mt-4 max-w-4xl text-lg leading-8 text-slate-200">{report.executiveSummary}</p>
            </div>
            <div className="rounded-[2rem] border border-white/10 bg-white/8 px-8 py-7 backdrop-blur">
              <div className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-300">Overall score</div>
              <div className="mt-3 text-7xl font-semibold tracking-[-0.06em]" style={{ color: overallColours.line }}>
                {report.overallScore}
              </div>
              <div className="mt-3 inline-flex rounded-full px-4 py-2 text-sm font-semibold" style={{ backgroundColor: overallColours.soft, color: overallColours.text }}>
                {report.ratingBand}
              </div>
            </div>
          </div>
          <div className="mt-8 h-3 overflow-hidden rounded-full bg-white/10">
            <div className="h-full rounded-full" style={{ width: `${report.overallScore}%`, backgroundColor: overallColours.line }} />
          </div>
        </div>

        <div className="px-8 py-8 md:px-10">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-[1.5rem] border border-slate-200 bg-[#f7f5f1] p-6">
              <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Strongest area</div>
              <div className="mt-3 text-lg font-semibold tracking-tight text-slate-950">{report.strongestArea.title}</div>
              <div className="mt-3">
                <ScorePill score={report.strongestArea.score} status={report.strongestArea.status} />
              </div>
            </div>
            <div className="rounded-[1.5rem] border border-slate-200 bg-[#f7f5f1] p-6">
              <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Weakest area</div>
              <div className="mt-3 text-lg font-semibold tracking-tight text-slate-950">{report.weakestArea.title}</div>
              <div className="mt-3">
                <ScorePill score={report.weakestArea.score} status={report.weakestArea.status} />
              </div>
            </div>
            <div className="rounded-[1.5rem] border border-slate-200 bg-[#f7f5f1] p-6">
              <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Primary diagnosis</div>
              <p className="mt-3 text-sm leading-7 text-slate-700">{report.primaryDiagnosis}</p>
            </div>
          </div>
        </div>
      </section>

      <section className="rounded-[1.75rem] border border-slate-200 bg-white p-8 shadow-[0_18px_50px_rgba(15,23,42,0.05)]">
        <div className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-400">Introductory letter</div>
        <div className="mt-5 max-w-4xl space-y-4 text-sm leading-7 text-slate-700">
          <p>{report.letter.salutation}</p>
          {report.letter.paragraphs.map((paragraph) => (
            <p key={paragraph}>{paragraph}</p>
          ))}
          <div className="pt-3">
            <p className="font-semibold text-slate-950">{report.letter.signatureName}</p>
            <p className="text-slate-500">{report.letter.signatureTitle}</p>
          </div>
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-5">
          <article className="rounded-[1.75rem] border border-slate-200 bg-white p-7 shadow-[0_18px_50px_rgba(15,23,42,0.05)]">
            <div className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-400">Score summary</div>
            <h3 className="mt-3 text-3xl font-semibold tracking-[-0.03em] text-slate-950">Performance by recruitment area</h3>
            <p className="mt-3 text-sm leading-7 text-slate-600">
              Each score reflects the current operating position and the level of control visible in that part of the process.
            </p>
            <div className="mt-6">
              <ScoreSummaryTable rows={report.scoreSummary} />
            </div>
          </article>

          <article className="rounded-[1.75rem] border border-slate-200 bg-white p-7 shadow-[0_18px_50px_rgba(15,23,42,0.05)]">
            <div className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-400">Scoring methodology</div>
            <p className="mt-3 text-sm leading-7 text-slate-600">
              The audit uses the submitted process inputs and current-state hiring data. Higher scores indicate stronger control, faster delivery and lower operating risk.
            </p>
            <div className="mt-6">
              <MethodologyTable rows={report.scoringMethodology} />
            </div>
          </article>
        </div>

        <div className="space-y-5">
          <article className="rounded-[1.75rem] border border-slate-200 bg-white p-7 shadow-[0_18px_50px_rgba(15,23,42,0.05)]">
            <div className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-400">Benchmark snapshot</div>
            <p className="mt-3 text-sm leading-7 text-slate-600">
              This summary shows how the current operating position compares with the target control band expected in a well-run hiring model.
            </p>
            <div className="mt-6">
              <BenchmarkTable rows={report.benchmarkSnapshot} />
            </div>
          </article>

          <article className="rounded-[1.75rem] border border-slate-200 bg-white p-7 shadow-[0_18px_50px_rgba(15,23,42,0.05)]">
            <div className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-400">Key findings</div>
            <div className="mt-5 space-y-4">
              {report.topIssues.slice(0, 3).map((issue) => (
                <div key={issue.id} className="rounded-[1.25rem] border border-slate-200 bg-[#f7f5f1] p-5">
                  <div className="flex items-center justify-between gap-4">
                    <h3 className="text-lg font-semibold text-slate-950">{issue.title}</h3>
                    <ScorePill score={issue.score} status={issue.status} />
                  </div>
                  <p className="mt-3 text-sm leading-7 text-slate-600">{issue.headlineDiagnosis}</p>
                </div>
              ))}
            </div>
          </article>
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1fr_1fr]">
        <article className="rounded-[1.75rem] border border-slate-200 bg-white p-7 shadow-[0_18px_50px_rgba(15,23,42,0.05)]">
          <div className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-400">Priority matrix</div>
          <p className="mt-3 text-sm leading-7 text-slate-600">
            These are the areas most likely to affect hiring pace, candidate quality and commercial control if left unchanged.
          </p>
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <MatrixCard title="Immediate attention" tone="red" items={report.priorityMatrix.slice(0, 2).map((row) => row.priorityArea)} />
            <MatrixCard title="Tighten next" tone="amber" items={report.priorityMatrix.slice(2, 4).map((row) => row.priorityArea)} />
            <MatrixCard title="Watch closely" tone="slate" items={watchAreas.length ? watchAreas : ["No additional watch items"]} />
            <MatrixCard title="Maintain" tone="green" items={report.strongestAreas.slice(0, 2).map((area) => area.title)} />
          </div>
        </article>

        <article className="rounded-[1.75rem] border border-slate-200 bg-white p-7 shadow-[0_18px_50px_rgba(15,23,42,0.05)]">
          <div className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-400">Charts and visual analysis</div>
          <div className="mt-6 space-y-5">
            <DistributionChart sections={report.sections} />
            <div className="rounded-[1.5rem] border border-slate-200 bg-[#f7f5f1] p-6">
              <div className="space-y-3">
                {report.visualAnalysisNotes.map((note) => (
                  <p key={note} className="text-sm leading-7 text-slate-700">
                    {note}
                  </p>
                ))}
              </div>
            </div>
          </div>
        </article>
      </section>

      <section className="rounded-[1.75rem] border border-slate-200 bg-white p-7 shadow-[0_18px_50px_rgba(15,23,42,0.05)]">
        <div className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-400">Section score profile</div>
        <div className="mt-6">
          <ScoreBars sections={report.sections} />
        </div>
      </section>

      <section className="space-y-5">
        <div className="rounded-[1.75rem] border border-slate-200 bg-white p-7 shadow-[0_18px_50px_rgba(15,23,42,0.05)]">
          <div className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-400">Detailed findings</div>
          <h3 className="mt-3 text-3xl font-semibold tracking-[-0.03em] text-slate-950">Section-by-section analysis</h3>
        </div>
        <div className="grid gap-5">
          {report.sections.map((section) => (
            <FindingsCard key={section.id} section={section} />
          ))}
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1fr_1fr]">
        <article className="rounded-[1.75rem] border border-slate-200 bg-white p-7 shadow-[0_18px_50px_rgba(15,23,42,0.05)]">
          <div className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-400">Priorities and roadmap</div>
          <div className="mt-6 grid gap-5">
            <div>
              <h3 className="text-2xl font-semibold tracking-tight text-slate-950">Top 5 strengths</h3>
              <div className="mt-4 space-y-3">
                {report.topStrengths.map((item) => (
                  <div key={item} className="rounded-2xl border border-slate-200 bg-[#f7f5f1] px-4 py-4 text-sm leading-6 text-slate-700">
                    {item}
                  </div>
                ))}
              </div>
            </div>
            <div>
              <h3 className="text-2xl font-semibold tracking-tight text-slate-950">Top 5 problems</h3>
              <div className="mt-4 space-y-3">
                {report.topProblems.map((item) => (
                  <div key={item} className="rounded-2xl border border-slate-200 bg-[#f7f5f1] px-4 py-4 text-sm leading-6 text-slate-700">
                    {item}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </article>

        <article className="rounded-[1.75rem] border border-slate-200 bg-white p-7 shadow-[0_18px_50px_rgba(15,23,42,0.05)]">
          <div className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-400">Action roadmap</div>
          <div className="mt-6 space-y-5">
            {[
              { title: "30 day plan", items: report.day30Plan },
              { title: "60 day plan", items: report.day60Plan },
              { title: "90 day plan", items: report.day90Plan },
            ].map((phase) => (
              <div key={phase.title} className="rounded-[1.5rem] border border-slate-200 bg-[#f7f5f1] p-5">
                <div className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">{phase.title}</div>
                <div className="mt-4 space-y-2">
                  {phase.items.map((item) => (
                    <div key={item} className="rounded-2xl bg-white px-4 py-3 text-sm leading-6 text-slate-700">
                      {item}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="rounded-[1.75rem] border border-[#d9d4cb] bg-[linear-gradient(180deg,#fbf8f2_0%,#ffffff_100%)] p-8 shadow-[0_18px_50px_rgba(15,23,42,0.05)]">
        <div className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-400">Final verdict</div>
        <p className="mt-4 max-w-4xl text-lg leading-8 text-slate-700">{report.finalVerdict}</p>
        <div className="mt-6 rounded-[1.5rem] border border-[#d9d4cb] bg-white px-6 py-5">
          <div className="text-sm font-semibold uppercase tracking-[0.18em]" style={{ color: BRAND_NAVY }}>
            Recommended next step
          </div>
          <p className="mt-3 text-base leading-8 text-slate-700">{report.recommendedNextStep}</p>
          <button
            type="button"
            onClick={onDownload}
            disabled={downloading}
            className="mt-6 inline-flex items-center rounded-full px-5 py-3 text-sm font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-60"
            style={{ backgroundColor: BRAND_NAVY }}
          >
            {downloading ? "Preparing PDF..." : "Download PDF report"}
          </button>
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
      <section className="rounded-[2.25rem] border border-[#d9d4cb] bg-white p-8 shadow-[0_32px_90px_rgba(15,23,42,0.08)] md:p-10">
        <div className="mb-8 border-b border-[#d9d4cb] pb-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div className="space-y-3">
              <div className="inline-flex rounded-full border border-slate-200 bg-[#f7f5f1] px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
                Step {completionLabel(step)}
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.28em]" style={{ color: BRAND_GOLD }}>
                  Bradford &amp; Marsh Consulting
                </div>
                <h2 className="mt-3 text-4xl font-semibold tracking-[-0.04em] text-slate-950 sm:text-5xl">
                  {step === 0 ? "Company profile" : currentSection?.title}
                </h2>
                <p className="mt-4 max-w-3xl text-lg leading-8 text-slate-600">
                  {step === 0
                    ? "Set the report context first. This information is used throughout the final Bradford & Marsh audit and PDF output."
                    : currentSection?.summary}
                </p>
              </div>
            </div>
            <div className="min-w-[180px] rounded-[1.5rem] border border-slate-200 bg-[#f7f5f1] px-5 py-4">
              <div className="mb-2 flex items-center justify-between text-sm text-slate-500">
                <span>Progress</span>
                <span>{progress}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-white">
                <div className="h-full rounded-full transition-all" style={{ width: `${progress}%`, backgroundColor: BRAND_NAVY }} />
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
            className="inline-flex items-center justify-center rounded-full px-5 py-3 text-sm font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-60"
            style={{ backgroundColor: BRAND_NAVY }}
          >
            {isPending ? "Generating report..." : step === totalSteps - 1 ? "Generate report" : "Continue"}
          </button>
        </div>
      </section>

      <aside className="space-y-6 xl:sticky xl:top-8 xl:self-start">
        <section className="rounded-[2rem] border border-[#d9d4cb] bg-[linear-gradient(180deg,#1f2a40_0%,#26344d_100%)] p-6 text-white shadow-[0_28px_80px_rgba(15,23,42,0.18)]">
          <div className="text-xs font-semibold uppercase tracking-[0.24em] text-[#d8c29b]">What you receive</div>
          <h3 className="mt-4 text-2xl font-semibold tracking-tight">A Bradford &amp; Marsh client report</h3>
          <div className="mt-6 space-y-4 text-sm leading-6 text-slate-200">
            <p>The report follows the Bradford &amp; Marsh consulting structure from executive overview through to roadmap and final verdict.</p>
            <p>Each of the {auditSections.length} sections is scored out of 100 using the existing recruitment audit model.</p>
            <p>The final PDF is formatted as a branded leadership document rather than a raw export.</p>
          </div>
        </section>

        <section className="rounded-[2rem] border border-[#d9d4cb] bg-white p-6 shadow-[0_16px_44px_rgba(15,23,42,0.06)]">
          <div className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Audit scope</div>
          <div className="mt-4 space-y-3">
            {auditSections.map((section, index) => (
              <div key={section.id} className="flex items-start gap-3 rounded-2xl border border-slate-100 bg-[#f7f5f1] px-4 py-3">
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
