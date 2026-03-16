from __future__ import annotations

import json
import os
import re
import textwrap
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


BASE_DIR = Path(__file__).resolve().parent
BENCHMARK_FILE = BASE_DIR / "uk_recruitment_benchmark_framework.xlsx"
OUTPUT_DIR = Path(os.environ.get("AUDIT_OUTPUT_DIR", "/tmp/BradfordMarshAI"))

SECTION_ORDER = [
    "Recruitment strategy and workforce planning",
    "Performance metrics and funnel conversion",
    "Employer brand and market perception",
    "Job adverts and job specifications",
    "Sourcing and advertising process",
    "Application handling and screening",
    "Interview process quality",
    "Decision making and offer process",
    "Onboarding and early retention",
    "Staff turnover risks",
    "Candidate experience",
    "Process ownership and accountability",
]

FINAL_SECTION_ORDER = [
    "Executive overview",
    "Top 5 strengths",
    "Top 5 problems",
    "30 day plan",
    "60 day plan",
    "90 day plan",
    "Overall recruitment score",
    "Final verdict",
]

SECTION_IDS = [
    "recruitment_strategy_and_workforce_planning",
    "performance_metrics_and_funnel_conversion",
    "employer_brand_and_market_perception",
    "job_adverts_and_job_specifications",
    "sourcing_and_advertising_process",
    "application_handling_and_screening",
    "interview_process_quality",
    "decision_making_and_offer_process",
    "onboarding_and_early_retention",
    "staff_turnover_risks",
    "candidate_experience",
    "process_ownership_and_accountability",
]

SECTION_ID_TO_TITLE = dict(zip(SECTION_IDS, SECTION_ORDER))

SECTION_KEYS = {
    "current_state": "Current state",
    "key_risks": "Key risks",
    "commercial_impact": "Commercial impact",
    "immediate_actions": "Immediate actions",
    "structural_improvements": "Structural improvements",
}

PRIMARY = RGBColor(24, 38, 71)
SECONDARY = RGBColor(79, 98, 122)
ACCENT = RGBColor(193, 154, 107)
TEXT = RGBColor(36, 36, 36)
MUTED = RGBColor(102, 112, 122)
LIGHT_BG = "F6F8FB"
SOFT_BG = "F8FAFC"
GREEN = RGBColor(22, 101, 52)
AMBER = RGBColor(180, 83, 9)
RED = RGBColor(185, 28, 28)
GREEN_FILL = "DCFCE7"
AMBER_FILL = "FEF3C7"
RED_FILL = "FEE2E2"
RAG_BANDS = [
    (0, 4, "#dc2626"),
    (4, 7, "#d97706"),
    (7, 10.01, "#16a34a"),
]

SYSTEM_PROMPT = """
You are a senior recruitment advisor writing for Bradford & Marsh Consulting.

Write in polished British English. Be direct, commercially credible and practical. Avoid AI filler, generic management jargon and repeated phrasing.

The report must feel coherent from start to finish:
- make the executive overview read like a synthesis, not a list
- ensure each detailed section builds logically from the business context, metrics and process controls supplied
- recommendations should be specific enough to act on next week
- acknowledge strengths without overpraising them
- where data is weak or missing, say so plainly
- vary sentence openings and sentence length so the writing does not sound templated
- explain what the operating data implies, not just what the numbers are
- use a senior advisory tone suitable for leadership review, with clear commercial implications
- make the strengths and weaknesses feel specific to the company profile supplied
""".strip()

REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "executive_overview": {"type": "string"},
        "top_strengths": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 5,
            "maxItems": 5,
        },
        "top_problems": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 5,
            "maxItems": 5,
        },
        "day_30_plan": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 5,
        },
        "day_60_plan": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 5,
        },
        "day_90_plan": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 5,
        },
        "overall_recruitment_score": {"type": "string"},
        "final_verdict": {"type": "string"},
        "sections": {
            "type": "object",
            "properties": {
                section_id: {
                    "type": "object",
                    "properties": {
                        "score": {"type": "integer", "minimum": 1, "maximum": 10},
                        "current_state": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 4},
                        "key_risks": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 4},
                        "commercial_impact": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 3},
                        "immediate_actions": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 4},
                        "structural_improvements": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 4},
                    },
                    "required": [
                        "score",
                        "current_state",
                        "key_risks",
                        "commercial_impact",
                        "immediate_actions",
                        "structural_improvements",
                    ],
                    "additionalProperties": False,
                }
                for section_id in SECTION_IDS
            },
            "required": SECTION_IDS,
            "additionalProperties": False,
        },
    },
    "required": [
        "executive_overview",
        "top_strengths",
        "top_problems",
        "day_30_plan",
        "day_60_plan",
        "day_90_plan",
        "overall_recruitment_score",
        "final_verdict",
        "sections",
    ],
    "additionalProperties": False,
}


def get_api_key() -> str:
    candidates = [
        os.environ.get("OPENAI_API_KEY", ""),
        _read_text_if_exists(BASE_DIR / "openai_api_key.txt"),
        _read_text_if_exists(Path.home() / ".openai_api_key.txt"),
    ]
    for value in candidates:
        value = value.strip()
        if value:
            return value
    raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY or add openai_api_key.txt alongside the app.")


def _read_text_if_exists(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


def parse_numeric_value(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    return float(match.group()) if match else None


def parse_time_to_hire_days(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    numeric = parse_numeric_value(text)
    if numeric is None:
        return None
    if "week" in text or re.search(r"\bw\b", text):
        return round(numeric * 7, 1)
    if "month" in text:
        return round(numeric * 30, 1)
    return round(numeric, 1)


def load_benchmarks(sector: str) -> pd.DataFrame:
    if not BENCHMARK_FILE.exists():
        raise FileNotFoundError(f"Benchmark workbook not found: {BENCHMARK_FILE}")

    df = pd.read_excel(BENCHMARK_FILE, sheet_name="Benchmarks")
    df.columns = [str(col).strip() for col in df.columns]
    df["sector"] = df["sector"].astype(str).str.strip()

    if sector.strip():
        matches = df[df["sector"].str.contains(sector.strip(), case=False, na=False)]
        if not matches.empty:
            return matches.reset_index(drop=True)

    national = df[df["region"].astype(str).str.contains("UK National", case=False, na=False)]
    return national.reset_index(drop=True) if not national.empty else df.reset_index(drop=True)


def build_benchmark_summary(metrics: dict, benchmark: pd.DataFrame) -> dict:
    benchmark_row = _pick_benchmark_row(benchmark, {})
    if benchmark_row.empty:
        return {"benchmark_row": {}, "comparisons": [], "summary_text": "No benchmark data available."}

    mapping = [
        ("time_to_hire_days", "avg_time_to_hire_days", "Time to hire", "days", False),
        ("applications_per_role", "avg_applications_per_role", "Applications per role", "", True),
        ("offer_acceptance", "avg_offer_acceptance_pct", "Offer acceptance", "%", True),
        ("first_year_attrition", "avg_attrition_pct", "First-year attrition", "%", False),
    ]

    comparisons = []
    summary_lines = []
    for client_key, benchmark_key, label, suffix, higher_is_better in mapping:
        client_value = metrics.get(client_key)
        benchmark_value = _safe_float(benchmark_row.get(benchmark_key))
        status = "No client figure supplied"
        if client_value is not None and benchmark_value is not None:
            delta = round(client_value - benchmark_value, 1)
            if abs(delta) <= max(1.0, benchmark_value * 0.03):
                status = "Broadly in line with benchmark"
            else:
                better = delta > 0 if higher_is_better else delta < 0
                if better:
                    status = f"{abs(delta):.1f}{suffix} better than benchmark"
                else:
                    status = f"{abs(delta):.1f}{suffix} behind benchmark"
        comparisons.append(
            {
                "label": label,
                "client_value": client_value,
                "benchmark_value": benchmark_value,
                "suffix": suffix,
                "status": status,
            }
        )
        client_display = "n/a" if client_value is None else f"{client_value:.1f}{suffix}"
        benchmark_display = "n/a" if benchmark_value is None else f"{benchmark_value:.1f}{suffix}"
        summary_lines.append(f"- {label}: client {client_display}, benchmark {benchmark_display}. {status}.")

    return {
        "benchmark_row": benchmark_row.to_dict(),
        "comparisons": comparisons,
        "summary_text": "\n".join(summary_lines),
    }


def auto_score_sections(data: dict, benchmark: pd.DataFrame) -> tuple[list[int], list[str]]:
    benchmark_row = _pick_benchmark_row(benchmark, data)
    metrics = data["metrics"]
    flags = data["process_flags"]

    metric_scores = {
        "time_to_hire": _metric_score(metrics.get("time_to_hire_days"), _safe_float(benchmark_row.get("avg_time_to_hire_days")), higher_is_better=False),
        "applications": _metric_score(metrics.get("applications_per_role"), _safe_float(benchmark_row.get("avg_applications_per_role")), higher_is_better=True),
        "offer_acceptance": _metric_score(metrics.get("offer_acceptance"), _safe_float(benchmark_row.get("avg_offer_acceptance_pct")), higher_is_better=True),
        "attrition": _metric_score(metrics.get("first_year_attrition"), _safe_float(benchmark_row.get("avg_attrition_pct")), higher_is_better=False),
        "feedback_speed": _feedback_score(metrics.get("interview_feedback_time_days")),
        "interview_design": _stage_score(metrics.get("interview_stages")),
        "screening_volume": _screening_score(metrics.get("candidates_reaching_interview")),
    }

    def flag_value(*names: str) -> float:
        if not names:
            return 5.0
        yes = sum(1 for name in names if flags.get(name))
        return 3.5 + (yes / len(names)) * 5.5

    def blend(*values: float) -> int:
        return max(1, min(10, round(sum(values) / len(values))))

    scores = [
        blend(flag_value("has_hiring_plan", "named_process_owner"), metric_scores["time_to_hire"], metric_scores["attrition"]),
        blend(flag_value("tracks_metrics"), metric_scores["offer_acceptance"], metric_scores["applications"], metric_scores["screening_volume"]),
        blend(flag_value("has_employer_brand"), metric_scores["applications"], metric_scores["offer_acceptance"]),
        blend(flag_value("standardised_job_specs"), metric_scores["applications"], metric_scores["offer_acceptance"]),
        blend(flag_value("multi_channel_sourcing"), metric_scores["applications"], metric_scores["screening_volume"]),
        blend(flag_value("structured_screening"), metric_scores["screening_volume"], metric_scores["feedback_speed"]),
        blend(flag_value("structured_interviews", "hiring_manager_training"), metric_scores["interview_design"], metric_scores["feedback_speed"]),
        blend(flag_value("fast_offer_process"), metric_scores["offer_acceptance"], metric_scores["feedback_speed"]),
        blend(flag_value("formal_onboarding"), metric_scores["attrition"], metric_scores["offer_acceptance"]),
        blend(metric_scores["attrition"], metric_scores["time_to_hire"]),
        blend(flag_value("collects_candidate_feedback"), metric_scores["feedback_speed"], metric_scores["offer_acceptance"]),
        blend(flag_value("named_process_owner", "tracks_metrics", "hiring_manager_training")),
    ]

    notes = [
        f"Planning maturity is {'stronger' if flags.get('has_hiring_plan') else 'weaker'} than ideal, with time to hire at {_fmt(metrics.get('time_to_hire_days'), ' days')}.",
        f"KPI visibility is {'embedded' if flags.get('tracks_metrics') else 'limited'}, with offer acceptance at {_fmt(metrics.get('offer_acceptance'), '%')}.",
        f"Employer brand is {'defined' if flags.get('has_employer_brand') else 'underdeveloped'}, and applications per role are {_fmt(metrics.get('applications_per_role'), '')}.",
        f"Job documentation is {'standardised' if flags.get('standardised_job_specs') else 'inconsistent'}, affecting role clarity and shortlist quality.",
        f"Sourcing mix is {'broad' if flags.get('multi_channel_sourcing') else 'narrow'}, with interview-ready candidate flow at {_fmt(metrics.get('candidates_reaching_interview'), '')}.",
        f"Screening is {'structured' if flags.get('structured_screening') else 'informal'}, which influences response speed and conversion quality.",
        f"Interview design combines {int(metrics.get('interview_stages') or 0) or 'an unknown number of'} stages with feedback turnaround of {_fmt(metrics.get('interview_feedback_time_days'), ' days')}.",
        f"Offer process is {'faster' if flags.get('fast_offer_process') else 'more exposed to delay'}, which shapes acceptance performance.",
        f"Onboarding is {'documented' if flags.get('formal_onboarding') else 'lightly controlled'}, with first-year attrition at {_fmt(metrics.get('first_year_attrition'), '%')}.",
        f"Retention pressure remains visible through first-year attrition of {_fmt(metrics.get('first_year_attrition'), '%')}.",
        f"Candidate feedback is {'captured' if flags.get('collects_candidate_feedback') else 'not systematically captured'}, while interview feedback speed remains material.",
        f"Ownership is {'clear' if flags.get('named_process_owner') else 'blurred'}, and manager training is {'present' if flags.get('hiring_manager_training') else 'limited'}.",
    ]

    return scores, notes


def generate_report_json(client, data: dict, benchmark_summary: dict) -> dict:
    prompt = _build_user_prompt(data, benchmark_summary)
    response = client.responses.create(
        model="gpt-4.1",
        instructions=SYSTEM_PROMPT,
        input=prompt,
        max_output_tokens=5000,
        temperature=0.5,
        text={
            "verbosity": "medium",
            "format": {
                "type": "json_schema",
                "name": "recruitment_audit_report",
                "schema": REPORT_SCHEMA,
                "strict": True,
            },
        },
    )
    report = json.loads(response.output_text)
    return _normalise_report(report, data["section_scores"])


def _build_user_prompt(data: dict, benchmark_summary: dict) -> str:
    strongest_sections = sorted(
        zip(SECTION_ORDER, data["section_scores"]),
        key=lambda item: item[1],
        reverse=True,
    )[:3]
    weakest_sections = sorted(
        zip(SECTION_ORDER, data["section_scores"]),
        key=lambda item: item[1],
    )[:3]
    section_scorecard = "\n".join(
        f"- {title}: {score}/10. {note}"
        for title, score, note in zip(SECTION_ORDER, data["section_scores"], data["section_notes"])
    )
    metrics_block = "\n".join(
        f"- {key.replace('_', ' ').title()}: {value or 'Not provided'}"
        for key, value in data["raw_metrics"].items()
    )
    flags_block = "\n".join(
        f"- {key.replace('_', ' ').title()}: {'Yes' if value else 'No'}"
        for key, value in data["process_flags"].items()
    )
    return f"""
Company profile
- Company: {data['company_name']}
- Sector: {data['sector']}
- Location: {data['location']}
- Headcount: {data['headcount']}
- Annual hiring volume: {data['annual_hiring_volume']}
- Key roles hired: {data['key_roles_hired']}

Metrics supplied
{metrics_block}

Operating controls
{flags_block}

Benchmark summary
{benchmark_summary['summary_text']}

Calculated scorecard
{section_scorecard}

Strongest areas
{chr(10).join(f"- {title}: {score}/10" for title, score in strongest_sections)}

Weakest areas
{chr(10).join(f"- {title}: {score}/10" for title, score in weakest_sections)}

Output requirements
- Use the same score for each detailed section as the supplied scorecard.
- Make the executive overview flow as a narrative, not as bullets.
- Keep strengths, problems and plans crisp and commercially grounded.
- Do not invent client facts that are not implied by the supplied data.
- Make the detailed sections feel connected rather than written in isolation.
- Where a benchmark gap is material, say what it means operationally.
""".strip()


def create_section_score_chart(company_name: str, section_scores: list[int]) -> Path:
    output_dir = _output_dir()
    path = output_dir / f"{_slug(company_name)}_section_scores.png"

    labels = [_short_label(title) for title in SECTION_ORDER]
    positions = list(range(len(labels)))

    plt.figure(figsize=(9.2, 6.8))
    for start, end, color in RAG_BANDS:
        plt.axvspan(start, end, color=color, alpha=0.08)
    bar_colors = [_score_hex(score) for score in section_scores]
    plt.barh(positions, section_scores, color=bar_colors, edgecolor="#0f172a", linewidth=0.4)
    plt.xlim(0, 10)
    plt.xticks(range(0, 11, 2))
    plt.yticks(positions, labels)
    plt.gca().invert_yaxis()
    plt.grid(axis="x", alpha=0.2, linestyle="--")
    plt.title(f"{company_name} section scores", fontsize=14, pad=14)
    plt.xlabel("Score out of 10")
    for pos, score in enumerate(section_scores):
        plt.text(min(score + 0.15, 9.7), pos, f"{score}/10", va="center", fontsize=9, color="#0f172a")
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()
    return path


def create_overall_score_chart(company_name: str, total_score: int) -> Path:
    output_dir = _output_dir()
    path = output_dir / f"{_slug(company_name)}_overall_score.png"

    max_score = 120
    score = min(total_score, max_score)
    pct = round((score / max_score) * 100)
    rating = _rating_for_score(score)
    fill_color = _score_hex(round((score / max_score) * 10))

    plt.figure(figsize=(8.8, 2.8))
    ax = plt.gca()
    ax.barh([0], [max_score], color="#e2e8f0", height=0.5)
    ax.barh([0], [score], color=fill_color, height=0.5)
    ax.set_xlim(0, max_score)
    ax.set_yticks([])
    ax.set_xticks(range(0, max_score + 1, 20))
    ax.grid(axis="x", alpha=0.18, linestyle="--")
    ax.set_title(f"{company_name} overall recruitment score", fontsize=14, pad=12)
    ax.text(score, 0, f"  {score}/120 ({pct}%)", va="center", ha="left", fontsize=10, color="#0f172a")
    ax.text(0, -0.48, f"Rating: {rating}", fontsize=10, color=fill_color)
    for spine in ax.spines.values():
        spine.set_visible(False)
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()
    return path


def create_benchmark_chart(company_name: str, metrics: dict, benchmark: pd.DataFrame) -> Path:
    output_dir = _output_dir()
    path = output_dir / f"{_slug(company_name)}_benchmark_compare.png"
    benchmark_row = _pick_benchmark_row(benchmark, {})

    items = [
        ("Time to hire", metrics.get("time_to_hire_days"), _safe_float(benchmark_row.get("avg_time_to_hire_days")), "days", False),
        ("Applications per role", metrics.get("applications_per_role"), _safe_float(benchmark_row.get("avg_applications_per_role")), "", True),
        ("Offer acceptance", metrics.get("offer_acceptance"), _safe_float(benchmark_row.get("avg_offer_acceptance_pct")), "%", True),
        ("First-year attrition", metrics.get("first_year_attrition"), _safe_float(benchmark_row.get("avg_attrition_pct")), "%", False),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(9.2, 6.6))
    axes = axes.flatten()
    for ax, (label, client_value, benchmark_value, suffix, higher_is_better) in zip(axes, items):
        client_value = client_value or 0
        benchmark_value = benchmark_value or 0
        ceiling = max(client_value, benchmark_value, 1) * 1.25
        ahead = client_value >= benchmark_value if higher_is_better else client_value <= benchmark_value
        client_color = "#16a34a" if ahead else "#dc2626"
        ax.barh(["Client", "Benchmark"], [client_value, benchmark_value], color=[client_color, "#cbd5e1"])
        ax.set_xlim(0, ceiling)
        ax.set_title(label, fontsize=11)
        ax.grid(axis="x", alpha=0.16, linestyle="--")
        ax.text(client_value, 0, f"  {client_value:.1f}{suffix}", va="center", ha="left", fontsize=9)
        ax.text(benchmark_value, 1, f"  {benchmark_value:.1f}{suffix}", va="center", ha="left", fontsize=9)
        direction = "Ahead of benchmark" if ahead else "Behind benchmark"
        ax.text(0, -0.42, direction, fontsize=9, color=client_color)
        for spine in ax.spines.values():
            spine.set_visible(False)

    fig.suptitle(f"{company_name} benchmark comparison", fontsize=14, y=0.98)
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()
    return path


def save_word_report(
    data: dict,
    report: dict,
    benchmark_summary: dict,
    section_chart: Path,
    overall_chart: Path,
    benchmark_chart: Path,
) -> Path:
    output_path = _output_dir() / f"{_slug(data['company_name'])}_recruitment_audit.docx"
    report = _normalise_report(report, data["section_scores"])
    document = Document()
    _set_document_defaults(document)
    _add_cover_page(document, data)
    _add_executive_snapshot(document, data, report)
    _add_key_findings_panel(document, data, report)
    _add_score_summary(document, data)
    _add_scoring_methodology(document, data, benchmark_summary)
    _add_benchmark_snapshot(document, benchmark_summary)
    _add_priority_matrix(document, data, report)
    _add_chart_section(document, [overall_chart, section_chart, benchmark_chart])
    document.add_page_break()
    _add_detailed_findings(document, data, report)
    _add_roadmap(document, report)
    _add_closing_page(document, report)
    document.save(output_path)
    return output_path


def _normalise_report(report: dict, fallback_scores: list[int]) -> dict:
    sections_by_id = report.get("sections", {}) or {}
    sections = []
    for index, section_id in enumerate(SECTION_IDS):
        title = SECTION_ID_TO_TITLE[section_id]
        section = sections_by_id.get(section_id, {})
        sections.append(
            {
                "title": title,
                "score": int(section.get("score", fallback_scores[index])),
                "current_state": _ensure_list(section.get("current_state"), 2),
                "key_risks": _ensure_list(section.get("key_risks"), 2),
                "commercial_impact": _ensure_list(section.get("commercial_impact"), 1),
                "immediate_actions": _ensure_list(section.get("immediate_actions"), 2),
                "structural_improvements": _ensure_list(section.get("structural_improvements"), 2),
            }
        )
    report["sections"] = sections
    return report


def _ensure_list(value, min_items: int) -> list[str]:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
    elif value:
        items = [str(value).strip()]
    else:
        items = []
    while len(items) < min_items:
        items.append("Further detail should be validated against the next review cycle.")
    return items


def _set_document_defaults(document: Document) -> None:
    normal = document.styles["Normal"]
    normal.font.name = "Aptos"
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = TEXT

    for name in ["Heading 1", "Heading 2", "Heading 3", "Title"]:
        if name in document.styles:
            document.styles[name].font.name = "Aptos"

    section = document.sections[0]
    section.top_margin = Inches(0.6)
    section.bottom_margin = Inches(0.6)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)


def _add_cover_page(document: Document, data: dict) -> None:
    p = document.add_paragraph()
    p.paragraph_format.space_before = Pt(54)
    run = p.add_run("Recruitment Operating Model Audit")
    run.bold = True
    run.font.name = "Aptos"
    run.font.size = Pt(24)
    run.font.color.rgb = PRIMARY

    p2 = document.add_paragraph()
    p2.paragraph_format.space_after = Pt(6)
    run2 = p2.add_run(data["company_name"])
    run2.bold = True
    run2.font.name = "Aptos"
    run2.font.size = Pt(17)
    run2.font.color.rgb = SECONDARY

    p3 = document.add_paragraph()
    p3.paragraph_format.space_after = Pt(16)
    run3 = p3.add_run(
        f"Prepared by Bradford & Marsh Consulting on {datetime.now().strftime('%d %B %Y')}"
    )
    run3.font.name = "Aptos"
    run3.font.size = Pt(11)
    run3.font.color.rgb = MUTED

    table = document.add_table(rows=4, cols=2)
    table.autofit = True
    rows = [
        ("Sector", data["sector"]),
        ("Location", data["location"]),
        ("Headcount", data["headcount"]),
        ("Annual hiring volume", data["annual_hiring_volume"]),
    ]
    for i, (label, value) in enumerate(rows):
        _set_cell(table.cell(i, 0), label, bold=True, color=PRIMARY)
        _set_cell(table.cell(i, 1), value)
        _shade_cell(table.cell(i, 0), LIGHT_BG)

    document.add_paragraph("")
    brand = document.add_paragraph()
    brand_run = brand.add_run("Bradford & Marsh Consulting")
    brand_run.bold = True
    brand_run.font.name = "Aptos"
    brand_run.font.size = Pt(11)
    brand_run.font.color.rgb = ACCENT
    document.add_page_break()


def _add_executive_snapshot(document: Document, data: dict, report: dict) -> None:
    _add_section_banner(document, "Executive overview")
    _add_paragraph(document, report["executive_overview"], after=6)

    cards = document.add_table(rows=1, cols=3)
    cards.autofit = True
    values = [
        ("Overall score", f"{data['total_score']}/120"),
        ("Rating", _rating_for_score(data["total_score"])),
        ("Key roles", data["key_roles_hired"]),
    ]
    for index, (label, value) in enumerate(values):
        cell = cards.cell(0, index)
        if index == 0:
            _shade_cell(cell, _score_fill(round((data["total_score"] / 120) * 10)))
        elif index == 1:
            _shade_cell(cell, _score_fill(round((data["total_score"] / 120) * 10)))
        else:
            _shade_cell(cell, SOFT_BG)
        _set_cell(cell, f"{label}\n{value}", bold=False)
    document.add_paragraph("")


def _add_key_findings_panel(document: Document, data: dict, report: dict) -> None:
    strongest = max(zip(SECTION_ORDER, data["section_scores"]), key=lambda item: item[1])
    weakest = min(zip(SECTION_ORDER, data["section_scores"]), key=lambda item: item[1])
    problem = report["top_problems"][0] if report.get("top_problems") else "No priority issue identified."
    table = document.add_table(rows=1, cols=3)
    table.autofit = True
    cards = [
        ("Strongest area", f"{strongest[0]}\n{strongest[1]}/10", GREEN_FILL, GREEN),
        ("Most urgent weakness", f"{weakest[0]}\n{weakest[1]}/10", RED_FILL, RED),
        ("Primary diagnosis", problem, AMBER_FILL, AMBER),
    ]
    for index, (label, value, fill, color) in enumerate(cards):
        cell = table.cell(0, index)
        _shade_cell(cell, fill)
        _set_cell(cell, f"{label}\n{value}", color=color)
    document.add_paragraph("")


def _add_score_summary(document: Document, data: dict) -> None:
    _add_section_banner(document, "Score summary")
    table = document.add_table(rows=1, cols=2)
    table.autofit = True
    header = table.rows[0].cells
    _set_cell(header[0], "Area", bold=True, color=PRIMARY)
    _set_cell(header[1], "Score", bold=True, color=PRIMARY)
    _shade_cell(header[0], LIGHT_BG)
    _shade_cell(header[1], LIGHT_BG)

    for title, score in zip(SECTION_ORDER, data["section_scores"]):
        cells = table.add_row().cells
        _set_cell(cells[0], title)
        _shade_cell(cells[1], _score_fill(score))
        _set_cell(cells[1], f"{score}/10", bold=True, color=_score_rgb(score))
    document.add_paragraph("")


def _add_scoring_methodology(document: Document, data: dict, benchmark_summary: dict) -> None:
    _add_section_banner(document, "Scoring methodology")
    _add_paragraph(
        document,
        (
            "The audit uses a 120-point framework across twelve operating areas, with each section scored out of 10. "
            "Scores are informed by three inputs: the performance metrics submitted, the process-control responses supplied in the assessment, "
            "and the benchmark position available for the selected sector. Higher scores indicate more repeatable control, stronger delivery discipline and lower operating risk."
        ),
        after=4,
    )

    table = document.add_table(rows=1, cols=3)
    table.autofit = True
    header = table.rows[0].cells
    for idx, label in enumerate(["Score band", "Interpretation", "Typical implication"]):
        _set_cell(header[idx], label, bold=True, color=PRIMARY)
        _shade_cell(header[idx], LIGHT_BG)

    rows = [
        ("7-10", "Established or strong", "Controls are embedded and performance risk is lower.", GREEN_FILL, GREEN),
        ("4-6", "Functional but inconsistent", "Capability exists, but execution quality is uneven or delayed.", AMBER_FILL, AMBER),
        ("1-3", "Material weakness", "The process is exposed to avoidable delay, quality leakage or governance risk.", RED_FILL, RED),
    ]
    for band, interpretation, implication, fill, color in rows:
        cells = table.add_row().cells
        _shade_cell(cells[0], fill)
        _set_cell(cells[0], band, bold=True, color=color)
        _set_cell(cells[1], interpretation)
        _set_cell(cells[2], implication)

    strongest_benchmark = benchmark_summary.get("comparisons", [])[:1]
    if strongest_benchmark:
        document.add_paragraph("")
    document.add_paragraph("")


def _add_benchmark_snapshot(document: Document, benchmark_summary: dict) -> None:
    comparisons = benchmark_summary.get("comparisons", [])
    if not comparisons:
        return

    _add_section_banner(document, "Benchmark snapshot")
    table = document.add_table(rows=1, cols=4)
    table.autofit = True
    header = table.rows[0].cells
    for idx, label in enumerate(["Metric", "Client", "Benchmark", "Comment"]):
        _set_cell(header[idx], label, bold=True, color=PRIMARY)
        _shade_cell(header[idx], LIGHT_BG)

    for item in comparisons:
        cells = table.add_row().cells
        suffix = item["suffix"]
        _set_cell(cells[0], item["label"])
        _set_cell(cells[1], "n/a" if item["client_value"] is None else f"{item['client_value']:.1f}{suffix}")
        _set_cell(cells[2], "n/a" if item["benchmark_value"] is None else f"{item['benchmark_value']:.1f}{suffix}")
        status_color, status_fill = _status_colors(item["status"])
        _shade_cell(cells[3], status_fill)
        _set_cell(cells[3], item["status"], color=status_color)
    document.add_paragraph("")


def _add_priority_matrix(document: Document, data: dict, report: dict) -> None:
    _add_section_banner(document, "Priority matrix")
    _add_paragraph(
        document,
        "The matrix below highlights the most commercially important improvement areas based on the lowest-scoring sections and the actions attached to them.",
        after=4,
    )

    priorities = _build_priority_matrix(data, report)
    table = document.add_table(rows=1, cols=5)
    table.autofit = True
    header = table.rows[0].cells
    for idx, label in enumerate(["Priority area", "Urgency", "Impact", "Why it matters", "First move"]):
        _set_cell(header[idx], label, bold=True, color=PRIMARY)
        _shade_cell(header[idx], LIGHT_BG)

    for item in priorities:
        cells = table.add_row().cells
        urgency_fill = {"Immediate": RED_FILL, "Next 30 days": AMBER_FILL, "Planned": GREEN_FILL}[item["urgency"]]
        urgency_color = {"Immediate": RED, "Next 30 days": AMBER, "Planned": GREEN}[item["urgency"]]
        _set_cell(cells[0], item["title"])
        _shade_cell(cells[1], urgency_fill)
        _set_cell(cells[1], item["urgency"], bold=True, color=urgency_color)
        _set_cell(cells[2], item["impact"])
        _set_cell(cells[3], item["why"])
        _set_cell(cells[4], item["action"])
    document.add_paragraph("")


def _add_chart_section(document: Document, chart_paths: list[Path]) -> None:
    _add_section_banner(document, "Charts and visual analysis")
    captions = [
        "Overall score against the full 120-point framework.",
        "Section-by-section scoring profile.",
        "Benchmark comparison with each metric plotted on its own scale.",
    ]
    for chart_path, caption in zip(chart_paths, captions):
        if chart_path.exists():
            document.add_picture(str(chart_path), width=Inches(6.45))
            cap = document.add_paragraph()
            cap.paragraph_format.space_before = Pt(2)
            cap.paragraph_format.space_after = Pt(8)
            run = cap.add_run(caption)
            run.italic = True
            run.font.name = "Aptos"
            run.font.size = Pt(9.2)
            run.font.color.rgb = MUTED


def _add_detailed_findings(document: Document, data: dict, report: dict) -> None:
    _add_section_banner(document, "Detailed findings")
    for section, note in zip(report["sections"], data["section_notes"]):
        _add_heading(document, section["title"], level=2)
        _add_metric_callout(document, f"Score: {section['score']}/10", section["score"])
        _add_supporting_note(document, note)
        for key, label in SECTION_KEYS.items():
            _add_heading(document, label, level=3)
            _add_bullets(document, section[key])


def _add_roadmap(document: Document, report: dict) -> None:
    document.add_section(WD_SECTION.NEW_PAGE)
    _add_section_banner(document, "Priorities and roadmap")

    _add_heading(document, "Top 5 strengths", level=2)
    _add_bullets(document, report["top_strengths"])

    _add_heading(document, "Top 5 problems", level=2)
    _add_bullets(document, report["top_problems"])

    _add_heading(document, "30 day plan", level=2)
    _add_bullets(document, report["day_30_plan"])

    _add_heading(document, "60 day plan", level=2)
    _add_bullets(document, report["day_60_plan"])

    _add_heading(document, "90 day plan", level=2)
    _add_bullets(document, report["day_90_plan"])


def _add_closing_page(document: Document, report: dict) -> None:
    document.add_section(WD_SECTION.NEW_PAGE)
    _add_section_banner(document, "Overall recruitment score")
    _add_paragraph(document, report["overall_recruitment_score"], after=8)
    _add_section_banner(document, "Final verdict")
    _add_paragraph(document, report["final_verdict"], after=6)


def _add_section_banner(document: Document, title: str) -> None:
    table = document.add_table(rows=1, cols=1)
    table.autofit = True
    cell = table.cell(0, 0)
    _shade_cell(cell, LIGHT_BG)
    _set_cell(cell, title, bold=True, color=PRIMARY)
    document.add_paragraph("")


def _add_heading(document: Document, title: str, level: int) -> None:
    paragraph = document.add_paragraph()
    paragraph.style = document.styles[f"Heading {min(level, 3)}"]
    paragraph.paragraph_format.space_before = Pt(8 if level == 1 else 5)
    paragraph.paragraph_format.space_after = Pt(3)
    run = paragraph.add_run(title)
    run.bold = True
    run.font.name = "Aptos"
    run.font.size = Pt(13 if level == 1 else 11.4 if level == 2 else 10.4)
    run.font.color.rgb = PRIMARY if level == 1 else SECONDARY


def _add_paragraph(document: Document, text: str, after: float = 3) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(after)
    paragraph.paragraph_format.line_spacing = 1.1
    run = paragraph.add_run(text.strip())
    run.font.name = "Aptos"
    run.font.size = Pt(10.4)
    run.font.color.rgb = TEXT


def _add_supporting_note(document: Document, text: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(4)
    run = paragraph.add_run(text.strip())
    run.italic = True
    run.font.name = "Aptos"
    run.font.size = Pt(9.6)
    run.font.color.rgb = MUTED


def _add_bullets(document: Document, items: list[str]) -> None:
    for item in items:
        bullet = document.add_paragraph(style="List Bullet")
        bullet.paragraph_format.space_before = Pt(0)
        bullet.paragraph_format.space_after = Pt(0.5)
        bullet.paragraph_format.left_indent = Inches(0.18)
        run = bullet.add_run(item)
        run.font.name = "Aptos"
        run.font.size = Pt(10.1)
        run.font.color.rgb = TEXT


def _add_metric_callout(document: Document, text: str, score: int) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(4)
    run = paragraph.add_run(text)
    run.bold = True
    run.font.name = "Aptos"
    run.font.size = Pt(10.5)
    run.font.color.rgb = _score_rgb(score)


def _shade_cell(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def _set_cell(cell, text: str, bold: bool = False, color: RGBColor = TEXT) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run(text)
    run.bold = bold
    run.font.name = "Aptos"
    run.font.size = Pt(10.0)
    run.font.color.rgb = color
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER


def _output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("._")
    return cleaned or "recruitment_audit"


def _size_band(headcount_value: str) -> str:
    headcount = parse_numeric_value(headcount_value)
    if headcount is None:
        return "SME"
    if headcount >= 1000:
        return "Enterprise"
    if headcount >= 250:
        return "Mid-Market"
    return "SME"


def _region_hint(location: str) -> str:
    text = location.lower()
    mapping = {
        "london": "London",
        "midlands": "Midlands",
        "manchester": "North West",
        "liverpool": "North West",
        "north west": "North West",
        "scotland": "Scotland",
        "glasgow": "Scotland",
        "edinburgh": "Scotland",
        "surrey": "South East",
        "kent": "South East",
        "south east": "South East",
    }
    for needle, region in mapping.items():
        if needle in text:
            return region
    return "UK National"


def _pick_benchmark_row(benchmark: pd.DataFrame, data: dict) -> pd.Series:
    if benchmark.empty:
        return pd.Series(dtype=object)

    working = benchmark.copy()
    size_band = _size_band(str(data.get("headcount", "")))
    region = _region_hint(str(data.get("location", "")))

    sized = working[working["company_size_band"].astype(str) == size_band]
    if not sized.empty:
        working = sized

    regional = working[working["region"].astype(str) == region]
    if regional.empty:
        regional = working[working["region"].astype(str) == "UK National"]
    if not regional.empty:
        working = regional

    return working.iloc[0]


def _metric_score(value: float | None, benchmark_value: float | None, higher_is_better: bool) -> float:
    if value is None or benchmark_value is None or benchmark_value == 0:
        return 5.5
    ratio = value / benchmark_value
    if higher_is_better:
        if ratio >= 1.2:
            return 8.8
        if ratio >= 1.05:
            return 7.8
        if ratio >= 0.95:
            return 6.8
        if ratio >= 0.8:
            return 5.5
        return 4.0
    if ratio <= 0.8:
        return 8.8
    if ratio <= 0.95:
        return 7.8
    if ratio <= 1.05:
        return 6.8
    if ratio <= 1.2:
        return 5.5
    return 4.0


def _feedback_score(days: float | None) -> float:
    if days is None:
        return 5.5
    if days <= 2:
        return 9.0
    if days <= 4:
        return 7.5
    if days <= 7:
        return 5.5
    return 3.8


def _stage_score(stages: float | None) -> float:
    if stages is None:
        return 5.5
    if stages <= 2:
        return 8.8
    if stages <= 3:
        return 7.2
    if stages <= 4:
        return 5.2
    return 3.8


def _screening_score(candidates: float | None) -> float:
    if candidates is None:
        return 5.5
    if candidates >= 5:
        return 8.0
    if candidates >= 3:
        return 6.8
    if candidates >= 2:
        return 5.4
    return 4.0


def _safe_float(value) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _short_label(title: str) -> str:
    mapping = {
        "Recruitment strategy and workforce planning": "Strategy & planning",
        "Performance metrics and funnel conversion": "Metrics & funnel",
        "Employer brand and market perception": "Employer brand",
        "Job adverts and job specifications": "Job adverts & specs",
        "Sourcing and advertising process": "Sourcing process",
        "Application handling and screening": "Screening",
        "Interview process quality": "Interviews",
        "Decision making and offer process": "Offers",
        "Onboarding and early retention": "Onboarding",
        "Staff turnover risks": "Turnover risk",
        "Candidate experience": "Candidate experience",
        "Process ownership and accountability": "Ownership",
    }
    return "\n".join(textwrap.wrap(mapping.get(title, title), width=18))


def _rating_for_score(total_score: int) -> str:
    if total_score >= 96:
        return "High maturity"
    if total_score >= 78:
        return "Established with gaps"
    if total_score >= 60:
        return "Functional but inconsistent"
    return "Needs substantial improvement"


def _score_rgb(score: int) -> RGBColor:
    if score >= 7:
        return GREEN
    if score >= 4:
        return AMBER
    return RED


def _score_fill(score: int) -> str:
    if score >= 7:
        return GREEN_FILL
    if score >= 4:
        return AMBER_FILL
    return RED_FILL


def _score_hex(score: int) -> str:
    if score >= 7:
        return "#16a34a"
    if score >= 4:
        return "#d97706"
    return "#dc2626"


def _status_colors(status: str) -> tuple[RGBColor, str]:
    lowered = status.lower()
    if "better" in lowered or "ahead" in lowered or "in line" in lowered:
        return GREEN, GREEN_FILL
    if "behind" in lowered:
        return RED, RED_FILL
    return AMBER, AMBER_FILL


def _fmt(value: float | None, suffix: str) -> str:
    return "not provided" if value is None else f"{value:.1f}{suffix}"


def _build_priority_matrix(data: dict, report: dict) -> list[dict[str, str]]:
    sections = report.get("sections", [])
    if isinstance(sections, dict):
        sections = [
            {
                "title": SECTION_ID_TO_TITLE.get(section_id, section_id.replace("_", " ").title()),
                **section,
            }
            for section_id, section in sections.items()
        ]

    priorities = []
    for section in sorted(sections, key=lambda item: item["score"])[:4]:
        if section["score"] <= 4:
            urgency = "Immediate"
            impact = "High"
        elif section["score"] <= 6:
            urgency = "Next 30 days"
            impact = "High"
        else:
            urgency = "Planned"
            impact = "Medium"

        priorities.append(
            {
                "title": section["title"],
                "urgency": urgency,
                "impact": impact,
                "why": section["commercial_impact"][0],
                "action": section["immediate_actions"][0],
            }
        )
    return priorities
