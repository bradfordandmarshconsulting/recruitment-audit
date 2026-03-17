export type SelectOption = {
  value: string;
  label: string;
  description: string;
  score: number;
};

export type SelectQuestion = {
  id: string;
  type: "select";
  label: string;
  description: string;
  options: SelectOption[];
};

export type NumberQuestion = {
  id: string;
  type: "number";
  label: string;
  description: string;
  min: number;
  max: number;
  step: number;
  unit?: string;
  placeholder: string;
};

export type Question = SelectQuestion | NumberQuestion;

export type ProfileField = {
  id: string;
  label: string;
  placeholder: string;
  type?: "text" | "email";
};

export type AuditSection = {
  id: string;
  title: string;
  strapline: string;
  summary: string;
  questions: Question[];
};

export type AuditProfile = {
  contactName: string;
  contactRole: string;
  companyName: string;
  sector: string;
  location: string;
  companySize: string;
  annualHiringVolume: string;
};

export type AuditAnswers = Record<string, string>;

export type AuditSubmission = {
  profile: AuditProfile;
  answers: AuditAnswers;
};

export const profileFields: ProfileField[] = [
  {
    id: "contactName",
    label: "Contact name",
    placeholder: "Michael Marsh",
  },
  {
    id: "contactRole",
    label: "Job title",
    placeholder: "Managing Director",
  },
  {
    id: "companyName",
    label: "Company name",
    placeholder: "Bradford & Marsh Consulting",
  },
  {
    id: "sector",
    label: "Sector",
    placeholder: "Professional Services",
  },
  {
    id: "location",
    label: "Location",
    placeholder: "Cheshire",
  },
  {
    id: "companySize",
    label: "Company size",
    placeholder: "SME",
  },
  {
    id: "annualHiringVolume",
    label: "Estimated annual hires",
    placeholder: "24",
  },
];

export const auditSections: AuditSection[] = [
  {
    id: "job-definition",
    title: "Job definition",
    strapline: "How clearly each role is defined before it reaches market",
    summary:
      "Weak role definition creates misaligned briefs, poor shortlists and longer time to hire.",
    questions: [
      {
        id: "roleBriefQuality",
        type: "select",
        label: "How clear are role briefs before hiring starts?",
        description: "Assess whether scope, outcomes and must-have capability are defined clearly.",
        options: [
          { value: "unclear", label: "Unclear", description: "Briefs are vague and often rewritten later.", score: 20 },
          { value: "mixed", label: "Mixed", description: "Some briefs are clear, others rely on assumptions.", score: 50 },
          { value: "clear", label: "Clear", description: "Most roles start with a defined brief and clear scope.", score: 78 },
          { value: "sharp", label: "Sharp", description: "Role scope, outcomes and non-negotiables are set up front.", score: 100 },
        ],
      },
      {
        id: "successMeasuresDefined",
        type: "select",
        label: "Are success measures defined for the role?",
        description: "This covers delivery expectations, not generic competencies.",
        options: [
          { value: "no", label: "No", description: "The business hires without defining success in post.", score: 20 },
          { value: "partial", label: "Partly", description: "Some roles include success measures but not consistently.", score: 55 },
          { value: "mostly", label: "Mostly", description: "Success measures are usually defined before launch.", score: 80 },
          { value: "yes", label: "Yes", description: "Each role is tied to clear outputs and early measures.", score: 100 },
        ],
      },
      {
        id: "briefAlignment",
        type: "select",
        label: "How aligned are decision makers on each brief?",
        description: "This should reflect alignment between hiring manager, leadership and talent support.",
        options: [
          { value: "low", label: "Low", description: "The brief changes once candidates are in process.", score: 25 },
          { value: "uneven", label: "Uneven", description: "Alignment improves after the first shortlist.", score: 55 },
          { value: "good", label: "Good", description: "The brief is usually agreed before launch.", score: 80 },
          { value: "tight", label: "Tight", description: "Decision makers are aligned from the start.", score: 100 },
        ],
      },
    ],
  },
  {
    id: "job-advertising",
    title: "Job advertising",
    strapline: "How well the market-facing message attracts the right applicants",
    summary:
      "Advert quality and channel choice drive applicant quality and reduce wasted screening effort.",
    questions: [
      {
        id: "advertSpecificity",
        type: "select",
        label: "How specific are job adverts?",
        description: "Consider role expectations, differentiators and clarity of scope.",
        options: [
          { value: "generic", label: "Generic", description: "Adverts read like broad job descriptions.", score: 20 },
          { value: "mixed", label: "Mixed", description: "Some roles are well written, others are generic.", score: 55 },
          { value: "strong", label: "Strong", description: "Most adverts explain the role and the offer well.", score: 82 },
          { value: "excellent", label: "Excellent", description: "Adverts are role-specific and attract the right intent.", score: 100 },
        ],
      },
      {
        id: "channelFit",
        type: "select",
        label: "How well do channels match the roles being hired?",
        description: "Use the quality of channel selection rather than raw volume.",
        options: [
          { value: "poor", label: "Poor", description: "Roles are pushed through the same channels regardless of market.", score: 20 },
          { value: "basic", label: "Basic", description: "There is some channel variation but little review.", score: 50 },
          { value: "good", label: "Good", description: "Channels are selected with some role-specific judgement.", score: 78 },
          { value: "precise", label: "Precise", description: "Channel choice is deliberate and based on actual conversion quality.", score: 100 },
        ],
      },
      {
        id: "qualifiedApplicantRate",
        type: "number",
        label: "What share of applicants meet baseline role criteria?",
        description: "Enter a percentage. This measures advert quality and targeting.",
        min: 0,
        max: 100,
        step: 1,
        unit: "%",
        placeholder: "35",
      },
    ],
  },
  {
    id: "source-effectiveness",
    title: "Source effectiveness",
    strapline: "How well the business knows which channels actually produce viable hires",
    summary:
      "Source performance should be judged by conversion quality, not just applicant volume.",
    questions: [
      {
        id: "sourceMixControl",
        type: "select",
        label: "How deliberately are sourcing channels chosen for each role?",
        description: "This covers referrals, direct search, job boards, social and agency support where relevant.",
        options: [
          { value: "reactive", label: "Reactive", description: "Channels are used out of habit rather than fit.", score: 20 },
          { value: "basic", label: "Basic", description: "There is some variation, but little real channel strategy.", score: 55 },
          { value: "targeted", label: "Targeted", description: "Channel choice usually reflects the role and market.", score: 82 },
          { value: "disciplined", label: "Disciplined", description: "Channel mix is selected deliberately and reviewed against outcomes.", score: 100 },
        ],
      },
      {
        id: "sourcePerformanceVisibility",
        type: "select",
        label: "How visible is source performance beyond applicant volume?",
        description: "Good visibility should show which channels deliver shortlisted, interviewed and hired candidates.",
        options: [
          { value: "none", label: "Not visible", description: "The business cannot see which sources produce quality.", score: 20 },
          { value: "partial", label: "Partly visible", description: "Some source data exists, but it is not reliable enough to steer decisions.", score: 55 },
          { value: "clear", label: "Clear", description: "The business can see which sources convert well.", score: 82 },
          { value: "managed", label: "Managed closely", description: "Source quality is visible and actively used to improve hiring performance.", score: 100 },
        ],
      },
      {
        id: "sourceDependency",
        type: "select",
        label: "How dependent is the business on one or two channels?",
        description: "Over-dependence increases risk when markets tighten or response rates drop.",
        options: [
          { value: "high", label: "Highly dependent", description: "Most hiring relies on the same small set of channels.", score: 20 },
          { value: "moderate", label: "Moderately dependent", description: "There is some variety, but the model still leans too heavily on a few sources.", score: 55 },
          { value: "balanced", label: "Balanced", description: "The source mix is varied enough to reduce risk.", score: 82 },
          { value: "diversified", label: "Well diversified", description: "The business has a controlled mix of sources and fallback options.", score: 100 },
        ],
      },
    ],
  },
  {
    id: "application-process",
    title: "Application process",
    strapline: "How easy it is for suitable candidates to complete an application",
    summary:
      "Application friction cuts volume, distorts conversion and pushes better candidates out early.",
    questions: [
      {
        id: "applicationFriction",
        type: "select",
        label: "How much friction sits in the application process?",
        description: "Think about duplicate entry, login barriers and unnecessary fields.",
        options: [
          { value: "high", label: "High", description: "The process is long or clumsy and candidates drop out.", score: 20 },
          { value: "moderate", label: "Moderate", description: "The process is workable but still feels heavy.", score: 55 },
          { value: "light", label: "Light", description: "The process is straightforward for most applicants.", score: 82 },
          { value: "minimal", label: "Minimal", description: "The process is short, clear and mobile-friendly.", score: 100 },
        ],
      },
      {
        id: "applicationSteps",
        type: "number",
        label: "How many mandatory steps does a standard application involve?",
        description: "Count only steps the candidate must complete.",
        min: 1,
        max: 10,
        step: 1,
        placeholder: "3",
      },
      {
        id: "mobileExperience",
        type: "select",
        label: "How strong is the mobile application experience?",
        description: "Most candidate traffic is mobile. Poor performance here reduces conversion fast.",
        options: [
          { value: "weak", label: "Weak", description: "Mobile completion is difficult or unreliable.", score: 20 },
          { value: "fair", label: "Fair", description: "Mobile works but still feels awkward.", score: 55 },
          { value: "good", label: "Good", description: "Most candidates can complete an application comfortably.", score: 82 },
          { value: "excellent", label: "Excellent", description: "Mobile application is clean, fast and low-friction.", score: 100 },
        ],
      },
    ],
  },
  {
    id: "screening",
    title: "Screening",
    strapline: "How consistently applicants are reviewed and moved forward",
    summary:
      "Weak screening slows decision-making and increases wasted interviews.",
    questions: [
      {
        id: "screeningCriteria",
        type: "select",
        label: "How clearly are screening criteria defined?",
        description: "This should reflect a documented baseline, not individual judgement calls.",
        options: [
          { value: "adhoc", label: "Ad hoc", description: "Review standards vary by person and by role.", score: 20 },
          { value: "partial", label: "Partial", description: "There is some structure but not enough consistency.", score: 55 },
          { value: "structured", label: "Structured", description: "Most roles have a defined screening standard.", score: 82 },
          { value: "disciplined", label: "Disciplined", description: "Screening is structured and consistent across the team.", score: 100 },
        ],
      },
      {
        id: "screeningResponseHours",
        type: "number",
        label: "How quickly are new applicants screened?",
        description: "Enter average turnaround in hours.",
        min: 1,
        max: 240,
        step: 1,
        unit: "hours",
        placeholder: "48",
      },
      {
        id: "cvReviewConsistency",
        type: "select",
        label: "How consistent is CV review between reviewers?",
        description: "This affects shortlisting quality and hiring manager confidence.",
        options: [
          { value: "erratic", label: "Erratic", description: "Review quality varies significantly by reviewer.", score: 20 },
          { value: "mixed", label: "Mixed", description: "There is some consistency but avoidable variance remains.", score: 55 },
          { value: "steady", label: "Steady", description: "Review standards are generally consistent.", score: 82 },
          { value: "high", label: "High", description: "Review standards are calibrated and dependable.", score: 100 },
        ],
      },
    ],
  },
  {
    id: "interview-process",
    title: "Interview process",
    strapline: "How well the business assesses candidates once they are in process",
    summary:
      "Interview discipline has a direct effect on conversion, quality of hire and candidate confidence.",
    questions: [
      {
        id: "interviewStages",
        type: "number",
        label: "How many interview stages does a typical role involve?",
        description: "Count all formal interview steps before offer.",
        min: 1,
        max: 8,
        step: 1,
        placeholder: "3",
      },
      {
        id: "interviewScorecards",
        type: "select",
        label: "Are scorecards or interview criteria used consistently?",
        description: "Structured assessment reduces opinion-led hiring.",
        options: [
          { value: "no", label: "No", description: "Interview decisions rely largely on individual judgement.", score: 20 },
          { value: "some", label: "Some use", description: "Some roles use structure, others do not.", score: 55 },
          { value: "regular", label: "Regular use", description: "Structured assessment is common across hiring.", score: 82 },
          { value: "standard", label: "Standard practice", description: "Interview structure is consistent and expected.", score: 100 },
        ],
      },
      {
        id: "interviewTurnaroundDays",
        type: "number",
        label: "How many days pass between interview stages?",
        description: "Use the average time between one stage ending and the next being completed.",
        min: 0,
        max: 30,
        step: 1,
        unit: "days",
        placeholder: "5",
      },
    ],
  },
  {
    id: "candidate-experience",
    title: "Candidate experience",
    strapline: "How well the process treats candidates from application to decision",
    summary:
      "Candidate experience affects acceptance rates, employer reputation and future hiring reach.",
    questions: [
      {
        id: "candidateCommunication",
        type: "select",
        label: "How proactive is candidate communication?",
        description: "Assess updates, expectation setting and responsiveness during the process.",
        options: [
          { value: "reactive", label: "Reactive", description: "Candidates chase updates and communication is inconsistent.", score: 20 },
          { value: "basic", label: "Basic", description: "Updates are sent, but often later than expected.", score: 55 },
          { value: "good", label: "Good", description: "Candidates are kept informed through most of the process.", score: 82 },
          { value: "excellent", label: "Excellent", description: "Communication is timely, clear and well managed.", score: 100 },
        ],
      },
      {
        id: "feedbackDays",
        type: "number",
        label: "How quickly do candidates receive interview feedback?",
        description: "Use the average turnaround in days.",
        min: 0,
        max: 20,
        step: 1,
        unit: "days",
        placeholder: "3",
      },
      {
        id: "candidateDropOff",
        type: "number",
        label: "What percentage of viable candidates drop out before decision?",
        description: "Estimate voluntary drop-off once the candidate is genuinely in process.",
        min: 0,
        max: 100,
        step: 1,
        unit: "%",
        placeholder: "12",
      },
    ],
  },
  {
    id: "offer-stage",
    title: "Offer stage",
    strapline: "How quickly and effectively the business converts a chosen candidate",
    summary:
      "Offer friction can undo the work done earlier in the process and increase replacement cost.",
    questions: [
      {
        id: "offerApprovalDays",
        type: "number",
        label: "How many days does offer approval usually take?",
        description: "Measure from verbal decision to approved offer ready to issue.",
        min: 0,
        max: 20,
        step: 1,
        unit: "days",
        placeholder: "2",
      },
      {
        id: "offerAcceptanceRate",
        type: "number",
        label: "What percentage of offers are accepted?",
        description: "Use a typical recent rate, not a one-off outlier.",
        min: 0,
        max: 100,
        step: 1,
        unit: "%",
        placeholder: "85",
      },
      {
        id: "closingPlan",
        type: "select",
        label: "Is there a clear plan to close preferred candidates?",
        description: "This includes handling counteroffers, objections and delays before start date.",
        options: [
          { value: "none", label: "No", description: "Closing is improvised and depends on individual effort.", score: 20 },
          { value: "partial", label: "Partly", description: "Some roles are handled well, others drift.", score: 55 },
          { value: "good", label: "Yes, usually", description: "The team usually manages closing with intent.", score: 82 },
          { value: "strong", label: "Yes, consistently", description: "Preferred candidates are managed actively through to acceptance.", score: 100 },
        ],
      },
    ],
  },
  {
    id: "time-to-hire",
    title: "Time to hire",
    strapline: "How quickly the business moves from approved role to accepted offer",
    summary:
      "Slow hiring extends vacancy cost, weakens candidate quality and damages conversion.",
    questions: [
      {
        id: "timeToHireDays",
        type: "number",
        label: "What is the average time to hire?",
        description: "Measure in calendar days from approved role to accepted offer.",
        min: 1,
        max: 180,
        step: 1,
        unit: "days",
        placeholder: "45",
      },
      {
        id: "pipelineReviewCadence",
        type: "select",
        label: "How often is active hiring progress reviewed?",
        description: "Use the real cadence, not the intended one.",
        options: [
          { value: "rare", label: "Rarely", description: "Progress is reviewed only when issues escalate.", score: 20 },
          { value: "irregular", label: "Irregularly", description: "Some roles are reviewed, others drift.", score: 50 },
          { value: "weekly", label: "Weekly", description: "Active vacancies are reviewed routinely.", score: 82 },
          { value: "twice-weekly", label: "Twice weekly or better", description: "The business manages pace actively.", score: 100 },
        ],
      },
      {
        id: "bottlenecksVisible",
        type: "select",
        label: "Can the business identify where hiring slows down?",
        description: "This should reflect evidence, not guesswork.",
        options: [
          { value: "no", label: "No", description: "Bottlenecks are noticed late and debated after the fact.", score: 20 },
          { value: "partial", label: "Partly", description: "Some problem points are visible, but not consistently.", score: 55 },
          { value: "mostly", label: "Mostly", description: "The team can usually identify the main delays.", score: 82 },
          { value: "yes", label: "Yes", description: "The business can see where pace drops and acts quickly.", score: 100 },
        ],
      },
    ],
  },
  {
    id: "cost-awareness",
    title: "Cost awareness",
    strapline: "How clearly the business understands recruitment cost and spend efficiency",
    summary:
      "If cost is not visible, inefficient hiring becomes normal and harder to challenge.",
    questions: [
      {
        id: "costPerHireVisibility",
        type: "select",
        label: "How clearly is cost per hire tracked?",
        description: "This should include agency use, advertising and internal effort where possible.",
        options: [
          { value: "not-tracked", label: "Not tracked", description: "The business cannot quantify cost per hire.", score: 20 },
          { value: "rough", label: "Rough view", description: "There is an estimate but little discipline behind it.", score: 50 },
          { value: "tracked", label: "Tracked", description: "Cost per hire is visible for most hiring activity.", score: 82 },
          { value: "managed", label: "Managed", description: "Cost is tracked and used to improve channel decisions.", score: 100 },
        ],
      },
      {
        id: "agencySpendControl",
        type: "select",
        label: "How controlled is external recruitment spend?",
        description: "Focus on approval discipline and value visibility.",
        options: [
          { value: "loose", label: "Loose", description: "Spend decisions are reactive and hard to review later.", score: 20 },
          { value: "mixed", label: "Mixed", description: "There is some control but limited commercial challenge.", score: 55 },
          { value: "clear", label: "Clear", description: "External spend is reviewed and governed sensibly.", score: 82 },
          { value: "tight", label: "Tight", description: "External spend is deliberate and linked to performance.", score: 100 },
        ],
      },
      {
        id: "budgetDiscipline",
        type: "select",
        label: "How disciplined is budget sign-off before hiring begins?",
        description: "Strong budget discipline reduces avoidable stop-start hiring.",
        options: [
          { value: "weak", label: "Weak", description: "Roles are launched before budget clarity exists.", score: 20 },
          { value: "partial", label: "Partial", description: "Some teams are disciplined, others are not.", score: 55 },
          { value: "good", label: "Good", description: "Budget is usually agreed before the role goes live.", score: 82 },
          { value: "strong", label: "Strong", description: "Budget approval is clear and reliable at the start.", score: 100 },
        ],
      },
    ],
  },
  {
    id: "conversion-rates",
    title: "Conversion rates",
    strapline: "How efficiently candidates move from stage to stage",
    summary:
      "Conversion quality reveals whether the process is attracting the right people and assessing them well.",
    questions: [
      {
        id: "applicationToInterviewRate",
        type: "number",
        label: "What percentage of applicants reach interview?",
        description: "Use a normal rate across typical roles.",
        min: 0,
        max: 100,
        step: 1,
        unit: "%",
        placeholder: "18",
      },
      {
        id: "interviewToOfferRate",
        type: "number",
        label: "What percentage of interviewed candidates receive an offer?",
        description: "This indicates screening quality and interview precision.",
        min: 0,
        max: 100,
        step: 1,
        unit: "%",
        placeholder: "28",
      },
      {
        id: "conversionReview",
        type: "select",
        label: "How often are stage conversion rates reviewed?",
        description: "Without review, conversion problems stay hidden.",
        options: [
          { value: "never", label: "Never", description: "Conversion data is not used in hiring reviews.", score: 20 },
          { value: "sometimes", label: "Sometimes", description: "Conversion is reviewed irregularly.", score: 50 },
          { value: "regularly", label: "Regularly", description: "Conversion data is reviewed for active roles.", score: 82 },
          { value: "managed", label: "Managed closely", description: "Conversion is tracked and used to correct problems quickly.", score: 100 },
        ],
      },
    ],
  },
  {
    id: "hiring-manager-alignment",
    title: "Hiring manager alignment",
    strapline: "How well hiring managers support pace, clarity and decision quality",
    summary:
      "Manager alignment affects speed, shortlist quality and the credibility of the whole process.",
    questions: [
      {
        id: "managerBriefQuality",
        type: "select",
        label: "How strong is hiring manager input at brief stage?",
        description: "This covers clarity, responsiveness and decision ownership.",
        options: [
          { value: "weak", label: "Weak", description: "Managers provide incomplete or shifting input.", score: 20 },
          { value: "mixed", label: "Mixed", description: "Some managers engage well, others slow the process down.", score: 55 },
          { value: "good", label: "Good", description: "Managers usually provide workable, timely input.", score: 82 },
          { value: "strong", label: "Strong", description: "Managers are clear, engaged and aligned from the start.", score: 100 },
        ],
      },
      {
        id: "managerFeedbackDays",
        type: "number",
        label: "How quickly do hiring managers return interview feedback?",
        description: "Use average turnaround in days.",
        min: 0,
        max: 20,
        step: 1,
        unit: "days",
        placeholder: "2",
      },
      {
        id: "managerCommitment",
        type: "select",
        label: "How reliably do hiring managers keep the process moving?",
        description: "Consider scheduling discipline, feedback quality and ownership.",
        options: [
          { value: "low", label: "Low", description: "Managers cause avoidable delay and inconsistency.", score: 20 },
          { value: "variable", label: "Variable", description: "Commitment depends on team or individual.", score: 55 },
          { value: "good", label: "Good", description: "Managers usually keep pace and take ownership.", score: 82 },
          { value: "high", label: "High", description: "Managers actively support fast, consistent hiring.", score: 100 },
        ],
      },
    ],
  },
];

export const scorePalette = {
  red: {
    text: "#991b1b",
    soft: "#fee2e2",
    line: "#fca5a5",
  },
  amber: {
    text: "#92400e",
    soft: "#fef3c7",
    line: "#fbbf24",
  },
  green: {
    text: "#166534",
    soft: "#dcfce7",
    line: "#4ade80",
  },
  ink: {
    text: "#111827",
    soft: "#f3f4f6",
    line: "#d1d5db",
  },
} as const;

export function getSectionById(sectionId: string): AuditSection | undefined {
  return auditSections.find((section) => section.id === sectionId);
}
