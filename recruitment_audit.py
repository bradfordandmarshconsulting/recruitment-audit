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
from PIL import Image as PILImage
from PIL import ImageChops
from matplotlib.ticker import MaxNLocator
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, StyleSheet1
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


BASE_DIR = Path(__file__).resolve().parent
BENCHMARK_FILE = BASE_DIR / "uk_recruitment_benchmark_framework.xlsx"
BENCHMARK_CSV_FILE = BASE_DIR / "uk_recruitment_benchmarks.csv"
OUTPUT_DIR = Path(os.environ.get("AUDIT_OUTPUT_DIR", "/tmp/BradfordMarshAI"))
BENCHMARK_ENV_VAR = "RECRUITMENT_BENCHMARK_FILE"
BRAND_LOGO = BASE_DIR / "public" / "brand" / "bradford-marsh-logo.png"
SIGNATURE_IMAGE = BASE_DIR / "public" / "brand" / "michael-marsh-signature.png"
SIGNATURE_CANDIDATES = [
    SIGNATURE_IMAGE,
    Path("/mnt/data/a_digital_image_features_a_stylized_signature_of_t.png"),
    Path("/Users/michaelmarsh/Desktop/a_digital_image_features_a_stylized_signature_of_t.png"),
]

PAGE_WIDTH, PAGE_HEIGHT = A4
PAGE_MARGIN_X = 18 * mm
PAGE_MARGIN_Y = 18 * mm
CHART_WIDTH = 5.4 * inch

PDF_FONT = "Helvetica"
PDF_FONT_BOLD = "Helvetica-Bold"

TEXT_COLOR = colors.HexColor("#1C2430")
SUBTLE_TEXT = colors.HexColor("#5F6876")
RULE_COLOR = colors.HexColor("#D8DCE3")
TABLE_SHADE = colors.HexColor("#F7F5F1")
BRAND_NAVY = colors.HexColor("#1F2A40")
BRAND_GOLD = colors.HexColor("#B5935A")
BRAND_PANEL = colors.HexColor("#F7F5F1")
BRAND_PANEL_ALT = colors.HexColor("#FAFBFC")
BRAND_PANEL_WARM = colors.HexColor("#FBF8F2")
GREEN_TEXT = colors.HexColor("#166534")
GREEN_BG = colors.HexColor("#DCFCE7")
AMBER_TEXT = colors.HexColor("#9A6700")
AMBER_BG = colors.HexColor("#FEF3C7")
RED_TEXT = colors.HexColor("#991B1B")
RED_BG = colors.HexColor("#FEE2E2")

BRAND_NAME = "Bradford & Marsh Consulting"
REPORT_TITLE = "Recruitment Operating Model Audit"
CONFIDENTIAL_LABEL = "Private & Confidential"
MANAGING_DIRECTOR_NAME = "Michael Marsh"
MANAGING_DIRECTOR_TITLE = "Managing Director"

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

SYSTEM_PROMPT = """
You are writing a final client report for a Recruitment Operating Model Audit.

Write in British English. Use short sentences. Be direct, commercial and precise.

Rules:
- No markdown.
- No asterisks, hashes or raw bullet symbols.
- No consultant filler.
- Do not use these words or phrases: robust, hampered, material, leverage, seamless, best-in-class, best in class, laid the groundwork, it is important to note, overall this suggests, in today's market.
- Keep the executive overview below 150 words.
- Make strengths, problems and actions specific.
- Each detailed section must include current state, key risks, commercial impact, immediate actions and structural improvements.
- Keep key risks to 2 points.
- Keep immediate actions to 2 points.
- Keep structural improvements to 2 points.
""".strip()

REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "executive_overview": {"type": "string"},
        "overall_recruitment_score": {"type": "string"},
        "final_verdict": {"type": "string"},
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
        "sections": {
            "type": "object",
            "properties": {
                section_id: {
                    "type": "object",
                    "properties": {
                        "score": {"type": "integer", "minimum": 1, "maximum": 10},
                        "current_state": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 4},
                        "key_risks": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 3},
                        "commercial_impact": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 3},
                        "immediate_actions": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 3},
                        "structural_improvements": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 3},
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
        "overall_recruitment_score",
        "final_verdict",
        "top_strengths",
        "top_problems",
        "day_30_plan",
        "day_60_plan",
        "day_90_plan",
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


def list_benchmark_sectors() -> list[str]:
    df = _load_benchmark_table()
    return (
        df["sector"]
        .dropna()
        .astype(str)
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .drop_duplicates()
        .sort_values()
        .tolist()
    )


def load_benchmarks(sector: str) -> pd.DataFrame:
    df = _load_benchmark_table()
    if sector.strip():
        matches = df[df["sector"].str.contains(sector.strip(), case=False, na=False)]
        if not matches.empty:
            return matches.reset_index(drop=True)
    national = df[df["region"].astype(str).str.contains("UK National", case=False, na=False)]
    return national.reset_index(drop=True) if not national.empty else df.reset_index(drop=True)


def _load_benchmark_table() -> pd.DataFrame:
    benchmark_path = _resolve_benchmark_file()
    if benchmark_path.suffix.lower() == ".csv":
        df = pd.read_csv(benchmark_path)
    else:
        df = pd.read_excel(benchmark_path, sheet_name="Benchmarks")
    return _normalise_benchmark_columns(df)


def _resolve_benchmark_file() -> Path:
    candidates = []
    configured = os.environ.get(BENCHMARK_ENV_VAR, "").strip()
    if configured:
        candidates.append(Path(configured).expanduser())
    candidates.extend(
        [
            BENCHMARK_FILE,
            BENCHMARK_CSV_FILE,
            Path.cwd() / "uk_recruitment_benchmark_framework.xlsx",
            Path.cwd() / "uk_recruitment_benchmarks.csv",
            Path.home() / "Desktop" / "uk_recruitment_benchmarks.csv",
        ]
    )
    for path in candidates:
        if path.exists():
            return path
    searched = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"Benchmark dataset not found. Checked: {searched}")


def _normalise_benchmark_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = df.copy()
    renamed.columns = [str(col).strip() for col in renamed.columns]
    renamed = renamed.rename(
        columns={
            "avg_time_to_hire": "avg_time_to_hire_days",
            "avg_applications": "avg_applications_per_role",
            "avg_offer_acceptance": "avg_offer_acceptance_pct",
            "avg_attrition": "avg_attrition_pct",
            "avg_application_to_interview": "avg_application_to_interview_pct",
            "avg_interview_to_offer": "avg_interview_to_offer_pct",
        }
    )

    if "sector" not in renamed.columns:
        raise ValueError("Benchmark data must include a 'sector' column.")

    defaults = {
        "company_size_band": "All sizes",
        "region": "UK National",
        "avg_time_to_hire_days": pd.NA,
        "avg_applications_per_role": pd.NA,
        "avg_offer_acceptance_pct": pd.NA,
        "avg_attrition_pct": pd.NA,
        "source_basis": "UK benchmark dataset",
        "data_quality_note": "",
    }
    for column, default in defaults.items():
        if column not in renamed.columns:
            renamed[column] = default

    renamed["sector"] = renamed["sector"].astype(str).str.strip()
    renamed["company_size_band"] = renamed["company_size_band"].fillna("All sizes").astype(str).str.strip()
    renamed["region"] = renamed["region"].fillna("UK National").astype(str).str.strip()
    return renamed


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
    for client_key, benchmark_key, label, suffix, higher_is_better in mapping:
        client_value = metrics.get(client_key)
        benchmark_value = _safe_float(benchmark_row.get(benchmark_key))
        if client_value is None or benchmark_value is None:
            continue
        delta = client_value - benchmark_value
        tolerance = max(1.0, abs(benchmark_value) * 0.03)
        if abs(delta) <= tolerance:
            status = "In line"
            comment = "In line with benchmark"
        else:
            ahead = delta > 0 if higher_is_better else delta < 0
            status = "Ahead" if ahead else "Behind"
            direction = "ahead of" if ahead else "behind"
            comment = f"{_format_metric_value(abs(delta), suffix)} {direction} benchmark"
        comparisons.append(
            {
                "label": label,
                "client_value": client_value,
                "benchmark_value": benchmark_value,
                "suffix": suffix,
                "status": status,
                "comment": comment,
            }
        )

    selected = _select_benchmark_comparisons(comparisons)
    summary_text = " ".join(
        f"{item['label']}: {_format_metric_value(item['client_value'], item['suffix'])} versus {_format_metric_value(item['benchmark_value'], item['suffix'])}. {item['comment']}."
        for item in selected
    )

    return {
        "benchmark_row": benchmark_row.to_dict(),
        "comparisons": selected,
        "summary_text": summary_text or "No useful benchmark comparisons were available.",
    }


def auto_score_sections(data: dict, benchmark: pd.DataFrame) -> tuple[list[int], list[str]]:
    benchmark_row = _pick_benchmark_row(benchmark, data)
    metrics = data["metrics"]
    flags = data["process_flags"]

    metric_scores = {
        "time_to_hire": _metric_score(
            metrics.get("time_to_hire_days"),
            _safe_float(benchmark_row.get("avg_time_to_hire_days")),
            higher_is_better=False,
        ),
        "applications": _metric_score(
            metrics.get("applications_per_role"),
            _safe_float(benchmark_row.get("avg_applications_per_role")),
            higher_is_better=True,
        ),
        "offer_acceptance": _metric_score(
            metrics.get("offer_acceptance"),
            _safe_float(benchmark_row.get("avg_offer_acceptance_pct")),
            higher_is_better=True,
        ),
        "attrition": _metric_score(
            metrics.get("first_year_attrition"),
            _safe_float(benchmark_row.get("avg_attrition_pct")),
            higher_is_better=False,
        ),
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
        f"Planning discipline is {'clearer' if flags.get('has_hiring_plan') else 'less structured'} than it should be, with time to hire at {_fmt(metrics.get('time_to_hire_days'), 'days')}.",
        f"KPI tracking is {'embedded' if flags.get('tracks_metrics') else 'limited'}, with offer acceptance at {_fmt(metrics.get('offer_acceptance'), '%')}.",
        f"Employer brand is {'defined' if flags.get('has_employer_brand') else 'underdeveloped'}, while applications per role are {_fmt(metrics.get('applications_per_role'), '')}.",
        f"Job documentation is {'standardised' if flags.get('standardised_job_specs') else 'inconsistent'}, which affects role clarity and shortlist quality.",
        f"Sourcing mix is {'broad' if flags.get('multi_channel_sourcing') else 'narrow'}, with interview-ready candidate flow at {_fmt(metrics.get('candidates_reaching_interview'), '')}.",
        f"Screening is {'structured' if flags.get('structured_screening') else 'informal'}, which affects response speed and conversion quality.",
        f"Interview design uses {int(metrics.get('interview_stages') or 0) or 'an unknown number of'} stages and feedback turnaround of {_fmt(metrics.get('interview_feedback_time_days'), 'days')}.",
        f"Offer handling is {'faster' if flags.get('fast_offer_process') else 'more exposed to delay'}, which shapes acceptance outcomes.",
        f"Onboarding is {'documented' if flags.get('formal_onboarding') else 'lightly controlled'}, with first-year attrition at {_fmt(metrics.get('first_year_attrition'), '%')}.",
        f"Turnover pressure remains visible through first-year attrition of {_fmt(metrics.get('first_year_attrition'), '%')}.",
        f"Candidate feedback is {'captured' if flags.get('collects_candidate_feedback') else 'not captured consistently'}, while interview feedback speed still needs attention.",
        f"Ownership is {'clear' if flags.get('named_process_owner') else 'blurred'}, and hiring manager training is {'present' if flags.get('hiring_manager_training') else 'limited'}.",
    ]
    return scores, notes


def generate_report_json(client, data: dict, benchmark_summary: dict) -> dict:
    prompt = _build_user_prompt(data, benchmark_summary)
    response = client.responses.create(
        model="gpt-4.1",
        instructions=SYSTEM_PROMPT,
        input=prompt,
        max_output_tokens=5000,
        temperature=0.4,
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
    normalised = _normalise_report(report, data["section_scores"])
    return _clean_report(normalised, data, benchmark_summary)


def build_fallback_report(data: dict, benchmark_summary: dict) -> dict:
    sections = {}
    for section_id, title, score, note in zip(SECTION_IDS, SECTION_ORDER, data["section_scores"], data["section_notes"]):
        sections[section_id] = {
            "score": score,
            "current_state": [note or f"{title} needs tighter operating control."],
            "key_risks": _fallback_key_risks(title),
            "commercial_impact": [_fallback_commercial_impact(title)],
            "immediate_actions": _fallback_actions_for_section(title),
            "structural_improvements": _fallback_structural_improvements(title),
        }

    report = {
        "executive_overview": "",
        "overall_recruitment_score": "",
        "final_verdict": "",
        "top_strengths": _fallback_strengths(data),
        "top_problems": _fallback_problems(data, benchmark_summary),
        "day_30_plan": [],
        "day_60_plan": [],
        "day_90_plan": [],
        "sections": sections,
    }
    return _clean_report(_normalise_report(report, data["section_scores"]), data, benchmark_summary)


def _build_user_prompt(data: dict, benchmark_summary: dict) -> str:
    strongest = sorted(zip(SECTION_ORDER, data["section_scores"]), key=lambda item: item[1], reverse=True)[:3]
    weakest = sorted(zip(SECTION_ORDER, data["section_scores"]), key=lambda item: item[1])[:3]
    scorecard = "\n".join(
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
- Contact name: {data['contact_name']}
- Job title: {data['job_title']}
- Phone number: {data['phone_number']}
- Email address: {data['email_address']}
- Office address: {data['office_address']}
- Sector: {data['sector']}
- Location: {data['location']}
- Headcount: {data['headcount']}
- Annual hiring volume: {data['annual_hiring_volume']}
- Key roles / job titles hired: {data['key_roles_hired']}

Metrics supplied
{metrics_block}

Operating controls
{flags_block}

Benchmark summary
{benchmark_summary['summary_text']}

Calculated scorecard
{scorecard}

Strongest areas
{chr(10).join(f"- {title}: {score}/10" for title, score in strongest)}

Weakest areas
{chr(10).join(f"- {title}: {score}/10" for title, score in weakest)}

Output requirements
- Use the supplied score for every section.
- Make the writing specific to the business context.
- Be commercially sharp and direct.
- Do not invent facts.
- Keep the final verdict concise.
""".strip()


def create_overall_score_chart(company_name: str, total_score: int) -> Path:
    path = _output_dir() / f"{_slug(company_name)}_overall_score.png"
    score = max(0, min(total_score, 120))
    percentage = round((score / 120) * 100)
    rating = _rating_for_score(score)
    if score >= 90:
        bar_colour = "#4ADE80"
    elif score >= 70:
        bar_colour = "#4ADE80"
    elif score >= 50:
        bar_colour = "#F59E0B"
    elif score >= 30:
        bar_colour = "#F59E0B"
    else:
        bar_colour = "#EF4444"

    fig, ax = plt.subplots(figsize=(6.4, 1.55))
    _apply_chart_style(fig, ax)
    ax.barh([0], [120], color="#E9EDF2", height=0.36)
    ax.barh([0], [score], color=bar_colour, height=0.36)
    ax.set_xlim(0, 120)
    ax.set_ylim(-0.45, 0.45)
    ax.set_yticks([])
    ax.set_xticks(range(0, 121, 20))
    ax.grid(axis="x", alpha=0.10, linestyle="--", color="#D7DCE4")
    fig.text(0.08, 0.92, company_name, fontsize=8.8, color="#5F6876")
    fig.text(0.08, 0.80, "Overall score", fontsize=12, color="#1F2A40", fontweight="bold")
    fig.text(0.92, 0.82, f"{score}/120 | {percentage}% | {rating}", fontsize=9.1, color="#1F2A40", fontweight="bold", ha="right")
    ax.annotate(
        f"{score}/120 ({percentage}%)",
        xy=(score, 0),
        xytext=(0, 10),
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontsize=8.3,
        color="#1F2A40",
        fontweight="bold",
    )
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.60, bottom=0.22)
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def create_section_score_chart(company_name: str, section_scores: list[int]) -> Path:
    path = _output_dir() / f"{_slug(company_name)}_section_scores.png"
    labels = [_short_label(title) for title in SECTION_ORDER]
    positions = list(range(len(labels)))
    colours = [_score_hex(score) for score in section_scores]

    fig, ax = plt.subplots(figsize=(6.5, 5.0))
    _apply_chart_style(fig, ax)
    ax.barh(positions, section_scores, color=colours, edgecolor="none", height=0.52)
    ax.set_xlim(0, 10)
    ax.set_xticks(range(0, 11, 2))
    ax.set_yticks(positions, labels)
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.10, linestyle="--", color="#D7DCE4")
    ax.set_xlabel("Score out of 10", color="#1F2A40", fontsize=8.8, labelpad=6)
    ax.set_title("Section scores", fontsize=12, fontweight="bold", color="#1F2A40", pad=10)
    for pos, score in enumerate(section_scores):
        ax.text(min(score + 0.14, 9.72), pos, f"{score}/10", va="center", fontsize=8.1, color="#1F2A40", fontweight="bold")
    fig.text(0.11, 0.95, company_name, fontsize=8.8, color="#5F6876")
    fig.tight_layout(rect=(0, 0.01, 1, 0.93))
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def create_benchmark_chart(company_name: str, metrics: dict, benchmark: pd.DataFrame) -> Path:
    path = _output_dir() / f"{_slug(company_name)}_benchmark_compare.png"
    benchmark_row = _pick_benchmark_row(benchmark, {})
    items = [
        ("Time to hire", metrics.get("time_to_hire_days"), _safe_float(benchmark_row.get("avg_time_to_hire_days")), "days", False),
        ("Applications per role", metrics.get("applications_per_role"), _safe_float(benchmark_row.get("avg_applications_per_role")), "", True),
        ("Offer acceptance", metrics.get("offer_acceptance"), _safe_float(benchmark_row.get("avg_offer_acceptance_pct")), "%", True),
        ("First-year attrition", metrics.get("first_year_attrition"), _safe_float(benchmark_row.get("avg_attrition_pct")), "%", False),
    ]
    items = [item for item in items if item[1] is not None and item[2] is not None]
    items = _select_benchmark_chart_items(items)

    if not items:
        fig, ax = plt.subplots(figsize=(6.0, 1.2))
        _apply_chart_style(fig, ax)
        ax.axis("off")
        ax.text(0.5, 0.5, "No benchmark comparison available", ha="center", va="center", fontsize=10, color="black")
        fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return path

    fig, axes = plt.subplots(len(items), 1, figsize=(6.5, 1.3 + len(items) * 1.02))
    if len(items) == 1:
        axes = [axes]

    for ax, (label, client_value, benchmark_value, suffix, higher_is_better) in zip(axes, items):
        _apply_chart_style(fig, ax)
        lower = min(client_value, benchmark_value, 0)
        upper = max(client_value, benchmark_value, 1)
        spread = max(upper - lower, upper * 0.2, 1)
        x_min = max(0, lower - spread * 0.2)
        x_max = upper + spread * 0.2
        ahead = client_value >= benchmark_value if higher_is_better else client_value <= benchmark_value

        ax.set_xlim(x_min, x_max)
        ax.set_ylim(-0.55, 0.55)
        ax.hlines(0, x_min, x_max, color="#D7DCE4", linewidth=1.2)
        ax.scatter([benchmark_value], [0], s=58, color="#B5935A", edgecolors="white", linewidths=0.7, zorder=3)
        ax.scatter([client_value], [0], s=68, color="#1F2A40", edgecolors="white", linewidths=0.7, marker="D", zorder=4)
        ax.set_yticks([])
        ax.xaxis.set_major_locator(MaxNLocator(4))
        ax.tick_params(axis="x", labelsize=7.8, colors="#5F6876")
        ax.grid(axis="x", alpha=0.08, linestyle="--", color="#D7DCE4")
        ax.set_title(label, fontsize=10.1, fontweight="bold", color="#1F2A40", pad=4)

        client_offset = 9 if client_value >= benchmark_value else -11
        client_va = "bottom" if client_value >= benchmark_value else "top"
        benchmark_offset = -11 if client_value >= benchmark_value else 9
        benchmark_va = "top" if client_value >= benchmark_value else "bottom"

        ax.annotate(
            f"Client {_format_metric_value(client_value, suffix)}",
            xy=(client_value, 0),
            xytext=(0, client_offset),
            textcoords="offset points",
            ha="center",
            va=client_va,
            fontsize=7.8,
            color="#1F2A40",
            fontweight="bold",
        )
        ax.annotate(
            f"Benchmark {_format_metric_value(benchmark_value, suffix)}",
            xy=(benchmark_value, 0),
            xytext=(0, benchmark_offset),
            textcoords="offset points",
            ha="center",
            va=benchmark_va,
            fontsize=7.7,
            color="#6B7280",
        )
        delta = abs(client_value - benchmark_value)
        direction = "Ahead of benchmark" if ahead else "Behind benchmark"
        ax.text(
            0.0,
            0.03,
            f"{direction} by {_format_metric_value(delta, suffix)}",
            transform=ax.transAxes,
            fontsize=7.8,
            color="#1F2A40",
            fontweight="bold",
        )
        for spine in ax.spines.values():
            spine.set_visible(False)

    fig.suptitle("Benchmark comparison", fontsize=12, fontweight="bold", color="#1F2A40", y=0.985)
    fig.text(0.10, 0.948, company_name, fontsize=8.8, color="#5F6876")
    fig.tight_layout(rect=(0, 0, 1, 0.93), h_pad=0.9)
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def save_pdf_report(
    data: dict,
    report: dict,
    benchmark_summary: dict,
    section_chart: Path,
    overall_chart: Path,
    benchmark_chart: Path,
) -> Path:
    output_path = _output_dir() / f"{_slug(data['company_name'])}_recruitment_audit.pdf"
    report = _clean_report(_normalise_report(report, data["section_scores"]), data, benchmark_summary)
    styles = _build_pdf_styles()

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=PAGE_MARGIN_X,
        rightMargin=PAGE_MARGIN_X,
        topMargin=PAGE_MARGIN_Y,
        bottomMargin=PAGE_MARGIN_Y,
        title=REPORT_TITLE,
        author=BRAND_NAME,
    )

    story = []
    _add_cover_page(story, styles, data)
    _add_md_letter(story, styles, data)
    _add_executive_overview(story, styles, data, report, benchmark_summary)
    _add_overall_score(story, styles, data, report, overall_chart)
    _add_key_insights(story, styles, data, report, benchmark_summary)
    _add_score_summary(story, styles, data)
    _add_benchmark_snapshot(story, styles, benchmark_summary)
    _add_priority_matrix(story, styles, report)
    _add_charts_section(story, styles, section_chart, benchmark_chart)
    _add_detailed_findings(story, styles, report)
    _add_list_section(story, styles, "Top 5 strengths", report["top_strengths"])
    _add_list_section(story, styles, "Top 5 problems", report["top_problems"])
    _add_list_section(story, styles, "30 day plan", report["day_30_plan"])
    _add_list_section(story, styles, "60 day plan", report["day_60_plan"])
    _add_list_section(story, styles, "90 day plan", report["day_90_plan"])
    _add_final_verdict(story, styles, report)

    doc.build(story, onFirstPage=_draw_page, onLaterPages=_draw_page)
    return output_path


def _normalise_report(report: dict, fallback_scores: list[int]) -> dict:
    sections_value = report.get("sections", {}) or {}
    if isinstance(sections_value, list):
        sections = []
        for index, section in enumerate(sections_value):
            section = section or {}
            sections.append(
                {
                    "title": str(section.get("title", SECTION_ORDER[index])),
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

    sections = []
    for index, section_id in enumerate(SECTION_IDS):
        section = (sections_value or {}).get(section_id, {})
        sections.append(
            {
                "title": SECTION_ID_TO_TITLE[section_id],
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


def _clean_report(report: dict, data: dict, benchmark_summary: dict) -> dict:
    cleaned = {
        "executive_overview": _clean_text(report.get("executive_overview"), max_sentences=5, max_words=140),
        "overall_recruitment_score": _clean_text(report.get("overall_recruitment_score"), max_sentences=2, max_words=40),
        "final_verdict": _clean_text(report.get("final_verdict"), max_sentences=3, max_words=65),
        "top_strengths": _clean_list(report.get("top_strengths"), max_items=5, max_words=16),
        "top_problems": _clean_list(report.get("top_problems"), max_items=5, max_words=16),
        "day_30_plan": _clean_list(report.get("day_30_plan"), max_items=5, max_words=16),
        "day_60_plan": _clean_list(report.get("day_60_plan"), max_items=5, max_words=16),
        "day_90_plan": _clean_list(report.get("day_90_plan"), max_items=5, max_words=16),
        "sections": [],
    }

    for index, section in enumerate(report.get("sections", [])):
        current_state_source = section.get("current_state")
        commercial_impact_source = section.get("commercial_impact")
        current_state = _compose_paragraph(
            current_state_source,
            None if current_state_source else data["section_notes"][index],
            max_sentences=3,
            max_words=60,
        )
        commercial_impact = _compose_paragraph(commercial_impact_source, None, max_sentences=2, max_words=42)
        immediate_actions = _clean_list(section.get("immediate_actions"), max_items=2, max_words=14)
        structural_improvements = _clean_list(section.get("structural_improvements"), max_items=2, max_words=14)
        key_risks = _clean_list(section.get("key_risks"), max_items=2, max_words=14)
        cleaned["sections"].append(
            {
                "title": SECTION_ORDER[index],
                "score": int(section.get("score", data["section_scores"][index])),
                "headline": _build_section_headline(SECTION_ORDER[index], int(section.get("score", data["section_scores"][index])), current_state),
                "current_state": current_state,
                "key_risks": key_risks or _fallback_key_risks(SECTION_ORDER[index]),
                "commercial_impact": commercial_impact or _fallback_commercial_impact(SECTION_ORDER[index]),
                "immediate_actions": immediate_actions or _fallback_actions_for_section(SECTION_ORDER[index]),
                "structural_improvements": structural_improvements or _fallback_structural_improvements(SECTION_ORDER[index]),
            }
        )

    if not cleaned["top_strengths"]:
        cleaned["top_strengths"] = _fallback_strengths(data)
    if not cleaned["top_problems"]:
        cleaned["top_problems"] = _fallback_problems(data, benchmark_summary)
    if not cleaned["day_30_plan"]:
        cleaned["day_30_plan"] = _fallback_actions(cleaned["sections"], "immediate_actions")
    if not cleaned["day_60_plan"]:
        cleaned["day_60_plan"] = _fallback_actions(cleaned["sections"], "structural_improvements")
    if not cleaned["day_90_plan"]:
        cleaned["day_90_plan"] = [
            "Reset score ownership across the full recruitment process.",
            "Track the agreed KPIs in a monthly leadership review.",
            "Re-run the audit after process changes are in place.",
        ]
    if not cleaned["overall_recruitment_score"]:
        cleaned["overall_recruitment_score"] = "The overall score points to a recruitment function that is workable, but not yet consistent enough in the areas that matter most."
    if not cleaned["final_verdict"]:
        cleaned["final_verdict"] = "The recruitment function can support current hiring demand, but the weakest areas need tighter control if the business wants better pace, stronger decision quality and lower hiring risk."

    cleaned["executive_overview"] = _build_executive_overview(data, cleaned, benchmark_summary)
    return cleaned


def _build_pdf_styles() -> StyleSheet1:
    styles = StyleSheet1()
    styles.add(
        ParagraphStyle(
            name="CoverBrand",
            fontName=PDF_FONT_BOLD,
            fontSize=17,
            leading=20,
            alignment=TA_CENTER,
            textColor=BRAND_NAVY,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CoverTitle",
            fontName=PDF_FONT_BOLD,
            fontSize=24,
            leading=28,
            alignment=TA_CENTER,
            textColor=BRAND_NAVY,
            spaceAfter=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CoverMeta",
            fontName=PDF_FONT,
            fontSize=10.2,
            leading=13,
            alignment=TA_CENTER,
            textColor=TEXT_COLOR,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CoverMetaLabel",
            fontName=PDF_FONT_BOLD,
            fontSize=8.8,
            leading=10,
            alignment=TA_LEFT,
            textColor=SUBTLE_TEXT,
            spaceAfter=1,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CoverMetaValue",
            fontName=PDF_FONT,
            fontSize=10.2,
            leading=12,
            alignment=TA_LEFT,
            textColor=TEXT_COLOR,
            spaceAfter=1,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Heading1",
            fontName=PDF_FONT_BOLD,
            fontSize=15,
            leading=18,
            alignment=TA_LEFT,
            textColor=BRAND_NAVY,
            spaceBefore=10,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Heading2",
            fontName=PDF_FONT_BOLD,
            fontSize=12,
            leading=14.5,
            alignment=TA_LEFT,
            textColor=BRAND_NAVY,
            spaceBefore=8,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Heading3",
            fontName=PDF_FONT_BOLD,
            fontSize=10,
            leading=12,
            alignment=TA_LEFT,
            textColor=BRAND_NAVY,
            spaceBefore=4,
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Body",
            fontName=PDF_FONT,
            fontSize=10,
            leading=14,
            alignment=TA_LEFT,
            textColor=TEXT_COLOR,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyTight",
            parent=styles["Body"],
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Small",
            fontName=PDF_FONT,
            fontSize=8.4,
            leading=10.2,
            alignment=TA_LEFT,
            textColor=SUBTLE_TEXT,
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionLabel",
            fontName=PDF_FONT_BOLD,
            fontSize=8.2,
            leading=10,
            alignment=TA_LEFT,
            textColor=SUBTLE_TEXT,
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ScoreBadge",
            fontName=PDF_FONT_BOLD,
            fontSize=10,
            leading=12,
            alignment=TA_CENTER,
            textColor=TEXT_COLOR,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Footer",
            fontName=PDF_FONT,
            fontSize=8.2,
            leading=9,
            alignment=TA_LEFT,
            textColor=SUBTLE_TEXT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="List",
            fontName=PDF_FONT,
            fontSize=10,
            leading=12.5,
            textColor=TEXT_COLOR,
            leftIndent=10,
        )
    )
    return styles


def _logo_image(width_mm: float) -> Image | None:
    if not BRAND_LOGO.exists():
        return None
    width = width_mm * mm
    height = width * (186 / 913)
    return Image(str(BRAND_LOGO), width=width, height=height)


def _signature_image(width_mm: float) -> Image | None:
    source = next((path for path in SIGNATURE_CANDIDATES if path.exists()), None)
    if not source:
        return None

    cropped_path = _output_dir() / f"{source.stem}_cropped.png"
    try:
        with PILImage.open(source).convert("RGBA") as image:
            background = PILImage.new("RGBA", image.size, (255, 255, 255, 255))
            diff = ImageChops.difference(image, background).convert("L")
            bbox = diff.point(lambda value: 255 if value > 8 else 0).getbbox()
            if bbox:
                image = image.crop(bbox)
            image.save(cropped_path)
            width = width_mm * mm
            height = width * (image.height / image.width)
    except Exception:
        return None

    return Image(str(cropped_path), width=width, height=height)


def _score_colours(score: int) -> tuple[colors.Color, colors.Color]:
    if score >= 8:
        return GREEN_BG, GREEN_TEXT
    if score >= 6:
        return AMBER_BG, AMBER_TEXT
    return RED_BG, RED_TEXT


def _status_label(score: int) -> str:
    if score >= 8:
        return "Strong"
    if score >= 6:
        return "Needs attention"
    return "Priority"


def _section_card_table(title: str, body: list, background: colors.Color = colors.white) -> Table:
    table = Table([[item] for item in body], colWidths=[170 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("BOX", (0, 0), (-1, -1), 0.6, RULE_COLOR),
                ("ROUNDEDCORNERS", [12, 12, 12, 12]),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _add_cover_page(story: list, styles: StyleSheet1, data: dict) -> None:
    story.append(Spacer(1, 50 * mm))
    logo = _logo_image(90)
    if logo:
        logo.hAlign = "CENTER"
        story.append(logo)
        story.append(Spacer(1, 10 * mm))
    else:
        story.append(Paragraph(BRAND_NAME, styles["CoverBrand"]))
    story.append(Paragraph(REPORT_TITLE, styles["CoverTitle"]))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(_clean_text(data["company_name"]), styles["CoverMeta"]))
    story.append(Spacer(1, 16 * mm))
    meta_rows = [
        [Paragraph("Sector", styles["CoverMetaLabel"]), Paragraph(_clean_text(data["sector"]), styles["CoverMetaValue"])],
        [Paragraph("Location", styles["CoverMetaLabel"]), Paragraph(_clean_text(data["location"]), styles["CoverMetaValue"])],
        [Paragraph("Date", styles["CoverMetaLabel"]), Paragraph(datetime.now().strftime("%d %B %Y"), styles["CoverMetaValue"])],
    ]
    meta_table = Table(meta_rows, colWidths=[42 * mm, 84 * mm], hAlign="CENTER")
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BRAND_PANEL_WARM),
                ("BOX", (0, 0), (-1, -1), 0.45, RULE_COLOR),
                ("LINEBELOW", (0, 0), (-1, -2), 0.35, RULE_COLOR),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph(CONFIDENTIAL_LABEL, styles["CoverMeta"]))
    story.append(Spacer(1, 92 * mm))
    story.append(PageBreak())


def _add_md_letter(story: list, styles: StyleSheet1, data: dict) -> None:
    logo = _logo_image(72)
    if logo:
        story.append(logo)
        story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(f"Dear {_clean_text(data['contact_name'])},", styles["Body"]))

    paragraphs = [
        "Thank you for taking the time to complete this recruitment audit assessment.",
        "This report sets out a clear view of how your recruitment process is currently operating, based on the information provided and our assessment of your hiring activity.",
        "It highlights where your process is working, where it is slowing down, and where inconsistency is likely affecting hiring outcomes. The aim is to give you a straightforward, evidence-based view of what needs attention and where improvements will have the most impact.",
        "You should be able to use this report to guide internal discussion, challenge current ways of working, and prioritise changes that will improve both hiring speed and quality.",
        "If you decide to act on the findings, we can support at different levels depending on what you need.",
        "We can manage job advertising and pass through all applicants, support with advertising and screening to provide a qualified shortlist, or take full ownership of the recruitment process from end to end. This includes advertising, screening, coordinating with hiring managers, managing interviews, collecting feedback, and handling offers.",
        "We can also design structured interview processes for specific roles, including tailored questions and scoring frameworks, to improve consistency and decision-making.",
        "If it would be useful to talk through the report or the next steps, I would be happy to do that with you directly.",
    ]
    for paragraph in paragraphs:
        story.append(Paragraph(paragraph, styles["Body"]))

    signature = _signature_image(34)
    sign_off_block = []
    if signature:
        signature.hAlign = "LEFT"
        sign_off_block.append(Spacer(1, 3 * mm))
        sign_off_block.append(signature)
        sign_off_block.append(Spacer(1, 3 * mm))
    else:
        sign_off_block.append(Spacer(1, 3 * mm))
        sign_off_block.append(Paragraph("[signature]", styles["Small"]))
        sign_off_block.append(Spacer(1, 3 * mm))
    sign_off_block.append(Paragraph(MANAGING_DIRECTOR_NAME, styles["BodyTight"]))
    sign_off_block.append(Paragraph(MANAGING_DIRECTOR_TITLE, styles["BodyTight"]))
    sign_off_block.append(Paragraph(BRAND_NAME, styles["Body"]))
    story.append(KeepTogether(sign_off_block))
    story.append(PageBreak())


def _add_executive_overview(story: list, styles: StyleSheet1, data: dict, report: dict, benchmark_summary: dict) -> None:
    story.append(Paragraph("Executive overview", styles["Heading1"]))
    overview_card = Table([[Paragraph(report["executive_overview"], styles["Body"])]], colWidths=[170 * mm], hAlign="LEFT")
    overview_card.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BRAND_PANEL_WARM),
                ("BOX", (0, 0), (-1, -1), 0.5, RULE_COLOR),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(overview_card)


def _add_overall_score(story: list, styles: StyleSheet1, data: dict, report: dict, overall_chart: Path) -> None:
    story.append(Paragraph("Overall score", styles["Heading1"]))
    score = int(data["total_score"])
    percentage = round((score / 120) * 100)
    rating = _rating_for_score(score)
    rows = [
        ["Total score", f"{score}/120"],
        ["Percentage", f"{percentage}%"],
        ["Rating band", rating],
    ]
    table = Table(rows, colWidths=[46 * mm, 108 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), PDF_FONT),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TEXTCOLOR", (0, 0), (-1, -1), TEXT_COLOR),
                ("BACKGROUND", (0, 0), (-1, -1), BRAND_PANEL_WARM),
                ("BACKGROUND", (0, 0), (0, -1), TABLE_SHADE),
                ("BOX", (0, 0), (-1, -1), 0.45, RULE_COLOR),
                ("LINEBELOW", (0, 0), (-1, -2), 0.35, RULE_COLOR),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 4 * mm))
    if overall_chart.exists():
        story.append(Image(str(overall_chart), width=CHART_WIDTH, height=CHART_WIDTH * 0.23))
        story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(report["overall_recruitment_score"], styles["Body"]))


def _add_key_insights(story: list, styles: StyleSheet1, data: dict, report: dict, benchmark_summary: dict) -> None:
    story.append(Paragraph("Key insights", styles["Heading1"]))
    insight_rows = [[Paragraph(_clean_text(line), styles["BodyTight"])] for line in _build_key_insights(data, report, benchmark_summary)]
    table = Table(insight_rows, colWidths=[170 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), PDF_FONT),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TEXTCOLOR", (0, 0), (-1, -1), TEXT_COLOR),
                ("BACKGROUND", (0, 0), (-1, -1), BRAND_PANEL_WARM),
                ("BOX", (0, 0), (-1, -1), 0.45, RULE_COLOR),
                ("LINEBELOW", (0, 0), (-1, -2), 0.35, RULE_COLOR),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(table)


def _add_score_summary(story: list, styles: StyleSheet1, data: dict) -> None:
    story.append(Paragraph("Score summary table", styles["Heading1"]))
    rows = [["Section", "Score", "Position"]]
    for title, score in zip(SECTION_ORDER, data["section_scores"]):
        rows.append([title, f"{score}/10", _section_rating(score)])
    table = Table(rows, colWidths=[108 * mm, 24 * mm, 38 * mm], repeatRows=1, hAlign="LEFT")
    table.setStyle(_table_style())
    story.append(table)


def _add_benchmark_snapshot(story: list, styles: StyleSheet1, benchmark_summary: dict) -> None:
    comparisons = benchmark_summary.get("comparisons", [])
    if not comparisons:
        return
    story.append(Paragraph("Benchmark snapshot", styles["Heading1"]))
    rows = [["Metric", "Client", "Benchmark", "Position"]]
    for item in comparisons:
        rows.append(
            [
                item["label"],
                _format_metric_value(item["client_value"], item["suffix"]),
                _format_metric_value(item["benchmark_value"], item["suffix"]),
                item["comment"],
            ]
        )
    table = Table(rows, colWidths=[50 * mm, 28 * mm, 30 * mm, 62 * mm], repeatRows=1, hAlign="LEFT")
    table.setStyle(_table_style())
    story.append(table)
    story.append(Spacer(1, 1.5 * mm))


def _add_priority_matrix(story: list, styles: StyleSheet1, report: dict) -> None:
    story.append(Paragraph("Priority matrix", styles["Heading1"]))
    story.append(
        Paragraph(
            "This matrix groups the most important issues by likely commercial impact and the urgency of action.",
            styles["Body"],
        )
    )
    quadrants = _build_priority_matrix(report)
    cells = []
    for item in quadrants:
        cell_body = [
            Paragraph(item["eyebrow"], styles["SectionLabel"]),
            Paragraph(item["title"], styles["Heading3"]),
        ]
        for row in item["items"]:
            cell_body.append(Paragraph(f"{row['title']}", styles["BodyTight"]))
            cell_body.append(Paragraph(f"Action: {row['action']}", styles["Small"]))
        if not item["items"]:
            cell_body.append(Paragraph("No additional areas currently sit in this quadrant.", styles["Small"]))
        cell = Table([[entry] for entry in cell_body], colWidths=[80 * mm])
        cell.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), item["background"]),
                    ("BOX", (0, 0), (-1, -1), 0.45, RULE_COLOR),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        cells.append(cell)
    matrix = Table([[cells[0], cells[1]], [cells[2], cells[3]]], colWidths=[84 * mm, 84 * mm], hAlign="LEFT")
    matrix.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    story.append(matrix)


def _add_charts_section(story: list, styles: StyleSheet1, section_chart: Path, benchmark_chart: Path) -> None:
    story.append(PageBreak())
    story.append(Spacer(1, -5 * mm))
    story.append(Paragraph("Charts and visual analysis", styles["Heading1"]))
    if section_chart.exists():
        story.append(Image(str(section_chart), width=CHART_WIDTH, height=CHART_WIDTH * 0.72))
        story.append(Paragraph("Section score profile across all twelve audit areas.", styles["Small"]))
    if benchmark_chart.exists():
        story.append(Spacer(1, 1 * mm))
        story.append(Image(str(benchmark_chart), width=CHART_WIDTH, height=CHART_WIDTH * 0.55))
        story.append(Paragraph("Benchmark comparison for the most useful submitted metrics.", styles["Small"]))


def _add_detailed_findings(story: list, styles: StyleSheet1, report: dict) -> None:
    story.append(PageBreak())
    story.append(Paragraph("Detailed findings", styles["Heading1"]))
    for section in report["sections"]:
        score_bg, score_text = _score_colours(section["score"])
        badge = Table(
            [[Paragraph(f"{section['score']}/10", styles["ScoreBadge"]), Paragraph(_status_label(section["score"]), styles["Small"])]],
            colWidths=[18 * mm, 30 * mm],
        )
        badge.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), score_bg),
                    ("TEXTCOLOR", (0, 0), (-1, -1), score_text),
                    ("BOX", (0, 0), (-1, -1), 0.4, score_bg),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        header = Table(
            [[Paragraph(section["title"], styles["Heading2"]), badge]],
            colWidths=[122 * mm, 48 * mm],
            hAlign="LEFT",
        )
        header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))

        actions = list(dict.fromkeys(section["immediate_actions"] + section["structural_improvements"]))[:3]
        block = [
            header,
            Paragraph(section["headline"], styles["Body"]),
            Paragraph("Current state", styles["Heading3"]),
            Paragraph(section["current_state"], styles["Body"]),
            Paragraph("Key risks", styles["Heading3"]),
            _bullet_list(section["key_risks"], styles),
            Paragraph("Commercial impact", styles["Heading3"]),
            Paragraph(section["commercial_impact"], styles["Body"]),
            Paragraph("Actions", styles["Heading3"]),
            _bullet_list(actions, styles),
        ]
        story.append(KeepTogether(_section_card_table(section["title"], block, background=BRAND_PANEL_ALT)))
        story.append(Spacer(1, 3 * mm))


def _add_list_section(story: list, styles: StyleSheet1, title: str, items: list[str]) -> None:
    story.append(Paragraph(title, styles["Heading1"]))
    story.append(_bullet_list(items, styles))


def _add_final_verdict(story: list, styles: StyleSheet1, report: dict) -> None:
    story.append(Paragraph("Final verdict", styles["Heading1"]))
    for paragraph in _build_final_verdict_paragraphs(report):
        story.append(Paragraph(paragraph, styles["Body"]))


def _bullet_list(items: list[str], styles: StyleSheet1) -> ListFlowable:
    list_items = [
        ListItem(Paragraph(_clean_text(item, max_sentences=1, max_words=18), styles["BodyTight"]), leftIndent=0)
        for item in items
        if _clean_text(item, max_sentences=1, max_words=18)
    ]
    return ListFlowable(
        list_items,
        bulletType="bullet",
        bulletFontName=PDF_FONT,
        bulletFontSize=9,
        bulletOffsetY=1,
        leftIndent=10,
    )


def _table_style() -> TableStyle:
    return TableStyle(
        [
            ("FONTNAME", (0, 0), (-1, 0), PDF_FONT_BOLD),
            ("FONTNAME", (0, 1), (-1, -1), PDF_FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("TEXTCOLOR", (0, 0), (-1, -1), TEXT_COLOR),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, RULE_COLOR),
            ("LINEBELOW", (0, 1), (-1, -1), 0.35, RULE_COLOR),
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_PANEL_ALT]),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
    )


def _draw_page(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(RULE_COLOR)
    canvas.line(doc.leftMargin, PAGE_HEIGHT - 10 * mm, PAGE_WIDTH - doc.rightMargin, PAGE_HEIGHT - 10 * mm)
    canvas.setFont(PDF_FONT_BOLD, 8)
    canvas.setFillColor(BRAND_NAVY)
    canvas.drawString(doc.leftMargin, PAGE_HEIGHT - 8.2 * mm, BRAND_NAME)
    if canvas.getPageNumber() > 2:
        canvas.setStrokeColor(RULE_COLOR)
        canvas.line(doc.leftMargin, 11 * mm, PAGE_WIDTH - doc.rightMargin, 11 * mm)
        canvas.setFont(PDF_FONT, 8)
        canvas.setFillColor(SUBTLE_TEXT)
        canvas.drawString(doc.leftMargin, 7.6 * mm, "Confidential client report")
        canvas.drawRightString(PAGE_WIDTH - doc.rightMargin, 7.6 * mm, f"Page {canvas.getPageNumber() - 2}")
    canvas.restoreState()


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
        if ratio >= 1.20:
            return 8.8
        if ratio >= 1.05:
            return 7.8
        if ratio >= 0.95:
            return 6.8
        if ratio >= 0.80:
            return 5.5
        return 4.0
    if ratio <= 0.80:
        return 8.8
    if ratio <= 0.95:
        return 7.8
    if ratio <= 1.05:
        return 6.8
    if ratio <= 1.20:
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
        "Recruitment strategy and workforce planning": "Strategy and planning",
        "Performance metrics and funnel conversion": "Metrics and funnel",
        "Employer brand and market perception": "Employer brand",
        "Job adverts and job specifications": "Job adverts and specs",
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
    if total_score >= 90:
        return "High performing"
    if total_score >= 70:
        return "Strong but inconsistent"
    if total_score >= 50:
        return "Functional but inconsistent"
    if total_score >= 30:
        return "Underperforming"
    return "Broken"


def _section_rating(score: int) -> str:
    if score >= 8:
        return "Strong"
    if score >= 6:
        return "Sound with gaps"
    if score >= 4:
        return "Inconsistent"
    return "Weak"


def _score_hex(score: int) -> str:
    if score >= 8:
        return "#4ADE80"
    if score >= 6:
        return "#F59E0B"
    if score >= 4:
        return "#EF4444"
    return "#EF4444"


def _fmt(value: float | None, suffix: str) -> str:
    return "not provided" if value is None else _format_metric_value(value, suffix)


def _build_priority_matrix(report: dict) -> list[dict]:
    sections = report.get("sections", [])
    weakest = sorted(sections, key=lambda item: item["score"])[:4]
    strongest = sorted(sections, key=lambda item: item["score"], reverse=True)[:2]
    watch = [item for item in sections if 6 <= item["score"] <= 7 and item not in weakest][:2]

    def row(section: dict) -> dict:
        return {
            "title": section["title"],
            "action": (section.get("immediate_actions") or ["Set one named owner and correct the process discipline."])[0],
        }

    return [
        {
            "eyebrow": "High impact | High urgency",
            "title": "Stabilise now",
            "background": RED_BG,
            "items": [row(item) for item in weakest[:2]],
        },
        {
            "eyebrow": "High impact | Lower urgency",
            "title": "Tighten next",
            "background": AMBER_BG,
            "items": [row(item) for item in weakest[2:4]],
        },
        {
            "eyebrow": "Lower impact | High visibility",
            "title": "Monitor",
            "background": TABLE_SHADE,
            "items": [row(item) for item in watch],
        },
        {
            "eyebrow": "Lower impact | Lower urgency",
            "title": "Maintain",
            "background": GREEN_BG,
            "items": [row(item) for item in strongest],
        },
    ]


def _build_executive_overview(data: dict, report: dict, benchmark_summary: dict) -> str:
    strongest = max(zip(SECTION_ORDER, data["section_scores"]), key=lambda item: item[1])
    weakest = min(zip(SECTION_ORDER, data["section_scores"]), key=lambda item: item[1])
    next_step = report["day_30_plan"][0] if report["day_30_plan"] else "assign one named owner to the weakest part of the process"
    comparisons = benchmark_summary.get("comparisons", [])
    benchmark_line = ""
    if comparisons:
        highlight = comparisons[0]
        benchmark_line = f"Against the UK benchmark, {highlight['label'].lower()} is {highlight['comment'].lower()}."

    sentences = [
        f"The recruitment process is {_rating_for_score(data['total_score']).lower()} at {data['total_score']}/120.",
        f"{strongest[0]} is holding up best at {strongest[1]}/10, while {weakest[0].lower()} is the clearest operational weakness at {weakest[1]}/10.",
        "The main commercial drag is uneven process control, which is likely slowing decisions and weakening hiring consistency.",
        benchmark_line,
        f"The immediate priority is to {next_step.rstrip('.').lower()}.",
    ]
    text = " ".join(sentence for sentence in sentences if sentence)
    return _clean_text(text, max_sentences=5, max_words=145)


def _build_key_insights(data: dict, report: dict, benchmark_summary: dict) -> list[str]:
    strongest = max(zip(SECTION_ORDER, data["section_scores"]), key=lambda item: item[1])
    weakest = min(zip(SECTION_ORDER, data["section_scores"]), key=lambda item: item[1])
    comparisons = benchmark_summary.get("comparisons", [])
    benchmark_line = "Benchmark comparison was limited by the data supplied."
    if comparisons:
        item = comparisons[0]
        benchmark_line = f"{item['label']} is {item['comment'].lower()}."
    first_problem = report["top_problems"][0] if report["top_problems"] else "Process control is uneven."
    first_action = report["day_30_plan"][0] if report["day_30_plan"] else "Tighten the weakest area first."
    return [
        f"Strongest area: {strongest[0]} at {strongest[1]}/10.",
        f"Weakest area: {weakest[0]} at {weakest[1]}/10.",
        benchmark_line,
        f"Immediate priority: {first_action.rstrip('.')}.",
    ]


def _build_final_verdict_paragraphs(report: dict) -> list[str]:
    sections = report.get("sections", [])
    if not sections:
        return [
            "The recruitment operating model can support current hiring activity, but it is not yet controlled closely enough to give leadership a dependable result.",
            "The main risk is uneven execution across the hiring process, which is likely creating delay, wasted effort and weaker decision quality.",
            "The next step is to tighten ownership, simplify control points and manage the process against a smaller set of hard measures so hiring becomes more predictable.",
        ]

    strongest = max(sections, key=lambda section: section["score"])
    weakest = min(sections, key=lambda section: section["score"])
    total_score = sum(section["score"] for section in sections)
    rating = _rating_for_score(total_score).lower()
    return [
        _clean_text(
            f"The recruitment operating model is {rating} at {total_score}/120. {strongest['title']} is providing the strongest foundation, but that is being diluted by weaker control in {weakest['title'].lower()}.",
            max_sentences=2,
            max_words=42,
        ),
        _clean_text(
            f"The main business risk is weak control in {weakest['title'].lower()}. That is likely slowing hiring decisions, increasing avoidable process waste and making hiring outcomes less reliable than they should be.",
            max_sentences=2,
            max_words=40,
        ),
        _clean_text(
            f"The next step is to tighten the weakest operating controls, assign clearer accountability and manage performance more closely. That matters because stronger discipline in those areas will improve pace, raise decision quality and give the business a more dependable hiring model.",
            max_sentences=2,
            max_words=42,
        ),
    ]


def _select_benchmark_comparisons(comparisons: list[dict]) -> list[dict]:
    useful = [item for item in comparisons if item["status"] != "In line"]
    if useful:
        return useful[:3]
    return comparisons[:2]


def _select_benchmark_chart_items(items: list[tuple]) -> list[tuple]:
    if len(items) <= 3:
        return items
    return items[:3]


def _format_metric_value(value: float | None, suffix: str) -> str:
    if value is None:
        return "n/a"
    if float(value).is_integer():
        number = str(int(value))
    else:
        number = f"{value:.1f}".rstrip("0").rstrip(".")
    if suffix == "days":
        return f"{number} days"
    if suffix == "%":
        return f"{number}%"
    return number


def _ensure_list(value, min_items: int) -> list[str]:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
    elif value:
        items = [str(value).strip()]
    else:
        items = []
    while len(items) < min_items:
        items.append("")
    return items


def _clean_text(value, max_sentences: int | None = None, max_words: int | None = None) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        value = " ".join(str(item) for item in value)
    text = str(value).replace("\r", "\n")
    text = re.sub(r"(?m)^\s*[*#>-]+\s*", "", text)
    text = re.sub(r"(?m)^\s*\d+[.)]\s*", "", text)
    text = text.replace("•", " ")
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"This area needs clearer definition in the next review cycle\.?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    replacements = {
        "This area needs clearer definition in the next review cycle.": "",
        "best-in-class": "strong",
        "best in class": "strong",
        "robust": "clear",
        "hampered": "slowed",
        "material": "clear",
        "leverage": "use",
        "seamless": "consistent",
        "laid the groundwork": "created a base",
        "it is important to note": "",
        "overall this suggests": "",
        "in today's market": "",
    }
    for source, target in replacements.items():
        if " " in source or "-" in source:
            text = re.sub(re.escape(source), target, text, flags=re.IGNORECASE)
        else:
            text = re.sub(rf"\b{re.escape(source)}\b", target, text, flags=re.IGNORECASE)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    text = re.sub(r"([.?!]){2,}", r"\1", text)
    text = re.sub(r"\b(top_problems|day_30_plan|day_60_plan|day_90_plan|sections)\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s{2,}", " ", text).strip()
    if max_sentences is not None:
        text = " ".join(_split_sentences(text)[:max_sentences])
    if max_words is not None:
        words = text.split()
        if len(words) > max_words:
            text = " ".join(words[:max_words]).rstrip(",;:")
            if text and text[-1] not in ".!?":
                text += "."
    return text.strip()


def _clean_list(items, max_items: int, max_words: int = 16) -> list[str]:
    if items is None:
        source = []
    elif isinstance(items, list):
        source = items
    else:
        source = [items]
    cleaned = []
    for item in source:
        text = _clean_text(item, max_sentences=1, max_words=max_words)
        if text:
            cleaned.append(text)
        if len(cleaned) >= max_items:
            break
    return cleaned


def _compose_paragraph(value, fallback: str | None, max_sentences: int, max_words: int) -> str:
    fragments = []
    if isinstance(value, list):
        fragments.extend(value)
    elif value:
        fragments.append(value)
    if fallback:
        fragments.append(fallback)
    sentences = []
    seen = set()
    for fragment in fragments:
        for sentence in _split_sentences(_clean_text(fragment, max_sentences=2, max_words=max_words)):
            key = sentence.lower()
            if key not in seen:
                sentences.append(sentence)
                seen.add(key)
            if len(sentences) >= max_sentences:
                return _clean_text(" ".join(sentences), max_sentences=max_sentences, max_words=max_words)
    return _clean_text(" ".join(sentences), max_sentences=max_sentences, max_words=max_words)


def _build_section_headline(title: str, score: int, current_state: str) -> str:
    title_lower = title.lower()
    if score >= 8:
        templates = [
            f"{title} is operating from a stronger base than the rest of the hiring process.",
            f"{title} is one of the more controlled parts of the recruitment model.",
            f"{title} is giving the business a more dependable platform than most other areas.",
        ]
    elif score >= 6:
        templates = [
            f"{title} is workable, but control and consistency still need tightening.",
            f"{title} is serviceable, though delivery discipline is not yet consistent enough.",
            f"{title} is holding together, but it is still not controlled tightly enough.",
        ]
    elif score >= 4:
        templates = [
            f"{title} is creating avoidable drag in the recruitment process.",
            f"{title} is starting to slow pace and weaken consistency across the wider process.",
            f"{title} is exposing the hiring model to delay and uneven execution.",
        ]
    else:
        templates = [
            f"{title} is a clear operational weakness in the current hiring model.",
            f"{title} is one of the main breakdown points in the recruitment process.",
            f"{title} is materially weakening control across the hiring cycle.".replace("materially", "clearly"),
        ]
    index = sum(ord(char) for char in title_lower) % len(templates)
    return templates[index]


def _fallback_key_risks(title: str) -> list[str]:
    return [
        f"{title} is leaving too much room for inconsistency.",
        "Slow decisions and uneven execution will continue if ownership stays unclear.",
    ]


def _fallback_commercial_impact(title: str) -> str:
    return f"Weakness in {title.lower()} is likely increasing time to hire and reducing confidence in hiring decisions."


def _fallback_actions_for_section(title: str) -> list[str]:
    return [
        f"Set one named owner for {title.lower()}.",
        "Agree the next operating change and track it weekly.",
    ]


def _fallback_structural_improvements(title: str) -> list[str]:
    return [
        f"Standardise how {title.lower()} is managed across all hires.",
        "Review delivery against the agreed process each month.",
    ]


def _split_sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [part.strip() for part in parts if part.strip()]


def _fallback_strengths(data: dict) -> list[str]:
    strongest = sorted(zip(SECTION_ORDER, data["section_scores"]), key=lambda item: item[1], reverse=True)[:5]
    return [f"{title} is currently scoring {score}/10." for title, score in strongest]


def _fallback_problems(data: dict, benchmark_summary: dict) -> list[str]:
    weakest = sorted(zip(SECTION_ORDER, data["section_scores"]), key=lambda item: item[1])[:4]
    problems = [f"{title} is currently scoring {score}/10." for title, score in weakest]
    for item in benchmark_summary.get("comparisons", []):
        if item["status"] != "In line":
            problems.append(f"{item['label']} is {item['comment'].lower()}.")
            break
    return problems[:5]


def _fallback_actions(sections: list[dict], key: str) -> list[str]:
    actions = []
    for section in sorted(sections, key=lambda item: item["score"])[:3]:
        actions.extend(section[key][:1])
    return actions[:3]


def _apply_chart_style(fig, ax) -> None:
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.tick_params(axis="x", colors="black", labelsize=8)
    ax.tick_params(axis="y", colors="black", labelsize=8)
    for spine in ax.spines.values():
        spine.set_visible(False)
