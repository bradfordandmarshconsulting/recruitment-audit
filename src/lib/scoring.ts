import { auditSections, type AuditAnswers, type AuditSection, type AuditSubmission, getSectionById } from "@/lib/audit-config";

export type ScoreStatus = "red" | "amber" | "green";

export type SectionReport = {
  id: string;
  title: string;
  strapline: string;
  score: number;
  status: ScoreStatus;
  headlineDiagnosis: string;
  currentState: string;
  keyRisks: string[];
  commercialImpact: string;
  immediateActions: string[];
  structuralImprovements: string[];
  evidence: string[];
};

export type ScoreSummaryRow = {
  title: string;
  score: number;
  status: ScoreStatus;
};

export type MethodologyRow = {
  band: string;
  interpretation: string;
  implication: string;
};

export type BenchmarkRow = {
  metric: string;
  client: string;
  target: string;
  comment: string;
  status: ScoreStatus;
};

export type PriorityMatrixEntry = {
  priorityArea: string;
  urgency: string;
  impact: string;
  whyItMatters: string;
  firstMove: string;
  status: ScoreStatus;
};

export type ReportLetter = {
  salutation: string;
  paragraphs: string[];
  signatureName: string;
  signatureTitle: string;
};

export type AuditReport = {
  generatedAt: string;
  profile: AuditSubmission["profile"];
  overallScore: number;
  overallStatus: ScoreStatus;
  ratingBand: string;
  scoreMeaning: string;
  executiveSummary: string;
  primaryDiagnosis: string;
  strongestArea: SectionReport;
  weakestArea: SectionReport;
  strongestAreas: SectionReport[];
  topIssues: SectionReport[];
  scoreSummary: ScoreSummaryRow[];
  scoringMethodology: MethodologyRow[];
  benchmarkSnapshot: BenchmarkRow[];
  priorityMatrix: PriorityMatrixEntry[];
  visualAnalysisNotes: string[];
  topStrengths: string[];
  topProblems: string[];
  day30Plan: string[];
  day60Plan: string[];
  day90Plan: string[];
  sections: SectionReport[];
  letter: ReportLetter;
  finalVerdict: string;
  recommendedNextStep: string;
};

type SectionCopySpec = {
  weak: string;
  mid: string;
  strong: string;
  risk: string;
  cost: string;
  structural: [string, string];
};

const sectionCopySpecs: Record<string, SectionCopySpec> = {
  "job-definition": {
    weak: "Role definition is not tight enough before hiring starts.",
    mid: "Role definition exists, but it still drifts once the process is live.",
    strong: "Role definition is mostly clear, but the handoff into hiring is not fully disciplined.",
    risk: "That creates mismatch between the brief, the shortlist and the final hire.",
    cost: "The business loses time in shortlisting, repeats interviews it should not need, and increases the risk of an early mismatch.",
    structural: [
      "Use one briefing format across all roles so scope, outcomes and non-negotiables are set before search starts.",
      "Tie the role brief to six-month success measures so assessment stays anchored to actual delivery.",
    ],
  },
  "job-advertising": {
    weak: "The advertising message is not focused enough to attract the right market.",
    mid: "Job advertising is getting roles to market, but the message is still too broad in places.",
    strong: "Job advertising is working well overall, with some room to sharpen targeting.",
    risk: "The business attracts volume without enough control over applicant quality.",
    cost: "That increases screening load, slows shortlist production and weakens the conversion rate from application to interview.",
    structural: [
      "Set one advert standard that covers role outcomes, package, reporting line and differentiators.",
      "Review advert performance by role family so weak messaging is corrected before it becomes the default.",
    ],
  },
  "source-effectiveness": {
    weak: "The source mix is not being managed tightly enough to protect quality.",
    mid: "Source activity is in place, but channel performance is not visible enough to guide decisions.",
    strong: "Source coverage is sound, but the mix could still be managed with more precision.",
    risk: "The team can end up repeating channels that create activity without producing viable hires.",
    cost: "That adds avoidable spend, creates noise in the funnel and reduces confidence in where good candidates are actually coming from.",
    structural: [
      "Track source performance through shortlist, interview and hire rather than applicant volume alone.",
      "Build a role-family source plan so the team is not overly dependent on one or two channels.",
    ],
  },
  "application-process": {
    weak: "The application process is too heavy and is likely pushing viable candidates out.",
    mid: "The application process works, but there is still more friction than there should be.",
    strong: "The application process is broadly functional, with a few steps still creating avoidable drag.",
    risk: "Good candidates may drop out before the business has a chance to assess them properly.",
    cost: "That lowers effective applicant quality, weakens conversion and forces the team to work harder for the same hiring result.",
    structural: [
      "Strip the process back to the minimum information needed for first review and remove duplicate entry points.",
      "Review the mobile application journey as a standard part of process governance.",
    ],
  },
  screening: {
    weak: "Screening lacks enough structure to produce consistent shortlist quality.",
    mid: "Screening is happening, but the standard is not applied consistently enough.",
    strong: "Screening control is reasonably sound, though there is still room to tighten consistency.",
    risk: "Weak candidates can move too far through the process while stronger candidates wait too long.",
    cost: "That creates wasted interviews, slower hiring decisions and lower confidence in the shortlist.",
    structural: [
      "Introduce one screening standard for each role family so reviewers are working to the same threshold.",
      "Set a service level for initial review and track exceptions weekly.",
    ],
  },
  "interview-process": {
    weak: "The interview process is not controlled tightly enough to support consistent decisions.",
    mid: "The interview process can work, but the design and feedback discipline are still uneven.",
    strong: "Interview quality is in a reasonable place, with some remaining exposure around pace and structure.",
    risk: "The business is exposed to inconsistent assessment and avoidable candidate drift between stages.",
    cost: "That raises the chance of lost candidates, slower offers and a weaker final hiring decision.",
    structural: [
      "Keep most roles to a defined stage design and use scorecards as standard rather than by exception.",
      "Measure interview turnaround and feedback quality by manager so delays can be challenged early.",
    ],
  },
  "candidate-experience": {
    weak: "Candidate experience is exposed and likely undermining conversion.",
    mid: "Candidate experience is serviceable, but communication and feedback are still too uneven.",
    strong: "Candidate experience is generally positive, though the process still loses polish at key moments.",
    risk: "Candidates can lose confidence in the process long before the final decision point.",
    cost: "That weakens offer conversion, damages employer perception and reduces the quality of the pipeline over time.",
    structural: [
      "Set a candidate communication standard across the whole process, including response and feedback timing.",
      "Use candidate feedback as a standing input in monthly process review.",
    ],
  },
  "offer-stage": {
    weak: "The offer stage is too slow and too exposed to drift.",
    mid: "The offer stage can close candidates, but not with enough consistency.",
    strong: "Offer control is broadly workable, though approval speed and closing discipline can still improve.",
    risk: "Preferred candidates may accept elsewhere while internal approvals or closing conversations lag.",
    cost: "That leads to repeated hiring cycles, more agency or advertising spend and avoidable vacancy cost.",
    structural: [
      "Create one offer approval route with a defined turnaround and named owner.",
      "Build closing plans into the final stage for priority hires rather than leaving them to ad hoc follow-up.",
    ],
  },
  "time-to-hire": {
    weak: "Hiring pace is not being managed well enough and delay is becoming normal.",
    mid: "Time to hire is visible, but the process is still losing speed in avoidable places.",
    strong: "Time to hire is mostly under control, with some remaining process drag to remove.",
    risk: "The business can lose momentum on live roles and give strong candidates too much time to disengage.",
    cost: "That extends vacancy cost, holds teams back operationally and forces more reactive hiring decisions.",
    structural: [
      "Set target time-to-hire ranges by role family and review exceptions with leadership.",
      "Track delay between stages so the business can see where pace is really being lost.",
    ],
  },
  "cost-awareness": {
    weak: "Recruitment cost is not visible enough to support disciplined decisions.",
    mid: "The business has some cost awareness, but not enough to steer spend properly.",
    strong: "Cost visibility is acceptable, though there is still room to tighten commercial control.",
    risk: "Low-yield spend can continue because the business cannot see clearly what value each route is producing.",
    cost: "That weakens return on recruitment spend and makes it harder to challenge poor channel or agency performance.",
    structural: [
      "Track cost per hire on a consistent basis across internal effort, advertising and external support.",
      "Link spend decisions to source and conversion performance rather than habit or urgency alone.",
    ],
  },
  "conversion-rates": {
    weak: "Conversion performance is not controlled tightly enough to protect hiring quality.",
    mid: "Conversion rates are visible, but they are not being used sharply enough to correct weak stages.",
    strong: "Conversion performance is one of the more stable parts of the process, with some room to refine.",
    risk: "The business may be feeding weak stages without identifying where the quality loss is actually happening.",
    cost: "That creates wasted interviews, slower shortlists and a lower return on sourcing effort.",
    structural: [
      "Review conversion by role and stage every week so weak points are corrected while vacancies are live.",
      "Use conversion data to separate attraction issues from screening and interview discipline issues.",
    ],
  },
  "hiring-manager-alignment": {
    weak: "Hiring manager alignment is too loose and is slowing the whole process down.",
    mid: "Hiring managers are engaged, but not with enough consistency to protect pace and quality.",
    strong: "Hiring manager support is reasonably strong, though it still needs tighter operating discipline.",
    risk: "The process can stall around briefs, interviews or feedback even when the recruitment team is ready to move.",
    cost: "That slows decisions, reduces candidate confidence and weakens accountability for the final outcome.",
    structural: [
      "Set manager service levels for briefing, interviewing and feedback as part of the recruitment process itself.",
      "Use one briefing and debrief structure so decisions are easier to compare and defend.",
    ],
  },
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
  return clampScore(scores.reduce((sum, value) => sum + value, 0) / scores.length);
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

function findQuestionLabel(sectionId: string, questionId: string): string {
  const mappedLabel = evidenceLabels[questionId];
  if (mappedLabel) {
    return mappedLabel;
  }
  const section = getSectionById(sectionId);
  const question = section?.questions.find((item) => item.id === questionId);
  return question?.label.replace(/\?$/, "").toLowerCase() ?? questionId;
}

function lowSignal(sectionId: string, answers: AuditAnswers): string[] {
  const pairs: Array<{ id: string; value: number }> = [];
  const section = getSectionById(sectionId);
  if (!section) {
    return [];
  }

  switch (sectionId) {
    case "job-definition":
      pairs.push(
        { id: "roleBriefQuality", value: scoreSelect(answers.roleBriefQuality, section, "roleBriefQuality") },
        { id: "successMeasuresDefined", value: scoreSelect(answers.successMeasuresDefined, section, "successMeasuresDefined") },
        { id: "briefAlignment", value: scoreSelect(answers.briefAlignment, section, "briefAlignment") },
      );
      break;
    case "job-advertising":
      pairs.push(
        { id: "advertSpecificity", value: scoreSelect(answers.advertSpecificity, section, "advertSpecificity") },
        { id: "channelFit", value: scoreSelect(answers.channelFit, section, "channelFit") },
        { id: "qualifiedApplicantRate", value: positiveRateScore(toNumber(answers.qualifiedApplicantRate), [45, 30, 20, 10]) },
      );
      break;
    case "source-effectiveness":
      pairs.push(
        { id: "sourceMixControl", value: scoreSelect(answers.sourceMixControl, section, "sourceMixControl") },
        { id: "sourcePerformanceVisibility", value: scoreSelect(answers.sourcePerformanceVisibility, section, "sourcePerformanceVisibility") },
        { id: "sourceDependency", value: scoreSelect(answers.sourceDependency, section, "sourceDependency") },
      );
      break;
    case "application-process":
      pairs.push(
        { id: "applicationFriction", value: scoreSelect(answers.applicationFriction, section, "applicationFriction") },
        { id: "applicationSteps", value: applicationStepsScore(toNumber(answers.applicationSteps)) },
        { id: "mobileExperience", value: scoreSelect(answers.mobileExperience, section, "mobileExperience") },
      );
      break;
    case "screening":
      pairs.push(
        { id: "screeningCriteria", value: scoreSelect(answers.screeningCriteria, section, "screeningCriteria") },
        { id: "screeningResponseHours", value: inverseDaysScore(toNumber(answers.screeningResponseHours), [24, 48, 72, 120]) },
        { id: "cvReviewConsistency", value: scoreSelect(answers.cvReviewConsistency, section, "cvReviewConsistency") },
      );
      break;
    case "interview-process":
      pairs.push(
        { id: "interviewStages", value: interviewStagesScore(toNumber(answers.interviewStages)) },
        { id: "interviewScorecards", value: scoreSelect(answers.interviewScorecards, section, "interviewScorecards") },
        { id: "interviewTurnaroundDays", value: inverseDaysScore(toNumber(answers.interviewTurnaroundDays), [2, 4, 7, 10]) },
      );
      break;
    case "candidate-experience":
      pairs.push(
        { id: "candidateCommunication", value: scoreSelect(answers.candidateCommunication, section, "candidateCommunication") },
        { id: "feedbackDays", value: inverseDaysScore(toNumber(answers.feedbackDays), [1, 2, 4, 6]) },
        { id: "candidateDropOff", value: inverseRateScore(toNumber(answers.candidateDropOff), [8, 15, 25, 35]) },
      );
      break;
    case "offer-stage":
      pairs.push(
        { id: "offerApprovalDays", value: inverseDaysScore(toNumber(answers.offerApprovalDays), [1, 2, 4, 6]) },
        { id: "offerAcceptanceRate", value: positiveRateScore(toNumber(answers.offerAcceptanceRate), [90, 80, 70, 60]) },
        { id: "closingPlan", value: scoreSelect(answers.closingPlan, section, "closingPlan") },
      );
      break;
    case "time-to-hire":
      pairs.push(
        { id: "timeToHireDays", value: inverseDaysScore(toNumber(answers.timeToHireDays), [30, 45, 60, 90]) },
        { id: "pipelineReviewCadence", value: scoreSelect(answers.pipelineReviewCadence, section, "pipelineReviewCadence") },
        { id: "bottlenecksVisible", value: scoreSelect(answers.bottlenecksVisible, section, "bottlenecksVisible") },
      );
      break;
    case "cost-awareness":
      pairs.push(
        { id: "costPerHireVisibility", value: scoreSelect(answers.costPerHireVisibility, section, "costPerHireVisibility") },
        { id: "agencySpendControl", value: scoreSelect(answers.agencySpendControl, section, "agencySpendControl") },
        { id: "budgetDiscipline", value: scoreSelect(answers.budgetDiscipline, section, "budgetDiscipline") },
      );
      break;
    case "conversion-rates":
      pairs.push(
        { id: "applicationToInterviewRate", value: balancedRateScore(toNumber(answers.applicationToInterviewRate), 12, 25, 8, 35) },
        { id: "interviewToOfferRate", value: balancedRateScore(toNumber(answers.interviewToOfferRate), 20, 35, 12, 45) },
        { id: "conversionReview", value: scoreSelect(answers.conversionReview, section, "conversionReview") },
      );
      break;
    case "hiring-manager-alignment":
      pairs.push(
        { id: "managerBriefQuality", value: scoreSelect(answers.managerBriefQuality, section, "managerBriefQuality") },
        { id: "managerFeedbackDays", value: inverseDaysScore(toNumber(answers.managerFeedbackDays), [1, 2, 3, 5]) },
        { id: "managerCommitment", value: scoreSelect(answers.managerCommitment, section, "managerCommitment") },
      );
      break;
    default:
      break;
  }

  return pairs
    .sort((a, b) => a.value - b.value)
    .slice(0, 2)
    .map((item) => findQuestionLabel(sectionId, item.id));
}

function lowPointText(sectionId: string, answers: AuditAnswers): string {
  const points = lowSignal(sectionId, answers);
  return points.length ? points.join(" and ").toLowerCase() : "process control";
}

function ratingBand(score: number): string {
  if (score <= 39) {
    return "Underperforming";
  }
  if (score <= 70) {
    return "Functional but inconsistent";
  }
  if (score <= 84) {
    return "Strong but inconsistent";
  }
  return "High performing";
}

function scoreMeaning(score: number): string {
  if (score <= 39) {
    return "The hiring model is exposed. Too many outcomes depend on workarounds rather than a reliable process.";
  }
  if (score <= 70) {
    return "The hiring model can support hiring, but execution quality is too uneven from one stage to the next.";
  }
  if (score <= 84) {
    return "The hiring model is in decent shape, though a few weaker sections are still limiting pace and consistency.";
  }
  return "The hiring model is performing strongly overall, with only a small number of areas left to tighten.";
}

function headlineDiagnosisFor(sectionId: string, score: number): string {
  const spec = sectionCopySpecs[sectionId];
  if (!spec) {
    return "The current position needs review.";
  }
  if (score <= 39) {
    return spec.weak;
  }
  if (score <= 70) {
    return spec.mid;
  }
  return spec.strong;
}

function currentStateFor(sectionId: string, score: number, answers: AuditAnswers): string {
  const headline = headlineDiagnosisFor(sectionId, score);
  const weakestSignals = lowPointText(sectionId, answers);
  if (score <= 39) {
    return cleanSentence(`${headline} The main breakdown sits around ${weakestSignals}, and the process is not being managed tightly enough to recover pace once it slips.`);
  }
  if (score <= 70) {
    return cleanSentence(`${headline} The visible pressure points are ${weakestSignals}, which means the process works in parts but does not hold the same standard throughout.`);
  }
  return cleanSentence(`${headline} The remaining exposure sits around ${weakestSignals}, which is where the next improvement pass should focus.`);
}

function keyRisksFor(sectionId: string, score: number, answers: AuditAnswers): string[] {
  const spec = sectionCopySpecs[sectionId];
  const weakestSignals = lowPointText(sectionId, answers);
  if (!spec) {
    return [];
  }
  if (score <= 39) {
    return [
      cleanSentence(`${spec.risk}`),
      cleanSentence(`${weakestSignals} are weak enough to slow decisions and reduce candidate confidence.`),
    ];
  }
  if (score <= 70) {
    return [
      cleanSentence(`${spec.risk}`),
      cleanSentence(`If ${weakestSignals} are not tightened, the business will keep seeing uneven pace and quality from one vacancy to the next.`),
    ];
  }
  return [
    cleanSentence(`${weakestSignals} remain the main exposure in this part of the process.`),
    cleanSentence(`If control drifts here, stronger stages will end up absorbing the problem later in the funnel.`),
  ];
}

function commercialImpactFor(sectionId: string, score: number): string {
  const spec = sectionCopySpecs[sectionId];
  if (!spec) {
    return "This is affecting hiring performance.";
  }
  if (score <= 39) {
    return cleanSentence(`${spec.cost} The commercial effect is slower hiring, weaker conversion and more avoidable spend.`);
  }
  if (score <= 70) {
    return cleanSentence(`${spec.cost} The business is carrying more delay and wasted effort than it should need to.`);
  }
  return cleanSentence(`${spec.cost} The gain from tightening this area is faster delivery with less wasted effort.`);
}

function recommendationsFor(sectionId: string): string[] {
  switch (sectionId) {
    case "job-definition":
      return [
        "Use one briefing format that covers scope, outcomes, package and non-negotiables before search starts.",
        "Define six-month success measures for each role so assessment is tied to delivery rather than assumptions.",
        "Hold a live briefing with the hiring manager before the role reaches market.",
      ];
    case "job-advertising":
      return [
        "Rewrite adverts around role outcomes, package, reporting line and differentiators rather than broad task lists.",
        "Review qualified applicant rates by role family so weak advert copy is corrected quickly.",
        "Stop using the same generic advert structure across very different candidate markets.",
      ];
    case "source-effectiveness":
      return [
        "Review source quality by shortlist, interview and hire rather than applicant volume alone.",
        "Reduce dependence on low-yield channels that create activity without enough quality.",
        "Set a deliberate source plan for each role family so the team has better fallback options.",
      ];
    case "application-process":
      return [
        "Reduce unnecessary fields and remove duplicate application steps.",
        "Test the mobile journey and fix any points where completion is harder than it should be.",
        "Set a standard for maximum application length and challenge exceptions.",
      ];
    case "screening":
      return [
        "Introduce a screening rubric for each role family and use it as the default.",
        "Set a response standard so viable applicants are reviewed within a defined window.",
        "Calibrate reviewers against the same threshold to improve shortlist consistency.",
      ];
    case "interview-process":
      return [
        "Keep most roles to a defined interview stage pattern and remove unnecessary steps.",
        "Use scorecards so final decisions are easier to compare and defend.",
        "Track feedback turnaround by manager and challenge delays immediately.",
      ];
    case "candidate-experience":
      return [
        "Set communication points for every stage so candidates know what happens next and when.",
        "Return interview feedback within a fixed timeframe and chase delayed responses.",
        "Use candidate feedback to identify where confidence is being lost in the process.",
      ];
    case "offer-stage":
      return [
        "Create one offer approval route with a named owner and expected turnaround.",
        "Prepare a closing plan before the final interview for priority hires.",
        "Review declined offers for repeated issues in timing, package or communication.",
      ];
    case "time-to-hire":
      return [
        "Review live vacancies on a fixed cadence with accountability for the next move on every role.",
        "Track stage delay so the business can see exactly where time is being lost.",
        "Set target time-to-hire ranges by role family and manage exceptions closely.",
      ];
    case "cost-awareness":
      return [
        "Track cost per hire on a consistent basis across internal and external activity.",
        "Require sign-off for external spend before agencies or new channels are engaged.",
        "Use cost visibility to challenge repeat spend that is not improving outcomes.",
      ];
    case "conversion-rates":
      return [
        "Track stage conversion for every live role and review it weekly.",
        "Use conversion data to isolate whether the issue sits with attraction, screening or interview quality.",
        "Correct weak funnel stages while roles are still open rather than after the hire is made.",
      ];
    case "hiring-manager-alignment":
      return [
        "Set manager service levels for briefs, interviews and feedback as part of the recruitment process.",
        "Escalate delayed feedback quickly so candidate momentum is protected.",
        "Use one briefing and debrief structure so decisions are cleaner and easier to compare.",
      ];
    default:
      return [];
  }
}

function structuralImprovementsFor(sectionId: string): string[] {
  return sectionCopySpecs[sectionId]?.structural ?? [];
}

function buildSectionReport(section: AuditSection, answers: AuditAnswers): SectionReport {
  const score = scoreBySection(section.id, answers);

  return {
    id: section.id,
    title: section.title,
    strapline: section.strapline,
    score,
    status: band(score),
    headlineDiagnosis: headlineDiagnosisFor(section.id, score),
    currentState: currentStateFor(section.id, score, answers),
    keyRisks: keyRisksFor(section.id, score, answers),
    commercialImpact: commercialImpactFor(section.id, score),
    immediateActions: recommendationsFor(section.id).slice(0, 2),
    structuralImprovements: structuralImprovementsFor(section.id),
    evidence: lowSignal(section.id, answers),
  };
}

function buildStrengths(sections: SectionReport[]): string[] {
  return [...sections]
    .sort((a, b) => b.score - a.score)
    .slice(0, 5)
    .map((section) => `${section.title} (${section.score}/100): ${section.headlineDiagnosis}`);
}

function buildProblems(sections: SectionReport[]): string[] {
  return [...sections]
    .sort((a, b) => a.score - b.score)
    .slice(0, 5)
    .map((section) => `${section.title} (${section.score}/100): ${section.headlineDiagnosis}`);
}

function uniqueItems(items: string[], limit: number): string[] {
  return [...new Set(items)].slice(0, limit);
}

function buildRoadmap(topIssues: SectionReport[]): { day30: string[]; day60: string[]; day90: string[] } {
  return {
    day30: uniqueItems(topIssues.flatMap((section) => section.immediateActions), 5),
    day60: uniqueItems(topIssues.flatMap((section) => section.structuralImprovements), 5),
    day90: uniqueItems(
      topIssues.flatMap((section) => [
        `Review whether ${section.title.toLowerCase()} is improving against the scorecard.`,
        `Embed the revised standard for ${section.title.toLowerCase()} into day-to-day manager practice.`,
      ]),
      5,
    ),
  };
}

function buildBenchmarkSnapshot(sections: SectionReport[], overallScore: number): BenchmarkRow[] {
  const greenCount = sections.filter((section) => section.status === "green").length;
  const amberCount = sections.filter((section) => section.status === "amber").length;
  const redCount = sections.filter((section) => section.status === "red").length;
  const weakest = [...sections].sort((a, b) => a.score - b.score)[0];

  return [
    {
      metric: "Overall operating score",
      client: `${overallScore}/100`,
      target: "71+",
      comment: overallScore >= 71 ? "Within the target band" : "Below the target band",
      status: band(overallScore),
    },
    {
      metric: "Sections meeting target band",
      client: `${greenCount} of ${sections.length}`,
      target: "Majority of sections",
      comment: greenCount >= Math.ceil(sections.length / 2) ? "More sections are controlled than exposed" : "Too many sections remain below target",
      status: greenCount >= Math.ceil(sections.length / 2) ? "green" : "amber",
    },
    {
      metric: "Amber and red sections",
      client: `${amberCount + redCount}`,
      target: "3 or fewer",
      comment: amberCount + redCount <= 3 ? "Exposure is contained" : "Too many sections still need correction",
      status: amberCount + redCount <= 3 ? "green" : amberCount + redCount <= 5 ? "amber" : "red",
    },
    {
      metric: "Lowest scoring area",
      client: `${weakest.title} ${weakest.score}/100`,
      target: "71+",
      comment: weakest.score >= 71 ? "Above the target band but still the main pressure point" : "Below the target band and needs early attention",
      status: weakest.status,
    },
  ];
}

function buildPriorityMatrix(topIssues: SectionReport[]): PriorityMatrixEntry[] {
  return topIssues.map((section, index) => ({
    priorityArea: section.title,
    urgency: index === 0 ? "Immediate" : index === 1 ? "High" : "Near term",
    impact: section.score <= 39 ? "High" : section.score <= 70 ? "Medium" : "Moderate",
    whyItMatters: section.commercialImpact,
    firstMove: section.immediateActions[0] ?? "Review the process and set one named owner.",
    status: section.status,
  }));
}

function buildScoringMethodology(): MethodologyRow[] {
  return [
    {
      band: "71 to 100",
      interpretation: "Strong",
      implication: "The process is controlled and repeatable, though there may still be room to tighten execution.",
    },
    {
      band: "40 to 70",
      interpretation: "Functional but inconsistent",
      implication: "Capability exists, but delivery quality is uneven and outcomes depend too much on individual effort.",
    },
    {
      band: "0 to 39",
      interpretation: "Underperforming",
      implication: "The process is exposed to avoidable delay, weaker hiring decisions and unnecessary commercial loss.",
    },
  ];
}

function buildLetter(contactName: string): ReportLetter {
  return {
    salutation: `Dear ${contactName},`,
    paragraphs: [
      "Thank you for completing the Recruitment Operating Model Audit.",
      "This report sets out how the current hiring process is operating in practice, where it is holding the business back, and which changes should come first.",
      "The aim is to give leadership a clear basis for discussion and action. The findings focus on operating discipline, speed, conversion quality and the parts of the process that are likely creating avoidable cost.",
      "If you would like to talk through the report or prioritise the next stage of work, I would be happy to do that with you directly.",
    ],
    signatureName: "Michael Marsh",
    signatureTitle: "Managing Director, Bradford & Marsh Consulting",
  };
}

function executiveSummary(overallScore: number, sections: SectionReport[], companyName: string): string {
  const strongest = [...sections].sort((a, b) => b.score - a.score)[0];
  const weakest = [...sections].sort((a, b) => a.score - b.score)[0];
  const weakestEvidence = weakest.evidence[0] ?? weakest.title.toLowerCase();
  const tone =
    overallScore <= 39
      ? "Your recruitment process is under real strain."
      : overallScore <= 70
        ? "Your recruitment process is functional but inconsistent."
        : "Your recruitment process is performing well overall, but a few weak points are still limiting efficiency.";

  return cleanSentence(
    `${tone} ${companyName} scores ${overallScore}/100 overall. The clearest breakdown sits in ${weakest.title.toLowerCase()}, particularly around ${weakestEvidence}, while ${strongest.title.toLowerCase()} is holding up best. The immediate priority is to tighten the weakest stages first so time to hire and candidate quality improve together.`,
  );
}

function primaryDiagnosis(overallScore: number, weakestArea: SectionReport): string {
  if (overallScore <= 39) {
    return `The audit points to a hiring model that is exposed, with the main breakdown in ${weakestArea.title.toLowerCase()}.`;
  }
  if (overallScore <= 70) {
    return `The hiring model can still deliver, but ${weakestArea.title.toLowerCase()} is weakening pace and consistency across the wider process.`;
  }
  return `The hiring model is in decent shape overall, but ${weakestArea.title.toLowerCase()} remains the clearest point of drag.`;
}

function visualAnalysisNotes(overallScore: number, sections: SectionReport[]): string[] {
  const weakest = [...sections].sort((a, b) => a.score - b.score)[0];
  const strongest = [...sections].sort((a, b) => b.score - a.score)[0];
  const spread = strongest.score - weakest.score;

  return [
    `The section score profile shows the clearest pressure in ${weakest.title.toLowerCase()} and the strongest control in ${strongest.title.toLowerCase()}.`,
    `The spread between the highest and lowest sections is ${spread} points, which indicates how uneven the current operating model is.`,
    `The overall score sits in the ${ratingBand(overallScore).toLowerCase()} band, so the next gains will come from tightening the weaker sections rather than adding more activity.`,
  ];
}

function finalVerdict(overallScore: number, weakestArea: SectionReport): string {
  if (overallScore <= 39) {
    return `The recruitment operating model is exposed. Leadership should correct ${weakestArea.title.toLowerCase()} first before increasing hiring demand or channel spend.`;
  }
  if (overallScore <= 70) {
    return `The recruitment operating model is capable, but not yet controlled enough to deliver predictable results. Tightening ${weakestArea.title.toLowerCase()} should be the first leadership priority.`;
  }
  return `The recruitment operating model is in a stronger position than most, but it is not finished. A focused improvement pass in ${weakestArea.title.toLowerCase()} would raise pace, protect conversion and make hiring performance more dependable.`;
}

export function buildAuditReport(submission: AuditSubmission): AuditReport {
  const sections = auditSections.map((section) => buildSectionReport(section, submission.answers));
  const overallScore = clampScore(average(sections.map((section) => section.score)));
  const overallStatus = band(overallScore);
  const strongestAreas = [...sections].sort((a, b) => b.score - a.score).slice(0, 5);
  const topIssues = [...sections].sort((a, b) => a.score - b.score).slice(0, 5);
  const strongestArea = strongestAreas[0];
  const weakestArea = topIssues[0];
  const roadmap = buildRoadmap(topIssues.slice(0, 3));

  return {
    generatedAt: new Date().toISOString(),
    profile: submission.profile,
    overallScore,
    overallStatus,
    ratingBand: ratingBand(overallScore),
    scoreMeaning: scoreMeaning(overallScore),
    executiveSummary: executiveSummary(overallScore, sections, submission.profile.companyName),
    primaryDiagnosis: primaryDiagnosis(overallScore, weakestArea),
    strongestArea,
    weakestArea,
    strongestAreas,
    topIssues,
    scoreSummary: sections.map((section) => ({
      title: section.title,
      score: section.score,
      status: section.status,
    })),
    scoringMethodology: buildScoringMethodology(),
    benchmarkSnapshot: buildBenchmarkSnapshot(sections, overallScore),
    priorityMatrix: buildPriorityMatrix(topIssues.slice(0, 4)),
    visualAnalysisNotes: visualAnalysisNotes(overallScore, sections),
    topStrengths: buildStrengths(sections),
    topProblems: buildProblems(sections),
    day30Plan: roadmap.day30,
    day60Plan: roadmap.day60,
    day90Plan: roadmap.day90,
    sections,
    letter: buildLetter(submission.profile.contactName),
    finalVerdict: finalVerdict(overallScore, weakestArea),
    recommendedNextStep:
      "Bradford & Marsh Consulting can translate these findings into a tighter hiring model, with clearer manager discipline, faster decision points and a cleaner process from brief through to onboarding.",
  };
}
