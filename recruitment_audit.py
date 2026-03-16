from __future__ import annotations

import json
import math
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from openai import OpenAI

MODEL_NAME = "gpt-4.1"
BENCHMARK_FILE = Path.home() / "Desktop" / "uk_recruitment_benchmark_framework.xlsx"

BRAND_NAME = "Bradford & Marsh Consulting"
BRAND_TAGLINE = "Recruitment Audit & Talent Advisory"

FONT_NAME = "Aptos"
FONT_SIZE = 10.5
TITLE_SIZE = 20
SUBTITLE_SIZE = 11.5
H1_SIZE = 15.5
H2_SIZE = 12.5
H3_SIZE = 10.5

TEXT_RGB = RGBColor(17, 24, 39)
MUTED_RGB = RGBColor(75, 85, 99)
WHITE_RGB = RGBColor(255, 255, 255)

TEXT_HEX = "#111827"
GOOD = "#15803D"
AMBER = "#D97706"
RISK = "#B91C1C"
DARK = "#111827"
GOLD = "#A16207"
LIGHT_GREY = "#E5E7EB"
MID_GREY = "#CBD5E1"
HEADER_FILL = "111827"
SUBHEADER_FILL = "F3F4F6"
GOOD_FILL = "DCFCE7"
AMBER_FILL = "FEF3C7"
RISK_FILL = "FEE2E2"

SECTIONS = [
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

REQUIRED_BENCHMARK_COLUMNS = {
    "sector",
    "avg_time_to_hire_days",
    "avg_applications_per_role",
    "avg_offer_acceptance_pct",
    "avg_attrition_pct",
}

SYSTEM_PROMPT = """
You are writing as an elite recruitment operations consultant operating at the top end of the advisory market.

Write in plain, professional British English.
Be clinical, evidence-led, commercially sharp and precise.
Do not use hype, marketing language, generic HR phrasing or filler.
Do not invent facts.
Do not soften weak performance.
Use the supplied scores exactly as provided.
Use the supplied diagnostic evidence actively. The report should feel like a high-end operating diagnosis, not a generic audit.

Return valid JSON only.

Use exactly this schema:
{
  "sections": [
    {
      "title": "string",
      "score": 0,
      "current_state": "string",
      "key_risks": "string",
      "commercial_impact": "string",
      "quick_wins": "string",
      "medium_term_improvements": "string"
    }
  ],
  "executive_summary": "string",
  "top_5_strengths": ["string", "string", "string", "string", "string"],
  "top_5_problems": ["string", "string", "string", "string", "string"],
  "day_30_plan": ["string"],
  "day_60_plan": ["string"],
  "day_90_plan": ["string"],
  "overall_score": {
    "total_score": 0,
    "percentage": 0
  },
  "final_verdict": "string"
}

Rules:
- sections must contain exactly 12 items
- titles must match the supplied titles in order
- scores must remain exactly as supplied
- top_5_strengths must contain exactly 5 items
- top_5_problems must contain exactly 5 items
- overall_score must match the supplied totals exactly
- current_state must describe what the operating reality appears to be now
- key_risks must focus on specific process, speed, governance, conversion and retention risks
- commercial_impact must translate issues into operational drag, hiring inefficiency, vacancy burden, interview load or repeat-hiring cost where supported
- quick_wins must be immediately executable
- medium_term_improvements must be structural improvements over the next 1-2 quarters
""".strip()


def clean_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", str(value).strip()).strip("_") or "recruitment_audit"


def normalise_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value).strip()).lower()


def xml_safe_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = re.sub(r"\x1B[@-_][0-?]*[ -/]*[@-~]", "", text)
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)
    return text.strip()


def parse_numeric_value(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = str(value).replace(",", "").replace("–", "-")
    numbers = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", cleaned)]
    if not numbers:
        return None
    if len(numbers) >= 2 and "-" in cleaned:
        return sum(numbers[:2]) / 2
    return numbers[0]


def parse_time_to_hire_days(value: str | None) -> float | None:
    if not value:
        return None
    text = str(value).strip().lower()
    numbers = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)]
    if not numbers:
        return None

    base = numbers[0]
    if len(numbers) >= 2 and "-" in text:
        base = sum(numbers[:2]) / 2

    if "week" in text or "wk" in text:
        return base * 7
    if "month" in text:
        return base * 30
    return base


def output_dir() -> Path:
    desktop = Path.home() / "Desktop"
    if desktop.exists() and desktop.is_dir():
        return desktop
    fallback = Path.home() / "recruitment_audit_outputs"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def get_api_key() -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in your environment.")
    return api_key


def safe_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def clamp_score(value: float) -> int:
    return max(0, min(10, int(round(value))))


def compare_higher_better(client: float | None, benchmark: float | None) -> float:
    if client is None or benchmark is None or benchmark == 0:
        return 0.0
    ratio = client / benchmark
    if ratio >= 1.30:
        return 2.0
    if ratio >= 1.10:
        return 1.0
    if ratio >= 0.90:
        return 0.0
    if ratio >= 0.75:
        return -1.0
    return -2.0


def compare_lower_better(client: float | None, benchmark: float | None) -> float:
    if client is None or benchmark is None or benchmark == 0:
        return 0.0
    ratio = client / benchmark
    if ratio <= 0.75:
        return 2.0
    if ratio <= 0.90:
        return 1.0
    if ratio <= 1.10:
        return 0.0
    if ratio <= 1.30:
        return -1.0
    return -2.0


def load_benchmarks(sector: str) -> pd.Series | None:
    if not BENCHMARK_FILE.exists():
        return None
    try:
        df = pd.read_excel(BENCHMARK_FILE, sheet_name="Benchmarks")
    except Exception:
        return None
    if not REQUIRED_BENCHMARK_COLUMNS.issubset(df.columns):
        return None
    df = df.copy()
    df["_sector"] = df["sector"].astype(str).map(normalise_text)
    match = df[df["_sector"] == normalise_text(sector)]
    if match.empty:
        return None
    return match.iloc[0]


def build_benchmark_summary(metrics: dict[str, float | None], benchmark: pd.Series | None) -> str:
    if benchmark is None:
        return (
            "No external benchmark data was available for the selected sector. "
            "Comparative analysis has therefore been limited to the information supplied and established good practice."
        )

    lines = [f"Sector benchmark matched: {xml_safe_text(benchmark['sector'])}"]
    mapping = {
        "time_to_hire_days": ("avg_time_to_hire_days", "Average time to hire", " days"),
        "applications_per_role": ("avg_applications_per_role", "Average applications per role", ""),
        "offer_acceptance": ("avg_offer_acceptance_pct", "Average offer acceptance", "%"),
        "first_year_attrition": ("avg_attrition_pct", "Average first year attrition", "%"),
    }
    for key, (bench_col, label, suffix) in mapping.items():
        client_val = metrics.get(key)
        bench_val = safe_float(benchmark.get(bench_col))
        if client_val is None or bench_val is None:
            continue
        lines.append(f"{label}: client {client_val:.1f}{suffix} versus benchmark {bench_val:.1f}{suffix}")
    return "\n".join(lines)


def band_from_value(value: float, low: float, high: float) -> str:
    if value <= low:
        return "low"
    if value >= high:
        return "high"
    return "moderate"


def derive_diagnostics(data: dict[str, Any], benchmark: pd.Series | None) -> dict[str, Any]:
    m = data["metrics"]
    f = data["process_flags"]

    applications = m.get("applications_per_role")
    interviewed = m.get("candidates_reaching_interview")
    acceptance = m.get("offer_acceptance")
    attrition = m.get("first_year_attrition")
    time_to_hire = m.get("time_to_hire_days")
    stages = m.get("interview_stages")
    feedback_days = m.get("interview_feedback_time_days")

    annual_hires = parse_numeric_value(str(data.get("annual_hiring_volume", ""))) or 0.0
    salary = m.get("average_salary")  # optional future field

    application_to_interview_pct = None
    if applications and interviewed is not None and applications > 0:
        application_to_interview_pct = round((interviewed / applications) * 100, 1)

    estimated_interviews_per_hire = None
    if interviewed is not None and stages is not None:
        estimated_interviews_per_hire = round(interviewed * stages, 1)

    annual_interview_hours = None
    if estimated_interviews_per_hire is not None and annual_hires:
        annual_interview_hours = round(estimated_interviews_per_hire * annual_hires, 1)

    estimated_backfills = None
    if attrition is not None and annual_hires:
        estimated_backfills = round((attrition / 100) * annual_hires, 1)

    vacancy_weeks = None
    if estimated_backfills is not None and time_to_hire is not None:
        vacancy_weeks = round((estimated_backfills * time_to_hire) / 7, 1)

    bench_time = safe_float(benchmark.get("avg_time_to_hire_days")) if benchmark is not None else None
    bench_apps = safe_float(benchmark.get("avg_applications_per_role")) if benchmark is not None else None
    bench_offer = safe_float(benchmark.get("avg_offer_acceptance_pct")) if benchmark is not None else None
    bench_attr = safe_float(benchmark.get("avg_attrition_pct")) if benchmark is not None else None

    if application_to_interview_pct is None:
        funnel_signal = "unknown"
    elif application_to_interview_pct < 8:
        funnel_signal = "severe conversion leakage"
    elif application_to_interview_pct < 15:
        funnel_signal = "weak conversion"
    elif application_to_interview_pct < 25:
        funnel_signal = "mixed conversion"
    else:
        funnel_signal = "healthy conversion"

    if time_to_hire is None:
        speed_signal = "unknown"
    elif bench_time is not None and time_to_hire > bench_time * 1.25:
        speed_signal = "slow versus benchmark"
    elif time_to_hire > 45:
        speed_signal = "slow"
    elif time_to_hire <= 30:
        speed_signal = "fast"
    else:
        speed_signal = "moderate"

    if acceptance is None:
        offer_signal = "unknown"
    elif bench_offer is not None and acceptance < bench_offer * 0.85:
        offer_signal = "weak competitiveness"
    elif acceptance < 60:
        offer_signal = "high offer risk"
    elif acceptance < 75:
        offer_signal = "moderate offer risk"
    else:
        offer_signal = "workable"

    if attrition is None:
        retention_signal = "unknown"
    elif bench_attr is not None and attrition > bench_attr * 1.5:
        retention_signal = "severe retention failure"
    elif attrition >= 40:
        retention_signal = "severe retention failure"
    elif attrition >= 25:
        retention_signal = "high retention risk"
    elif attrition >= 15:
        retention_signal = "moderate retention risk"
    else:
        retention_signal = "stable"

    if stages is None and feedback_days is None:
        interview_signal = "unknown"
    elif (stages is not None and stages >= 4) or (feedback_days is not None and feedback_days >= 7):
        interview_signal = "high process friction"
    elif (stages is not None and stages >= 3) or (feedback_days is not None and feedback_days >= 4):
        interview_signal = "moderate process friction"
    else:
        interview_signal = "lean"

    bottleneck_candidates: list[tuple[str, float]] = []

    if application_to_interview_pct is not None:
        if application_to_interview_pct < 8:
            bottleneck_candidates.append(("top-of-funnel quality and screening", 5.0))
        elif application_to_interview_pct < 15:
            bottleneck_candidates.append(("screening efficiency", 3.0))

    if stages is not None:
        if stages >= 4:
            bottleneck_candidates.append(("interview design", 4.0))
        elif stages == 3:
            bottleneck_candidates.append(("interview pacing", 2.0))

    if feedback_days is not None:
        if feedback_days >= 7:
            bottleneck_candidates.append(("decision speed", 4.0))
        elif feedback_days >= 4:
            bottleneck_candidates.append(("candidate handling speed", 2.0))

    if acceptance is not None:
        if acceptance < 60:
            bottleneck_candidates.append(("offer competitiveness or close process", 4.0))
        elif acceptance < 75:
            bottleneck_candidates.append(("offer conversion", 2.0))

    if attrition is not None:
        if attrition >= 40:
            bottleneck_candidates.append(("onboarding and quality-of-hire", 5.0))
        elif attrition >= 25:
            bottleneck_candidates.append(("early retention", 3.0))

    primary_bottleneck = "unclear"
    if bottleneck_candidates:
        primary_bottleneck = sorted(bottleneck_candidates, key=lambda x: x[1], reverse=True)[0][0]

    maturity_points = 0
    maturity_points += 1 if f.get("has_hiring_plan") else 0
    maturity_points += 1 if f.get("tracks_metrics") else 0
    maturity_points += 1 if f.get("has_employer_brand") else 0
    maturity_points += 1 if f.get("standardised_job_specs") else 0
    maturity_points += 1 if f.get("multi_channel_sourcing") else 0
    maturity_points += 1 if f.get("structured_screening") else 0
    maturity_points += 1 if f.get("structured_interviews") else 0
    maturity_points += 1 if f.get("fast_offer_process") else 0
    maturity_points += 1 if f.get("formal_onboarding") else 0
    maturity_points += 1 if f.get("collects_candidate_feedback") else 0
    maturity_points += 1 if f.get("named_process_owner") else 0
    maturity_points += 1 if f.get("hiring_manager_training") else 0

    if maturity_points <= 3:
        maturity_level = "Level 1 - Reactive"
    elif maturity_points <= 6:
        maturity_level = "Level 2 - Emerging"
    elif maturity_points <= 9:
        maturity_level = "Level 3 - Structured"
    else:
        maturity_level = "Level 4 - Managed"

    likely_failure_pattern = []
    if retention_signal in {"severe retention failure", "high retention risk"}:
        likely_failure_pattern.append("early retention is destroying downstream value")
    if funnel_signal in {"severe conversion leakage", "weak conversion"}:
        likely_failure_pattern.append("top-of-funnel quality or screening alignment is weak")
    if interview_signal == "high process friction":
        likely_failure_pattern.append("interview process drag is slowing decisions")
    if offer_signal in {"high offer risk", "weak competitiveness"}:
        likely_failure_pattern.append("offer conversion is not strong enough")
    if not likely_failure_pattern:
        likely_failure_pattern.append("the process appears functional but under-optimised")

    vacancy_cost_estimate = None
    replacement_cost_estimate = None
    if salary and time_to_hire:
        daily_salary = salary / 260
        vacancy_cost_estimate = round(daily_salary * time_to_hire, 0)
    if salary and estimated_backfills is not None:
        replacement_cost_estimate = round((salary * 0.30) * estimated_backfills, 0)

    return {
        "application_to_interview_pct": application_to_interview_pct,
        "estimated_interviews_per_hire": estimated_interviews_per_hire,
        "annual_interview_hours": annual_interview_hours,
        "estimated_backfills": estimated_backfills,
        "vacancy_weeks": vacancy_weeks,
        "vacancy_cost_estimate": vacancy_cost_estimate,
        "replacement_cost_estimate": replacement_cost_estimate,
        "funnel_signal": funnel_signal,
        "speed_signal": speed_signal,
        "offer_signal": offer_signal,
        "retention_signal": retention_signal,
        "interview_signal": interview_signal,
        "primary_bottleneck": primary_bottleneck,
        "maturity_points": maturity_points,
        "maturity_level": maturity_level,
        "likely_failure_pattern": "; ".join(likely_failure_pattern),
        "benchmark_time": bench_time,
        "benchmark_apps": bench_apps,
        "benchmark_offer": bench_offer,
        "benchmark_attrition": bench_attr,
    }


def auto_score_sections(data: dict[str, Any], benchmark: pd.Series | None) -> tuple[list[int], list[str]]:
    m = data["metrics"]
    f = data["process_flags"]
    d = derive_diagnostics(data, benchmark)
    data["diagnostics"] = d

    bench_time = d["benchmark_time"]
    bench_apps = d["benchmark_apps"]
    bench_offer = d["benchmark_offer"]
    bench_attrition = d["benchmark_attrition"]

    scores: list[int] = []
    notes: list[str] = []

    def add(raw_score: float, note: str) -> None:
        scores.append(clamp_score(raw_score))
        notes.append(note)

    score = 4.0
    if f["has_hiring_plan"]:
        score += 3.0
    if f["named_process_owner"]:
        score += 1.0
    if f["tracks_metrics"]:
        score += 1.0
    if d["retention_signal"] == "severe retention failure":
        score -= 1.0
    add(score, "Scored from planning discipline, ownership clarity, KPI visibility and whether downstream outcomes support the planning model.")

    score = 4.0
    if f["tracks_metrics"]:
        score += 3.0
    score += compare_lower_better(m["time_to_hire_days"], bench_time)
    score += compare_higher_better(m["applications_per_role"], bench_apps)
    score += compare_higher_better(m["offer_acceptance"], bench_offer)
    if d["application_to_interview_pct"] is not None:
        if d["application_to_interview_pct"] < 8:
            score -= 2.0
        elif d["application_to_interview_pct"] < 15:
            score -= 1.0
        elif d["application_to_interview_pct"] >= 25:
            score += 1.0
    add(score, "Scored from KPI maturity, benchmarked metrics and observed funnel efficiency rather than raw volumes alone.")

    score = 4.0
    if f["has_employer_brand"]:
        score += 3.0
    if m["applications_per_role"] is not None:
        if m["applications_per_role"] >= 80:
            score += 2.0
        elif m["applications_per_role"] >= 40:
            score += 1.0
        elif m["applications_per_role"] < 15:
            score -= 1.0
    if m["offer_acceptance"] is not None and m["offer_acceptance"] < 60:
        score -= 1.0
    add(score, "Scored from employer brand maturity, market pull and indirect competitiveness signals such as application volume and offer conversion.")

    score = 4.0
    if f["standardised_job_specs"]:
        score += 4.0
    if f["has_employer_brand"]:
        score += 1.0
    if d["application_to_interview_pct"] is not None and d["application_to_interview_pct"] < 10:
        score -= 1.0
    add(score, "Scored from specification consistency and whether the advert-to-interview yield suggests role clarity or mismatch.")

    score = 4.0
    if f["multi_channel_sourcing"]:
        score += 3.0
    score += compare_higher_better(m["applications_per_role"], bench_apps)
    if d["funnel_signal"] == "severe conversion leakage":
        score -= 1.0
    add(score, "Scored from channel breadth, applicant flow and whether sourcing appears to be producing usable candidate volume.")

    score = 4.0
    if f["structured_screening"]:
        score += 4.0
    score += compare_lower_better(m["time_to_hire_days"], bench_time)
    if d["application_to_interview_pct"] is not None:
        if d["application_to_interview_pct"] < 8:
            score -= 2.0
        elif d["application_to_interview_pct"] < 15:
            score -= 1.0
    if m["interview_feedback_time_days"] is not None:
        if m["interview_feedback_time_days"] <= 2:
            score += 1.0
        elif m["interview_feedback_time_days"] >= 7:
            score -= 1.0
    add(score, "Scored from screening consistency, response speed and whether candidate flow is converting efficiently into interviews.")

    score = 4.0
    if f["structured_interviews"]:
        score += 4.0
    if f["hiring_manager_training"]:
        score += 2.0
    if m["interview_stages"] is not None:
        if m["interview_stages"] >= 4:
            score -= 2.0
        elif m["interview_stages"] == 3:
            score -= 1.0
        elif m["interview_stages"] <= 2:
            score += 1.0
    if m["interview_feedback_time_days"] is not None and m["interview_feedback_time_days"] >= 7:
        score -= 1.0
    if d["retention_signal"] == "severe retention failure":
        score -= 1.0
    add(score, "Scored from assessment structure, stage load, feedback speed and whether downstream outcomes undermine the claimed quality of assessment.")

    score = 4.0
    if f["fast_offer_process"]:
        score += 3.0
    score += compare_higher_better(m["offer_acceptance"], bench_offer)
    score += compare_lower_better(m["time_to_hire_days"], bench_time)
    if m["interview_feedback_time_days"] is not None and m["interview_feedback_time_days"] >= 7:
        score -= 1.0
    add(score, "Scored from decision speed, offer conversion and whether the process appears fast enough to protect preferred candidates.")

    score = 4.0
    if f["formal_onboarding"]:
        score += 4.0
    score += compare_lower_better(m["first_year_attrition"], bench_attrition)
    if m["first_year_attrition"] is not None:
        if m["first_year_attrition"] >= 40:
            score -= 3.0
        elif m["first_year_attrition"] >= 25:
            score -= 2.0
    add(score, "Scored from onboarding structure and hard retention outcomes rather than process intent alone.")

    score = 4.0
    score += compare_lower_better(m["first_year_attrition"], bench_attrition)
    if m["first_year_attrition"] is not None:
        if m["first_year_attrition"] <= 10:
            score += 2.0
        elif m["first_year_attrition"] <= 20:
            score += 1.0
        elif m["first_year_attrition"] >= 40:
            score -= 3.0
        elif m["first_year_attrition"] >= 25:
            score -= 2.0
    add(score, "Scored primarily from first-year attrition as a direct indicator of hiring quality and retention risk.")

    score = 4.0
    if f["collects_candidate_feedback"]:
        score += 3.0
    if f["structured_screening"]:
        score += 1.0
    if f["structured_interviews"]:
        score += 1.0
    score += compare_lower_better(m["time_to_hire_days"], bench_time)
    if m["interview_stages"] is not None and m["interview_stages"] >= 4:
        score -= 1.0
    if m["interview_feedback_time_days"] is not None and m["interview_feedback_time_days"] >= 7:
        score -= 1.0
    add(score, "Scored from journey speed, process friction and whether the candidate experience is likely to sustain or damage conversion.")

    score = 4.0
    if f["named_process_owner"]:
        score += 3.0
    if f["tracks_metrics"]:
        score += 2.0
    if f["has_hiring_plan"]:
        score += 1.0
    if d["retention_signal"] == "severe retention failure":
        score -= 1.0
    add(score, "Scored from accountability, governance discipline and whether operational outcomes suggest the process is genuinely controlled.")

    return scores, notes


def build_diagnostic_snapshot(data: dict[str, Any]) -> str:
    d = data["diagnostics"]
    lines = [
        f"Maturity level: {d['maturity_level']}",
        f"Primary bottleneck: {d['primary_bottleneck']}",
        f"Funnel signal: {d['funnel_signal']}",
        f"Speed signal: {d['speed_signal']}",
        f"Offer signal: {d['offer_signal']}",
        f"Retention signal: {d['retention_signal']}",
        f"Interview friction signal: {d['interview_signal']}",
        f"Likely failure pattern: {d['likely_failure_pattern']}",
    ]
    if d["application_to_interview_pct"] is not None:
        lines.append(f"Application-to-interview conversion: {d['application_to_interview_pct']}%")
    if d["estimated_interviews_per_hire"] is not None:
        lines.append(f"Estimated interviews per hire: {d['estimated_interviews_per_hire']}")
    if d["annual_interview_hours"] is not None:
        lines.append(f"Estimated annual interview hours: {d['annual_interview_hours']}")
    if d["estimated_backfills"] is not None:
        lines.append(f"Estimated annual backfills driven by attrition: {d['estimated_backfills']}")
    if d["vacancy_weeks"] is not None:
        lines.append(f"Estimated vacancy weeks from repeat hiring load: {d['vacancy_weeks']}")
    if d["vacancy_cost_estimate"] is not None:
        lines.append(f"Approximate vacancy cost per role: £{d['vacancy_cost_estimate']:,.0f}")
    if d["replacement_cost_estimate"] is not None:
        lines.append(f"Approximate annual replacement cost proxy: £{d['replacement_cost_estimate']:,.0f}")
    return "\n".join(lines)


def build_user_prompt(data: dict[str, Any], benchmark_summary: str) -> str:
    lines = [
        "Write a recruitment audit using the fixed scores below.",
        "",
        f"Client: {data['company_name']}",
        f"Sector: {data['sector']}",
        f"Headcount: {data['headcount']}",
        f"Location: {data['location']}",
        f"Annual Hiring Volume: {data['annual_hiring_volume']}",
        f"Key Roles Hired: {data['key_roles_hired']}",
        "",
        "Key funnel metrics observed",
        f"Applications per role: {data['raw_metrics']['applications_per_role']}",
        f"Candidates reaching interview: {data['raw_metrics']['candidates_reaching_interview']}",
        f"Offer acceptance rate: {data['raw_metrics']['offer_acceptance']}",
        f"Average time to hire: {data['raw_metrics']['time_to_hire']}",
        f"Interview stages: {data['raw_metrics']['interview_stages']}",
        f"Interview feedback time: {data['raw_metrics']['interview_feedback_time']}",
        f"First-year attrition: {data['raw_metrics']['first_year_attrition']}",
        "",
        "Diagnostic snapshot",
        build_diagnostic_snapshot(data),
        "",
        "Operational indicators",
    ]

    for key, value in data["process_flags"].items():
        lines.append(f"{key.replace('_', ' ').capitalize()}: {'Yes' if value else 'No'}")

    lines.extend(["", "Benchmark context", benchmark_summary, "", "Fixed section scores"])

    for i, title in enumerate(SECTIONS, start=1):
        lines.append(
            f"{i}. {title} | Score: {data['section_scores'][i - 1]}/10 | "
            f"Scoring basis: {data['section_notes'][i - 1]}"
        )

    lines.extend(
        [
            "",
            f"Total Score: {data['total_score']}/120",
            f"Percentage: {data['percentage_score']}%",
            "",
            "Write with a clinical, premium consultancy tone.",
            "Make the narrative feel diagnostic and specific, not generic.",
            "Do not change any score.",
        ]
    )
    return "\n".join(lines)


def extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in model response.")
        return json.loads(match.group(0))


def ensure_list_of_strings(value: Any, exact_length: int | None = None) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("Expected a list.")
    items = [xml_safe_text(item) for item in value if xml_safe_text(item)]
    if exact_length is not None and len(items) != exact_length:
        raise ValueError(f"Expected exactly {exact_length} items, got {len(items)}.")
    return items


def validate_report_json(report: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    sections = report.get("sections")
    if not isinstance(sections, list) or len(sections) != 12:
        raise ValueError("Report must contain exactly 12 sections.")

    cleaned_sections: list[dict[str, Any]] = []
    for idx, section in enumerate(sections):
        cleaned_sections.append(
            {
                "title": SECTIONS[idx],
                "score": data["section_scores"][idx],
                "current_state": xml_safe_text(section.get("current_state", "")),
                "key_risks": xml_safe_text(section.get("key_risks", "")),
                "commercial_impact": xml_safe_text(section.get("commercial_impact", "")),
                "quick_wins": xml_safe_text(section.get("quick_wins", "")),
                "medium_term_improvements": xml_safe_text(section.get("medium_term_improvements", "")),
            }
        )

    return {
        "sections": cleaned_sections,
        "executive_summary": xml_safe_text(report.get("executive_summary", "")),
        "top_5_strengths": ensure_list_of_strings(report.get("top_5_strengths", []), exact_length=5),
        "top_5_problems": ensure_list_of_strings(report.get("top_5_problems", []), exact_length=5),
        "day_30_plan": ensure_list_of_strings(report.get("day_30_plan", [])),
        "day_60_plan": ensure_list_of_strings(report.get("day_60_plan", [])),
        "day_90_plan": ensure_list_of_strings(report.get("day_90_plan", [])),
        "overall_score": {
            "total_score": data["total_score"],
            "percentage": data["percentage_score"],
        },
        "final_verdict": xml_safe_text(report.get("final_verdict", "")),
    }


def generate_report_json(client: OpenAI, data: dict[str, Any], benchmark_summary: str) -> dict[str, Any]:
    response = client.responses.create(
        model=MODEL_NAME,
        input=f"{SYSTEM_PROMPT}\n\n{build_user_prompt(data, benchmark_summary)}",
    )
    return validate_report_json(extract_json_object(response.output_text.strip()), data)


def score_colour(score: float, scale: float) -> str:
    pct = (score / scale) * 100
    if pct <= 40:
        return RISK
    if pct <= 70:
        return AMBER
    return GOOD


def score_status(score: int) -> str:
    if score <= 4:
        return "High Risk"
    if score <= 7:
        return "Moderate"
    return "Strong"


def score_fill(score: int) -> str:
    if score <= 4:
        return RISK_FILL
    if score <= 7:
        return AMBER_FILL
    return GOOD_FILL


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_cell_text(cell, text: str, bold: bool = False, color: RGBColor = TEXT_RGB, size: float = FONT_SIZE) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = paragraph.add_run(xml_safe_text(text))
    run.bold = bold
    run.font.name = FONT_NAME
    run.font.size = Pt(size)
    run.font.color.rgb = color
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def style_run(run, bold: bool = False, size: float = FONT_SIZE, color: RGBColor = TEXT_RGB) -> None:
    run.bold = bold
    run.font.name = FONT_NAME
    run.font.size = Pt(size)
    run.font.color.rgb = color


def add_text_paragraph(
    doc: Document,
    text: str,
    bold: bool = False,
    size: float = FONT_SIZE,
    center: bool = False,
    colour: RGBColor = TEXT_RGB,
) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.15
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(xml_safe_text(text))
    style_run(run, bold=bold, size=size, color=colour)


def add_divider(doc: Document, width: int = 30) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(8)
    run = p.add_run("—" * width)
    style_run(run, size=10, color=MUTED_RGB)


def add_heading_clean(doc: Document, text: str, level: int) -> None:
    p = doc.add_heading(xml_safe_text(text), level=level)
    p.paragraph_format.space_before = Pt(8 if level == 1 else 4)
    p.paragraph_format.space_after = Pt(6)
    for run in p.runs:
        run.font.name = FONT_NAME
        run.font.color.rgb = TEXT_RGB


def add_list_block(doc: Document, items: list[str]) -> None:
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.1
        run = p.add_run(xml_safe_text(item))
        style_run(run, size=FONT_SIZE)


def add_client_summary_table(doc: Document, data: dict[str, Any]) -> None:
    table = doc.add_table(rows=6, cols=2)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    rows = [
        ("Client", data["company_name"]),
        ("Sector", data["sector"]),
        ("Location", data["location"]),
        ("Headcount", str(data["headcount"])),
        ("Annual Hiring Volume", str(data["annual_hiring_volume"])),
        ("Key Roles Hired", str(data["key_roles_hired"])),
    ]
    for i, (label, value) in enumerate(rows):
        set_cell_shading(table.rows[i].cells[0], SUBHEADER_FILL)
        set_cell_text(table.rows[i].cells[0], label, bold=True, size=9.5)
        set_cell_text(table.rows[i].cells[1], value, size=9.5)


def add_cover_page(doc: Document, data: dict[str, Any]) -> None:
    add_text_paragraph(doc, BRAND_NAME, bold=True, size=TITLE_SIZE, center=True)
    add_text_paragraph(doc, BRAND_TAGLINE, size=SUBTITLE_SIZE, center=True, colour=MUTED_RGB)
    add_divider(doc)
    add_text_paragraph(doc, "Recruitment Audit Report", bold=True, size=22, center=True)
    add_text_paragraph(doc, data["company_name"], bold=True, size=14, center=True)
    add_text_paragraph(doc, f"Prepared by {BRAND_NAME}", size=10, center=True, colour=MUTED_RGB)
    add_text_paragraph(doc, f"Prepared on {datetime.today().strftime('%d %B %Y')}", size=10, center=True, colour=MUTED_RGB)
    doc.add_paragraph("")
    add_client_summary_table(doc, data)


def create_section_score_chart(company_name: str, scores: list[int]) -> Path:
    labels = [str(i) for i in range(1, 13)]
    colours = [score_colour(v, 10) for v in scores]

    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    x = list(range(len(labels)))
    bars = ax.bar(x, scores, color=colours, width=0.62)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8, color=TEXT_HEX)
    ax.set_ylim(0, 10.8)
    ax.set_ylabel("Score", fontsize=9, color=TEXT_HEX)
    ax.set_title("Audit score chart", fontsize=11, color=TEXT_HEX, pad=12)
    ax.grid(axis="y", linestyle="--", alpha=0.20)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(MID_GREY)
    ax.spines["bottom"].set_color(MID_GREY)

    for rect, value in zip(bars, scores):
        ax.text(
            rect.get_x() + rect.get_width() / 2,
            value + 0.15,
            str(value),
            ha="center",
            va="bottom",
            fontsize=8,
            color=TEXT_HEX,
        )

    path = output_dir() / f"{clean_filename(company_name)}_section_scores.png"
    plt.tight_layout(pad=1.1)
    plt.savefig(path, dpi=240, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def create_overall_score_chart(company_name: str, total_score: int) -> Path:
    fig, ax = plt.subplots(figsize=(7.4, 1.7))
    ax.barh(["Overall"], [total_score], color=score_colour(total_score, 120), height=0.45)
    ax.barh(["Overall"], [120 - total_score], left=[total_score], color=LIGHT_GREY, height=0.45)

    ax.set_xlim(0, 120)
    ax.set_xlabel("Score out of 120", fontsize=9, color=TEXT_HEX)
    ax.set_title("Overall score chart", fontsize=11, color=TEXT_HEX, pad=10)
    ax.grid(axis="x", linestyle="--", alpha=0.20)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color(MID_GREY)
    ax.tick_params(axis="x", labelsize=8, colors=TEXT_HEX)
    ax.tick_params(axis="y", labelsize=8, colors=TEXT_HEX)
    ax.text(min(total_score + 1, 116), 0, f"{total_score}/120", va="center", fontsize=8, color=TEXT_HEX)

    path = output_dir() / f"{clean_filename(company_name)}_overall_score.png"
    plt.tight_layout(pad=1.0)
    plt.savefig(path, dpi=240, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def create_benchmark_chart(company_name: str, metrics: dict[str, float | None], benchmark: pd.Series | None) -> Path | None:
    if benchmark is None:
        return None

    labels: list[str] = []
    client_values: list[float] = []
    benchmark_values: list[float] = []
    suffixes: list[str] = []

    mapping = {
        "time_to_hire_days": ("avg_time_to_hire_days", "Time to hire", "d"),
        "applications_per_role": ("avg_applications_per_role", "Applications", ""),
        "offer_acceptance": ("avg_offer_acceptance_pct", "Offer acceptance", "%"),
        "first_year_attrition": ("avg_attrition_pct", "Attrition", "%"),
    }

    for key, (bench_col, label, suffix) in mapping.items():
        client_value = metrics.get(key)
        bench_value = safe_float(benchmark.get(bench_col))
        if client_value is None or bench_value is None:
            continue
        labels.append(label)
        client_values.append(float(client_value))
        benchmark_values.append(float(bench_value))
        suffixes.append(suffix)

    if not labels:
        return None

    x = list(range(len(labels)))
    width = 0.34
    max_value = max(client_values + benchmark_values)

    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    ax.bar([i - width / 2 for i in x], client_values, width=width, label="Client", color=DARK)
    ax.bar([i + width / 2 for i in x], benchmark_values, width=width, label="Benchmark", color=GOLD)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8, color=TEXT_HEX)
    ax.set_title("Benchmark comparison chart", fontsize=11, color=TEXT_HEX, pad=12)
    ax.grid(axis="y", linestyle="--", alpha=0.20)
    ax.legend(frameon=False, fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(MID_GREY)
    ax.spines["bottom"].set_color(MID_GREY)

    bump = max_value * 0.03 if max_value > 0 else 0.5
    for i, value in enumerate(client_values):
        ax.text(i - width / 2, value + bump, f"{value:.1f}{suffixes[i]}", ha="center", fontsize=8, color=TEXT_HEX)
    for i, value in enumerate(benchmark_values):
        ax.text(i + width / 2, value + bump, f"{value:.1f}{suffixes[i]}", ha="center", fontsize=8, color=TEXT_HEX)

    path = output_dir() / f"{clean_filename(company_name)}_benchmark_chart.png"
    plt.tight_layout(pad=1.1)
    plt.savefig(path, dpi=240, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def add_score_summary_table(doc: Document, scores: list[int]) -> None:
    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    headers = ["Audit Area", "Score", "Status", "Scoring Basis"]
    for idx, header in enumerate(headers):
        cell = table.rows[0].cells[idx]
        set_cell_shading(cell, HEADER_FILL)
        set_cell_text(cell, header, bold=True, color=WHITE_RGB, size=9)

    scoring_basis = [
        "Planning, governance and ownership",
        "KPI visibility and funnel performance",
        "Employer brand and market pull",
        "Advert consistency and role clarity",
        "Channel mix and sourcing reach",
        "Screening structure and pace",
        "Interview control and assessment quality",
        "Decision speed and offer conversion",
        "Onboarding quality and early retention",
        "Retention risk and attrition profile",
        "Candidate journey and feedback discipline",
        "Ownership, reporting and accountability",
    ]

    for title, score, basis in zip(SECTIONS, scores, scoring_basis):
        row = table.add_row()
        set_cell_text(row.cells[0], title, size=9)
        set_cell_text(row.cells[1], f"{score}/10", bold=True, size=9)
        set_cell_shading(row.cells[2], score_fill(score))
        set_cell_text(row.cells[2], score_status(score), bold=True, size=9)
        set_cell_text(row.cells[3], basis, size=9)


def add_diagnostic_snapshot_table(doc: Document, diagnostics: dict[str, Any]) -> None:
    table = doc.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    headers = ["Diagnostic", "Value"]
    for idx, header in enumerate(headers):
        cell = table.rows[0].cells[idx]
        set_cell_shading(cell, HEADER_FILL)
        set_cell_text(cell, header, bold=True, color=WHITE_RGB, size=9)

    items = [
        ("Maturity level", diagnostics["maturity_level"]),
        ("Primary bottleneck", diagnostics["primary_bottleneck"]),
        ("Funnel signal", diagnostics["funnel_signal"]),
        ("Speed signal", diagnostics["speed_signal"]),
        ("Offer signal", diagnostics["offer_signal"]),
        ("Retention signal", diagnostics["retention_signal"]),
        ("Interview friction", diagnostics["interview_signal"]),
        ("Failure pattern", diagnostics["likely_failure_pattern"]),
    ]

    if diagnostics["application_to_interview_pct"] is not None:
        items.append(("Application-to-interview conversion", f"{diagnostics['application_to_interview_pct']}%"))
    if diagnostics["estimated_interviews_per_hire"] is not None:
        items.append(("Estimated interviews per hire", str(diagnostics["estimated_interviews_per_hire"])))
    if diagnostics["annual_interview_hours"] is not None:
        items.append(("Estimated annual interview hours", str(diagnostics["annual_interview_hours"])))
    if diagnostics["estimated_backfills"] is not None:
        items.append(("Attrition-driven backfills", str(diagnostics["estimated_backfills"])))
    if diagnostics["vacancy_weeks"] is not None:
        items.append(("Vacancy weeks from repeat hiring load", str(diagnostics["vacancy_weeks"])))

    for label, value in items:
        row = table.add_row()
        set_cell_shading(row.cells[0], SUBHEADER_FILL)
        set_cell_text(row.cells[0], label, bold=True, size=9)
        set_cell_text(row.cells[1], value, size=9)


def save_word_report(
    data: dict[str, Any],
    report: dict[str, Any],
    benchmark_summary: str,
    section_chart: Path | None,
    overall_chart: Path | None,
    benchmark_chart: Path | None,
) -> Path:
    path = output_dir() / f"{clean_filename(data['company_name'])}_recruitment_audit.docx"
    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(0.65)
        section.bottom_margin = Inches(0.65)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    styles = doc.styles
    for style_name in ["Normal", "Heading 1", "Heading 2", "Heading 3"]:
        styles[style_name].font.name = FONT_NAME
        styles[style_name].font.color.rgb = TEXT_RGB

    styles["Normal"].font.size = Pt(FONT_SIZE)
    styles["Heading 1"].font.size = Pt(H1_SIZE)
    styles["Heading 2"].font.size = Pt(H2_SIZE)
    styles["Heading 3"].font.size = Pt(H3_SIZE)

    add_cover_page(doc, data)

    doc.add_section(WD_SECTION.NEW_PAGE)

    add_heading_clean(doc, "Executive overview", level=1)
    add_text_paragraph(doc, report["executive_summary"])

    add_divider(doc)
    add_heading_clean(doc, "Overall recruitment score", level=1)
    add_text_paragraph(doc, f"{data['total_score']}/120 ({data['percentage_score']}%)", bold=True, size=14)
    if overall_chart:
        doc.add_picture(str(overall_chart), width=Inches(5.9))

    add_divider(doc)
    add_heading_clean(doc, "Diagnostic snapshot", level=1)
    add_diagnostic_snapshot_table(doc, data["diagnostics"])

    add_divider(doc)
    add_heading_clean(doc, "Audit score chart", level=1)
    if section_chart:
        doc.add_picture(str(section_chart), width=Inches(6.1))

    if benchmark_chart:
        add_divider(doc)
        add_heading_clean(doc, "Benchmark comparison chart", level=1)
        doc.add_picture(str(benchmark_chart), width=Inches(6.1))

    add_divider(doc)
    add_heading_clean(doc, "Detailed audit", level=1)
    add_text_paragraph(
        doc,
        f"Recruitment audit for {data['company_name']} ({data['sector']}, {data['location']}, {data['headcount']} employees)"
    )
    add_text_paragraph(doc, f"Note on benchmarks: {benchmark_summary}")

    add_heading_clean(doc, "Key funnel metrics observed", level=2)
    funnel_lines = [
        f"Applications per role: {data['raw_metrics']['applications_per_role']}",
        f"Candidates reaching interview: {data['raw_metrics']['candidates_reaching_interview']}",
        f"Offer acceptance rate: {data['raw_metrics']['offer_acceptance']}",
        f"Average time to hire: {data['raw_metrics']['time_to_hire']}",
        f"Interview stages: {data['raw_metrics']['interview_stages']}",
        f"Interview feedback: {data['raw_metrics']['interview_feedback_time']}",
        f"First-year attrition: {data['raw_metrics']['first_year_attrition']}",
    ]
    for line in funnel_lines:
        add_text_paragraph(doc, line)

    add_divider(doc)
    add_heading_clean(doc, "Section score summary", level=1)
    add_score_summary_table(doc, data["section_scores"])

    add_divider(doc)
    for i, section in enumerate(report["sections"], start=1):
        add_heading_clean(doc, f"{i}) {section['title']}", level=1)
        add_text_paragraph(doc, f"Score: {section['score']}/10", bold=True)

        add_heading_clean(doc, "Current state", level=2)
        add_text_paragraph(doc, section["current_state"])

        add_heading_clean(doc, "Key risks", level=2)
        add_text_paragraph(doc, section["key_risks"])

        add_heading_clean(doc, "Commercial impact", level=2)
        add_text_paragraph(doc, section["commercial_impact"])

        add_heading_clean(doc, "Quick wins", level=2)
        add_text_paragraph(doc, section["quick_wins"])

        add_heading_clean(doc, "Medium term improvements", level=2)
        add_text_paragraph(doc, section["medium_term_improvements"])

    add_divider(doc)
    add_heading_clean(doc, "Top 5 strengths", level=1)
    add_list_block(doc, report["top_5_strengths"])

    add_divider(doc)
    add_heading_clean(doc, "Top 5 problems", level=1)
    add_list_block(doc, report["top_5_problems"])

    add_divider(doc)
    add_heading_clean(doc, "30 day plan", level=1)
    add_list_block(doc, report["day_30_plan"])

    add_heading_clean(doc, "60 day plan", level=1)
    add_list_block(doc, report["day_60_plan"])

    add_heading_clean(doc, "90 day plan", level=1)
    add_list_block(doc, report["day_90_plan"])

    add_divider(doc)
    add_heading_clean(doc, "Final verdict", level=1)
    add_text_paragraph(doc, report["final_verdict"])

    doc.save(path)
    return path


if __name__ == "__main__":
    client = OpenAI(api_key=get_api_key())
    print("This module is designed to be imported by app.py.")
