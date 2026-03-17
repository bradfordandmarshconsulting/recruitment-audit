"use client";

import Image from "next/image";
import { useEffect, useRef, useState, useTransition } from "react";

import {
  auditSections,
  profileFields,
  scorePalette,
  type AuditAnswers,
  type AuditProfile,
  type AuditSection,
  type Question,
} from "@/lib/audit-config";
import type { AuditReport, ScoreStatus, SectionReport } from "@/lib/scoring";

type AuditApiResponse = {
  report?: AuditReport;
  error?: string;
};

const BRAND_NAVY = "#1f2a40";

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

const totalQuestionCount = auditSections.reduce((count, section) => count + section.questions.length, 0);

const profileFieldGuidance: Record<keyof AuditProfile, { title: string; description: string }> = {
  contactName: {
    title: "Who is completing this audit?",
    description: "This name is used in the report letter and client-facing cover details.",
  },
  contactRole: {
    title: "What is their job title?",
    description: "This helps position the report correctly for leadership review.",
  },
  companyName: {
    title: "Which organisation is being assessed?",
    description: "Use the client company name exactly as it should appear on the report.",
  },
  sector: {
    title: "Which sector does the business operate in?",
    description: "Sector context is used across the audit summary and benchmark commentary.",
  },
  location: {
    title: "Where is the business based?",
    description: "Use the main office location or the operating base the audit relates to.",
  },
  companySize: {
    title: "What is the approximate size of the business?",
    description: "This provides context for scale, process complexity and hiring cadence.",
  },
  annualHiringVolume: {
    title: "How many hires are typically made in a year?",
    description: "A realistic estimate is enough. This supports the operating context in the report.",
  },
};

type ExperiencePhase = "profile" | "section-intro" | "question" | "section-complete";

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

function validateProfileField(fieldId: keyof AuditProfile, profile: AuditProfile) {
  return profile[fieldId].trim() ? "" : `Enter ${profileFields.find((field) => field.id === fieldId)?.label.toLowerCase()}.`;
}

function validateQuestion(question: Question, answers: AuditAnswers) {
  return answers[question.id] ? "" : `Complete ${question.label.toLowerCase()}.`;
}

function QuestionProgress({
  sectionIndex,
  questionIndex,
  sectionQuestionCount,
  overallProgress,
  sectionProgress,
}: {
  sectionIndex: number;
  questionIndex: number;
  sectionQuestionCount: number;
  overallProgress: number;
  sectionProgress: number;
}) {
  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">Section progress</div>
          <div className="mt-2 text-sm text-slate-600">
            Section {sectionIndex + 1} of {auditSections.length}
            <span className="mx-2 text-slate-300">/</span>
            Question {questionIndex + 1} of {sectionQuestionCount}
          </div>
        </div>
        <div className="min-w-[180px] text-left sm:text-right">
          <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">Overall progress</div>
          <div className="mt-2 text-sm text-slate-600">{overallProgress}% complete</div>
        </div>
      </div>
      <div className="space-y-3">
        <div>
          <div className="mb-2 flex items-center justify-between text-xs uppercase tracking-[0.18em] text-slate-400">
            <span>Section</span>
            <span>{sectionProgress}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-100">
            <div className="h-full rounded-full transition-all duration-300" style={{ width: `${sectionProgress}%`, backgroundColor: BRAND_NAVY }} />
          </div>
        </div>
        <div>
          <div className="mb-2 flex items-center justify-between text-xs uppercase tracking-[0.18em] text-slate-400">
            <span>Overall</span>
            <span>{overallProgress}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-100">
            <div className="h-full rounded-full transition-all duration-300" style={{ width: `${overallProgress}%`, backgroundColor: "#b5935a" }} />
          </div>
        </div>
      </div>
    </div>
  );
}

function ProfileFieldScreen({
  fieldId,
  value,
  onChange,
  index,
}: {
  fieldId: keyof AuditProfile;
  value: string;
  onChange: (value: string) => void;
  index: number;
}) {
  const field = profileFields.find((item) => item.id === fieldId)!;
  const guidance = profileFieldGuidance[fieldId];

  return (
    <div className="space-y-10" style={{ animation: "diagnosticFade 280ms ease-out" }}>
      <div className="space-y-5">
        <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
          Report setup
          <span className="mx-2 text-slate-300">/</span>
          Field {index + 1} of {profileFields.length}
        </div>
        <div className="space-y-4">
          <h2 className="max-w-3xl text-4xl font-semibold tracking-[-0.04em] text-slate-950 sm:text-5xl">{guidance.title}</h2>
          <p className="max-w-2xl text-lg leading-8 text-slate-600">{guidance.description}</p>
        </div>
      </div>

      <div className="max-w-2xl space-y-4">
        <label htmlFor={field.id} className="block text-sm font-semibold uppercase tracking-[0.16em] text-slate-400">
          {field.label}
        </label>
        <input
          id={field.id}
          type={field.type ?? "text"}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={field.placeholder}
          className="w-full rounded-[1.75rem] border border-slate-200 bg-white px-6 py-5 text-2xl text-slate-950 outline-none transition placeholder:text-slate-300 focus:border-slate-400"
        />
      </div>
    </div>
  );
}

function SectionIntroScreen({
  section,
  sectionIndex,
}: {
  section: AuditSection;
  sectionIndex: number;
}) {
  return (
    <div className="space-y-10" style={{ animation: "diagnosticFade 280ms ease-out" }}>
      <div className="space-y-5">
        <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
          Section {sectionIndex + 1} of {auditSections.length}
        </div>
        <div className="space-y-4">
          <h2 className="max-w-3xl text-4xl font-semibold tracking-[-0.04em] text-slate-950 sm:text-5xl">{section.title}</h2>
          <p className="max-w-2xl text-xl leading-8 text-slate-600">{section.strapline}</p>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <div className="rounded-[1.75rem] bg-[#f7f5f1] p-7">
          <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">What is being assessed</div>
          <p className="mt-4 text-base leading-8 text-slate-700">This section assesses {section.strapline.charAt(0).toLowerCase() + section.strapline.slice(1)}.</p>
        </div>
        <div className="rounded-[1.75rem] bg-slate-950 p-7 text-white">
          <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-300">Why it matters commercially</div>
          <p className="mt-4 text-base leading-8 text-slate-200">{section.summary}</p>
        </div>
      </div>
    </div>
  );
}

function QuestionScreen({
  section,
  question,
  value,
  onSelect,
  onNumberChange,
  sectionIndex,
  questionIndex,
  overallProgress,
}: {
  section: AuditSection;
  question: Question;
  value: string;
  onSelect: (nextValue: string) => void;
  onNumberChange: (nextValue: string) => void;
  sectionIndex: number;
  questionIndex: number;
  overallProgress: number;
}) {
  const sectionProgress = Math.round((questionIndex / section.questions.length) * 100);

  return (
    <div className="space-y-10" style={{ animation: "diagnosticFade 280ms ease-out" }}>
      <QuestionProgress
        sectionIndex={sectionIndex}
        questionIndex={questionIndex}
        sectionQuestionCount={section.questions.length}
        overallProgress={overallProgress}
        sectionProgress={sectionProgress}
      />

      <div className="space-y-5">
        <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">{section.title}</div>
        <div className="space-y-4">
          <h2 className="max-w-3xl text-4xl font-semibold tracking-[-0.04em] text-slate-950 sm:text-5xl">{question.label}</h2>
          <p className="max-w-2xl text-lg leading-8 text-slate-600">{question.description}</p>
        </div>
      </div>

      {question.type === "select" ? (
        <div className="max-w-3xl space-y-4">
          {question.options.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => onSelect(option.value)}
              className={`w-full rounded-[1.75rem] px-6 py-6 text-left transition ${
                value === option.value
                  ? "bg-slate-950 text-white shadow-[0_24px_60px_rgba(15,23,42,0.18)]"
                  : "bg-[#f8f6f2] text-slate-950 hover:bg-white hover:shadow-[0_18px_45px_rgba(15,23,42,0.08)]"
              }`}
            >
              <div className="text-lg font-semibold">{option.label}</div>
              <div className={`mt-2 max-w-2xl text-base leading-7 ${value === option.value ? "text-slate-200" : "text-slate-600"}`}>
                {option.description}
              </div>
            </button>
          ))}
        </div>
      ) : (
        <div className="max-w-2xl space-y-4">
          <label htmlFor={question.id} className="block text-sm font-semibold uppercase tracking-[0.16em] text-slate-400">
            Response
          </label>
          <div className="relative">
            <input
              id={question.id}
              type="number"
              inputMode="decimal"
              min={question.min}
              max={question.max}
              step={question.step}
              value={value}
              onChange={(event) => onNumberChange(event.target.value)}
              placeholder={question.placeholder}
              className="w-full rounded-[1.75rem] border border-slate-200 bg-white px-6 py-5 pr-20 text-3xl text-slate-950 outline-none transition placeholder:text-slate-300 focus:border-slate-400"
            />
            {question.unit ? (
              <span className="pointer-events-none absolute right-6 top-1/2 -translate-y-1/2 text-lg font-medium text-slate-400">{question.unit}</span>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}

function SectionCompleteScreen({
  section,
  sectionIndex,
  overallProgress,
}: {
  section: AuditSection;
  sectionIndex: number;
  overallProgress: number;
}) {
  return (
    <div className="space-y-10" style={{ animation: "diagnosticFade 280ms ease-out" }}>
      <QuestionProgress
        sectionIndex={sectionIndex}
        questionIndex={section.questions.length - 1}
        sectionQuestionCount={section.questions.length}
        overallProgress={overallProgress}
        sectionProgress={100}
      />

      <div className="space-y-5">
        <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">Section complete</div>
        <div className="space-y-4">
          <h2 className="max-w-3xl text-4xl font-semibold tracking-[-0.04em] text-slate-950 sm:text-5xl">{section.title} complete</h2>
          <p className="max-w-2xl text-lg leading-8 text-slate-600">
            This part of the diagnostic is complete. The next section will assess the next pressure point in the recruitment process.
          </p>
        </div>
      </div>

      <div className="max-w-2xl rounded-[1.75rem] bg-[#f7f5f1] p-7">
        <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">Why this matters</div>
        <p className="mt-4 text-base leading-8 text-slate-700">{section.summary}</p>
      </div>
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
  eyebrow,
  title,
  items,
  tone,
}: {
  eyebrow: string;
  title: string;
  items: { title: string; note: string }[];
  tone: "red" | "amber" | "green";
}) {
  const toneClasses =
    tone === "red"
      ? "border-red-200 bg-red-50 text-red-800"
      : tone === "amber"
        ? "border-amber-200 bg-amber-50 text-amber-800"
        : "border-green-200 bg-green-50 text-green-800";

  return (
    <div className={`rounded-[1.5rem] border p-4 ${toneClasses}`}>
      <div className="text-[11px] font-semibold uppercase tracking-[0.18em] opacity-75">{eyebrow}</div>
      <div className="mt-2 text-sm font-semibold uppercase tracking-[0.16em]">{title}</div>
      <div className="mt-3 space-y-2">
        {items.length ? (
          items.map((item) => (
            <div key={item.title} className="rounded-2xl bg-white px-4 py-3">
              <div className="text-sm font-semibold text-slate-900">{item.title}</div>
              <div className="mt-1 text-sm leading-6 text-slate-600">{item.note}</div>
            </div>
          ))
        ) : (
          <div className="rounded-2xl bg-white px-4 py-3 text-sm leading-6 text-slate-600">
            No additional areas currently sit in this quadrant.
          </div>
        )}
      </div>
    </div>
  );
}

type MatrixQuadrant = {
  eyebrow: string;
  title: string;
  tone: "red" | "amber" | "green";
  items: { title: string; note: string }[];
};

function priorityQuadrants(report: AuditReport): MatrixQuadrant[] {
  const watchSections = report.sections
    .filter(
      (section) =>
        section.score >= 71 &&
        section.score < 85 &&
        !report.priorityMatrix.some((row) => row.priorityArea === section.title) &&
        !report.strongestAreas.slice(0, 2).some((area) => area.title === section.title),
    )
    .slice(0, 2);

  return [
    {
      eyebrow: "High impact | High urgency",
      title: "Stabilise now",
      tone: "red",
      items: report.priorityMatrix.slice(0, 2).map((row) => ({
        title: row.priorityArea,
        note: row.firstMove,
      })),
    },
    {
      eyebrow: "High impact | Lower urgency",
      title: "Tighten next",
      tone: "amber",
      items: report.priorityMatrix.slice(2, 4).map((row) => ({
        title: row.priorityArea,
        note: row.firstMove,
      })),
    },
    {
      eyebrow: "Lower impact | High visibility",
      title: "Monitor",
      tone: "amber",
      items: watchSections.map((section) => ({
        title: section.title,
        note: section.headlineDiagnosis,
      })),
    },
    {
      eyebrow: "Lower impact | Lower urgency",
      title: "Maintain",
      tone: "green",
      items: report.strongestAreas.slice(0, 2).map((section) => ({
        title: section.title,
        note: section.headlineDiagnosis,
      })),
    },
  ];
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
  const matrixQuadrants = priorityQuadrants(report);

  return (
    <div className="space-y-8">
      <section className="overflow-hidden rounded-[2.25rem] border border-[#d9d4cb] bg-white shadow-[0_32px_90px_rgba(15,23,42,0.08)]">
        <div className="border-b border-[#d9d4cb] bg-[linear-gradient(135deg,#1f2a40_0%,#26344d_100%)] px-8 py-8 text-white md:px-10">
          <div className="inline-flex rounded-[1.25rem] border border-white/10 bg-white px-5 py-3 shadow-[0_18px_40px_rgba(15,23,42,0.14)]">
            <Image src="/brand/bradford-marsh-logo.png" alt="Bradford & Marsh Consulting" width={228} height={46} priority />
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
        <div className="flex items-center justify-between gap-6 border-b border-slate-200 pb-5">
          <div className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-400">Introductory letter</div>
          <Image src="/brand/bradford-marsh-logo.png" alt="Bradford & Marsh Consulting" width={206} height={42} />
        </div>
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
            {matrixQuadrants.map((quadrant) => (
              <MatrixCard
                key={quadrant.title}
                eyebrow={quadrant.eyebrow}
                title={quadrant.title}
                tone={quadrant.tone}
                items={quadrant.items}
              />
            ))}
          </div>
          <p className="mt-4 text-sm leading-7 text-slate-500">
            Quadrants reflect the likely business impact of each gap and how quickly leadership should act.
          </p>
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
  const [phase, setPhase] = useState<ExperiencePhase>("profile");
  const [profileIndex, setProfileIndex] = useState(0);
  const [sectionIndex, setSectionIndex] = useState(0);
  const [questionIndex, setQuestionIndex] = useState(0);
  const [error, setError] = useState("");
  const [report, setReport] = useState<AuditReport | null>(null);
  const [isPending, startTransition] = useTransition();
  const [isDownloading, setIsDownloading] = useState(false);
  const autoAdvanceRef = useRef<number | null>(null);

  const currentProfileField = profileFields[profileIndex];
  const currentSection = auditSections[sectionIndex];
  const currentQuestion = phase === "question" ? currentSection.questions[questionIndex] : null;
  const answeredQuestionCount = auditSections.reduce(
    (count, section) => count + section.questions.filter((question) => answers[question.id]).length,
    0,
  );
  const overallProgress = Math.round((answeredQuestionCount / totalQuestionCount) * 100);

  const updateProfile = (fieldId: keyof AuditProfile, value: string) => {
    setProfile((current) => ({ ...current, [fieldId]: value }));
  };

  const updateAnswer = (questionId: string, value: string) => {
    setAnswers((current) => ({ ...current, [questionId]: value }));
  };

  useEffect(() => {
    return () => {
      if (autoAdvanceRef.current) {
        window.clearTimeout(autoAdvanceRef.current);
      }
    };
  }, []);

  const clearAutoAdvance = () => {
    if (autoAdvanceRef.current) {
      window.clearTimeout(autoAdvanceRef.current);
      autoAdvanceRef.current = null;
    }
  };

  const moveToNextQuestion = () => {
    setError("");
    if (questionIndex < currentSection.questions.length - 1) {
      setQuestionIndex((current) => current + 1);
      return;
    }
    setPhase("section-complete");
  };

  const advanceProfile = () => {
    const validationMessage = validateProfileField(currentProfileField.id as keyof AuditProfile, profile);
    if (validationMessage) {
      setError(validationMessage);
      return;
    }

    setError("");

    if (profileIndex < profileFields.length - 1) {
      setProfileIndex((current) => current + 1);
      return;
    }

    setProfileIndex(0);
    setSectionIndex(0);
    setQuestionIndex(0);
    setPhase("section-intro");
  };

  const continueQuestion = () => {
    if (!currentQuestion) {
      return;
    }

    const validationMessage = validateQuestion(currentQuestion, answers);
    if (validationMessage) {
      setError(validationMessage);
      return;
    }

    setError("");
    moveToNextQuestion();
  };

  const generateReport = () => {
    clearAutoAdvance();
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

  const nextStep = () => {
    clearAutoAdvance();

    if (phase === "profile") {
      advanceProfile();
      return;
    }

    if (phase === "section-intro") {
      setError("");
      setQuestionIndex(0);
      setPhase("question");
      return;
    }

    if (phase === "question") {
      continueQuestion();
      return;
    }

    if (sectionIndex < auditSections.length - 1) {
      setError("");
      setSectionIndex((current) => current + 1);
      setQuestionIndex(0);
      setPhase("section-intro");
      return;
    }

    generateReport();
  };

  const previousStep = () => {
    clearAutoAdvance();
    setError("");

    if (phase === "profile") {
      setProfileIndex((current) => Math.max(current - 1, 0));
      return;
    }

    if (phase === "section-intro") {
      if (sectionIndex === 0) {
        setPhase("profile");
        setProfileIndex(profileFields.length - 1);
        return;
      }

      const previousSectionIndex = sectionIndex - 1;
      setSectionIndex(previousSectionIndex);
      setQuestionIndex(auditSections[previousSectionIndex].questions.length - 1);
      setPhase("question");
      return;
    }

    if (phase === "question") {
      if (questionIndex > 0) {
        setQuestionIndex((current) => current - 1);
        return;
      }

      setPhase("section-intro");
      return;
    }

    setPhase("question");
    setQuestionIndex(currentSection.questions.length - 1);
  };

  const handleSelectAnswer = (questionId: string, value: string) => {
    updateAnswer(questionId, value);
    setError("");
    clearAutoAdvance();
    autoAdvanceRef.current = window.setTimeout(() => {
      moveToNextQuestion();
      autoAdvanceRef.current = null;
    }, 220);
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
    <div className="mx-auto max-w-5xl">
      <section className="rounded-[2.5rem] border border-[#d9d4cb] bg-white px-8 py-8 shadow-[0_32px_90px_rgba(15,23,42,0.08)] md:px-12 md:py-10">
        <div className="border-b border-[#ece7de] pb-8">
          <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
            <div className="space-y-5">
              <Image src="/brand/bradford-marsh-logo.png" alt="Bradford & Marsh Consulting" width={238} height={48} priority />
              <div className="space-y-3">
                <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#b5935a]">Recruitment Operating Model Audit</div>
                <p className="max-w-2xl text-base leading-7 text-slate-600">
                  A structured diagnostic of how recruitment is operating today, one decision point at a time.
                </p>
              </div>
            </div>
            <div className="rounded-[1.5rem] bg-[#f7f5f1] px-5 py-4 text-sm leading-6 text-slate-600">
              {phase === "profile"
                ? `Report setup ${profileIndex + 1} of ${profileFields.length}`
                : `Section ${sectionIndex + 1} of ${auditSections.length}`}
            </div>
          </div>
        </div>

        <div className="mx-auto max-w-3xl py-12">
          {phase === "profile" ? (
            <ProfileFieldScreen
              fieldId={currentProfileField.id as keyof AuditProfile}
              value={profile[currentProfileField.id as keyof AuditProfile]}
              onChange={(value) => updateProfile(currentProfileField.id as keyof AuditProfile, value)}
              index={profileIndex}
            />
          ) : phase === "section-intro" ? (
            <SectionIntroScreen section={currentSection} sectionIndex={sectionIndex} />
          ) : phase === "section-complete" ? (
            <SectionCompleteScreen section={currentSection} sectionIndex={sectionIndex} overallProgress={overallProgress} />
          ) : (
            <QuestionScreen
              section={currentSection}
              question={currentQuestion!}
              value={answers[currentQuestion!.id] ?? ""}
              onSelect={(value) => handleSelectAnswer(currentQuestion!.id, value)}
              onNumberChange={(value) => updateAnswer(currentQuestion!.id, value)}
              sectionIndex={sectionIndex}
              questionIndex={questionIndex}
              overallProgress={overallProgress}
            />
          )}

          {error ? (
            <div className="mt-8 rounded-[1.5rem] border border-red-200 bg-red-50 px-5 py-4 text-sm font-medium text-red-700">{error}</div>
          ) : null}
        </div>

        <div className="border-t border-[#ece7de] pt-6">
          <div className="mx-auto flex max-w-3xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <button
              type="button"
              onClick={previousStep}
              disabled={(phase === "profile" && profileIndex === 0) || isPending}
              className="inline-flex items-center justify-center rounded-full border border-slate-200 px-5 py-3 text-sm font-semibold text-slate-600 transition hover:border-slate-300 hover:text-slate-950 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Back
            </button>
            <button
              type="button"
              onClick={nextStep}
              disabled={isPending || (phase === "question" && currentQuestion?.type === "select")}
              className="inline-flex items-center justify-center rounded-full px-6 py-3 text-sm font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-60"
              style={{ backgroundColor: BRAND_NAVY }}
            >
              {isPending
                ? "Generating report..."
                : phase === "section-intro"
                  ? "Begin section"
                  : phase === "section-complete"
                    ? sectionIndex === auditSections.length - 1
                      ? "Generate report"
                      : "Continue"
                    : phase === "profile"
                      ? profileIndex === profileFields.length - 1
                        ? "Begin assessment"
                        : "Continue"
                      : currentQuestion?.type === "number"
                        ? questionIndex === currentSection.questions.length - 1
                          ? "Complete section"
                          : "Continue"
                        : "Continue"}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
