from __future__ import annotations

import html
import json
import os
import subprocess
import traceback
from datetime import datetime
from pathlib import Path

from flask import Flask, request, send_file
from openai import OpenAI

from recruitment_audit import (
    SECTION_ORDER,
    _rating_for_score,
    build_fallback_report,
    get_api_key,
    list_benchmark_sectors,
    load_benchmarks,
    build_benchmark_summary,
    auto_score_sections,
    generate_report_json,
    create_section_score_chart,
    create_overall_score_chart,
    create_benchmark_chart,
    save_pdf_report,
    parse_time_to_hire_days,
    parse_numeric_value,
)

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
MAILER_SCRIPT = BASE_DIR / "send_audit_notification.mjs"
NOTIFICATION_RECIPIENTS = [
    "max@bradfordandmarsh.co.uk",
    "will@bradfordandmarsh.co.uk",
    "michael@bradfordandmarsh.co.uk",
]

FALLBACK_SECTORS = [
    "Accounting / Audit",
    "Agriculture / Food Production",
    "Architecture / Design",
    "Aerospace / Defence",
    "Automotive",
    "Construction",
    "Consulting",
    "Consumer Goods / FMCG",
    "Education",
    "Ecommerce",
    "Energy / Utilities",
    "Engineering",
    "Financial Services",
    "Healthcare",
    "Hospitality",
    "Insurance",
    "Investment Management",
    "Legal Services",
    "Life Sciences",
    "Logistics / Supply Chain",
    "Manufacturing",
    "Media / Marketing / Advertising",
    "Medical Devices",
    "Non-Profit / Charity",
    "Pharmaceuticals",
    "Private Equity / Venture Capital",
    "Professional Services",
    "Property / Real Estate",
    "Public Sector / Government",
    "Retail",
    "SaaS",
    "Technology / Software",
    "Telecommunications",
    "Transport / Aviation / Maritime",
    "Travel / Leisure",
    "Other",
]

YES_NO_FIELDS = [
    ("has_hiring_plan", "Do you have a formal recruitment or workforce plan in place?"),
    ("tracks_metrics", "Do you track recruitment KPIs on a regular basis?"),
    ("has_employer_brand", "Do you have a defined employer brand or EVP?"),
    ("standardised_job_specs", "Do you use standard job adverts and job descriptions?"),
    ("multi_channel_sourcing", "Do you use multiple sourcing channels consistently?"),
    ("structured_screening", "Do you follow a consistent screening process?"),
    ("structured_interviews", "Do you use structured interviews or interview scorecards?"),
    ("fast_offer_process", "Do you have a fast and consistent offer approval process?"),
    ("formal_onboarding", "Do you follow a documented onboarding process?"),
    ("collects_candidate_feedback", "Do you collect candidate experience feedback?"),
    ("named_process_owner", "Is there a clearly named owner for the recruitment process?"),
    ("hiring_manager_training", "Do hiring managers receive interview or hiring training?"),
]


def yes_no_to_bool(value: str | None) -> bool:
    return str(value).strip().lower() in {"yes", "y", "true"}


def get_sector_options() -> list[str]:
    try:
        sectors = list_benchmark_sectors()
        if sectors:
            return sectors
    except Exception:
        pass
    return FALLBACK_SECTORS


def _notification_attachment_name(company_name: str, completed_at: datetime) -> str:
    safe_company = "".join(char if char.isalnum() else "_" for char in company_name.strip()).strip("_") or "Company"
    safe_company = "_".join(part for part in safe_company.split("_") if part)
    return f"{safe_company}_Recruitment_Audit_{completed_at.strftime('%Y-%m-%d')}.pdf"


def send_audit_notification(data: dict, report: dict, pdf_path: Path) -> None:
    if not MAILER_SCRIPT.exists():
        raise FileNotFoundError(f"Notification script not found at {MAILER_SCRIPT}")

    weakest_index = min(range(len(SECTION_ORDER)), key=lambda index: data["section_scores"][index])
    weakest_title = SECTION_ORDER[weakest_index]
    weakest_score = data["section_scores"][weakest_index]
    rating_band = _rating_for_score(data["total_score"])
    recommendation = report.get("recommended_intervention", {})
    completed_at = datetime.now()

    payload = {
        "smtp": {
            "host": os.environ.get("AUDIT_NOTIFICATION_SMTP_HOST", "smtp.office365.com"),
            "port": int(os.environ.get("AUDIT_NOTIFICATION_SMTP_PORT", "587")),
            "secure": False,
            "user": os.environ.get("AUDIT_NOTIFICATION_SMTP_USER", "audit@bradfordandmarsh.co.uk"),
            "pass": os.environ.get("AUDIT_NOTIFICATION_SMTP_PASS", ""),
        },
        "from": os.environ.get("AUDIT_NOTIFICATION_FROM", "audit@bradfordandmarsh.co.uk"),
        "to": NOTIFICATION_RECIPIENTS,
        "subject": f"New Audit Completed — {data['company_name']} — {completed_at.strftime('%d %B %Y')}",
        "text": "\n".join(
            [
                "New Recruitment Audit Completed",
                "--------------------------------",
                f"Company:        {data['company_name']}",
                f"Sector:         {data['sector']}",
                f"Location:       {data['location']}",
                "",
                f"Contact:        {data['contact_name']}",
                f"Title:          {data['job_title']}",
                f"Email:          {data['email_address']}",
                f"Phone:          {data['phone_number']}",
                "",
                f"Overall score:  {data['total_score']}/120 — {rating_band}",
                f"Weakest area:   {weakest_title} ({weakest_score}/10)",
                f"Recommended:    {recommendation.get('support_level', 'Not set')} — {recommendation.get('pricing', 'Pricing not set')}",
                "",
                f"Completed:      {completed_at.strftime('%d %B %Y %H:%M')}",
                "--------------------------------",
            ]
        ),
        "attachmentPath": str(pdf_path),
        "attachmentName": _notification_attachment_name(data["company_name"], completed_at),
    }

    subprocess.run(
        ["node", str(MAILER_SCRIPT)],
        input=json.dumps(payload),
        text=True,
        cwd=str(BASE_DIR),
        check=True,
        capture_output=True,
    )



def render_page(title: str, body: str) -> str:
    return f"""
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{title}</title>
        <style>
            :root {{
                --bg: #f4efe8;
                --bg-strong: #e6dfd6;
                --panel: rgba(255, 255, 255, 0.92);
                --panel-strong: #ffffff;
                --panel-soft: #f8f3ed;
                --ink: #142033;
                --muted: #5d6778;
                --muted-2: #8f98a6;
                --line: rgba(89, 103, 122, 0.20);
                --line-strong: rgba(48, 61, 79, 0.34);
                --brand: #142033;
                --brand-2: #2b3950;
                --accent: #b88d57;
                --accent-soft: rgba(184, 141, 87, 0.14);
                --success: #047857;
                --success-soft: rgba(4, 120, 87, 0.10);
                --error: #b91c1c;
                --error-soft: rgba(185, 28, 28, 0.08);
                --shadow-xl: 0 24px 56px rgba(20, 32, 51, 0.10);
                --shadow-lg: 0 16px 34px rgba(20, 32, 51, 0.08);
                --shadow-md: 0 8px 20px rgba(20, 32, 51, 0.05);
                --radius-2xl: 28px;
                --radius-xl: 22px;
                --radius-lg: 18px;
                --radius-md: 14px;
                --font-sans: "Aptos", "Inter", "Segoe UI", sans-serif;
                --font-display: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif;
            }}

            * {{ box-sizing: border-box; }}
            html, body {{
                margin: 0;
                padding: 0;
                min-height: 100%;
                font-family: var(--font-sans);
                color: var(--ink);
                background: linear-gradient(180deg, #faf7f2 0%, var(--bg) 52%, #eee7de 100%);
            }}
            body {{ min-height: 100vh; }}
            .shell {{ max-width: 960px; margin: 0 auto; padding: 28px 30px 72px; }}
            .topbar {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; margin-bottom: 16px; }}
            .brand-lockup {{ display: flex; align-items: center; gap: 16px; }}
            .brand-mark {{
                width: 62px; height: 62px; border-radius: 18px; display: grid; place-items: center;
                background: var(--brand);
                color: white; font-family: var(--font-display); font-size: 23px; letter-spacing: 0.04em;
                box-shadow: 0 12px 24px rgba(20, 32, 51, 0.12);
                position: relative; overflow: hidden;
            }}
            .brand-mark:after {{
                content: ""; position: absolute; inset: 1px; border-radius: 17px;
                border: 1px solid rgba(255,255,255,0.10);
            }}
            .brand {{ display: flex; flex-direction: column; gap: 4px; }}
            .brand-overline {{ font-size: 11px; font-weight: 800; letter-spacing: 0.16em; text-transform: uppercase; color: var(--accent); }}
            .brand-name {{ font-size: 20px; font-weight: 700; letter-spacing: -0.02em; font-family: var(--font-display); }}
            .brand-sub {{ color: var(--muted); font-size: 13px; max-width: 48ch; line-height: 1.5; }}
            .trust-pill {{
                color: var(--muted);
                border-radius: 999px;
                padding: 8px 0;
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 0.02em;
                text-transform: none;
            }}
            .hero {{
                background: rgba(255,255,255,0.82);
                color: var(--ink);
                border: 1px solid rgba(20, 32, 51, 0.07);
                border-radius: 28px;
                box-shadow: var(--shadow-md);
                padding: 26px 28px;
                margin-bottom: 18px;
            }}
            .hero h1 {{ margin: 0 0 10px; font-size: clamp(26px, 2.8vw, 34px); line-height: 1.1; letter-spacing: -0.03em; font-family: var(--font-display); font-weight: 700; color: var(--brand); }}
            .hero p {{ margin: 0; max-width: 40ch; color: var(--muted); font-size: 16px; line-height: 1.6; }}
            .hero-trust {{ margin-top: 14px; color: var(--muted); font-size: 12px; letter-spacing: 0.02em; }}

            .progress-shell {{ position: sticky; top: 12px; z-index: 30; margin-bottom: 18px; }}
            .progress-bar {{
                background: rgba(255,255,255,0.8); border: 1px solid rgba(20, 32, 51, 0.08);
                box-shadow: var(--shadow-md); backdrop-filter: blur(10px);
                border-radius: 22px; padding: 16px 18px;
            }}
            .progress-top {{ display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 14px; }}
            .progress-title {{ font-size: 13px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); }}
            .progress-stage-name {{ margin-top: 4px; font-size: 22px; letter-spacing: -0.03em; line-height: 1.1; font-family: var(--font-display); font-weight: 700; color: var(--brand); }}
            .progress-metrics {{ display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }}
            .progress-step-label {{ font-size: 12px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); }}
            .progress-percent {{ font-size: 14px; font-weight: 800; color: var(--brand); }}
            .track {{ width: 100%; height: 10px; border-radius: 999px; background: rgba(148, 163, 184, 0.18); overflow: hidden; margin-bottom: 14px; }}
            .track-fill {{ width: 0%; height: 100%; border-radius: 999px; background: #142033; transition: width 0.28s ease; }}
            .stepper {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }}
            .step {{
                min-width: 0; display: flex; align-items: center; gap: 12px; padding: 13px 14px; border-radius: 16px;
                border: 1px solid rgba(20, 32, 51, 0.06); background: rgba(248, 250, 252, 0.76);
                transition: box-shadow 0.22s ease, border-color 0.22s ease, background 0.22s ease;
            }}
            .step-dot {{ width: 34px; height: 34px; border-radius: 999px; display: grid; place-items: center; font-size: 12px; font-weight: 800; color: var(--muted); background: rgba(148, 163, 184, 0.14); flex: 0 0 auto; }}
            .step-copy {{ min-width: 0; }}
            .step-kicker {{ color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 800; margin-bottom: 4px; }}
            .step-title {{ font-size: 14px; font-weight: 800; color: var(--brand); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
            .step.active {{ background: rgba(255,255,255,0.98); border-color: rgba(15, 23, 42, 0.18); box-shadow: 0 10px 22px rgba(15, 23, 42, 0.06); }}
            .step.active .step-dot {{ background: var(--brand); color: white; }}
            .step.complete {{ background: rgba(4, 120, 87, 0.05); border-color: rgba(4, 120, 87, 0.12); }}
            .step.complete .step-dot {{ background: rgba(4, 120, 87, 0.14); color: var(--success); }}

            .assessment-wrap {{ display: flex; justify-content: center; }}
            .panel {{
                background: rgba(255,255,255,0.9);
                border: 1px solid rgba(20, 32, 51, 0.08); backdrop-filter: blur(10px);
                border-radius: var(--radius-2xl); box-shadow: var(--shadow-lg); overflow: hidden;
            }}
            .assessment-panel {{ width: min(100%, 760px); }}
            .stage {{ display: none; padding: 42px 42px 24px; animation: stageIn 0.22s ease; min-height: 460px; }}
            .stage.active {{ display: block; }}
            @keyframes stageIn {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: translateY(0); }} }}

            .section-head {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 24px; margin-bottom: 26px; }}
            .section-kicker {{ display: inline-flex; align-items: center; gap: 8px; margin-bottom: 10px; color: var(--accent); font-size: 12px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; }}
            .section-title {{ margin: 0 0 8px; font-size: 30px; letter-spacing: -0.04em; line-height: 1.08; font-family: var(--font-display); font-weight: 700; }}
            .section-copy {{ margin: 0; max-width: 56ch; color: var(--muted); line-height: 1.6; font-size: 15px; }}
            .stage-step {{ display: none; }}
            .stage-step.active {{ display: block; animation: stageIn 0.24s ease; }}
            .step-panel {{
                padding: 28px;
                border: 1px solid rgba(20, 32, 51, 0.07);
                border-radius: 24px;
                background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248, 250, 252, 0.84));
                box-shadow: var(--shadow-md);
            }}
            .step-overline {{ color: var(--muted); font-size: 11px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 14px; }}
            .step-headline {{ margin: 0 0 10px; font-size: 28px; letter-spacing: -0.04em; line-height: 1.08; font-family: var(--font-display); font-weight: 700; color: var(--brand); }}
            .step-support {{ margin: 0 0 26px; color: var(--muted); line-height: 1.7; font-size: 15px; max-width: 50ch; }}
            .step-fields {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 22px 18px; }}
            .field {{ display: flex; flex-direction: column; gap: 6px; }}
            .field.full {{ grid-column: 1 / -1; }}
            label {{ font-size: 12px; font-weight: 700; color: var(--brand); letter-spacing: 0.01em; }}
            .hint {{ color: var(--muted); font-size: 12px; line-height: 1.6; }}
            input, select, textarea {{
                width: 100%; border: 1px solid rgba(100, 116, 139, 0.16); background: rgba(255,255,255,0.96);
                border-radius: 16px; padding: 17px 16px; font: inherit; color: var(--ink); outline: none;
                transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
            }}
            input:hover, select:hover, textarea:hover {{ border-color: rgba(51, 65, 85, 0.22); background: rgba(255,255,255,0.98); }}
            input:focus, select:focus, textarea:focus {{ border-color: rgba(15, 23, 42, 0.30); box-shadow: 0 0 0 6px rgba(15, 23, 42, 0.08); background: white; }}
            .input-wrap {{ position: relative; }}
            .input-wrap input {{ padding-right: 88px; }}
            .suffix {{ position: absolute; right: 14px; top: 50%; transform: translateY(-50%); font-size: 12px; font-weight: 800; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; pointer-events: none; }}

            .footer-bar {{ display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 24px 38px 32px; border-top: 1px solid rgba(148, 163, 184, 0.16); background: rgba(248,250,252,0.58); }}
            .footer-copy {{ max-width: 60ch; color: var(--muted); line-height: 1.7; font-size: 13px; }}
            .button-row {{ display: flex; gap: 10px; flex-wrap: wrap; justify-content: flex-end; }}
            .button {{
                appearance: none; border: none; border-radius: 16px; padding: 15px 20px; font-size: 14px; font-weight: 800;
                letter-spacing: 0.01em; cursor: pointer; text-decoration: none;
                transition: box-shadow 0.22s ease, opacity 0.22s ease, background 0.22s ease, border-color 0.22s ease;
            }}
            .button-primary {{ color: white; background: #142033; box-shadow: 0 12px 24px rgba(15, 23, 42, 0.16); }}
            .button-secondary {{ background: rgba(255,255,255,0.96); color: var(--brand); border: 1px solid rgba(15, 23, 42, 0.12); box-shadow: 0 8px 18px rgba(15, 23, 42, 0.05); }}
            .button-ghost {{ background: rgba(248, 250, 252, 0.96); color: var(--muted); border: 1px solid rgba(148, 163, 184, 0.18); }}
            .button[hidden] {{ display: none !important; }}
            .button:hover {{ opacity: 0.96; }}

            .sidebar {{ position: sticky; top: 118px; display: grid; gap: 14px; }}
            .sidebar-card {{
                background: linear-gradient(180deg, rgba(255,255,255,0.94), rgba(255,255,255,0.88));
                border: 1px solid rgba(255,255,255,0.72); border-radius: 24px; padding: 22px; box-shadow: var(--shadow-md); backdrop-filter: blur(14px);
            }}
            .sidebar-card.brand-card {{
                background: linear-gradient(165deg, rgba(20, 32, 51, 0.98), rgba(39, 52, 73, 0.95));
                color: white;
            }}
            .sidebar-card.brand-card .sidebar-kicker {{ color: rgba(184, 141, 87, 0.92); }}
            .sidebar-card.brand-card .sidebar-title,
            .sidebar-card.brand-card p,
            .sidebar-card.brand-card .sidebar-copy {{ color: rgba(255,255,255,0.88); }}
            .sidebar-kicker {{ color: var(--accent); font-size: 11px; font-weight: 800; letter-spacing: 0.10em; text-transform: uppercase; margin-bottom: 10px; }}
            .sidebar-title {{ margin: 0 0 10px; font-size: 22px; letter-spacing: -0.04em; font-family: var(--font-display); font-weight: 700; }}
            .sidebar-copy, .sidebar-card p {{ margin: 0; color: var(--muted); line-height: 1.75; font-size: 14px; }}
            .sidebar-mark {{
                width: 52px; height: 52px; border-radius: 16px; display: grid; place-items: center; margin-bottom: 14px;
                background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.10);
                font-family: var(--font-display); font-size: 22px; letter-spacing: 0.04em;
            }}
            .sidebar-rule {{ width: 56px; height: 2px; background: rgba(184, 141, 87, 0.92); margin: 16px 0; }}
            .summary-list {{ display: grid; gap: 10px; margin-top: 18px; }}
            .summary-item {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 14px; border-radius: 16px; background: rgba(248, 250, 252, 0.88); border: 1px solid rgba(148, 163, 184, 0.10); }}
            .summary-label {{ color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; }}
            .summary-value {{ text-align: right; font-weight: 800; color: var(--brand); font-size: 13px; }}
            .metric-chip-row {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }}
            .chip {{ display: inline-flex; align-items: center; gap: 7px; padding: 10px 12px; border-radius: 999px; background: rgba(15, 23, 42, 0.04); color: var(--brand); font-size: 12px; font-weight: 700; }}
            .chip-dot {{ width: 8px; height: 8px; border-radius: 999px; background: var(--accent); }}
            .capture-list {{ display: grid; gap: 10px; margin-top: 16px; }}
            .capture-item {{ display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 12px 14px; border-radius: 16px; background: rgba(248, 250, 252, 0.9); border: 1px solid rgba(148, 163, 184, 0.12); }}
            .capture-item strong {{ font-size: 13px; }}
            .capture-state {{ font-size: 11px; font-weight: 800; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); }}
            .capture-item.complete {{ background: rgba(4, 120, 87, 0.06); border-color: rgba(4, 120, 87, 0.14); }}
            .capture-item.complete .capture-state {{ color: var(--success); }}
            .trust-grid {{ display: grid; gap: 10px; margin-top: 14px; }}
            .trust-row {{ display: flex; align-items: flex-start; gap: 10px; color: var(--muted); font-size: 13px; line-height: 1.65; }}
            .trust-mark {{ width: 20px; height: 20px; border-radius: 999px; background: rgba(15, 23, 42, 0.06); color: var(--brand); display: grid; place-items: center; font-size: 12px; font-weight: 900; flex: 0 0 auto; margin-top: 1px; }}
            .preview-list {{ display: grid; gap: 10px; margin-top: 16px; }}
            .preview-row {{
                display: flex; align-items: flex-start; gap: 10px; padding: 12px 14px; border-radius: 16px;
                background: rgba(248, 250, 252, 0.9); border: 1px solid rgba(148, 163, 184, 0.12);
            }}
            .preview-index {{
                width: 28px; height: 28px; border-radius: 999px; display: grid; place-items: center;
                background: rgba(20, 32, 51, 0.08); color: var(--brand); font-size: 12px; font-weight: 800; flex: 0 0 auto;
            }}
            .preview-copy strong {{ display: block; color: var(--brand); font-size: 13px; margin-bottom: 4px; }}
            .preview-copy span {{ color: var(--muted); font-size: 13px; line-height: 1.55; }}
            .source-note {{
                margin-top: 16px; padding-top: 16px; border-top: 1px solid rgba(148, 163, 184, 0.16);
                color: var(--muted); font-size: 12px; line-height: 1.7;
            }}
            .cred-row {{
                display: flex; justify-content: space-between; gap: 12px; padding: 11px 0; border-bottom: 1px solid rgba(148, 163, 184, 0.12);
            }}
            .cred-row:last-child {{ border-bottom: none; }}
            .cred-label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; font-weight: 700; }}
            .cred-value {{ color: var(--brand); font-size: 13px; font-weight: 800; text-align: right; }}

            .status {{ border-radius: 26px; padding: 30px; border: 1px solid var(--line); background: rgba(255,255,255,0.94); box-shadow: var(--shadow-lg); }}
            .status.success {{ background: rgba(236, 253, 245, 0.96); border-color: rgba(167, 243, 208, 0.92); }}
            .status.error {{ background: rgba(254, 242, 242, 0.96); border-color: rgba(254, 202, 202, 0.96); }}
            .status h2 {{ margin: 0 0 10px; font-size: 30px; letter-spacing: -0.03em; }}
            .status p {{ margin: 8px 0; line-height: 1.7; }}
            .status pre {{ white-space: pre-wrap; background: rgba(255,255,255,0.80); border: 1px solid rgba(209, 213, 219, 0.8); padding: 16px; border-radius: 12px; overflow-x: auto; font-size: 12px; line-height: 1.5; margin-top: 18px; }}
            .back-link {{ display: inline-block; margin-top: 18px; color: var(--ink); font-weight: 800; text-decoration: none; }}

            .loading-overlay {{
                position: fixed; inset: 0; background: rgba(245, 247, 251, 0.76); backdrop-filter: blur(8px);
                display: none; align-items: center; justify-content: center; z-index: 1000; padding: 16px;
            }}
            .loading-card {{
                width: min(560px, calc(100vw - 32px)); background: rgba(255,255,255,0.96); border: 1px solid rgba(255,255,255,0.92);
                border-radius: 28px; box-shadow: var(--shadow-xl); padding: 30px;
            }}
            .loading-head {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 14px; }}
            .loading-pill {{ display: inline-flex; align-items: center; gap: 8px; padding: 9px 12px; border-radius: 999px; background: rgba(15, 23, 42, 0.05); color: var(--brand); font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.06em; }}
            .spinner {{ width: 16px; height: 16px; border-radius: 999px; border: 2.5px solid rgba(15, 23, 42, 0.14); border-top-color: #111827; animation: spin 0.9s linear infinite; }}
            .loading-card h3 {{ margin: 0 0 10px; font-size: 28px; letter-spacing: -0.04em; font-family: var(--font-display); font-weight: 700; }}
            .loading-card p {{ margin: 0; color: var(--muted); line-height: 1.75; }}
            .loading-track {{ width: 100%; height: 12px; border-radius: 999px; background: rgba(148, 163, 184, 0.18); overflow: hidden; margin: 20px 0 14px; }}
            .loading-fill {{ height: 100%; width: 0%; border-radius: 999px; background: linear-gradient(90deg, #0f172a, #334155, #a16207); transition: width 0.35s ease; }}
            .loading-meta {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; color: var(--muted); font-size: 13px; margin-bottom: 12px; }}
            .loading-list {{ display: grid; gap: 9px; margin-top: 14px; }}
            .loading-list-item {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 14px; border-radius: 16px; background: rgba(248, 250, 252, 0.9); border: 1px solid rgba(148, 163, 184, 0.12); color: var(--muted); font-size: 13px; }}
            .loading-list-item.is-active {{ border-color: rgba(15, 23, 42, 0.10); background: rgba(15, 23, 42, 0.04); color: var(--brand); }}
            .completion-state {{ display: none; }}
            .completion-kicker {{ color: var(--accent); font-size: 11px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 10px; }}
            .completion-list {{ display: grid; gap: 10px; margin: 18px 0; }}
            .completion-item {{ padding: 12px 14px; border-radius: 16px; background: rgba(4, 120, 87, 0.06); border: 1px solid rgba(4, 120, 87, 0.14); color: var(--brand); font-size: 13px; line-height: 1.6; }}
            .completion-actions {{ display: flex; justify-content: flex-end; gap: 10px; margin-top: 12px; }}
            @keyframes spin {{ to {{ transform: rotate(360deg); }} }}

            @media (max-width: 1120px) {{
                .stepper {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
            }}
            @media (max-width: 980px) {{
                .step-fields, .stepper {{ grid-template-columns: 1fr; }}
                .topbar, .footer-bar, .progress-top {{ flex-direction: column; align-items: flex-start; }}
                .stage, .footer-bar {{ padding-left: 22px; padding-right: 22px; }}
                .button-row {{ width: 100%; }}
                .button {{ width: 100%; }}
                .hero {{ padding: 22px; }}
                .hero h1 {{ font-size: 24px; max-width: none; }}
                .shell {{ padding-top: 20px; }}
                .brand-lockup {{ align-items: flex-start; }}
                .progress-metrics {{ align-items: flex-start; }}
                .step-panel {{ padding: 22px; }}
                .step-headline {{ font-size: 24px; }}
            }}
        </style>
    </head>
    <body>
        <div class="shell">
            {body}
        </div>

        <div class="loading-overlay" id="loadingOverlay">
            <div class="loading-card">
                <div id="loadingState">
                    <div class="loading-head">
                        <div class="loading-pill"><span class="spinner"></span> Analysing</div>
                        <div id="loadingPercent">0%</div>
                    </div>
                    <div class="brand-overline" style="margin-bottom: 8px;">Bradford &amp; Marsh Consulting</div>
                    <h3>Analysing your recruitment model…</h3>
                    <p>
                        Reviewing process control, hiring performance and benchmark positioning
                    </p>

                    <div class="loading-track">
                        <div class="loading-fill" id="loadingFill"></div>
                    </div>

                    <div class="loading-meta">
                        <div id="loadingStatus">Preparing submission</div>
                        <div>Preparing download</div>
                    </div>

                    <div class="loading-list">
                        <div class="loading-list-item is-active"><span>Reviewing business profile</span><span>01</span></div>
                        <div class="loading-list-item"><span>Analysing hiring performance</span><span>02</span></div>
                        <div class="loading-list-item"><span>Reviewing process control</span><span>03</span></div>
                        <div class="loading-list-item"><span>Preparing final report</span><span>04</span></div>
                    </div>
                </div>

                <div class="completion-state" id="completionState">
                    <div class="completion-kicker">Report ready</div>
                    <h3>Your Recruitment Audit is Ready</h3>
                    <p>Your report has been generated and is ready to download</p>
                    <div class="completion-list">
                        <div class="completion-item" id="completionFilename">File prepared</div>
                    </div>
                    <div class="completion-actions">
                        <button class="button button-primary" type="button" id="downloadComplete">Download Report</button>
                        <button class="button button-secondary" type="button" id="startNewAudit">Start New Audit</button>
                    </div>
                </div>
            </div>
        </div>

        <script>
            (function() {{
                const form = document.getElementById("auditForm");
                const stages = Array.from(document.querySelectorAll(".stage"));
                const stepEls = Array.from(document.querySelectorAll(".step"));
                const nextBtn = document.querySelector("[data-next-step]");
                const prevBtn = document.querySelector("[data-prev-step]");
                const submitBtn = form ? form.querySelector('button[type="submit"]') : null;
                const progressFill = document.getElementById("progressFill");
                const progressPercent = document.getElementById("progressPercent");
                const progressStageLabel = document.getElementById("progressStageLabel");
                const progressStageName = document.getElementById("progressStageName");
                const progressStepLabel = document.getElementById("progressStepLabel");
                const stepFooterCopy = document.getElementById("stepFooterCopy");
                const downloadComplete = document.getElementById("downloadComplete");
                const startNewAudit = document.getElementById("startNewAudit");
                let isSubmitting = false;
                let currentStageIndex = 0;
                let currentStageStepIndex = 0;
                let latestDownloadUrl = "";
                let latestFilename = "recruitment_audit.pdf";
                const completedSteps = new Set();
                const stageDefinitions = stages.map((stage, stageIndex) => {{
                    return {{
                        element: stage,
                        title: stage.getAttribute("data-stage-title") || "Stage " + (stageIndex + 1),
                        steps: Array.from(stage.querySelectorAll(".stage-step")),
                    }};
                }});
                const totalStepCount = stageDefinitions.reduce((count, stage) => count + stage.steps.length, 0);

                function fieldFilled(field) {{
                    return String(field.value || "").trim() !== "";
                }}

                function stepKey(stageIndex, stepIndex) {{
                    return String(stageIndex) + ":" + String(stepIndex);
                }}

                function stepFields(stageIndex, stepIndex) {{
                    const stage = stageDefinitions[stageIndex];
                    if (!stage || !stage.steps[stepIndex]) return [];
                    return Array.from(stage.steps[stepIndex].querySelectorAll("input, select, textarea"));
                }}

                function stepIsComplete(stageIndex, stepIndex) {{
                    const fields = stepFields(stageIndex, stepIndex);
                    return fields.length > 0 && fields.every(fieldFilled);
                }}

                function syncCompletedSteps() {{
                    Array.from(completedSteps).forEach((key) => {{
                        const parts = key.split(":").map(Number);
                        if (parts.length !== 2 || !stepIsComplete(parts[0], parts[1])) {{
                            completedSteps.delete(key);
                        }}
                    }});
                }}

                function markCurrentStepComplete() {{
                    if (stepIsComplete(currentStageIndex, currentStageStepIndex)) {{
                        completedSteps.add(stepKey(currentStageIndex, currentStageStepIndex));
                    }}
                }}

                function stageIsComplete(stageIndex) {{
                    const stage = stageDefinitions[stageIndex];
                    if (!stage) return false;
                    return stage.steps.every((_, stepIndex) => completedSteps.has(stepKey(stageIndex, stepIndex)));
                }}

                function currentStage() {{
                    return stageDefinitions[currentStageIndex];
                }}

                function currentStepElement() {{
                    const stage = currentStage();
                    return stage ? stage.steps[currentStageStepIndex] : null;
                }}

                function updateProgress() {{
                    syncCompletedSteps();
                    const total = Math.round((completedSteps.size / totalStepCount) * 100);
                    if (progressFill) progressFill.style.width = total + "%";
                    if (progressPercent) progressPercent.textContent = total + "% complete";
                    if (progressStageLabel) progressStageLabel.textContent = "Stage " + (currentStageIndex + 1) + " of " + stageDefinitions.length;
                    if (progressStageName) progressStageName.textContent = currentStage().title;
                    if (progressStepLabel) progressStepLabel.textContent = "Step " + (currentStageStepIndex + 1) + " of " + currentStage().steps.length;

                    stepEls.forEach((el, index) => {{
                        el.classList.toggle("active", index === currentStageIndex);
                        el.classList.toggle("complete", stageIsComplete(index));
                    }});

                    stageDefinitions.forEach((stage, stageIndex) => {{
                        stage.element.classList.toggle("active", stageIndex === currentStageIndex);
                        stage.steps.forEach((step, stepIndex) => {{
                            step.classList.toggle("active", stageIndex === currentStageIndex && stepIndex === currentStageStepIndex);
                            const localLabel = step.querySelector("[data-local-step-label]");
                            if (localLabel) localLabel.textContent = "Step " + (stepIndex + 1) + " of " + stage.steps.length;
                        }});
                    }});

                    const atFirstStep = currentStageIndex === 0 && currentStageStepIndex === 0;
                    const atFinalStep = currentStageIndex === stageDefinitions.length - 1 && currentStageStepIndex === currentStage().steps.length - 1;
                    if (prevBtn) prevBtn.hidden = atFirstStep;
                    if (nextBtn) nextBtn.hidden = atFinalStep;
                    if (submitBtn) submitBtn.hidden = !atFinalStep;
                    if (stepFooterCopy) {{
                        const support = currentStepElement() ? currentStepElement().querySelector(".step-support") : null;
                        stepFooterCopy.textContent = support ? support.textContent : "Complete each step to build the final recruitment audit report.";
                    }}
                }}

                function showStep(stageIndex, stepIndex) {{
                    currentStageIndex = Math.max(0, Math.min(stageDefinitions.length - 1, stageIndex));
                    currentStageStepIndex = Math.max(0, Math.min(currentStage().steps.length - 1, stepIndex));
                    updateProgress();
                }}

                function validateCurrentStep() {{
                    const fields = stepFields(currentStageIndex, currentStageStepIndex);
                    for (const field of fields) {{
                        if (!field.checkValidity()) {{
                            field.reportValidity();
                            field.focus();
                            return false;
                        }}
                    }}
                    return true;
                }}

                function nextPosition() {{
                    if (currentStageStepIndex < currentStage().steps.length - 1) {{
                        return [currentStageIndex, currentStageStepIndex + 1];
                    }}
                    return [currentStageIndex + 1, 0];
                }}

                function previousPosition() {{
                    if (currentStageStepIndex > 0) {{
                        return [currentStageIndex, currentStageStepIndex - 1];
                    }}
                    const previousStageIndex = currentStageIndex - 1;
                    return [previousStageIndex, stageDefinitions[previousStageIndex].steps.length - 1];
                }}

                if (nextBtn) {{
                    nextBtn.addEventListener("click", () => {{
                        if (!validateCurrentStep()) return;
                        markCurrentStepComplete();
                        const target = nextPosition();
                        showStep(target[0], target[1]);
                    }});
                }}
                if (prevBtn) {{
                    prevBtn.addEventListener("click", () => {{
                        const target = previousPosition();
                        showStep(target[0], target[1]);
                    }});
                }}

                Array.from(document.querySelectorAll("#auditForm input, #auditForm select, #auditForm textarea")).forEach((field) => {{
                    field.addEventListener("input", updateProgress);
                    field.addEventListener("change", updateProgress);
                }});

                function setLoadingState(pct, text, activeIndex) {{
                    const overlay = document.getElementById("loadingOverlay");
                    const loadingFill = document.getElementById("loadingFill");
                    const loadingPercent = document.getElementById("loadingPercent");
                    const loadingStatus = document.getElementById("loadingStatus");
                    const loadingItems = Array.from(document.querySelectorAll(".loading-list-item"));
                    if (overlay) overlay.style.display = "flex";
                    if (loadingFill) loadingFill.style.width = pct + "%";
                    if (loadingPercent) loadingPercent.textContent = pct + "%";
                    if (loadingStatus) loadingStatus.textContent = text;
                    loadingItems.forEach((item, itemIndex) => item.classList.toggle("is-active", itemIndex === activeIndex));
                }}

                function showCompletionState(filename) {{
                    const overlay = document.getElementById("loadingOverlay");
                    const loadingState = document.getElementById("loadingState");
                    const completionState = document.getElementById("completionState");
                    const completionFilename = document.getElementById("completionFilename");
                    if (overlay) overlay.style.display = "flex";
                    if (loadingState) loadingState.style.display = "none";
                    if (completionState) completionState.style.display = "block";
                    if (completionFilename) completionFilename.textContent = "Prepared file: " + filename;
                }}

                function resetOverlayState() {{
                    const overlay = document.getElementById("loadingOverlay");
                    const loadingState = document.getElementById("loadingState");
                    const completionState = document.getElementById("completionState");
                    if (overlay) overlay.style.display = "none";
                    if (loadingState) loadingState.style.display = "block";
                    if (completionState) completionState.style.display = "none";
                }}

                function triggerReportDownload() {{
                    if (!latestDownloadUrl) return;
                    const link = document.createElement("a");
                    link.href = latestDownloadUrl;
                    link.download = latestFilename;
                    document.body.appendChild(link);
                    link.click();
                    link.remove();
                }}

                async function downloadReport(event) {{
                    if (isSubmitting) {{
                        event.preventDefault();
                        return;
                    }}
                    isSubmitting = true;
                    const submitButtons = Array.from(form.querySelectorAll('button[type="submit"], button[data-next-step], button[data-prev-step]'));
                    submitButtons.forEach((button) => button.disabled = true);

                    let visualProgress = 0;
                    let phaseIndex = 0;
                    const startedAt = Date.now();
                    const phases = [
                        {{ target: 18, text: "Reviewing business profile", index: 0 }},
                        {{ target: 42, text: "Analysing hiring performance", index: 1 }},
                        {{ target: 71, text: "Reviewing process control", index: 2 }},
                        {{ target: 92, text: "Preparing final report", index: 3 }},
                    ];

                    setLoadingState(0, "Preparing analysis", 0);
                    const timer = window.setInterval(() => {{
                        const phase = phases[Math.min(phaseIndex, phases.length - 1)];
                        if (visualProgress < phase.target) {{
                            visualProgress += 1;
                        }} else if (phaseIndex < phases.length - 1) {{
                            phaseIndex += 1;
                        }}
                        const active = phases[Math.min(phaseIndex, phases.length - 1)];
                        setLoadingState(visualProgress, active.text, active.index);
                    }}, 140);

                    try {{
                        const response = await fetch(form.action, {{
                            method: "POST",
                            body: new FormData(form),
                        }});

                        if (!response.ok) {{
                            const errorHtml = await response.text();
                            document.open();
                            document.write(errorHtml);
                            document.close();
                            return;
                        }}

                        visualProgress = 96;
                        setLoadingState(96, "Finalising download", 3);

                        const blob = await response.blob();
                        const disposition = response.headers.get("Content-Disposition") || "";
                        const match = disposition.match(/filename=([^;]+)/i);
                        const filename = match ? match[1].trim().replace(/^\"|\"$/g, "") : "recruitment_audit.pdf";
                        latestFilename = filename;

                        visualProgress = 100;
                        setLoadingState(100, "Report ready", 3);

                        if (latestDownloadUrl) {{
                            window.URL.revokeObjectURL(latestDownloadUrl);
                        }}
                        latestDownloadUrl = window.URL.createObjectURL(blob);
                        const remainingDelay = Math.max(2200 - (Date.now() - startedAt), 0);
                        window.setTimeout(() => {{
                            showCompletionState(filename);
                            isSubmitting = false;
                            submitButtons.forEach((button) => button.disabled = false);
                        }}, remainingDelay);
                    }} catch (error) {{
                        resetOverlayState();
                        isSubmitting = false;
                        submitButtons.forEach((button) => button.disabled = false);
                        window.alert("The report could not be generated. Please try again.");
                    }} finally {{
                        window.clearInterval(timer);
                    }}
                }}

                if (form) {{
                    form.addEventListener("keydown", function(event) {{
                        if (event.key === "Enter" && event.target.tagName !== "TEXTAREA") {{
                            event.preventDefault();
                            if (submitBtn && !submitBtn.hidden) {{
                                submitBtn.click();
                            }} else if (nextBtn && !nextBtn.hidden) {{
                                nextBtn.click();
                            }}
                        }}
                    }});
                    form.addEventListener("submit", function(event) {{
                        if (!validateCurrentStep()) {{
                            event.preventDefault();
                            return;
                        }}
                        markCurrentStepComplete();
                        event.preventDefault();
                        downloadReport(event);
                    }});
                }}
                if (downloadComplete) {{
                    downloadComplete.addEventListener("click", triggerReportDownload);
                }}
                if (startNewAudit) {{
                    startNewAudit.addEventListener("click", () => {{
                        if (latestDownloadUrl) {{
                            window.URL.revokeObjectURL(latestDownloadUrl);
                            latestDownloadUrl = "";
                        }}
                        window.location.href = window.location.pathname;
                    }});
                }}
                showStep(0, 0);
            }})();
        </script>
    </body>
    </html>
    """



@app.route("/")
def form():
    sectors = get_sector_options()
    sector_options = "\n".join(
        f'<option value="{sector}">{sector}</option>' for sector in sectors
    )

    def render_yes_no_field(field_name: str, label: str) -> str:
        return f"""
        <div class="field yes-no-field">
            <label for="{field_name}">{label}</label>
            <select id="{field_name}" name="{field_name}" required>
                <option value="">Select…</option>
                <option value="Yes">Yes</option>
                <option value="No">No</option>
            </select>
        </div>
        """

    process_step_copy = [
        (
            "Define how recruitment is planned and measured.",
            "These controls show whether hiring is being managed with basic structure and visibility.",
        ),
        (
            "Review the controls used before candidates enter the process.",
            "This shows whether sourcing and screening are being run consistently enough to support good hiring decisions.",
        ),
        (
            "Assess interview discipline and offer control.",
            "These answers indicate how consistently interview decisions are made and how quickly offers move through approval.",
        ),
        (
            "Check accountability after interview and offer.",
            "These controls show whether ownership, feedback and onboarding are strong enough to support retention.",
        ),
    ]
    process_control_steps_html = "\n".join(
        f"""
        <div class="stage-step{' active' if step_number == 1 else ''}" data-step-number="{step_number}">
            <div class="step-panel">
                <div class="step-overline" data-local-step-label>Step {step_number} of 4</div>
                <h3 class="step-headline">{headline}</h3>
                <p class="step-support">{support}</p>
                <div class="step-fields">
                    {''.join(render_yes_no_field(field_name, label) for field_name, label in YES_NO_FIELDS[(step_number - 1) * 3: step_number * 3])}
                </div>
            </div>
        </div>
        """
        for step_number, (headline, support) in enumerate(process_step_copy, start=1)
    )

    body = f"""
    <div class="topbar">
        <div class="brand-lockup">
            <div class="brand-mark">B&amp;M</div>
                <div class="brand">
                    <div class="brand-overline">Bradford & Marsh Consulting</div>
                    <div class="brand-name">Recruitment Operating Model Audit</div>
                    <div class="brand-sub">Controlled diagnostic for evaluating recruitment performance, operating discipline and hiring risk.</div>
                </div>
        </div>
        <div class="trust-pill">Used to evaluate recruitment performance across UK businesses</div>
    </div>

    <div class="hero">
        <h1>Recruitment Operating Model Audit</h1>
        <p>Assess hiring efficiency, control, and risk across your recruitment process.</p>
        <div class="hero-trust">Used to evaluate recruitment performance across UK businesses</div>
    </div>

    <div class="progress-shell">
        <div class="progress-bar">
            <div class="progress-top">
                <div>
                    <div class="progress-title" id="progressStageLabel">Stage 1 of 4</div>
                    <div class="progress-stage-name" id="progressStageName">Business Profile</div>
                </div>
                <div class="progress-metrics">
                    <div class="progress-step-label" id="progressStepLabel">Step 1 of 3</div>
                    <div class="progress-percent" id="progressPercent">0% complete</div>
                </div>
            </div>
            <div class="track"><div class="track-fill" id="progressFill"></div></div>

            <div class="stepper">
                <div class="step active">
                    <div class="step-dot">01</div>
                    <div class="step-copy">
                        <div class="step-kicker">Stage 1</div>
                        <div class="step-title">Business Profile</div>
                    </div>
                </div>
                <div class="step">
                    <div class="step-dot">02</div>
                    <div class="step-copy">
                        <div class="step-kicker">Stage 2</div>
                        <div class="step-title">Hiring Context</div>
                    </div>
                </div>
                <div class="step">
                    <div class="step-dot">03</div>
                    <div class="step-copy">
                        <div class="step-kicker">Stage 3</div>
                        <div class="step-title">Hiring Performance</div>
                    </div>
                </div>
                <div class="step">
                    <div class="step-dot">04</div>
                    <div class="step-copy">
                        <div class="step-kicker">Stage 4</div>
                        <div class="step-title">Process Control</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="assessment-wrap">
        <form id="auditForm" method="post" action="/generate">
            <div class="panel assessment-panel">
                <section class="stage active" data-stage="1" data-stage-title="Business Profile">
                    <div class="section-head">
                        <div>
                            <div class="section-kicker">Stage 1</div>
                            <h2 class="section-title">Business Profile</h2>
                            <p class="section-copy">Set the business context used to interpret the audit.</p>
                        </div>
                    </div>

                    <div class="stage-step active" data-step-number="1">
                        <div class="step-panel">
                            <div class="step-overline" data-local-step-label>Step 1 of 3</div>
                            <h3 class="step-headline">Identify the business being assessed.</h3>
                            <p class="step-support">These details anchor the report and benchmark position.</p>
                            <div class="step-fields">
                                <div class="field">
                                    <label for="company_name">What is the name of your company?</label>
                                    <input id="company_name" name="company_name" required>
                                </div>

                                <div class="field">
                                    <label for="sector">Which sector does your business operate in?</label>
                                    <select id="sector" name="sector" required>
                                        <option value="">Select…</option>
                                        {sector_options}
                                    </select>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="stage-step" data-step-number="2">
                        <div class="step-panel">
                            <div class="step-overline" data-local-step-label>Step 2 of 3</div>
                            <h3 class="step-headline">Confirm location and operating footprint.</h3>
                            <p class="step-support">This defines where the hiring model is being run and managed.</p>
                            <div class="step-fields">
                                <div class="field">
                                    <label for="location">Where is the business based?</label>
                                    <input id="location" name="location" autocomplete="address-level2" required>
                                </div>

                                <div class="field full">
                                    <label for="office_address">What is the office address?</label>
                                    <textarea id="office_address" name="office_address" rows="3" autocomplete="street-address" required></textarea>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="stage-step" data-step-number="3">
                        <div class="step-panel">
                            <div class="step-overline" data-local-step-label>Step 3 of 3</div>
                            <h3 class="step-headline">Capture the scale of the hiring requirement.</h3>
                            <p class="step-support">These inputs show the size of the business and the demand placed on recruitment.</p>
                            <div class="step-fields">
                                <div class="field has-suffix">
                                    <label for="headcount">How many employees does the business have?</label>
                                    <div class="input-wrap">
                                        <input id="headcount" name="headcount" inputmode="numeric" pattern="[0-9, ]+" title="Use numbers only." required>
                                        <span class="suffix">employees</span>
                                    </div>
                                </div>

                                <div class="field has-suffix">
                                    <label for="annual_hiring_volume">How many hires do you typically make each year?</label>
                                    <div class="input-wrap">
                                        <input id="annual_hiring_volume" name="annual_hiring_volume" inputmode="numeric" pattern="[0-9, ]+" title="Use numbers only." required>
                                        <span class="suffix">hires</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                <section class="stage" data-stage="2" data-stage-title="Hiring Context">
                    <div class="section-head">
                        <div>
                            <div class="section-kicker">Stage 2</div>
                            <h2 class="section-title">Hiring Context</h2>
                            <p class="section-copy">Identify the stakeholder and the roles that shape recruitment demand.</p>
                        </div>
                    </div>

                    <div class="stage-step active" data-step-number="1">
                        <div class="step-panel">
                            <div class="step-overline" data-local-step-label>Step 1 of 3</div>
                            <h3 class="step-headline">Identify the audit contact.</h3>
                            <p class="step-support">This ensures the report is addressed correctly and positioned for internal review.</p>
                            <div class="step-fields">
                                <div class="field">
                                    <label for="contact_name">What is the name of the person completing this audit?</label>
                                    <input id="contact_name" name="contact_name" autocomplete="name" required>
                                </div>

                                <div class="field">
                                    <label for="job_title">What is their job title?</label>
                                    <input id="job_title" name="job_title" autocomplete="organization-title" required>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="stage-step" data-step-number="2">
                        <div class="step-panel">
                            <div class="step-overline" data-local-step-label>Step 2 of 3</div>
                            <h3 class="step-headline">Confirm how Bradford & Marsh should contact you.</h3>
                            <p class="step-support">These details are used for report delivery and any follow-up discussion.</p>
                            <div class="step-fields">
                                <div class="field">
                                    <label for="phone_number">What is the best phone number to use?</label>
                                    <input id="phone_number" name="phone_number" type="tel" autocomplete="tel" inputmode="tel" pattern="[0-9+()\\-\\s]{{7,}}" title="Enter a valid phone number." required>
                                </div>

                                <div class="field">
                                    <label for="email_address">What is the best email address to use?</label>
                                    <input id="email_address" name="email_address" type="email" autocomplete="email" required>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="stage-step" data-step-number="3">
                        <div class="step-panel">
                            <div class="step-overline" data-local-step-label>Step 3 of 3</div>
                            <h3 class="step-headline">Set the core hiring scope.</h3>
                            <p class="step-support">This clarifies the roles that define the current recruitment model.</p>
                            <div class="step-fields">
                                <div class="field full">
                                    <label for="key_roles_hired">Which roles or job titles do you hire for most often?</label>
                                    <input id="key_roles_hired" name="key_roles_hired" placeholder="e.g. Sales Managers, Service Engineers, Finance Business Partners" required>
                                    <div class="hint">Use representative job titles, not a numeric count.</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                <section class="stage" data-stage="3" data-stage-title="Hiring Performance">
                    <div class="section-head">
                        <div>
                            <div class="section-kicker">Stage 3</div>
                            <h2 class="section-title">Hiring Performance</h2>
                            <p class="section-copy">Capture the operational metrics that show where hiring is strong or under pressure.</p>
                        </div>
                    </div>

                    <div class="stage-step active" data-step-number="1">
                        <div class="step-panel">
                            <div class="step-overline" data-local-step-label>Step 1 of 4</div>
                            <h3 class="step-headline">Measure pace and top-of-funnel volume.</h3>
                            <p class="step-support">These figures show how quickly roles are filled and how much candidate interest reaches the process.</p>
                            <div class="step-fields">
                                <div class="field has-suffix">
                                    <label for="time_to_hire">How long does it currently take to hire a role?</label>
                                    <div class="input-wrap">
                                        <input id="time_to_hire" name="time_to_hire" placeholder="e.g. 42" required>
                                        <span class="suffix">days</span>
                                    </div>
                                </div>

                                <div class="field has-suffix">
                                    <label for="applications_per_role">How many applications do you receive for a typical role?</label>
                                    <div class="input-wrap">
                                        <input id="applications_per_role" name="applications_per_role" placeholder="e.g. 36" inputmode="decimal" pattern="[0-9., ]+" title="Use numbers only." required>
                                        <span class="suffix">applications</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="stage-step" data-step-number="2">
                        <div class="step-panel">
                            <div class="step-overline" data-local-step-label>Step 2 of 4</div>
                            <h3 class="step-headline">Check offer acceptance and early retention.</h3>
                            <p class="step-support">These measures show whether the business is securing the right hires and keeping them.</p>
                            <div class="step-fields">
                                <div class="field has-suffix">
                                    <label for="offer_acceptance">What percentage of offers are accepted?</label>
                                    <div class="input-wrap">
                                        <input id="offer_acceptance" name="offer_acceptance" placeholder="e.g. 72" inputmode="decimal" pattern="[0-9., ]+" title="Use numbers only." required>
                                        <span class="suffix">%</span>
                                    </div>
                                </div>

                                <div class="field has-suffix">
                                    <label for="first_year_attrition">What percentage of hires leave within the first year?</label>
                                    <div class="input-wrap">
                                        <input id="first_year_attrition" name="first_year_attrition" placeholder="e.g. 18" inputmode="decimal" pattern="[0-9., ]+" title="Use numbers only." required>
                                        <span class="suffix">%</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="stage-step" data-step-number="3">
                        <div class="step-panel">
                            <div class="step-overline" data-local-step-label>Step 3 of 4</div>
                            <h3 class="step-headline">Review interview design and decision speed.</h3>
                            <p class="step-support">These answers show how much friction is built into the interview process.</p>
                            <div class="step-fields">
                                <div class="field has-suffix">
                                    <label for="interview_stages">How many interview stages are typically used?</label>
                                    <div class="input-wrap">
                                        <input id="interview_stages" name="interview_stages" placeholder="e.g. 2" inputmode="numeric" pattern="[0-9 ]+" title="Use numbers only." required>
                                        <span class="suffix">stages</span>
                                    </div>
                                </div>

                                <div class="field has-suffix">
                                    <label for="interview_feedback_time">How long does interview feedback usually take to return?</label>
                                    <div class="input-wrap">
                                        <input id="interview_feedback_time" name="interview_feedback_time" placeholder="e.g. 2" required>
                                        <span class="suffix">days</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="stage-step" data-step-number="4">
                        <div class="step-panel">
                            <div class="step-overline" data-local-step-label>Step 4 of 4</div>
                            <h3 class="step-headline">Measure how much shortlist volume reaches interview.</h3>
                            <p class="step-support">This shows whether the funnel is producing enough viable candidates for decision-making.</p>
                            <div class="step-fields">
                                <div class="field has-suffix full">
                                    <label for="candidates_reaching_interview">How many candidates typically reach interview for each role?</label>
                                    <div class="input-wrap">
                                        <input id="candidates_reaching_interview" name="candidates_reaching_interview" placeholder="e.g. 5" inputmode="decimal" pattern="[0-9., ]+" title="Use numbers only." required>
                                        <span class="suffix">candidates</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                <section class="stage" data-stage="4" data-stage-title="Process Control">
                    <div class="section-head">
                        <div>
                            <div class="section-kicker">Stage 4</div>
                            <h2 class="section-title">Process Control</h2>
                            <p class="section-copy">Assess how consistently recruitment is governed, owned and run in practice.</p>
                        </div>
                    </div>

                    {process_control_steps_html}
                </section>

                <div class="footer-bar">
                    <div class="footer-copy" id="stepFooterCopy">
                        Complete each step to build the final recruitment audit report.
                    </div>
                    <div class="button-row">
                        <button class="button button-ghost" type="button" data-prev-step>Back</button>
                        <button class="button button-secondary" type="button" data-next-step>Continue</button>
                        <button class="button button-primary" type="submit" hidden>Generate Audit Report</button>
                    </div>
                </div>
            </div>
        </form>
    </div>
    """

    return render_page("Recruitment Operating Model Audit", body)


@app.route("/generate", methods=["POST"])
def generate():
    try:
        client = None
        try:
            client = OpenAI(api_key=get_api_key())
        except ValueError:
            pass

        data = {
            "company_name": request.form.get("company_name", "").strip(),
            "contact_name": request.form.get("contact_name", "").strip(),
            "job_title": request.form.get("job_title", "").strip(),
            "phone_number": request.form.get("phone_number", "").strip(),
            "email_address": request.form.get("email_address", "").strip(),
            "office_address": request.form.get("office_address", "").strip(),
            "sector": request.form.get("sector", "").strip(),
            "location": request.form.get("location", "").strip(),
            "headcount": request.form.get("headcount", "").strip(),
            "annual_hiring_volume": request.form.get("annual_hiring_volume", "").strip(),
            "key_roles_hired": request.form.get("key_roles_hired", "").strip(),
            "raw_metrics": {
                "time_to_hire": request.form.get("time_to_hire", "").strip(),
                "applications_per_role": request.form.get("applications_per_role", "").strip(),
                "offer_acceptance": request.form.get("offer_acceptance", "").strip(),
                "first_year_attrition": request.form.get("first_year_attrition", "").strip(),
                "interview_stages": request.form.get("interview_stages", "").strip(),
                "interview_feedback_time": request.form.get("interview_feedback_time", "").strip(),
                "candidates_reaching_interview": request.form.get("candidates_reaching_interview", "").strip(),
            },
            "metrics": {
                "time_to_hire_days": parse_time_to_hire_days(request.form.get("time_to_hire", "").strip()),
                "applications_per_role": parse_numeric_value(request.form.get("applications_per_role", "").strip()),
                "offer_acceptance": parse_numeric_value(request.form.get("offer_acceptance", "").strip()),
                "first_year_attrition": parse_numeric_value(request.form.get("first_year_attrition", "").strip()),
                "interview_stages": parse_numeric_value(request.form.get("interview_stages", "").strip()),
                "interview_feedback_time_days": parse_time_to_hire_days(request.form.get("interview_feedback_time", "").strip()),
                "candidates_reaching_interview": parse_numeric_value(request.form.get("candidates_reaching_interview", "").strip()),
            },
            "process_flags": {
                "has_hiring_plan": yes_no_to_bool(request.form.get("has_hiring_plan")),
                "tracks_metrics": yes_no_to_bool(request.form.get("tracks_metrics")),
                "has_employer_brand": yes_no_to_bool(request.form.get("has_employer_brand")),
                "standardised_job_specs": yes_no_to_bool(request.form.get("standardised_job_specs")),
                "multi_channel_sourcing": yes_no_to_bool(request.form.get("multi_channel_sourcing")),
                "structured_screening": yes_no_to_bool(request.form.get("structured_screening")),
                "structured_interviews": yes_no_to_bool(request.form.get("structured_interviews")),
                "fast_offer_process": yes_no_to_bool(request.form.get("fast_offer_process")),
                "formal_onboarding": yes_no_to_bool(request.form.get("formal_onboarding")),
                "collects_candidate_feedback": yes_no_to_bool(request.form.get("collects_candidate_feedback")),
                "named_process_owner": yes_no_to_bool(request.form.get("named_process_owner")),
                "hiring_manager_training": yes_no_to_bool(request.form.get("hiring_manager_training")),
            },
        }

        benchmark = load_benchmarks()
        benchmark_summary = build_benchmark_summary(data["metrics"], benchmark, data["sector"], data["key_roles_hired"])

        section_scores, section_notes = auto_score_sections(data, benchmark)
        data["section_scores"] = section_scores
        data["section_notes"] = section_notes
        data["total_score"] = sum(section_scores)
        data["percentage_score"] = round((data["total_score"] / 120) * 100, 1)

        report = generate_report_json(client, data, benchmark_summary) if client is not None else build_fallback_report(data, benchmark_summary)

        section_chart = create_section_score_chart(data["company_name"], data["section_scores"], benchmark, data["sector"])
        overall_chart = create_overall_score_chart(data["company_name"], data["total_score"])
        benchmark_chart = create_benchmark_chart(data["company_name"], data["metrics"], benchmark, data["sector"], data["key_roles_hired"])

        pdf_path = save_pdf_report(
            data=data,
            report=report,
            benchmark_summary=benchmark_summary,
            section_chart=section_chart,
            overall_chart=overall_chart,
            benchmark_chart=benchmark_chart,
        )
        try:
            send_audit_notification(data, report, pdf_path)
        except Exception:
            app.logger.exception("Audit notification email failed")

        download_name = f"{data['company_name'].strip().replace(' ', '_')}_recruitment_audit.pdf"

        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=download_name,
            mimetype="application/pdf",
        )

    except Exception as exc:
        traceback_text = traceback.format_exc()
        expose_traceback = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
        detail_html = (
            f"<pre>{html.escape(traceback_text)}</pre>"
            if expose_traceback
            else "<p>Please verify the API key, benchmark workbook and required Python packages, then try again.</p>"
        )
        body = f"""
        <div class="status error">
            <h2>Report generation failed</h2>
            <p><strong>Error type:</strong> {html.escape(type(exc).__name__)}</p>
            <p><strong>Error:</strong> {html.escape(str(exc))}</p>
            {detail_html}
            <a class="back-link" href="/">Return to the form</a>
        </div>
        """
        return render_page("Report generation failed", body), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
