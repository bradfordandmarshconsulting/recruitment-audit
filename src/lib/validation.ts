import { auditSections, profileFields, type AuditAnswers, type AuditSubmission } from "@/lib/audit-config";

type UnknownRecord = Record<string, unknown>;

function cleanText(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function ensureObject(value: unknown, label: string): UnknownRecord {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`Invalid ${label}.`);
  }
  return value as UnknownRecord;
}

export function parseSubmission(input: unknown): AuditSubmission {
  const body = ensureObject(input, "request body");
  const rawProfile = ensureObject(body.profile, "profile");
  const rawAnswers = ensureObject(body.answers, "answers");

  const profile = profileFields.reduce<Record<string, string>>((accumulator, field) => {
    const value = cleanText(rawProfile[field.id]);
    if (!value) {
      throw new Error(`Missing ${field.label.toLowerCase()}.`);
    }
    accumulator[field.id] = value;
    return accumulator;
  }, {});

  const answers = auditSections.reduce<AuditAnswers>((accumulator, section) => {
    for (const question of section.questions) {
      const value = cleanText(rawAnswers[question.id]);
      if (!value) {
        throw new Error(`Missing answer for ${question.label.toLowerCase()}.`);
      }
      accumulator[question.id] = value;
    }
    return accumulator;
  }, {});

  return {
    profile: {
      contactName: profile.contactName,
      contactRole: profile.contactRole,
      companyName: profile.companyName,
      sector: profile.sector,
      location: profile.location,
      companySize: profile.companySize,
      annualHiringVolume: profile.annualHiringVolume,
    },
    answers,
  };
}
