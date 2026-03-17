import { auditSections, type AuditAnswers, type AuditSection, type AuditSubmission, getSectionById } from "@/lib/audit-config";

export type ScoreStatus = "red" | "amber" | "green";

export type SectionReport = {
  id: string;
  title: string;
  strapline: string;
  score: number;
  status: ScoreStatus;
  currentState: string;
  keyRisks: string[];
  commercialImpact: string;
  immediateActions: string[];
  diagnosis: string;
  impact: string;
  recommendations: string[];
  consultantNote: string;
  evidence: string[];
};

export type AuditReport = {
  generatedAt: string;
  profile: AuditSubmission["profile"];
  overallScore: number;
  overallStatus: ScoreStatus;
  scoreMeaning: string;
  executiveSummary: string;
  strongestAreas: SectionReport[];
  topIssues: SectionReport[];
  priorityActions: string[];
  sections: SectionReport[];
  recommendedNextStep: string;
};

function toNumber(value: string | undefined): number {
  if (!value) {
    return 0;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function clampScore(score: number): number {
  return Math.max(0, Math.min(100, Math.round(score)));
}

function band(score: number): ScoreStatus {
  if (score <= 39) {
    return "red";
  }
  if (score <= 70) {
    return "amber";
  }
  return "green";
}

function average(scores: number[]): number {
  if (!scores.length) {
    return 0;
  }
  const total = scores.reduce((sum, value) => sum + value, 0);
  return clampScore(total / scores.length);
}

function scoreSelect(value: string | undefined, section: AuditSection, questionId: string): number {
  const question = section.questions.find((item) => item.id === questionId && item.type === "select");
  if (!question || question.type !== "select") {
    return 0;
  }
  const option = question.options.find((item) => item.value === value);
  return option?.score ?? 0;
}

function inverseDaysScore(days: number, thresholds: [number, number, number, number]): number {
  const [excellent, good, fair, weak] = thresholds;
  if (days <= excellent) {
    return 100;
  }
  if (days <= good) {
    return 82;
  }
  if (days <= fair) {
    return 60;
  }
  if (days <= weak) {
    return 38;
  }
  return 18;
}

function inverseRateScore(rate: number, thresholds: [number, number, number, number]): number {
  const [excellent, good, fair, weak] = thresholds;
  if (rate <= excellent) {
    return 100;
  }
  if (rate <= good) {
    return 82;
  }
  if (rate <= fair) {
    return 58;
  }
  if (rate <= weak) {
    return 35;
  }
  return 18;
}

function positiveRateScore(rate: number, thresholds: [number, number, number, number]): number {
  const [excellent, good, fair, weak] = thresholds;
  if (rate >= excellent) {
    return 100;
  }
  if (rate >= good) {
    return 82;
  }
  if (rate >= fair) {
    return 60;
  }
  if (rate >= weak) {
    return 38;
  }
  return 18;
}

function balancedRateScore(rate: number, idealMin: number, idealMax: number, outerMin: number, outerMax: number): number {
  if (rate >= idealMin && rate <= idealMax) {
    return 100;
  }
  if (rate >= idealMin - 5 && rate <= idealMax + 5) {
    return 82;
  }
  if (rate >= outerMin && rate <= outerMax) {
    return 60;
  }
  if (rate >= outerMin - 10 && rate <= outerMax + 10) {
    return 38;
  }
  return 18;
}

function applicationStepsScore(steps: number): number {
  if (steps <= 2) {
    return 100;
  }
  if (steps <= 4) {
    return 82;
  }
  if (steps <= 6) {
    return 58;
  }
  if (steps <= 8) {
    return 35;
  }
  return 18;
}

function interviewStagesScore(stages: number): number {
  if (stages <= 2) {
    return 92;
  }
  if (stages <= 3) {
    return 100;
  }
  if (stages <= 4) {
    return 62;
  }
  if (stages <= 5) {
    return 35;
  }
  return 18;
}

function scoreBySection(sectionId: string, answers: AuditAnswers): number {
  const section = getSectionById(sectionId);
  if (!section) {
    return 0;
  }

  switch (sectionId) {
    case "job-definition":
      return average([
        scoreSelect(answers.roleBriefQuality, section, "roleBriefQuality"),
        scoreSelect(answers.successMeasuresDefined, section, "successMeasuresDefined"),
        scoreSelect(answers.briefAlignment, section, "briefAlignment"),
      ]);
    case "job-advertising":
      return average([
        scoreSelect(answers.advertSpecificity, section, "advertSpecificity"),
        scoreSelect(answers.channelFit, section, "channelFit"),
        positiveRateScore(toNumber(answers.qualifiedApplicantRate), [45, 30, 20, 10]),
      ]);
    case "source-effectiveness":
      return average([
        scoreSelect(answers.sourceMixControl, section, "sourceMixControl"),
        scoreSelect(answers.sourcePerformanceVisibility, section, "sourcePerformanceVisibility"),
        scoreSelect(answers.sourceDependency, section, "sourceDependency"),
      ]);
    case "application-process":
      return average([
        scoreSelect(answers.applicationFriction, section, "applicationFriction"),
        applicationStepsScore(toNumber(answers.applicationSteps)),
        scoreSelect(answers.mobileExperience, section, "mobileExperience"),
      ]);
    case "screening":
      return average([
        scoreSelect(answers.screeningCriteria, section, "screeningCriteria"),
        inverseDaysScore(toNumber(answers.screeningResponseHours), [24, 48, 72, 120]),
        scoreSelect(answers.cvReviewConsistency, section, "cvReviewConsistency"),
      ]);
    case "interview-process":
      return average([
        interviewStagesScore(toNumber(answers.interviewStages)),
        scoreSelect(answers.interviewScorecards, section, "interviewScorecards"),
        inverseDaysScore(toNumber(answers.interviewTurnaroundDays), [2, 4, 7, 10]),
      ]);
    case "candidate-experience":
      return average([
        scoreSelect(answers.candidateCommunication, section, "candidateCommunication"),
        inverseDaysScore(toNumber(answers.feedbackDays), [1, 2, 4, 6]),
        inverseRateScore(toNumber(answers.candidateDropOff), [8, 15, 25, 35]),
      ]);
    case "offer-stage":
      return average([
        inverseDaysScore(toNumber(answers.offerApprovalDays), [1, 2, 4, 6]),
        positiveRateScore(toNumber(answers.offerAcceptanceRate), [90, 80, 70, 60]),
        scoreSelect(answers.closingPlan, section, "closingPlan"),
      ]);
    case "time-to-hire":
      return average([
        inverseDaysScore(toNumber(answers.timeToHireDays), [30, 45, 60, 90]),
        scoreSelect(answers.pipelineReviewCadence, section, "pipelineReviewCadence"),
        scoreSelect(answers.bottlenecksVisible, section, "bottlenecksVisible"),
      ]);
    case "cost-awareness":
      return average([
        scoreSelect(answers.costPerHireVisibility, section, "costPerHireVisibility"),
        scoreSelect(answers.agencySpendControl, section, "agencySpendControl"),
        scoreSelect(answers.budgetDiscipline, section, "budgetDiscipline"),
      ]);
    case "conversion-rates":
      return average([
        balancedRateScore(toNumber(answers.applicationToInterviewRate), 12, 25, 8, 35),
        balancedRateScore(toNumber(answers.interviewToOfferRate), 20, 35, 12, 45),
        scoreSelect(answers.conversionReview, section, "conversionReview"),
      ]);
    case "hiring-manager-alignment":
      return average([
        scoreSelect(answers.managerBriefQuality, section, "managerBriefQuality"),
        inverseDaysScore(toNumber(answers.managerFeedbackDays), [1, 2, 3, 5]),
        scoreSelect(answers.managerCommitment, section, "managerCommitment"),
      ]);
    default:
      return 0;
  }
}

function cleanSentence(text: string): string {
  return text.replace(/\s+/g, " ").trim();
}

function sectionVerb(title: string): "is" | "are" {
  return /s$/i.test(title) ? "are" : "is";
}

const evidenceLabels: Record<string, string> = {
  roleBriefQuality: "brief clarity",
  successMeasuresDefined: "defined success measures",
  briefAlignment: "decision-maker alignment",
  advertSpecificity: "advert specificity",
  channelFit: "channel selection",
  qualifiedApplicantRate: "qualified applicant rate",
  sourceMixControl: "source mix discipline",
  sourcePerformanceVisibility: "source performance visibility",
  sourceDependency: "source dependency",
  applicationFriction: "application friction",
  applicationSteps: "application length",
  mobileExperience: "mobile application quality",
  screeningCriteria: "screening criteria",
  screeningResponseHours: "screening speed",
  cvReviewConsistency: "review consistency",
  interviewStages: "interview stage count",
  interviewScorecards: "interview structure",
  interviewTurnaroundDays: "interview turnaround time",
  candidateCommunication: "candidate communication",
  feedbackDays: "feedback turnaround time",
  candidateDropOff: "candidate drop-off",
  offerApprovalDays: "offer approval speed",
  offerAcceptanceRate: "offer acceptance rate",
  closingPlan: "candidate closing discipline",
  timeToHireDays: "time to hire",
  pipelineReviewCadence: "pipeline review cadence",
  bottlenecksVisible: "bottleneck visibility",
  costPerHireVisibility: "cost visibility",
  agencySpendControl: "external spend control",
  budgetDiscipline: "budget sign-off discipline",
  applicationToInterviewRate: "application to interview conversion",
  interviewToOfferRate: "interview to offer conversion",
  conversionReview: "conversion review discipline",
  managerBriefQuality: "manager briefing quality",
  managerFeedbackDays: "manager feedback speed",
  managerCommitment: "manager process commitment",
};

function findQuestionLabel(section: AuditSection, questionId: string): string {
  const mappedLabel = evidenceLabels[questionId];
  if (mappedLabel) {
    return mappedLabel;
  }
  const question = section.questions.find((item) => item.id === questionId);
  return question?.label.replace(/\?$/, "").toLowerCase() ?? questionId;
}

function lowSignal(sectionId: string, answers: AuditAnswers): string[] {
  const pairs: Array<{ id: string; value: number }> = [];

  switch (sectionId) {
    case "job-definition":
      pairs.push(
        { id: "roleBriefQuality", value: scoreSelect(answers.roleBriefQuality, getSectionById(sectionId)!, "roleBriefQuality") },
        { id: "successMeasuresDefined", value: scoreSelect(answers.successMeasuresDefined, getSectionById(sectionId)!, "successMeasuresDefined") },
        { id: "briefAlignment", value: scoreSelect(answers.briefAlignment, getSectionById(sectionId)!, "briefAlignment") },
      );
      break;
    case "job-advertising":
      pairs.push(
        { id: "advertSpecificity", value: scoreSelect(answers.advertSpecificity, getSectionById(sectionId)!, "advertSpecificity") },
        { id: "channelFit", value: scoreSelect(answers.channelFit, getSectionById(sectionId)!, "channelFit") },
        { id: "qualifiedApplicantRate", value: positiveRateScore(toNumber(answers.qualifiedApplicantRate), [45, 30, 20, 10]) },
      );
      break;
    case "application-process":
      pairs.push(
        { id: "applicationFriction", value: scoreSelect(answers.applicationFriction, getSectionById(sectionId)!, "applicationFriction") },
        { id: "applicationSteps", value: applicationStepsScore(toNumber(answers.applicationSteps)) },
        { id: "mobileExperience", value: scoreSelect(answers.mobileExperience, getSectionById(sectionId)!, "mobileExperience") },
      );
      break;
    case "source-effectiveness":
      pairs.push(
        { id: "sourceMixControl", value: scoreSelect(answers.sourceMixControl, getSectionById(sectionId)!, "sourceMixControl") },
        { id: "sourcePerformanceVisibility", value: scoreSelect(answers.sourcePerformanceVisibility, getSectionById(sectionId)!, "sourcePerformanceVisibility") },
        { id: "sourceDependency", value: scoreSelect(answers.sourceDependency, getSectionById(sectionId)!, "sourceDependency") },
      );
      break;
    case "screening":
      pairs.push(
        { id: "screeningCriteria", value: scoreSelect(answers.screeningCriteria, getSectionById(sectionId)!, "screeningCriteria") },
        { id: "screeningResponseHours", value: inverseDaysScore(toNumber(answers.screeningResponseHours), [24, 48, 72, 120]) },
        { id: "cvReviewConsistency", value: scoreSelect(answers.cvReviewConsistency, getSectionById(sectionId)!, "cvReviewConsistency") },
      );
      break;
    case "interview-process":
      pairs.push(
        { id: "interviewStages", value: interviewStagesScore(toNumber(answers.interviewStages)) },
        { id: "interviewScorecards", value: scoreSelect(answers.interviewScorecards, getSectionById(sectionId)!, "interviewScorecards") },
        { id: "interviewTurnaroundDays", value: inverseDaysScore(toNumber(answers.interviewTurnaroundDays), [2, 4, 7, 10]) },
      );
      break;
    case "candidate-experience":
      pairs.push(
        { id: "candidateCommunication", value: scoreSelect(answers.candidateCommunication, getSectionById(sectionId)!, "candidateCommunication") },
        { id: "feedbackDays", value: inverseDaysScore(toNumber(answers.feedbackDays), [1, 2, 4, 6]) },
        { id: "candidateDropOff", value: inverseRateScore(toNumber(answers.candidateDropOff), [8, 15, 25, 35]) },
      );
      break;
    case "offer-stage":
      pairs.push(
        { id: "offerApprovalDays", value: inverseDaysScore(toNumber(answers.offerApprovalDays), [1, 2, 4, 6]) },
        { id: "offerAcceptanceRate", value: positiveRateScore(toNumber(answers.offerAcceptanceRate), [90, 80, 70, 60]) },
        { id: "closingPlan", value: scoreSelect(answers.closingPlan, getSectionById(sectionId)!, "closingPlan") },
      );
      break;
    case "time-to-hire":
      pairs.push(
        { id: "timeToHireDays", value: inverseDaysScore(toNumber(answers.timeToHireDays), [30, 45, 60, 90]) },
        { id: "pipelineReviewCadence", value: scoreSelect(answers.pipelineReviewCadence, getSectionById(sectionId)!, "pipelineReviewCadence") },
        { id: "bottlenecksVisible", value: scoreSelect(answers.bottlenecksVisible, getSectionById(sectionId)!, "bottlenecksVisible") },
      );
      break;
    case "cost-awareness":
      pairs.push(
        { id: "costPerHireVisibility", value: scoreSelect(answers.costPerHireVisibility, getSectionById(sectionId)!, "costPerHireVisibility") },
        { id: "agencySpendControl", value: scoreSelect(answers.agencySpendControl, getSectionById(sectionId)!, "agencySpendControl") },
        { id: "budgetDiscipline", value: scoreSelect(answers.budgetDiscipline, getSectionById(sectionId)!, "budgetDiscipline") },
      );
      break;
    case "conversion-rates":
      pairs.push(
        { id: "applicationToInterviewRate", value: balancedRateScore(toNumber(answers.applicationToInterviewRate), 12, 25, 8, 35) },
        { id: "interviewToOfferRate", value: balancedRateScore(toNumber(answers.interviewToOfferRate), 20, 35, 12, 45) },
        { id: "conversionReview", value: scoreSelect(answers.conversionReview, getSectionById(sectionId)!, "conversionReview") },
      );
      break;
    case "hiring-manager-alignment":
      pairs.push(
        { id: "managerBriefQuality", value: scoreSelect(answers.managerBriefQuality, getSectionById(sectionId)!, "managerBriefQuality") },
        { id: "managerFeedbackDays", value: inverseDaysScore(toNumber(answers.managerFeedbackDays), [1, 2, 3, 5]) },
        { id: "managerCommitment", value: scoreSelect(answers.managerCommitment, getSectionById(sectionId)!, "managerCommitment") },
      );
      break;
    default:
      break;
  }

  return pairs
    .sort((a, b) => a.value - b.value)
    .slice(0, 2)
    .map((item) => findQuestionLabel(getSectionById(sectionId)!, item.id));
}

function diagnosisFor(section: AuditSection, score: number, answers: AuditAnswers): string {
  const lowPoints = lowSignal(section.id, answers);
  const lowPointText = lowPoints.length ? lowPoints.join(" and ").toLowerCase() : "process discipline";
  const sectionLabel = section.title.toLowerCase();
  const verb = sectionVerb(section.title);

  if (score <= 39) {
    return cleanSentence(
      `${section.title} ${verb} not being controlled tightly enough. The weakest points are ${lowPointText}, and that is creating avoidable delay, weak decisions and wasted effort.`,
    );
  }
  if (score <= 70) {
    return cleanSentence(
      `${section.title} ${verb} serviceable but inconsistent. The current setup shows clear slippage around ${lowPointText}, so ${sectionLabel} outcomes depend too heavily on individual effort.`,
    );
  }
  return cleanSentence(
    `${section.title} ${verb} operating with good control. The process is clear, but ${lowPointText} still need tightening to protect consistency as hiring volume changes.`,
  );
}

function keyRisksFor(section: AuditSection, score: number, answers: AuditAnswers): string[] {
  const lowPoints = lowSignal(section.id, answers);
  const weakestPoint = lowPoints[0] ?? "process control";
  const secondaryPoint = lowPoints[1] ?? "decision quality";

  if (score <= 39) {
    return [
      `Weak control over ${weakestPoint} is slowing the process and increasing inconsistency.`,
      `The current position is likely to damage shortlist quality, conversion and candidate confidence.`,
    ];
  }

  if (score <= 70) {
    return [
      `${weakestPoint} is not consistent enough and is creating avoidable variance between roles or teams.`,
      `If ${secondaryPoint} is not tightened, hiring quality and pace will remain uneven.`,
    ];
  }

  return [
    `${weakestPoint} is the main area that still needs tighter discipline.`,
    `Without that improvement, stronger parts of the process will end up carrying weaker ones.`,
  ];
}

function impactFor(section: AuditSection, score: number): string {
  const sectionTitle = section.title.toLowerCase();
  if (score <= 39) {
    return cleanSentence(
      `This is increasing time to hire, reducing shortlist quality and creating avoidable candidate loss. In commercial terms, weak ${sectionTitle} performance is adding hidden cost to every live vacancy.`,
    );
  }
  if (score <= 70) {
    return cleanSentence(
      `The current position is adding friction to the process and reducing conversion quality at key stages. That means more wasted interviews, slower decisions and less confidence in hiring outcomes.`,
    );
  }
  return cleanSentence(
    `The process is performing well enough to support growth, but sharper discipline here would still protect speed and candidate quality. The gain is lower waste and more predictable hiring performance.`,
  );
}

function recommendationsFor(sectionId: string): string[] {
  switch (sectionId) {
    case "job-definition":
      return [
        "Set a mandatory role brief covering scope, outcomes, non-negotiables and package before search starts.",
        "Define success measures for the first six months so assessment stays anchored to delivery.",
        "Lock hiring manager alignment in a short briefing call before the role reaches market.",
      ];
    case "job-advertising":
      return [
        "Rewrite adverts around role outcomes, reporting line, package and genuine selling points.",
        "Match channels to role type and review qualified applicant rates by source every month.",
        "Stop running generic copy across different vacancies when the candidate markets are not the same.",
      ];
    case "source-effectiveness":
      return [
        "Review source quality by shortlist, interview and hire rather than applicant volume alone.",
        "Reduce dependence on low-yield channels that create activity without quality.",
        "Build a deliberate source mix for each role family so the team has better fallback options.",
      ];
    case "application-process":
      return [
        "Reduce unnecessary application fields and remove duplicate data entry.",
        "Cut mandatory steps to the minimum needed for first review.",
        "Test the application flow on mobile and fix any avoidable friction immediately.",
      ];
    case "screening":
      return [
        "Set role-specific screening criteria before the role goes live.",
        "Introduce a response standard so viable applicants are reviewed within a defined window.",
        "Calibrate reviewers against the same baseline to improve shortlist consistency.",
      ];
    case "interview-process":
      return [
        "Keep most roles to two or three purposeful interview stages.",
        "Use structured scorecards so interview quality does not depend on individual style.",
        "Set an interview turnaround target and track adherence weekly.",
      ];
    case "candidate-experience":
      return [
        "Set clear communication points so candidates know what happens next and when.",
        "Return interview feedback within a fixed timeframe and chase delayed responses.",
        "Track viable candidate drop-off and investigate the point where confidence is lost.",
      ];
    case "offer-stage":
      return [
        "Shorten offer approval steps so preferred candidates do not wait unnecessarily.",
        "Prepare a closing plan for priority hires before the final interview stage is complete.",
        "Review declined offers for patterns in package, timing and competing options.",
      ];
    case "time-to-hire":
      return [
        "Review live vacancies on a fixed cadence with clear accountability for next actions.",
        "Measure delay between stages so the business can see where pace is being lost.",
        "Set a target time to hire by role family and manage exceptions actively.",
      ];
    case "cost-awareness":
      return [
        "Track cost per hire using a consistent method across internal and external spend.",
        "Require sign-off on external spend before agencies or new channels are engaged.",
        "Use cost visibility to challenge low-performing channels rather than repeating them.",
      ];
    case "conversion-rates":
      return [
        "Track conversion from application through to acceptance for each active role.",
        "Use weak conversion points to isolate whether the issue sits with attraction, screening or interview quality.",
        "Review conversion weekly so poor funnel performance is corrected while roles are still live.",
      ];
    case "hiring-manager-alignment":
      return [
        "Agree manager service levels for briefs, interviews and feedback before search begins.",
        "Escalate delayed feedback quickly so candidate momentum is protected.",
        "Use a standard briefing and debrief format to improve decision quality across teams.",
      ];
    default:
      return [];
  }
}

function consultantNoteFor(section: AuditSection, score: number): string {
  if (score <= 39) {
    return `This area needs active correction, not minor process tuning. If it is left alone, it will continue to drag performance in the rest of the hiring model down with it.`;
  }
  if (score <= 70) {
    return `The core process exists, but it is not controlled tightly enough to deliver consistent outcomes. Tightening a few operating rules here would improve pace quickly.`;
  }
  return `This is one of the more stable parts of the process. The priority is to preserve that discipline and stop weaker stages elsewhere from eroding it.`;
}

function scoreMeaning(score: number): string {
  if (score <= 39) {
    return "The hiring model is under strain. Too many outcomes depend on workarounds rather than a reliable process.";
  }
  if (score <= 70) {
    return "The hiring model is serviceable, but inconsistent. Performance is acceptable in places and weak where control drops.";
  }
  return "The hiring model is in good shape. The process is functioning with control, though a few improvements would still sharpen pace and quality.";
}

function buildSectionReport(section: AuditSection, answers: AuditAnswers): SectionReport {
  const score = scoreBySection(section.id, answers);
  const diagnosis = diagnosisFor(section, score, answers);
  const impact = impactFor(section, score);
  const recommendations = recommendationsFor(section.id);

  return {
    id: section.id,
    title: section.title,
    strapline: section.strapline,
    score,
    status: band(score),
    currentState: diagnosis,
    keyRisks: keyRisksFor(section, score, answers),
    commercialImpact: impact,
    immediateActions: recommendations.slice(0, 2),
    diagnosis,
    impact,
    recommendations,
    consultantNote: consultantNoteFor(section, score),
    evidence: lowSignal(section.id, answers),
  };
}

function executiveSummary(overallScore: number, sections: SectionReport[], companyName: string): string {
  const strongest = [...sections].sort((a, b) => b.score - a.score)[0];
  const weakest = [...sections].sort((a, b) => a.score - b.score)[0];
  const tone =
    overallScore <= 39
      ? "The recruitment process is currently losing pace, control and candidate quality."
      : overallScore <= 70
        ? "The recruitment process can deliver, but it is not consistent enough to do so predictably."
        : "The recruitment process is performing well overall, with a small number of areas still limiting efficiency.";

  return cleanSentence(
    `${companyName} shows an overall score of ${overallScore}/100. ${tone} The strongest area is ${strongest.title.toLowerCase()}, while the weakest area is ${weakest.title.toLowerCase()}. The main commercial issue is avoidable delay and uneven conversion caused by inconsistent operating discipline. The immediate priority is to tighten the weakest stages first so hiring speed and candidate quality improve together.`,
  );
}

export function buildAuditReport(submission: AuditSubmission): AuditReport {
  const sections = auditSections.map((section) => buildSectionReport(section, submission.answers));
  const overallScore = clampScore(average(sections.map((section) => section.score)));
  const sortedByScore = [...sections].sort((a, b) => a.score - b.score);
  const strongestAreas = [...sections].sort((a, b) => b.score - a.score).slice(0, 3);
  const topIssues = sortedByScore.slice(0, 3);
  const priorityActions = topIssues.flatMap((section) => section.recommendations.slice(0, 1)).slice(0, 3);

  return {
    generatedAt: new Date().toISOString(),
    profile: submission.profile,
    overallScore,
    overallStatus: band(overallScore),
    scoreMeaning: scoreMeaning(overallScore),
    executiveSummary: executiveSummary(overallScore, sections, submission.profile.companyName),
    strongestAreas,
    topIssues,
    priorityActions,
    sections,
    recommendedNextStep:
      "The findings point to a clear operating improvement plan rather than a bigger hiring problem. Bradford & Marsh Consulting can help redesign the weak points, tighten manager discipline and put a cleaner delivery model in place without adding unnecessary process.",
  };
}
