import React from "react";
import {
  Document,
  Page,
  StyleSheet,
  Text,
  View,
} from "@react-pdf/renderer";

import type { AuditReport, ScoreStatus, SectionReport } from "@/lib/scoring";

const styles = StyleSheet.create({
  page: {
    paddingTop: 44,
    paddingBottom: 44,
    paddingHorizontal: 44,
    backgroundColor: "#ffffff",
    color: "#111827",
    fontSize: 10.5,
    fontFamily: "Helvetica",
    lineHeight: 1.5,
  },
  coverPage: {
    paddingTop: 64,
    paddingBottom: 56,
    paddingHorizontal: 52,
    backgroundColor: "#ffffff",
    color: "#111827",
    fontFamily: "Helvetica",
  },
  coverBrand: {
    fontSize: 14,
    letterSpacing: 1.2,
    textTransform: "uppercase",
    marginBottom: 12,
  },
  coverRule: {
    width: 120,
    height: 2,
    backgroundColor: "#d1d5db",
    marginBottom: 30,
  },
  coverTitle: {
    fontSize: 26,
    lineHeight: 1.2,
    fontFamily: "Helvetica-Bold",
    marginBottom: 18,
  },
  coverMetaBlock: {
    marginTop: 28,
    gap: 10,
  },
  coverMetaRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    borderBottomWidth: 1,
    borderBottomColor: "#e5e7eb",
    paddingBottom: 8,
  },
  coverMetaLabel: {
    color: "#6b7280",
    width: "36%",
  },
  coverMetaValue: {
    width: "62%",
    textAlign: "right",
    fontFamily: "Helvetica-Bold",
  },
  coverFooter: {
    position: "absolute",
    left: 52,
    right: 52,
    bottom: 42,
    borderTopWidth: 1,
    borderTopColor: "#e5e7eb",
    paddingTop: 14,
    color: "#6b7280",
    fontSize: 9,
    flexDirection: "row",
    justifyContent: "space-between",
  },
  sectionTitle: {
    fontFamily: "Helvetica-Bold",
    fontSize: 18,
    marginBottom: 10,
  },
  bodyText: {
    marginBottom: 10,
  },
  mutedText: {
    color: "#6b7280",
  },
  scoreHero: {
    borderWidth: 1,
    borderColor: "#e5e7eb",
    borderRadius: 12,
    padding: 18,
    marginBottom: 18,
  },
  scoreRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  scoreValue: {
    fontFamily: "Helvetica-Bold",
    fontSize: 28,
  },
  statusPill: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
    fontSize: 9,
    fontFamily: "Helvetica-Bold",
    textTransform: "uppercase",
  },
  progressTrack: {
    height: 8,
    borderRadius: 999,
    backgroundColor: "#eef2f7",
    overflow: "hidden",
    marginBottom: 10,
  },
  progressFill: {
    height: 8,
    borderRadius: 999,
  },
  label: {
    fontFamily: "Helvetica-Bold",
    fontSize: 10,
    marginBottom: 4,
  },
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
  },
  card: {
    borderWidth: 1,
    borderColor: "#e5e7eb",
    borderRadius: 12,
    padding: 14,
    backgroundColor: "#ffffff",
  },
  scoreCard: {
    width: "48%",
  },
  scoreCardTitle: {
    fontFamily: "Helvetica-Bold",
    marginBottom: 4,
  },
  scoreCardValue: {
    fontFamily: "Helvetica-Bold",
    fontSize: 20,
    marginBottom: 6,
  },
  issueBlock: {
    borderWidth: 1,
    borderColor: "#e5e7eb",
    borderRadius: 12,
    padding: 12,
    backgroundColor: "#f8fafc",
    marginBottom: 10,
  },
  sectionBlock: {
    borderWidth: 1,
    borderColor: "#e5e7eb",
    borderRadius: 14,
    padding: 16,
    marginBottom: 14,
  },
  sectionHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 10,
  },
  sectionName: {
    width: "72%",
  },
  sectionNameText: {
    fontFamily: "Helvetica-Bold",
    fontSize: 14,
    marginBottom: 3,
  },
  sectionStrapline: {
    color: "#6b7280",
    fontSize: 9.5,
  },
  sectionScoreBox: {
    width: 78,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#e5e7eb",
    borderRadius: 12,
    paddingVertical: 10,
    paddingHorizontal: 8,
  },
  sectionScoreValue: {
    fontFamily: "Helvetica-Bold",
    fontSize: 18,
  },
  sectionMiniLabel: {
    fontFamily: "Helvetica-Bold",
    fontSize: 9,
    marginBottom: 4,
  },
  listBlock: {
    marginBottom: 10,
  },
  listItem: {
    marginBottom: 6,
  },
  finalNote: {
    borderWidth: 1,
    borderColor: "#e5e7eb",
    borderRadius: 12,
    padding: 16,
    marginTop: 8,
  },
  statGrid: {
    flexDirection: "row",
    gap: 10,
    marginTop: 10,
    marginBottom: 18,
  },
  statCard: {
    flex: 1,
    borderWidth: 1,
    borderColor: "#e5e7eb",
    borderRadius: 12,
    padding: 12,
    backgroundColor: "#f9fafb",
  },
  statLabel: {
    fontSize: 8.5,
    color: "#6b7280",
    textTransform: "uppercase",
    marginBottom: 5,
    fontFamily: "Helvetica-Bold",
  },
  statValue: {
    fontSize: 12,
    fontFamily: "Helvetica-Bold",
    marginBottom: 4,
  },
  metricGrid: {
    flexDirection: "row",
    gap: 10,
    marginTop: 10,
    marginBottom: 18,
  },
  metricColumn: {
    flex: 1,
  },
  matrixGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
    marginTop: 10,
  },
  matrixCell: {
    width: "48%",
    borderWidth: 1,
    borderColor: "#e5e7eb",
    borderRadius: 12,
    padding: 12,
  },
  matrixTitle: {
    fontSize: 8.5,
    fontFamily: "Helvetica-Bold",
    textTransform: "uppercase",
    marginBottom: 6,
  },
  matrixItem: {
    borderRadius: 10,
    backgroundColor: "#ffffff",
    paddingVertical: 8,
    paddingHorizontal: 10,
    marginTop: 6,
  },
  scoreRowCard: {
    width: "48%",
    borderWidth: 1,
    borderColor: "#e5e7eb",
    borderRadius: 12,
    padding: 12,
    marginBottom: 8,
  },
  scoreBarTrack: {
    height: 6,
    borderRadius: 999,
    backgroundColor: "#e5e7eb",
    overflow: "hidden",
    marginTop: 8,
  },
  scoreBarFill: {
    height: 6,
    borderRadius: 999,
  },
});

function statusColours(status: ScoreStatus) {
  if (status === "green") {
    return { text: "#166534", background: "#dcfce7", line: "#4ade80" };
  }
  if (status === "amber") {
    return { text: "#92400e", background: "#fef3c7", line: "#f59e0b" };
  }
  return { text: "#991b1b", background: "#fee2e2", line: "#f87171" };
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

function ScoreOverviewRow({ section }: { section: SectionReport }) {
  const colours = statusColours(section.status);

  return (
    <View style={styles.scoreRowCard}>
      <View style={styles.scoreRow}>
        <Text style={styles.scoreCardTitle}>{section.title}</Text>
        <Text style={[styles.label, { color: colours.text }]}>{section.score}/100</Text>
      </View>
      <View style={styles.scoreBarTrack}>
        <View style={[styles.scoreBarFill, { width: `${section.score}%`, backgroundColor: colours.line }]} />
      </View>
    </View>
  );
}

function DetailSection({ section }: { section: SectionReport }) {
  const colours = statusColours(section.status);

  return (
    <View style={styles.sectionBlock} wrap={false}>
      <View style={styles.sectionHeader}>
        <View style={styles.sectionName}>
          <Text style={styles.sectionNameText}>{section.title}</Text>
          <Text style={styles.sectionStrapline}>{section.strapline}</Text>
        </View>
        <View style={[styles.sectionScoreBox, { backgroundColor: colours.background }]}>
          <Text style={[styles.sectionScoreValue, { color: colours.text }]}>{section.score}</Text>
          <Text>{statusLabel(section.status)}</Text>
        </View>
      </View>

      <View style={styles.listBlock}>
        <Text style={styles.sectionMiniLabel}>Current State</Text>
        <Text>{section.currentState}</Text>
      </View>

      <View style={styles.listBlock}>
        <Text style={styles.sectionMiniLabel}>Key Risks</Text>
        {section.keyRisks.map((risk) => (
          <Text key={risk} style={styles.listItem}>
            • {risk}
          </Text>
        ))}
      </View>

      <View style={styles.listBlock}>
        <Text style={styles.sectionMiniLabel}>Commercial Impact</Text>
        <Text>{section.commercialImpact}</Text>
      </View>

      <View style={styles.listBlock}>
        <Text style={styles.sectionMiniLabel}>Immediate Actions</Text>
        {section.immediateActions.map((action) => (
          <Text key={action} style={styles.listItem}>
            • {action}
          </Text>
        ))}
      </View>

      <View>
        <Text style={styles.sectionMiniLabel}>Consultant note</Text>
        <Text>{section.consultantNote}</Text>
      </View>
    </View>
  );
}

export function AuditPdfDocument({ report }: { report: AuditReport }) {
  const overallColours = statusColours(report.overallStatus);
  const strongestArea = report.strongestAreas[0];
  const weakestArea = report.topIssues[0];
  const watchAreas = report.sections.filter((section) => section.score > 70 && section.score < 85).slice(0, 2);

  return (
    <Document title={`${report.profile.companyName} Recruitment Audit`}>
      <Page size="A4" style={styles.coverPage}>
        <Text style={styles.coverBrand}>Bradford & Marsh Consulting</Text>
        <View style={styles.coverRule} />
        <Text style={styles.coverTitle}>Recruitment Audit</Text>
        <Text style={styles.bodyText}>
          A structured assessment of how the hiring process is operating today, where it is losing pace, and what should change first.
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
          <Text>Recruitment process review</Text>
        </View>
      </Page>

      <Page size="A4" style={styles.page}>
        <Text style={styles.sectionTitle}>Executive summary</Text>
        <Text style={styles.bodyText}>{report.executiveSummary}</Text>

        <View style={styles.scoreHero}>
          <View style={styles.scoreRow}>
            <View>
              <Text style={styles.label}>Overall score</Text>
              <Text style={[styles.scoreValue, { color: overallColours.text }]}>{report.overallScore}/100</Text>
            </View>
            <Text style={[styles.statusPill, { color: overallColours.text, backgroundColor: overallColours.background }]}>
              {statusLabel(report.overallStatus)}
            </Text>
          </View>
          <View style={styles.progressTrack}>
            <View style={[styles.progressFill, { width: `${report.overallScore}%`, backgroundColor: overallColours.line }]} />
          </View>
          <Text>{report.scoreMeaning}</Text>
        </View>

        <View style={styles.statGrid}>
          <View style={styles.statCard}>
            <Text style={styles.statLabel}>Strongest area</Text>
            <Text style={styles.statValue}>{strongestArea.title}</Text>
            <Text>{strongestArea.score}/100</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statLabel}>Weakest area</Text>
            <Text style={styles.statValue}>{weakestArea.title}</Text>
            <Text>{weakestArea.score}/100</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statLabel}>Audit scope</Text>
            <Text style={styles.statValue}>{report.sections.length} sections</Text>
            <Text>End-to-end recruitment process review</Text>
          </View>
        </View>

        <Text style={styles.sectionTitle}>Top issues holding hiring back</Text>
        {report.topIssues.map((issue) => (
          <View key={issue.id} style={styles.issueBlock}>
            <Text style={[styles.label, { color: statusColours(issue.status).text }]}>
              {issue.title} ({issue.score}/100)
            </Text>
            <Text>{issue.currentState}</Text>
          </View>
        ))}

        <View style={styles.metricGrid}>
          <View style={styles.metricColumn}>
            <Text style={[styles.sectionTitle, { marginTop: 8 }]}>Priority actions</Text>
            {report.priorityActions.map((action) => (
              <Text key={action} style={styles.listItem}>
                • {action}
              </Text>
            ))}
          </View>
          <View style={styles.metricColumn}>
            <Text style={[styles.sectionTitle, { marginTop: 8 }]}>Priority matrix</Text>
            <View style={styles.matrixGrid}>
              <View style={[styles.matrixCell, { backgroundColor: "#fef2f2" }]}>
                <Text style={[styles.matrixTitle, { color: "#991b1b" }]}>Immediate attention</Text>
                {report.topIssues.slice(0, 2).map((issue) => (
                  <View key={issue.id} style={styles.matrixItem}>
                    <Text>{issue.title}</Text>
                  </View>
                ))}
              </View>
              <View style={[styles.matrixCell, { backgroundColor: "#fffbeb" }]}>
                <Text style={[styles.matrixTitle, { color: "#92400e" }]}>Tighten next</Text>
                {report.topIssues.slice(2, 3).map((issue) => (
                  <View key={issue.id} style={styles.matrixItem}>
                    <Text>{issue.title}</Text>
                  </View>
                ))}
              </View>
              <View style={[styles.matrixCell, { backgroundColor: "#f8fafc" }]}>
                <Text style={[styles.matrixTitle, { color: "#475569" }]}>Watch closely</Text>
                {watchAreas.map((issue) => (
                  <View key={issue.id} style={styles.matrixItem}>
                    <Text>{issue.title}</Text>
                  </View>
                ))}
              </View>
              <View style={[styles.matrixCell, { backgroundColor: "#f0fdf4" }]}>
                <Text style={[styles.matrixTitle, { color: "#166534" }]}>Maintain</Text>
                {report.strongestAreas.slice(0, 2).map((issue) => (
                  <View key={issue.id} style={styles.matrixItem}>
                    <Text>{issue.title}</Text>
                  </View>
                ))}
              </View>
            </View>
          </View>
        </View>

        <Text style={[styles.sectionTitle, { marginTop: 18 }]}>Score overview</Text>
        <View style={styles.grid}>
          {report.sections.map((section) => (
            <ScoreOverviewRow key={section.id} section={section} />
          ))}
        </View>
      </Page>

      <Page size="A4" style={styles.page}>
        <Text style={styles.sectionTitle}>Detailed findings</Text>
        <Text style={[styles.bodyText, styles.mutedText]}>
          Each section score reflects the current operating position and the level of control visible in the process.
        </Text>

        {report.sections.slice(0, 5).map((section) => (
          <DetailSection key={section.id} section={section} />
        ))}
      </Page>

      <Page size="A4" style={styles.page}>
        {report.sections.slice(5).map((section) => (
          <DetailSection key={section.id} section={section} />
        ))}

        <Text style={[styles.sectionTitle, { marginTop: 8 }]}>Recruitment audit summary</Text>
        <View style={styles.finalNote}>
          <Text style={styles.bodyText}>{report.scoreMeaning}</Text>
          <Text style={styles.label}>Recommended next step</Text>
          <Text>{report.recommendedNextStep}</Text>
        </View>
      </Page>
    </Document>
  );
}
