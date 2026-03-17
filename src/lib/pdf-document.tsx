import React from "react";
import { Document, Page, StyleSheet, Text, View } from "@react-pdf/renderer";

import type {
  AuditReport,
  BenchmarkRow,
  MethodologyRow,
  PriorityMatrixEntry,
  ScoreStatus,
  SectionReport,
} from "@/lib/scoring";

const BRAND_NAVY = "#1f2a40";
const BRAND_GOLD = "#b5935a";
const BRAND_CHARCOAL = "#1c2430";
const BRAND_GREY = "#6b7280";
const BRAND_LINE = "#d8dce3";
const BRAND_PANEL = "#f7f5f1";

const styles = StyleSheet.create({
  coverPage: {
    paddingTop: 58,
    paddingBottom: 52,
    paddingHorizontal: 56,
    backgroundColor: "#ffffff",
    color: BRAND_CHARCOAL,
    fontFamily: "Helvetica",
  },
  page: {
    paddingTop: 72,
    paddingBottom: 54,
    paddingHorizontal: 48,
    backgroundColor: "#ffffff",
    color: BRAND_CHARCOAL,
    fontSize: 10,
    fontFamily: "Helvetica",
    lineHeight: 1.55,
  },
  header: {
    position: "absolute",
    top: 24,
    left: 48,
    right: 48,
    paddingBottom: 10,
    borderBottomWidth: 1,
    borderBottomColor: BRAND_LINE,
    flexDirection: "row",
    justifyContent: "space-between",
  },
  headerBrand: {
    fontSize: 9,
    fontFamily: "Helvetica-Bold",
    color: BRAND_NAVY,
    textTransform: "uppercase",
    letterSpacing: 1.2,
  },
  headerMeta: {
    fontSize: 8.5,
    color: BRAND_GREY,
  },
  footer: {
    position: "absolute",
    left: 48,
    right: 48,
    bottom: 20,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: BRAND_LINE,
    flexDirection: "row",
    justifyContent: "space-between",
    fontSize: 8.5,
    color: BRAND_GREY,
  },
  coverBrand: {
    fontSize: 13,
    fontFamily: "Helvetica-Bold",
    color: BRAND_NAVY,
    textTransform: "uppercase",
    letterSpacing: 1.4,
    marginBottom: 16,
  },
  coverRule: {
    width: 120,
    height: 2,
    backgroundColor: BRAND_GOLD,
    marginBottom: 30,
  },
  coverMonogram: {
    width: 54,
    height: 54,
    borderRadius: 27,
    borderWidth: 1,
    borderColor: BRAND_GOLD,
    color: BRAND_NAVY,
    textAlign: "center",
    fontFamily: "Helvetica-Bold",
    fontSize: 20,
    lineHeight: 2.55,
    marginBottom: 24,
  },
  coverTitle: {
    fontSize: 27,
    lineHeight: 1.18,
    fontFamily: "Helvetica-Bold",
    color: BRAND_NAVY,
    marginBottom: 12,
  },
  coverSubTitle: {
    fontSize: 12,
    lineHeight: 1.7,
    color: BRAND_GREY,
    marginBottom: 30,
    maxWidth: "90%",
  },
  coverMetaBlock: {
    marginTop: 18,
    borderTopWidth: 1,
    borderTopColor: BRAND_LINE,
  },
  coverMetaRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingTop: 10,
    paddingBottom: 10,
    borderBottomWidth: 1,
    borderBottomColor: BRAND_LINE,
  },
  coverMetaLabel: {
    width: "35%",
    color: BRAND_GREY,
    fontSize: 10,
  },
  coverMetaValue: {
    width: "62%",
    textAlign: "right",
    fontSize: 10,
    fontFamily: "Helvetica-Bold",
    color: BRAND_CHARCOAL,
  },
  coverFooter: {
    position: "absolute",
    left: 56,
    right: 56,
    bottom: 26,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: BRAND_LINE,
    flexDirection: "row",
    justifyContent: "space-between",
    fontSize: 8.5,
    color: BRAND_GREY,
  },
  letterBlock: {
    marginTop: 18,
  },
  letterSignature: {
    marginTop: 20,
  },
  h1: {
    fontSize: 24,
    fontFamily: "Helvetica-Bold",
    color: BRAND_NAVY,
    marginBottom: 10,
  },
  h2: {
    fontSize: 18,
    fontFamily: "Helvetica-Bold",
    color: BRAND_NAVY,
    marginBottom: 10,
  },
  h3: {
    fontSize: 13,
    fontFamily: "Helvetica-Bold",
    color: BRAND_NAVY,
    marginBottom: 6,
  },
  body: {
    fontSize: 10,
    lineHeight: 1.6,
    marginBottom: 10,
    color: BRAND_CHARCOAL,
  },
  muted: {
    color: BRAND_GREY,
  },
  heroPanel: {
    borderWidth: 1,
    borderColor: BRAND_LINE,
    backgroundColor: BRAND_PANEL,
    borderRadius: 14,
    padding: 18,
    marginBottom: 18,
  },
  heroTop: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 12,
  },
  scoreValue: {
    fontSize: 38,
    fontFamily: "Helvetica-Bold",
  },
  scoreLabel: {
    fontSize: 9,
    textTransform: "uppercase",
    color: BRAND_GREY,
    marginBottom: 4,
    letterSpacing: 1.1,
  },
  pill: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 999,
    fontSize: 8.5,
    fontFamily: "Helvetica-Bold",
    textTransform: "uppercase",
    alignSelf: "flex-start",
  },
  progressTrack: {
    height: 8,
    borderRadius: 999,
    backgroundColor: "#e6e9ef",
    overflow: "hidden",
    marginBottom: 10,
  },
  progressFill: {
    height: 8,
    borderRadius: 999,
  },
  statGrid: {
    flexDirection: "row",
    marginTop: 8,
    marginBottom: 18,
  },
  statCard: {
    flex: 1,
    borderWidth: 1,
    borderColor: BRAND_LINE,
    borderRadius: 12,
    backgroundColor: "#ffffff",
    padding: 12,
    marginRight: 10,
  },
  statCardLast: {
    marginRight: 0,
  },
  statLabel: {
    fontSize: 8.5,
    fontFamily: "Helvetica-Bold",
    textTransform: "uppercase",
    color: BRAND_GREY,
    marginBottom: 5,
    letterSpacing: 0.9,
  },
  statValue: {
    fontSize: 12,
    fontFamily: "Helvetica-Bold",
    color: BRAND_NAVY,
    marginBottom: 4,
  },
  insightCard: {
    borderWidth: 1,
    borderColor: BRAND_LINE,
    borderRadius: 12,
    backgroundColor: "#ffffff",
    padding: 12,
    marginBottom: 10,
  },
  table: {
    borderWidth: 1,
    borderColor: BRAND_LINE,
    borderRadius: 12,
    overflow: "hidden",
    marginBottom: 16,
  },
  tableHeader: {
    flexDirection: "row",
    backgroundColor: BRAND_NAVY,
    paddingTop: 8,
    paddingBottom: 8,
    paddingHorizontal: 10,
  },
  tableHeaderText: {
    fontSize: 8.5,
    fontFamily: "Helvetica-Bold",
    color: "#ffffff",
    textTransform: "uppercase",
    letterSpacing: 0.8,
  },
  tableRow: {
    flexDirection: "row",
    paddingTop: 9,
    paddingBottom: 9,
    paddingHorizontal: 10,
    borderTopWidth: 1,
    borderTopColor: BRAND_LINE,
  },
  tableRowAlt: {
    backgroundColor: "#fafafb",
  },
  cellText: {
    fontSize: 9,
    color: BRAND_CHARCOAL,
    lineHeight: 1.45,
  },
  cellStrong: {
    fontFamily: "Helvetica-Bold",
  },
  matrixCard: {
    borderWidth: 1,
    borderColor: BRAND_LINE,
    borderRadius: 12,
    padding: 12,
    marginBottom: 10,
  },
  chartPanel: {
    borderWidth: 1,
    borderColor: BRAND_LINE,
    borderRadius: 12,
    padding: 12,
    marginBottom: 12,
    backgroundColor: "#ffffff",
  },
  chartRow: {
    marginBottom: 8,
  },
  chartLabelRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 4,
  },
  chartLabel: {
    fontSize: 8.5,
    color: BRAND_CHARCOAL,
    width: "62%",
  },
  chartValue: {
    fontSize: 8.5,
    fontFamily: "Helvetica-Bold",
    color: BRAND_CHARCOAL,
  },
  chartTrack: {
    height: 7,
    borderRadius: 999,
    backgroundColor: "#e6e9ef",
    overflow: "hidden",
  },
  chartFill: {
    height: 7,
    borderRadius: 999,
  },
  findingsBlock: {
    borderWidth: 1,
    borderColor: BRAND_LINE,
    borderRadius: 14,
    padding: 14,
    marginBottom: 14,
    backgroundColor: "#ffffff",
  },
  findingsHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 10,
  },
  findingsTitleWrap: {
    width: "72%",
  },
  findingsTitle: {
    fontSize: 14,
    fontFamily: "Helvetica-Bold",
    color: BRAND_NAVY,
    marginBottom: 4,
  },
  findingsStrapline: {
    fontSize: 8.8,
    color: BRAND_GREY,
  },
  findingsBadge: {
    width: 82,
    paddingVertical: 9,
    paddingHorizontal: 8,
    borderRadius: 12,
    alignItems: "center",
  },
  findingsBadgeScore: {
    fontSize: 18,
    fontFamily: "Helvetica-Bold",
  },
  findingsBadgeLabel: {
    fontSize: 8.5,
    marginTop: 2,
  },
  findingsDiagnosis: {
    fontSize: 10.5,
    fontFamily: "Helvetica-Bold",
    color: BRAND_NAVY,
    marginBottom: 8,
  },
  findingsPanel: {
    borderWidth: 1,
    borderColor: BRAND_LINE,
    borderRadius: 10,
    backgroundColor: BRAND_PANEL,
    padding: 10,
    marginBottom: 8,
  },
  listItem: {
    fontSize: 9.5,
    lineHeight: 1.5,
    marginBottom: 4,
  },
  roadmapGrid: {
    flexDirection: "row",
    marginBottom: 16,
  },
  roadmapColumn: {
    flex: 1,
    marginRight: 10,
  },
  roadmapColumnLast: {
    marginRight: 0,
  },
  verdictPanel: {
    borderWidth: 1,
    borderColor: BRAND_GOLD,
    backgroundColor: "#fbf8f2",
    borderRadius: 14,
    padding: 16,
    marginTop: 8,
  },
});

function statusColours(status: ScoreStatus) {
  if (status === "green") {
    return { text: "#166534", background: "#dcfce7", line: "#4ade80" };
  }
  if (status === "amber") {
    return { text: "#9a6700", background: "#fef3c7", line: "#f59e0b" };
  }
  return { text: "#991b1b", background: "#fee2e2", line: "#ef4444" };
}

function statusLabel(status: ScoreStatus) {
  if (status === "green") {
    return "Strong";
  }
  if (status === "amber") {
    return "Needs work";
  }
  return "Critical";
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date(value));
}

function PageChrome() {
  return (
    <>
      <View fixed style={styles.header}>
        <Text style={styles.headerBrand}>Bradford & Marsh Consulting</Text>
        <Text style={styles.headerMeta}>Recruitment Operating Model Audit</Text>
      </View>
      <View fixed style={styles.footer}>
        <Text>Confidential client report</Text>
        <Text render={({ pageNumber, totalPages }) => `Page ${pageNumber} of ${totalPages}`} />
      </View>
    </>
  );
}

function ScorePill({ score, status }: { score: number; status: ScoreStatus }) {
  const colours = statusColours(status);
  return (
    <View style={[styles.pill, { backgroundColor: colours.background }]}>
      <Text style={{ color: colours.text }}>{score}/100</Text>
    </View>
  );
}

function ScoreSummaryTable({ rows }: { rows: AuditReport["scoreSummary"] }) {
  return (
    <View style={styles.table}>
      <View style={styles.tableHeader}>
        <Text style={[styles.tableHeaderText, { width: "70%" }]}>Area</Text>
        <Text style={[styles.tableHeaderText, { width: "30%", textAlign: "right" }]}>Score</Text>
      </View>
      {rows.map((row, index) => {
        const colours = statusColours(row.status);
        return (
          <View key={row.title} style={[styles.tableRow, index % 2 === 1 ? styles.tableRowAlt : {}]}>
            <Text style={[styles.cellText, { width: "70%" }]}>{row.title}</Text>
            <Text style={[styles.cellText, styles.cellStrong, { width: "30%", textAlign: "right", color: colours.text }]}>
              {row.score}/100
            </Text>
          </View>
        );
      })}
    </View>
  );
}

function MethodologyTable({ rows }: { rows: MethodologyRow[] }) {
  return (
    <View style={styles.table}>
      <View style={styles.tableHeader}>
        <Text style={[styles.tableHeaderText, { width: "20%" }]}>Band</Text>
        <Text style={[styles.tableHeaderText, { width: "24%" }]}>Interpretation</Text>
        <Text style={[styles.tableHeaderText, { width: "56%" }]}>Typical implication</Text>
      </View>
      {rows.map((row, index) => (
        <View key={row.band} style={[styles.tableRow, index % 2 === 1 ? styles.tableRowAlt : {}]}>
          <Text style={[styles.cellText, styles.cellStrong, { width: "20%" }]}>{row.band}</Text>
          <Text style={[styles.cellText, { width: "24%" }]}>{row.interpretation}</Text>
          <Text style={[styles.cellText, { width: "56%" }]}>{row.implication}</Text>
        </View>
      ))}
    </View>
  );
}

function BenchmarkTable({ rows }: { rows: BenchmarkRow[] }) {
  return (
    <View style={styles.table}>
      <View style={styles.tableHeader}>
        <Text style={[styles.tableHeaderText, { width: "28%" }]}>Metric</Text>
        <Text style={[styles.tableHeaderText, { width: "18%" }]}>Client</Text>
        <Text style={[styles.tableHeaderText, { width: "18%" }]}>Target</Text>
        <Text style={[styles.tableHeaderText, { width: "36%" }]}>Comment</Text>
      </View>
      {rows.map((row, index) => {
        const colours = statusColours(row.status);
        return (
          <View key={row.metric} style={[styles.tableRow, index % 2 === 1 ? styles.tableRowAlt : {}]}>
            <Text style={[styles.cellText, styles.cellStrong, { width: "28%" }]}>{row.metric}</Text>
            <Text style={[styles.cellText, { width: "18%", color: colours.text }]}>{row.client}</Text>
            <Text style={[styles.cellText, { width: "18%" }]}>{row.target}</Text>
            <Text style={[styles.cellText, { width: "36%" }]}>{row.comment}</Text>
          </View>
        );
      })}
    </View>
  );
}

function PriorityMatrix({ rows }: { rows: PriorityMatrixEntry[] }) {
  return (
    <View>
      {rows.map((row) => {
        const colours = statusColours(row.status);
        return (
          <View key={row.priorityArea} style={[styles.matrixCard, { backgroundColor: colours.background }]}>
            <Text style={[styles.h3, { marginBottom: 4 }]}>{row.priorityArea}</Text>
            <Text style={[styles.body, { marginBottom: 6 }]}>
              {row.urgency} priority. {row.impact} impact.
            </Text>
            <Text style={[styles.body, { marginBottom: 6 }]}>{row.whyItMatters}</Text>
            <Text style={[styles.body, styles.muted]}>First move: {row.firstMove}</Text>
          </View>
        );
      })}
    </View>
  );
}

function SectionScoreChart({ sections }: { sections: SectionReport[] }) {
  return (
    <View style={styles.chartPanel}>
      <Text style={styles.h3}>Section score profile</Text>
      {sections.map((section) => {
        const colours = statusColours(section.status);
        return (
          <View key={section.id} style={styles.chartRow}>
            <View style={styles.chartLabelRow}>
              <Text style={styles.chartLabel}>{section.title}</Text>
              <Text style={styles.chartValue}>{section.score}/100</Text>
            </View>
            <View style={styles.chartTrack}>
              <View style={[styles.chartFill, { width: `${section.score}%`, backgroundColor: colours.line }]} />
            </View>
          </View>
        );
      })}
    </View>
  );
}

function BandDistributionChart({ sections }: { sections: SectionReport[] }) {
  const distribution = [
    { label: "Green sections", value: sections.filter((section) => section.status === "green").length, total: sections.length, status: "green" as ScoreStatus },
    { label: "Amber sections", value: sections.filter((section) => section.status === "amber").length, total: sections.length, status: "amber" as ScoreStatus },
    { label: "Red sections", value: sections.filter((section) => section.status === "red").length, total: sections.length, status: "red" as ScoreStatus },
  ];

  return (
    <View style={styles.chartPanel}>
      <Text style={styles.h3}>Score distribution</Text>
      {distribution.map((item) => {
        const colours = statusColours(item.status);
        const width = item.total ? `${(item.value / item.total) * 100}%` : "0%";
        return (
          <View key={item.label} style={styles.chartRow}>
            <View style={styles.chartLabelRow}>
              <Text style={styles.chartLabel}>{item.label}</Text>
              <Text style={styles.chartValue}>
                {item.value} of {item.total}
              </Text>
            </View>
            <View style={styles.chartTrack}>
              <View style={[styles.chartFill, { width, backgroundColor: colours.line }]} />
            </View>
          </View>
        );
      })}
    </View>
  );
}

function FindingsCard({ section }: { section: SectionReport }) {
  const colours = statusColours(section.status);

  return (
    <View style={styles.findingsBlock} wrap={false}>
      <View style={styles.findingsHeader}>
        <View style={styles.findingsTitleWrap}>
          <Text style={styles.findingsTitle}>{section.title}</Text>
          <Text style={styles.findingsStrapline}>{section.strapline}</Text>
        </View>
        <View style={[styles.findingsBadge, { backgroundColor: colours.background }]}>
          <Text style={[styles.findingsBadgeScore, { color: colours.text }]}>{section.score}</Text>
          <Text style={[styles.findingsBadgeLabel, { color: colours.text }]}>{statusLabel(section.status)}</Text>
        </View>
      </View>

      <Text style={styles.findingsDiagnosis}>{section.headlineDiagnosis}</Text>

      <View style={styles.findingsPanel}>
        <Text style={styles.h3}>Current State</Text>
        <Text style={styles.body}>{section.currentState}</Text>
      </View>

      <View style={styles.findingsPanel}>
        <Text style={styles.h3}>Key Risks</Text>
        {section.keyRisks.map((risk) => (
          <Text key={risk} style={styles.listItem}>
            • {risk}
          </Text>
        ))}
      </View>

      <View style={styles.findingsPanel}>
        <Text style={styles.h3}>Commercial Impact</Text>
        <Text style={styles.body}>{section.commercialImpact}</Text>
      </View>

      <View style={styles.findingsPanel}>
        <Text style={styles.h3}>Immediate Actions</Text>
        {section.immediateActions.map((action) => (
          <Text key={action} style={styles.listItem}>
            • {action}
          </Text>
        ))}
      </View>

      <View style={styles.findingsPanel}>
        <Text style={styles.h3}>Structural Improvements</Text>
        {section.structuralImprovements.map((item) => (
          <Text key={item} style={styles.listItem}>
            • {item}
          </Text>
        ))}
      </View>
    </View>
  );
}

function chunkSections<T>(items: T[], size: number): T[][] {
  const chunks: T[][] = [];
  for (let index = 0; index < items.length; index += size) {
    chunks.push(items.slice(index, index + size));
  }
  return chunks;
}

export function AuditPdfDocument({ report }: { report: AuditReport }) {
  const overallColours = statusColours(report.overallStatus);
  const findingsPages = chunkSections(report.sections, 3);

  return (
    <Document title={`${report.profile.companyName} Recruitment Audit`}>
      <Page size="A4" style={styles.coverPage}>
        <Text style={styles.coverBrand}>Bradford & Marsh Consulting</Text>
        <View style={styles.coverRule} />
        <Text style={styles.coverMonogram}>B&amp;M</Text>
        <Text style={styles.coverTitle}>Recruitment Operating Model Audit</Text>
        <Text style={styles.coverSubTitle}>
          A structured review of how the recruitment process is operating today, where delivery is drifting, and what leadership should correct first.
        </Text>

        <View style={styles.coverMetaBlock}>
          <View style={styles.coverMetaRow}>
            <Text style={styles.coverMetaLabel}>Client</Text>
            <Text style={styles.coverMetaValue}>{report.profile.companyName}</Text>
          </View>
          <View style={styles.coverMetaRow}>
            <Text style={styles.coverMetaLabel}>Prepared for</Text>
            <Text style={styles.coverMetaValue}>{report.profile.contactName}</Text>
          </View>
          <View style={styles.coverMetaRow}>
            <Text style={styles.coverMetaLabel}>Role</Text>
            <Text style={styles.coverMetaValue}>{report.profile.contactRole}</Text>
          </View>
          <View style={styles.coverMetaRow}>
            <Text style={styles.coverMetaLabel}>Sector</Text>
            <Text style={styles.coverMetaValue}>{report.profile.sector}</Text>
          </View>
          <View style={styles.coverMetaRow}>
            <Text style={styles.coverMetaLabel}>Location</Text>
            <Text style={styles.coverMetaValue}>{report.profile.location}</Text>
          </View>
          <View style={styles.coverMetaRow}>
            <Text style={styles.coverMetaLabel}>Date</Text>
            <Text style={styles.coverMetaValue}>{formatDate(report.generatedAt)}</Text>
          </View>
        </View>

        <View style={styles.coverFooter}>
          <Text>Confidential</Text>
          <Text>Prepared by Bradford & Marsh Consulting</Text>
        </View>
      </Page>

      <Page size="A4" style={styles.page}>
        <PageChrome />
        <Text style={styles.h1}>Introductory letter</Text>
        <View style={styles.letterBlock}>
          <Text style={styles.body}>Michael Marsh</Text>
          <Text style={[styles.body, styles.muted]}>Managing Director</Text>
          <Text style={[styles.body, styles.muted]}>Bradford &amp; Marsh Consulting</Text>
        </View>
        <View style={styles.letterBlock}>
          <Text style={styles.body}>{report.letter.salutation}</Text>
          {report.letter.paragraphs.map((paragraph) => (
            <Text key={paragraph} style={styles.body}>
              {paragraph}
            </Text>
          ))}
        </View>
        <View style={styles.letterSignature}>
          <Text style={styles.body}>{report.letter.signatureName}</Text>
          <Text style={[styles.body, styles.muted]}>{report.letter.signatureTitle}</Text>
        </View>
      </Page>

      <Page size="A4" style={styles.page}>
        <PageChrome />
        <Text style={styles.h1}>Executive overview</Text>
        <Text style={styles.body}>{report.executiveSummary}</Text>

        <View style={styles.heroPanel}>
          <View style={styles.heroTop}>
            <View>
              <Text style={styles.scoreLabel}>Overall score</Text>
              <Text style={[styles.scoreValue, { color: overallColours.text }]}>{report.overallScore}/100</Text>
            </View>
            <View>
              <Text style={styles.scoreLabel}>Rating band</Text>
              <View style={[styles.pill, { backgroundColor: overallColours.background }]}>
                <Text style={{ color: overallColours.text }}>{report.ratingBand}</Text>
              </View>
            </View>
          </View>
          <View style={styles.progressTrack}>
            <View style={[styles.progressFill, { width: `${report.overallScore}%`, backgroundColor: overallColours.line }]} />
          </View>
          <Text style={styles.body}>{report.scoreMeaning}</Text>
        </View>

        <View style={styles.statGrid}>
          <View style={styles.statCard}>
            <Text style={styles.statLabel}>Strongest area</Text>
            <Text style={styles.statValue}>{report.strongestArea.title}</Text>
            <ScorePill score={report.strongestArea.score} status={report.strongestArea.status} />
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statLabel}>Weakest area</Text>
            <Text style={styles.statValue}>{report.weakestArea.title}</Text>
            <ScorePill score={report.weakestArea.score} status={report.weakestArea.status} />
          </View>
          <View style={[styles.statCard, styles.statCardLast]}>
            <Text style={styles.statLabel}>Primary diagnosis</Text>
            <Text style={styles.body}>{report.primaryDiagnosis}</Text>
          </View>
        </View>

        <Text style={styles.h2}>Key insight panel</Text>
        {report.topIssues.slice(0, 3).map((issue) => (
          <View key={issue.id} style={styles.insightCard}>
            <View style={styles.heroTop}>
              <Text style={styles.h3}>{issue.title}</Text>
              <ScorePill score={issue.score} status={issue.status} />
            </View>
            <Text style={styles.body}>{issue.headlineDiagnosis}</Text>
          </View>
        ))}
      </Page>

      <Page size="A4" style={styles.page}>
        <PageChrome />
        <Text style={styles.h1}>Score summary</Text>
        <ScoreSummaryTable rows={report.scoreSummary} />

        <Text style={styles.h2}>Scoring methodology</Text>
        <Text style={styles.body}>
          The audit scores each operating area out of 100 using the submitted process inputs and current-state hiring data. Higher scores indicate more repeatable control, better delivery discipline and lower operating risk.
        </Text>
        <MethodologyTable rows={report.scoringMethodology} />

        <Text style={styles.h2}>Benchmark snapshot</Text>
        <BenchmarkTable rows={report.benchmarkSnapshot} />
      </Page>

      <Page size="A4" style={styles.page}>
        <PageChrome />
        <Text style={styles.h1}>Priority matrix</Text>
        <Text style={styles.body}>
          The areas below are the most commercially important improvement points based on the lowest scores and the likely effect on hiring pace, decision quality and candidate conversion.
        </Text>
        <PriorityMatrix rows={report.priorityMatrix} />

        <Text style={styles.h2}>Charts and visual analysis</Text>
        <SectionScoreChart sections={report.sections} />
        <BandDistributionChart sections={report.sections} />
        {report.visualAnalysisNotes.map((note) => (
          <Text key={note} style={styles.body}>
            {note}
          </Text>
        ))}
      </Page>

      {findingsPages.map((pageSections, index) => (
        <Page key={`findings-${index}`} size="A4" style={styles.page}>
          <PageChrome />
          <Text style={styles.h1}>{index === 0 ? "Detailed findings" : "Detailed findings continued"}</Text>
          {pageSections.map((section) => (
            <FindingsCard key={section.id} section={section} />
          ))}
        </Page>
      ))}

      <Page size="A4" style={styles.page}>
        <PageChrome />
        <Text style={styles.h1}>Priorities and roadmap</Text>

        <View style={styles.roadmapGrid}>
          <View style={styles.roadmapColumn}>
            <Text style={styles.h2}>Top 5 strengths</Text>
            {report.topStrengths.map((item) => (
              <View key={item} style={styles.insightCard}>
                <Text style={styles.body}>{item}</Text>
              </View>
            ))}
          </View>
          <View style={[styles.roadmapColumn, styles.roadmapColumnLast]}>
            <Text style={styles.h2}>Top 5 problems</Text>
            {report.topProblems.map((item) => (
              <View key={item} style={styles.insightCard}>
                <Text style={styles.body}>{item}</Text>
              </View>
            ))}
          </View>
        </View>

        <Text style={styles.h2}>30 day plan</Text>
        {report.day30Plan.map((item) => (
          <Text key={item} style={styles.listItem}>
            • {item}
          </Text>
        ))}

        <Text style={[styles.h2, { marginTop: 8 }]}>60 day plan</Text>
        {report.day60Plan.map((item) => (
          <Text key={item} style={styles.listItem}>
            • {item}
          </Text>
        ))}

        <Text style={[styles.h2, { marginTop: 8 }]}>90 day plan</Text>
        {report.day90Plan.map((item) => (
          <Text key={item} style={styles.listItem}>
            • {item}
          </Text>
        ))}

        <Text style={[styles.h2, { marginTop: 12 }]}>Final verdict</Text>
        <View style={styles.verdictPanel}>
          <Text style={styles.body}>{report.finalVerdict}</Text>
          <Text style={[styles.h3, { marginTop: 6 }]}>Recommended next step</Text>
          <Text style={styles.body}>{report.recommendedNextStep}</Text>
        </View>
      </Page>
    </Document>
  );
}
