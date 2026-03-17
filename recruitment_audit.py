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
BENCHMARK_CSV_FILE = BASE_DIR / "data" / "uk_recruitment_benchmarks.csv"
OUTPUT_DIR = Path(os.environ.get("AUDIT_OUTPUT_DIR", "/tmp/BradfordMarshAI"))
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

BENCHMARK_REQUIRED_COLUMNS = [
    "benchmark_type",
    "category",
    "time_to_hire_days",
    "applications_per_role",
    "offer_acceptance_rate",
    "first_year_attrition_rate",
    "application_to_interview_rate",
    "interview_to_offer_rate",
    "source",
    "year",
    "notes",
]

BENCHMARK_NUMERIC_COLUMNS = [
    "time_to_hire_days",
    "applications_per_role",
    "offer_acceptance_rate",
    "first_year_attrition_rate",
    "application_to_interview_rate",
    "interview_to_offer_rate",
]

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
- Every section diagnosis must identify the stage of the hiring process, the supporting metric or observable behaviour, and the root cause.
- Every commercial impact statement must refer to time, cost or revenue exposure.
- Every action must name an owner, a timeframe, and a measurable outcome.
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
    df = load_benchmarks()
    return (
        df.loc[df["benchmark_type"] == "industry", "category"]
        .dropna()
        .astype(str)
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .drop_duplicates()
        .sort_values(key=lambda col: col.str.lower())
        .tolist()
    )


def load_benchmarks(sector: str | None = None) -> pd.DataFrame:
    benchmark_path = BENCHMARK_CSV_FILE
    if not benchmark_path.exists():
        raise FileNotFoundError(f"Benchmark dataset not found at {benchmark_path}")
    try:
        df = pd.read_csv(benchmark_path)
    except Exception as exc:
        raise ValueError(f"Unable to read benchmark dataset at {benchmark_path}: {exc}") from exc
    return _normalise_benchmark_columns(df, benchmark_path)


def get_benchmark(sector: str, role: str, benchmarks: pd.DataFrame | None = None) -> pd.Series:
    df = load_benchmarks() if benchmarks is None else benchmarks.copy()
    if df.empty:
        raise ValueError("Benchmark dataset is empty.")

    industry_row = _select_benchmark_by_type(df, "industry", sector)
    function_row = _select_function_benchmark(df, role)

    if not industry_row.empty and not function_row.empty:
        return _blend_benchmarks(industry_row, function_row)
    if not industry_row.empty:
        return industry_row
    if not function_row.empty:
        return function_row
    industry_average = _average_benchmark(df, "industry")
    function_average = _average_benchmark(df, "function")
    if not industry_average.empty and not function_average.empty:
        return _blend_benchmarks(industry_average, function_average)
    if not industry_average.empty:
        return industry_average
    if not function_average.empty:
        return function_average
    return _average_benchmark(df, "all")


def _normalise_benchmark_columns(df: pd.DataFrame, benchmark_path: Path) -> pd.DataFrame:
    renamed = df.copy()
    renamed.columns = [str(col).strip() for col in renamed.columns]
    missing = [column for column in BENCHMARK_REQUIRED_COLUMNS if column not in renamed.columns]
    if missing:
        raise ValueError(f"Benchmark dataset at {benchmark_path} is missing required columns: {', '.join(missing)}")

    renamed = renamed[BENCHMARK_REQUIRED_COLUMNS].copy()
    renamed["benchmark_type"] = renamed["benchmark_type"].astype(str).str.strip().str.lower()
    renamed["category"] = renamed["category"].astype(str).str.strip()
    invalid_types = sorted(set(renamed["benchmark_type"]) - {"industry", "function"})
    if invalid_types:
        raise ValueError(f"Benchmark dataset at {benchmark_path} contains invalid benchmark_type values: {', '.join(invalid_types)}")
    for column in BENCHMARK_NUMERIC_COLUMNS:
        renamed[column] = pd.to_numeric(renamed[column], errors="coerce")
    if renamed["category"].replace("", pd.NA).isna().any():
        raise ValueError(f"Benchmark dataset at {benchmark_path} contains blank category values.")
    renamed["source"] = renamed["source"].fillna("").astype(str).str.strip()
    renamed["year"] = renamed["year"].where(pd.notna(renamed["year"]), pd.NA)
    renamed["notes"] = renamed["notes"].fillna("").astype(str).str.strip()
    return renamed.reset_index(drop=True)


def build_benchmark_summary(metrics: dict, benchmark: pd.DataFrame, sector: str, role: str) -> dict:
    benchmark_row = get_benchmark(sector, role, benchmark)
    if benchmark_row.empty:
        return {"benchmark_row": {}, "comparisons": [], "summary_text": "No benchmark data available."}

    mapping = [
        ("time_to_hire_days", "time_to_hire_days", "Time to hire", "days", False),
        ("applications_per_role", "applications_per_role", "Applications per role", "", True),
        ("offer_acceptance", "offer_acceptance_rate", "Offer acceptance", "%", True),
        ("first_year_attrition", "first_year_attrition_rate", "First-year attrition", "%", False),
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
            above = delta > 0
            status = "Above" if above else "Below"
            direction = "above benchmark" if above else "below benchmark"
            comment = f"{_format_metric_value(abs(delta), suffix)} {direction}"
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
            _safe_float(benchmark_row.get("time_to_hire_days")),
            higher_is_better=False,
        ),
        "applications": _metric_score(
            metrics.get("applications_per_role"),
            _safe_float(benchmark_row.get("applications_per_role")),
            higher_is_better=True,
        ),
        "offer_acceptance": _metric_score(
            metrics.get("offer_acceptance"),
            _safe_float(benchmark_row.get("offer_acceptance_rate")),
            higher_is_better=True,
        ),
        "attrition": _metric_score(
            metrics.get("first_year_attrition"),
            _safe_float(benchmark_row.get("first_year_attrition_rate")),
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
        _attrition_note(
            metrics.get("first_year_attrition"),
            "onboarding",
            "documented" if flags.get("formal_onboarding") else "lightly controlled",
        ),
        _attrition_note(metrics.get("first_year_attrition"), "turnover"),
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
- In each section diagnosis, state the exact hiring stage, the supporting metric or observable behaviour, and the root cause.
- In each commercial impact paragraph, refer to time, cost or revenue exposure.
- In each action, name the owner, timeframe and measurable outcome.
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


def create_benchmark_chart(company_name: str, metrics: dict, benchmark: pd.DataFrame, sector: str, role: str) -> Path:
    path = _output_dir() / f"{_slug(company_name)}_benchmark_compare.png"
    benchmark_row = get_benchmark(sector, role, benchmark)
    items = [
        ("Time to hire", metrics.get("time_to_hire_days"), _safe_float(benchmark_row.get("time_to_hire_days")), "days", False),
        ("Applications per role", metrics.get("applications_per_role"), _safe_float(benchmark_row.get("applications_per_role")), "", True),
        ("Offer acceptance", metrics.get("offer_acceptance"), _safe_float(benchmark_row.get("offer_acceptance_rate")), "%", True),
        ("First-year attrition", metrics.get("first_year_attrition"), _safe_float(benchmark_row.get("first_year_attrition_rate")), "%", False),
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
        "core_constraint": "",
        "sections": [],
    }

    for index, section in enumerate(report.get("sections", [])):
        title = SECTION_ORDER[index]
        score = int(section.get("score", data["section_scores"][index]))
        current_state = _build_section_current_state(title, score, data, benchmark_summary)
        commercial_impact = _build_section_commercial_impact(title, score, data, benchmark_summary)
        immediate_actions, structural_improvements = _build_section_actions(title, score, data)
        key_risks = _build_section_key_risks(title, score, data, benchmark_summary)
        cleaned["sections"].append(
            {
                "title": title,
                "score": score,
                "headline": _build_section_headline(title, score, data, benchmark_summary),
                "current_state": current_state,
                "key_risks": key_risks,
                "commercial_impact": commercial_impact,
                "immediate_actions": immediate_actions,
                "structural_improvements": structural_improvements,
            }
        )

    cleaned["top_strengths"] = _build_top_strengths(cleaned["sections"])
    cleaned["top_problems"] = _build_top_problems(cleaned["sections"], benchmark_summary)
    cleaned["day_30_plan"] = _build_day_plan(cleaned["sections"], 30)
    cleaned["day_60_plan"] = _build_day_plan(cleaned["sections"], 60)
    cleaned["day_90_plan"] = _build_day_plan(cleaned["sections"], 90)
    if not cleaned["overall_recruitment_score"]:
        cleaned["overall_recruitment_score"] = "The overall score points to a recruitment function that is workable, but not yet consistent enough in the areas that matter most."
    if not cleaned["final_verdict"]:
        cleaned["final_verdict"] = "The recruitment function can support current hiring demand, but the weakest areas need tighter control if the business wants better pace, stronger decision quality and lower hiring risk."

    cleaned["executive_overview"] = _build_executive_overview(data, cleaned, benchmark_summary)
    cleaned["core_constraint"] = _build_core_constraint(data, cleaned, benchmark_summary)
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
        "This report gives you a clear view of how the recruitment operating model is performing across planning, process control, delivery pace and decision quality. It reflects the information provided and tests how the current hiring process is working in practice rather than how it is intended to work on paper.",
        "The findings are designed to show where hiring performance is being protected, where it is drifting, and where weak control is likely increasing delay, process waste or avoidable hiring risk. That matters because small failures in recruitment execution quickly become a commercial problem when they affect speed, quality and management time.",
        "Used properly, this report should help you challenge current assumptions, focus discussion on the parts of the process that need intervention first, and decide where tighter ownership or better operating discipline is required. It is intended to support leadership judgement, not sit as a passive summary.",
        "If you decide to act on the findings, Bradford & Marsh can support at the level that suits the business. That may mean improving advertising and screening, taking ownership of end-to-end delivery, or designing a more structured interview and decision process so hiring becomes faster, clearer and more consistent.",
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
    story.append(Spacer(1, 3 * mm))
    constraint_card = Table(
        [
            [Paragraph("Core Constraint", styles["SectionLabel"])],
            [Paragraph(report["core_constraint"], styles["Body"])],
        ],
        colWidths=[170 * mm],
        hAlign="LEFT",
    )
    constraint_card.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BRAND_PANEL_ALT),
                ("BOX", (0, 0), (-1, -1), 0.5, RULE_COLOR),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(constraint_card)


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
            _bullet_list(section["key_risks"], styles, max_words=22),
            Paragraph("Commercial impact", styles["Heading3"]),
            Paragraph(section["commercial_impact"], styles["Body"]),
            Paragraph("Actions", styles["Heading3"]),
            _bullet_list(actions, styles, max_words=42),
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


def _bullet_list(items: list[str], styles: StyleSheet1, max_words: int = 18) -> ListFlowable:
    list_items = [
        ListItem(Paragraph(_clean_text(item, max_sentences=2, max_words=max_words), styles["BodyTight"]), leftIndent=0)
        for item in items
        if _clean_text(item, max_sentences=2, max_words=max_words)
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

def _pick_benchmark_row(benchmark: pd.DataFrame, data: dict) -> pd.Series:
    return get_benchmark(str(data.get("sector", "")), str(data.get("key_roles_hired", "")), benchmark)


def _normalise_category(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").strip().lower()).strip()


def _extract_role_candidates(role: str) -> list[str]:
    text = str(role or "").strip()
    if not text:
        return []
    parts = re.split(r",|/|;|\band\b|\n", text, flags=re.IGNORECASE)
    cleaned = []
    for part in parts:
        value = _normalise_category(part)
        if value and value not in cleaned:
            cleaned.append(value)
    return cleaned


def _closest_benchmark_match(frame: pd.DataFrame, target: str) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=object)
    normalised_target = _normalise_category(target)
    if not normalised_target:
        return pd.Series(dtype=object)

    working = frame.copy()
    working["_match_key"] = working["category"].map(_normalise_category)
    exact = working[working["_match_key"] == normalised_target]
    if not exact.empty:
        return exact.iloc[0].drop(labels="_match_key")
    return pd.Series(dtype=object)


def _average_benchmark(frame: pd.DataFrame, benchmark_type: str) -> pd.Series:
    working = frame.copy()
    if benchmark_type in {"industry", "function"}:
        typed = working[working["benchmark_type"] == benchmark_type]
        if not typed.empty:
            working = typed
    if working.empty:
        return pd.Series(dtype=object)

    averaged = {column: working[column].mean(skipna=True) for column in BENCHMARK_NUMERIC_COLUMNS}
    averaged.update(
        {
            "benchmark_type": benchmark_type,
            "category": "Average benchmark",
            "source": "Weighted dataset average",
            "year": pd.NA,
            "notes": f"Average benchmark fallback for {benchmark_type}.",
        }
    )
    return pd.Series(averaged)


def _select_benchmark_by_type(df: pd.DataFrame, benchmark_type: str, target: str) -> pd.Series:
    if not _normalise_category(target):
        return pd.Series(dtype=object)
    typed = df[df["benchmark_type"] == benchmark_type].reset_index(drop=True)
    if typed.empty:
        return pd.Series(dtype=object)

    matched = _closest_benchmark_match(typed, target)
    return matched if not matched.empty else pd.Series(dtype=object)


def _select_function_benchmark(df: pd.DataFrame, role: str) -> pd.Series:
    if not _extract_role_candidates(role):
        return pd.Series(dtype=object)
    typed = df[df["benchmark_type"] == "function"].reset_index(drop=True)
    if typed.empty:
        return pd.Series(dtype=object)

    for candidate in _extract_role_candidates(role):
        matched = _closest_benchmark_match(typed, candidate)
        if not matched.empty:
            return matched
    return pd.Series(dtype=object)


def _blend_benchmarks(industry_row: pd.Series, function_row: pd.Series) -> pd.Series:
    blended = {}
    for column in BENCHMARK_NUMERIC_COLUMNS:
        industry_value = _safe_float(industry_row.get(column))
        function_value = _safe_float(function_row.get(column))
        if industry_value is None and function_value is None:
            blended[column] = pd.NA
        elif industry_value is None:
            blended[column] = function_value
        elif function_value is None:
            blended[column] = industry_value
        else:
            blended[column] = round((industry_value * 0.6) + (function_value * 0.4), 2)
    blended.update(
        {
            "benchmark_type": "blended",
            "category": f"{industry_row.get('category', 'Industry')} + {function_row.get('category', 'Function')}",
            "source": f"60% industry ({industry_row.get('category', '')}) / 40% function ({function_row.get('category', '')})",
            "year": industry_row.get("year") if pd.notna(industry_row.get("year")) else function_row.get("year"),
            "notes": "Blended benchmark using 60% industry and 40% function weighting.",
        }
    )
    return pd.Series(blended)


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


def _attrition_note(value: float | None, context: str, onboarding_state: str | None = None) -> str:
    display_value = _fmt(value, "%")
    if value is not None and value >= 50:
        if context == "onboarding":
            return f"First-year attrition is exceptionally high at {display_value}, indicating a severe retention and onboarding issue."
        return f"First-year attrition is exceptionally high at {display_value}, indicating a severe retention issue after hire."
    if context == "onboarding":
        return f"Onboarding is {onboarding_state}, with first-year attrition at {display_value}."
    return f"Turnover pressure remains visible through first-year attrition of {display_value}."


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

    buckets = [
        {
            "eyebrow": "High impact | High urgency",
            "title": "Stabilise now",
            "background": RED_BG,
            "items": weakest[:2],
        },
        {
            "eyebrow": "High impact | Lower urgency",
            "title": "Tighten next",
            "background": AMBER_BG,
            "items": weakest[2:4],
        },
        {
            "eyebrow": "Lower impact | High visibility",
            "title": "Monitor",
            "background": TABLE_SHADE,
            "items": watch,
        },
        {
            "eyebrow": "Lower impact | Lower urgency",
            "title": "Maintain",
            "background": GREEN_BG,
            "items": strongest,
        },
    ]

    assigned_titles = set()
    quadrants = []
    for bucket in buckets:
        unique_items = []
        for item in bucket["items"]:
            title = item["title"]
            if title in assigned_titles:
                continue
            assigned_titles.add(title)
            unique_items.append(row(item))
        quadrants.append(
            {
                "eyebrow": bucket["eyebrow"],
                "title": bucket["title"],
                "background": bucket["background"],
                "items": unique_items,
            }
        )
    return quadrants


SECTION_DIAGNOSTIC_MAP = {
    "Recruitment strategy and workforce planning": {
        "location": "role approval and workforce planning",
        "metric_label": "Time to hire",
        "metric_key": "time_to_hire_days",
        "suffix": "days",
        "owner": "Managing director and hiring lead",
        "timeframe": "within 10 working days",
        "next_timeframe": "within 4 weeks",
        "result": "open roles are prioritised against one live hiring plan",
        "next_result": "every open vacancy has a dated owner, target hire date and escalation route",
    },
    "Performance metrics and funnel conversion": {
        "location": "funnel measurement and conversion tracking",
        "metric_label": "Offer acceptance",
        "metric_key": "offer_acceptance",
        "suffix": "%",
        "owner": "Recruitment lead",
        "timeframe": "within 2 weeks",
        "next_timeframe": "within 5 weeks",
        "result": "weekly funnel conversion data is visible for every active role",
        "next_result": "drop-off points are reviewed each week and corrected faster",
    },
    "Employer brand and market perception": {
        "location": "candidate attraction and market positioning",
        "metric_label": "Applications per role",
        "metric_key": "applications_per_role",
        "suffix": "",
        "owner": "Recruitment lead and marketing lead",
        "timeframe": "within 3 weeks",
        "next_timeframe": "within 6 weeks",
        "result": "the market message is aligned to the roles the business most needs to fill",
        "next_result": "application quality and offer acceptance improve on priority roles",
    },
    "Job adverts and job specifications": {
        "location": "role briefing and advert drafting",
        "metric_label": "Applications per role",
        "metric_key": "applications_per_role",
        "suffix": "",
        "owner": "Hiring manager and recruitment lead",
        "timeframe": "within 10 working days",
        "next_timeframe": "within 4 weeks",
        "result": "every new role uses one approved brief and advert structure",
        "next_result": "shortlists contain a higher share of interview-ready applicants",
    },
    "Sourcing and advertising process": {
        "location": "channel selection and candidate sourcing",
        "metric_label": "Candidates reaching interview",
        "metric_key": "candidates_reaching_interview",
        "suffix": "",
        "owner": "Recruitment lead",
        "timeframe": "within 2 weeks",
        "next_timeframe": "within 6 weeks",
        "result": "channel choice is based on conversion rather than habit",
        "next_result": "the business reaches a reliable volume of interview-ready candidates",
    },
    "Application handling and screening": {
        "location": "application review and shortlist decision",
        "metric_label": "Candidates reaching interview",
        "metric_key": "candidates_reaching_interview",
        "suffix": "",
        "owner": "Recruitment lead",
        "timeframe": "within 10 working days",
        "next_timeframe": "within 4 weeks",
        "result": "applications are screened to one standard within 48 hours",
        "next_result": "shortlists are faster and stronger across active roles",
    },
    "Interview process quality": {
        "location": "interview design and feedback",
        "metric_label": "Interview feedback time",
        "metric_key": "interview_feedback_time_days",
        "suffix": "days",
        "owner": "Hiring manager and recruitment lead",
        "timeframe": "within 2 weeks",
        "next_timeframe": "within 5 weeks",
        "result": "all interview stages use one question set and scorecard",
        "next_result": "feedback returns within 48 hours and decisions are more consistent",
    },
    "Decision making and offer process": {
        "location": "offer approval and release",
        "metric_label": "Offer acceptance",
        "metric_key": "offer_acceptance",
        "suffix": "%",
        "owner": "Hiring manager and approval owner",
        "timeframe": "within 10 working days",
        "next_timeframe": "within 4 weeks",
        "result": "offer decisions move through one approval path without avoidable delay",
        "next_result": "offer release time drops and acceptance improves",
    },
    "Onboarding and early retention": {
        "location": "onboarding and first-90-day integration",
        "metric_label": "First-year attrition",
        "metric_key": "first_year_attrition",
        "suffix": "%",
        "owner": "HR lead and hiring manager",
        "timeframe": "within 3 weeks",
        "next_timeframe": "within 8 weeks",
        "result": "every new hire follows a defined onboarding plan with named checkpoints",
        "next_result": "first-90-day dropout becomes visible and easier to reduce",
    },
    "Staff turnover risks": {
        "location": "first-year retention review",
        "metric_label": "First-year attrition",
        "metric_key": "first_year_attrition",
        "suffix": "%",
        "owner": "HR lead",
        "timeframe": "within 2 weeks",
        "next_timeframe": "within 6 weeks",
        "result": "avoidable first-year exits are reviewed by cause each month",
        "next_result": "backfill demand and repeat hiring cost begin to fall",
    },
    "Candidate experience": {
        "location": "candidate communication and feedback",
        "metric_label": "Interview feedback time",
        "metric_key": "interview_feedback_time_days",
        "suffix": "days",
        "owner": "Recruitment lead",
        "timeframe": "within 10 working days",
        "next_timeframe": "within 4 weeks",
        "result": "candidates receive one clear communication standard at every stage",
        "next_result": "drop-off reduces and candidate sentiment becomes measurable",
    },
    "Process ownership and accountability": {
        "location": "end-to-end process ownership",
        "metric_label": "Time to hire",
        "metric_key": "time_to_hire_days",
        "suffix": "days",
        "owner": "Managing director",
        "timeframe": "within 10 working days",
        "next_timeframe": "within 4 weeks",
        "result": "one named owner is accountable for weekly recruitment performance",
        "next_result": "handoffs, decisions and escalations move faster",
    },
}


def _section_context(title: str) -> dict:
    return SECTION_DIAGNOSTIC_MAP[title]


def _annual_hiring_volume(data: dict) -> float | None:
    return parse_numeric_value(data.get("annual_hiring_volume"))


def _metric_display(value: float | None, suffix: str) -> str:
    return _format_metric_value(value, suffix)


def _find_comparison(benchmark_summary: dict, label: str) -> dict | None:
    for item in benchmark_summary.get("comparisons", []):
        if item.get("label") == label:
            return item
    return None


def _section_supporting_evidence(title: str, data: dict, benchmark_summary: dict) -> str:
    metrics = data["metrics"]
    flags = data["process_flags"]
    applications = metrics.get("applications_per_role")
    interviews = metrics.get("candidates_reaching_interview")
    feedback = metrics.get("interview_feedback_time_days")
    stages = metrics.get("interview_stages")
    time_to_hire = metrics.get("time_to_hire_days")
    offer_acceptance = metrics.get("offer_acceptance")
    attrition = metrics.get("first_year_attrition")

    if title == "Recruitment strategy and workforce planning":
        return f"time to hire is {_metric_display(time_to_hire, 'days')} and a formal hiring plan is {'in place' if flags.get('has_hiring_plan') else 'not in place'}"
    if title == "Performance metrics and funnel conversion":
        return f"offer acceptance is {_metric_display(offer_acceptance, '%')} and KPI tracking is {'present' if flags.get('tracks_metrics') else 'not present'}"
    if title == "Employer brand and market perception":
        return f"applications per role are {_metric_display(applications, '')} and the employer proposition is {'defined' if flags.get('has_employer_brand') else 'not clearly defined'}"
    if title == "Job adverts and job specifications":
        return f"job documents are {'standardised' if flags.get('standardised_job_specs') else 'not standardised'} and applications per role are {_metric_display(applications, '')}"
    if title == "Sourcing and advertising process":
        return f"multi-channel sourcing is {'used' if flags.get('multi_channel_sourcing') else 'not used consistently'} and interview-ready flow is {_metric_display(interviews, '')} candidates per role"
    if title == "Application handling and screening":
        return f"screening is {'structured' if flags.get('structured_screening') else 'informal'} and only {_metric_display(interviews, '')} candidates are reaching interview per role"
    if title == "Interview process quality":
        return f"the process uses {int(stages) if stages else 'an unclear number of'} interview stages and feedback takes {_metric_display(feedback, 'days')}"
    if title == "Decision making and offer process":
        return f"offer acceptance is {_metric_display(offer_acceptance, '%')} and the approval path is {'fast' if flags.get('fast_offer_process') else 'exposed to delay'}"
    if title == "Onboarding and early retention":
        return f"first-year attrition is {_metric_display(attrition, '%')} and onboarding is {'documented' if flags.get('formal_onboarding') else 'not documented'}"
    if title == "Staff turnover risks":
        return f"first-year attrition is {_metric_display(attrition, '%')} and the business is carrying repeated backfill risk"
    if title == "Candidate experience":
        return f"candidate feedback is {'collected' if flags.get('collects_candidate_feedback') else 'not collected consistently'} and interview feedback takes {_metric_display(feedback, 'days')}"
    return f"ownership is {'clear' if flags.get('named_process_owner') else 'unclear'} and hiring manager training is {'in place' if flags.get('hiring_manager_training') else 'limited'}"


def _section_root_cause(title: str, data: dict) -> str:
    flags = data["process_flags"]
    if title == "Recruitment strategy and workforce planning":
        return "an ownership issue around workforce planning and role prioritisation"
    if title == "Performance metrics and funnel conversion":
        return "a process issue because the funnel is not being measured consistently"
    if title == "Employer brand and market perception":
        return "a decision issue because the market message is not clear enough for the roles being hired"
    if title == "Job adverts and job specifications":
        return "a process issue in how roles are briefed and written before launch"
    if title == "Sourcing and advertising process":
        return "a decision issue in channel choice and sourcing mix"
    if title == "Application handling and screening":
        return "a process issue in how applications are reviewed and shortlisted"
    if title == "Interview process quality":
        return "a decision issue because interview structure and interviewer calibration are inconsistent"
    if title == "Decision making and offer process":
        return "an ownership issue in approval speed and final decision control"
    if title == "Onboarding and early retention":
        return "a process issue because new hires are not being brought into role with enough structure"
    if title == "Staff turnover risks":
        return "an ownership issue because early exits are not being tracked back to their cause tightly enough"
    if title == "Candidate experience":
        return "a process issue because candidate communication is not managed to one standard"
    if flags.get("named_process_owner"):
        return "a decision issue because accountabilities are spread across too many people"
    return "an ownership issue because no single person is controlling the recruitment model end to end"


def _headline_templates(score: int) -> list[str]:
    if score >= 8:
        return [
            "In the part of the process covering {location}, {title_lower} is comparatively settled: {support}, which reflects {root_cause}.",
            "Across the stage covering {location}, {title_lower} is one of the stronger areas: {support}, supported by {root_cause}.",
            "The clearest stability in the hiring model sits in the stage covering {location}: {support}, with {root_cause} giving this area a firmer base.",
        ]
    if score >= 6:
        return [
            "In the part of the process covering {location}, {title_lower} is serviceable but uneven: {support}, which points to {root_cause}.",
            "Around the stage covering {location}, {title_lower} is producing mixed results: {support}, driven largely by {root_cause}.",
            "{title} is not failing in the stage covering {location}, but {support} shows the effect of {root_cause}.",
        ]
    if score >= 4:
        return [
            "The pressure point sits in the stage covering {location}: {support}, and the underlying cause is {root_cause}.",
            "In the stage covering {location}, {title_lower} is creating visible friction: {support}, which traces back to {root_cause}.",
            "{title} is slowing the process in the stage covering {location}; {support} and the main cause is {root_cause}.",
        ]
    return [
        "The main breakdown sits in the stage covering {location}: {support}, and the root cause is {root_cause}.",
        "In the stage covering {location}, {title_lower} is now a serious constraint: {support}, driven by {root_cause}.",
        "{title} is failing in the stage covering {location}; {support} and the business is dealing with {root_cause}.",
    ]


def _build_section_headline(title: str, score: int, data: dict, benchmark_summary: dict) -> str:
    context = _section_context(title)
    support = _section_supporting_evidence(title, data, benchmark_summary)
    root_cause = _section_root_cause(title, data)
    templates = _headline_templates(score)
    index = sum(ord(char) for char in title) % len(templates)
    return _clean_text(
        templates[index].format(
            title=title,
            title_lower=title.lower(),
            location=context["location"],
            support=support,
            root_cause=root_cause,
        ),
        max_sentences=2,
        max_words=56,
    )


def _build_section_current_state(title: str, score: int, data: dict, benchmark_summary: dict) -> str:
    context = _section_context(title)
    support = _section_supporting_evidence(title, data, benchmark_summary)
    root_cause = _section_root_cause(title, data)
    comparison = _find_comparison(benchmark_summary, context["metric_label"])
    benchmark_line = ""
    if comparison:
        benchmark_line = f"Against the benchmark, {context['metric_label'].lower()} is {comparison['comment'].lower()}."
    text = " ".join(
        sentence
        for sentence in [
            f"In the part of the process covering {context['location']}, the evidence shows that {support}.",
            f"The underlying issue is {root_cause}.",
            benchmark_line,
        ]
        if sentence
    )
    return _clean_text(text, max_sentences=3, max_words=62)


def _vacancy_day_exposure(data: dict) -> str:
    annual_volume = _annual_hiring_volume(data)
    time_to_hire = data["metrics"].get("time_to_hire_days")
    if annual_volume is None or time_to_hire is None:
        return "Vacancy cover is taking management time back out of the business."
    total_days = int(round(annual_volume * time_to_hire))
    return f"At the current pace, the business is carrying roughly {total_days} vacancy days across the year."


def _build_section_commercial_impact(title: str, score: int, data: dict, benchmark_summary: dict) -> str:
    metrics = data["metrics"]
    annual_volume = _annual_hiring_volume(data)
    if title == "Recruitment strategy and workforce planning":
        return _clean_text(
            f"{_vacancy_day_exposure(data)} That extends time to productivity on open roles and keeps senior managers in repeated approval discussions instead of revenue-producing work.",
            max_sentences=2,
            max_words=46,
        )
    if title == "Performance metrics and funnel conversion":
        return _clean_text(
            "Without clean funnel reporting, the business loses time in the wrong stages and repeats spend on channels that are not converting. That pushes up cost per hire and delays corrective action when roles stall.",
            max_sentences=2,
            max_words=42,
        )
    if title == "Employer brand and market perception":
        return _clean_text(
            "Weak attraction quality means more advertising effort is needed to reach the same shortlist volume. That raises sourcing cost and stretches time to hire on commercially important roles.",
            max_sentences=2,
            max_words=40,
        )
    if title == "Job adverts and job specifications":
        return _clean_text(
            "Poor role definition creates irrelevant applications, weak briefs and rework for hiring managers. That increases screening time and slows down the point at which a viable shortlist can be built.",
            max_sentences=2,
            max_words=41,
        )
    if title == "Sourcing and advertising process":
        return _clean_text(
            "When sourcing mix is chosen poorly, the business pays for activity that does not create interview-ready candidates. That adds direct channel cost and lengthens vacancy days on revenue-critical roles.",
            max_sentences=2,
            max_words=41,
        )
    if title == "Application handling and screening":
        return _clean_text(
            "Slow or inconsistent screening keeps weak applicants in the funnel and delays contact with strong ones. That wastes recruiter hours and increases the risk of losing viable candidates before interview.",
            max_sentences=2,
            max_words=41,
        )
    if title == "Interview process quality":
        return _clean_text(
            "Each extra interview stage and delayed feedback cycle adds management time and pushes decisions back. That raises interview cost, slows time to hire and lowers the odds of securing strong candidates.",
            max_sentences=2,
            max_words=41,
        )
    if title == "Decision making and offer process":
        return _clean_text(
            f"At {_metric_display(metrics.get('offer_acceptance'), '%')} offer acceptance, the business is already losing part of the shortlist after the final decision. That means repeated interview effort, longer vacancy cover and more manager time spent on replacement offers.",
            max_sentences=2,
            max_words=44,
        )
    if title == "Onboarding and early retention":
        return _clean_text(
            f"At {_metric_display(metrics.get('first_year_attrition'), '%')} first-year attrition, replacement cost is returning quickly after each hire. The business is paying twice through repeat recruitment effort and lost ramp-up time.",
            max_sentences=2,
            max_words=38,
        )
    if title == "Staff turnover risks":
        return _clean_text(
            f"Early exits at {_metric_display(metrics.get('first_year_attrition'), '%')} create repeated backfill demand and lost productive time. That increases recruitment cost and keeps teams operating below required capacity.",
            max_sentences=2,
            max_words=37,
        )
    if title == "Candidate experience":
        return _clean_text(
            "Poor communication slows decision cycles and reduces the chance that candidates stay engaged through to offer. That weakens conversion, increases drop-off and forces more sourcing work into the process.",
            max_sentences=2,
            max_words=39,
        )
    return _clean_text(
        "Weak ownership means decisions sit in queues, actions drift and issues are found too late. That adds time to open vacancies and increases management effort across the full recruitment cycle.",
        max_sentences=2,
        max_words=38,
    )


def _build_section_key_risks(title: str, score: int, data: dict, benchmark_summary: dict) -> list[str]:
    if title == "Interview process quality":
        return [
            "Interview decisions depend too much on individual judgement rather than one scoring standard.",
            "Feedback delay gives strong candidates more time to exit the process.",
        ]
    if title in {"Onboarding and early retention", "Staff turnover risks"}:
        return [
            "Early attrition will keep creating repeat vacancies and replacement cost.",
            "The business will struggle to learn why hires leave if ownership stays fragmented.",
        ]
    if title == "Process ownership and accountability":
        return [
            "Issues will continue to move slowly because no one owns the full hiring cycle.",
            "Performance drift will remain hidden until vacancies have already aged.",
        ]
    return [
        f"The weakness at { _section_context(title)['location'] } will continue to slow the wider hiring process.",
        "Management time will keep being pulled into avoidable rework if the root cause is left unresolved.",
    ]


def _build_section_actions(title: str, score: int, data: dict) -> tuple[list[str], list[str]]:
    context = _section_context(title)
    owner = context["owner"]
    first = _clean_text(
        f"{owner} - {context['timeframe']}: tighten control in the stage covering {context['location']}. Outcome: {context['result']}.",
        max_sentences=2,
        max_words=40,
    )
    second = _clean_text(
        f"{owner} - {context['next_timeframe']}: track the agreed change against one weekly measure. Outcome: {context['next_result']}.",
        max_sentences=2,
        max_words=40,
    )
    return [first], [second]


def _build_core_constraint(data: dict, report: dict, benchmark_summary: dict) -> str:
    weakest = min(report["sections"], key=lambda section: section["score"])
    context = _section_context(weakest["title"])
    support = _section_supporting_evidence(weakest["title"], data, benchmark_summary)
    return _clean_text(
        f"{weakest['title']} is the current core constraint. The bottleneck sits {context['location']}, where {support}. Because every downstream decision depends on this part of the process, weak control here slows the whole hiring system and reduces the quality of the outcome.",
        max_sentences=3,
        max_words=60,
    )


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
        f"The recruitment operating model is {_rating_for_score(data['total_score']).lower()} at {data['total_score']}/120.",
        f"{strongest[0]} is the strongest area at {strongest[1]}/10, while {weakest[0].lower()} is the weakest at {weakest[1]}/10.",
        f"The main commercial issue is pressure in {weakest[0].lower()}, which is adding delay, management time and avoidable hiring risk.",
        benchmark_line,
        f"The immediate next move is to {next_step.rstrip('.').lower()}.",
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
        "not controlled tightly enough": "",
        "functioning but not optimised": "",
        "holding together": "",
    }
    for source, target in replacements.items():
        if " " in source or "-" in source:
            text = re.sub(re.escape(source), target, text, flags=re.IGNORECASE)
        else:
            text = re.sub(rf"\b{re.escape(source)}\b", target, text, flags=re.IGNORECASE)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    text = re.sub(r"([.?!]){2,}", r"\1", text)
    text = re.sub(
        r"\b(recruitment_strategy_and_workforce_planning|performance_metrics_and_funnel_conversion|employer_brand_and_market_perception|job_adverts_and_job_specifications|sourcing_and_advertising_process|application_handling_and_screening|interview_process_quality|decision_making_and_offer_process|onboarding_and_early_retention|staff_turnover_risks|candidate_experience|process_ownership_and_accountability|top_strengths|top_problems|day_30_plan|day_60_plan|day_90_plan|sections)\b",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\{[^{}]+\}", "", text)
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


def _build_top_strengths(sections: list[dict]) -> list[str]:
    strengths = []
    for section in sorted(sections, key=lambda item: item["score"], reverse=True):
        if section["score"] < 7:
            continue
        strengths.append(
            _clean_text(
                f"{section['title']} is a clear strength at {section['score']}/10.",
                max_sentences=1,
                max_words=16,
            )
        )
        if len(strengths) >= 5:
            break
    return strengths or [
        _clean_text(
            f"{section['title']} is stronger than most other areas at {section['score']}/10.",
            max_sentences=1,
            max_words=16,
        )
        for section in sorted(sections, key=lambda item: item["score"], reverse=True)[:3]
    ]


def _build_top_problems(sections: list[dict], benchmark_summary: dict) -> list[str]:
    problems = []
    for section in sorted(sections, key=lambda item: item["score"]):
        if section["score"] > 6 and len(problems) >= 3:
            continue
        problems.append(
            _clean_text(
                f"{section['title']} is a current weakness at {section['score']}/10.",
                max_sentences=1,
                max_words=16,
            )
        )
        if len(problems) >= 4:
            break
    for item in benchmark_summary.get("comparisons", []):
        if item["status"] == "In line":
            continue
        problems.append(_clean_text(f"{item['label']} is {item['comment'].lower()}.", max_sentences=1, max_words=16))
        break
    unique = []
    seen = set()
    for item in problems:
        key = item.lower()
        if item and key not in seen:
            unique.append(item)
            seen.add(key)
    return unique[:5]


def _build_day_plan(sections: list[dict], day: int) -> list[str]:
    weakest = sorted(sections, key=lambda item: item["score"])[:3]
    focus_titles = [section["title"].lower() for section in weakest]
    if day == 30:
        actions = [
            f"Assign one accountable owner to {focus_titles[0]}.",
            f"Set weekly operating reviews across {focus_titles[1]} and {focus_titles[2]}.",
            "Confirm the core hiring KPIs and start tracking them in one place.",
        ]
    elif day == 60:
        actions = [
            f"Standardise how {focus_titles[0]} is run across active hiring.",
            f"Tighten handoffs and response standards in {focus_titles[1]}.",
            f"Brief hiring managers on the required process discipline for {focus_titles[2]}.",
        ]
    else:
        actions = [
            "Review the impact of the operating changes against the agreed KPIs.",
            "Close any remaining control gaps in the weakest parts of the process.",
            "Reset leadership ownership for the next audit cycle.",
        ]
    return [_clean_text(action, max_sentences=1, max_words=16) for action in actions]


def _apply_chart_style(fig, ax) -> None:
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.tick_params(axis="x", colors="black", labelsize=8)
    ax.tick_params(axis="y", colors="black", labelsize=8)
    for spine in ax.spines.values():
        spine.set_visible(False)
