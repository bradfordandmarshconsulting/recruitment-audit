from __future__ import annotations

import base64
import html
import os
import traceback
from datetime import datetime
from pathlib import Path

from flask import Flask, request, send_file
import httpx
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
NOTIFICATION_RECIPIENTS = [
    "max@bradfordandmarsh.co.uk",
    "will@bradfordandmarsh.co.uk",
    "michael@bradfordandmarsh.co.uk",
]

FALLBACK_SECTORS = [
    "Other",
]

TIER_SCORE_THRESHOLD = 0.55

WIZARD_STEPS = [
    {
        "title": "About you",
        "subtitle": "So we know who to send the report to.",
        "kind": "contact",
        "fields": [
            {"name": "contact_name", "label": "Full name", "placeholder": "e.g. Max Powell", "type": "text", "autocomplete": "name"},
            {"name": "job_title", "label": "Job title", "placeholder": "e.g. Head of People", "type": "text", "autocomplete": "organization-title"},
            {"name": "email_address", "label": "Email address", "placeholder": "e.g. max@company.com", "type": "email", "autocomplete": "email"},
            {"name": "phone_number", "label": "Phone number", "placeholder": "e.g. 07700 900123", "type": "tel", "autocomplete": "tel"},
            {"name": "company_name", "label": "Company name", "placeholder": "e.g. Acme Telecom", "type": "text", "autocomplete": "organization"},
        ],
    },
    {
        "title": "Planning & strategy",
        "subtitle": "How hiring decisions get made before a role goes live.",
        "kind": "questions",
        "questions": [
            {
                "name": "has_hiring_plan",
                "label": "When a new role opens, is there a workforce plan or headcount forecast behind it — or does hiring tend to be reactive?",
                "options": [
                    ("1.0", "Always planned"),
                    ("0.7", "Mostly planned"),
                    ("0.4", "Sometimes planned"),
                    ("0.1", "Usually reactive"),
                ],
            },
            {
                "name": "tracks_metrics",
                "label": "Do you track hiring metrics like time to hire, cost per hire, or offer acceptance — and actually review them?",
                "options": [
                    ("1.0", "Yes, reviewed regularly"),
                    ("0.7", "Tracked but rarely reviewed"),
                    ("0.4", "Loosely tracked"),
                    ("0.1", "Not really"),
                ],
            },
        ],
    },
    {
        "title": "Brand & attraction",
        "subtitle": "How candidates see you before they apply.",
        "kind": "questions",
        "questions": [
            {
                "name": "has_employer_brand",
                "label": "If a candidate Googled your company right now, would they find a clear picture of what it's like to work there?",
                "options": [
                    ("1.0", "Yes, it's well defined"),
                    ("0.7", "Partially — some content exists"),
                    ("0.4", "Not much out there"),
                    ("0.1", "Probably not"),
                ],
            },
            {
                "name": "standardised_job_specs",
                "label": "Are your job adverts written to a consistent standard, or does it depend on who drafts them?",
                "options": [
                    ("1.0", "Consistent standard"),
                    ("0.7", "Mostly consistent"),
                    ("0.4", "Varies quite a bit"),
                    ("0.1", "No real standard"),
                ],
            },
        ],
    },
    {
        "title": "Sourcing & screening",
        "subtitle": "How candidates enter and move through the top of the funnel.",
        "kind": "questions",
        "questions": [
            {
                "name": "multi_channel_sourcing",
                "label": "How do you typically find candidates — is it the same channels every time, or do you mix it up depending on the role?",
                "options": [
                    ("1.0", "Multi-channel, role by role"),
                    ("0.7", "A few go-to channels"),
                    ("0.4", "Mostly one channel"),
                    ("0.1", "Whatever works at the time"),
                ],
            },
            {
                "name": "structured_screening",
                "label": "When applications come in, is there a set process for screening them — or does each manager handle it their own way?",
                "options": [
                    ("1.0", "Standard process, consistently followed"),
                    ("0.7", "Process exists but not always followed"),
                    ("0.4", "Informal — manager dependent"),
                    ("0.1", "No set process"),
                ],
            },
        ],
    },
    {
        "title": "Interviews & decisions",
        "subtitle": "Where good candidates are either secured or lost.",
        "kind": "questions",
        "questions": [
            {
                "name": "structured_interviews",
                "label": "Do your interviews follow a set structure — same questions, same scorecard — or is it more conversational?",
                "options": [
                    ("1.0", "Structured with scorecards"),
                    ("0.7", "Mostly structured"),
                    ("0.4", "Semi-structured"),
                    ("0.1", "Mainly conversational"),
                ],
            },
            {
                "name": "fast_offer_process",
                "label": "Once you've found the right person, how quickly can you get an offer out the door?",
                "options": [
                    ("1.0", "Within 24–48 hours"),
                    ("0.7", "Within a week"),
                    ("0.4", "It varies — sometimes longer"),
                    ("0.1", "It often gets held up"),
                ],
            },
        ],
    },
    {
        "title": "Onboarding & retention",
        "subtitle": "What happens after someone says yes.",
        "kind": "questions",
        "questions": [
            {
                "name": "formal_onboarding",
                "label": "Is there a documented onboarding process that every new starter goes through, or does it depend on the team?",
                "options": [
                    ("1.0", "Fully documented and consistent"),
                    ("0.7", "Documented but inconsistent"),
                    ("0.4", "Informal — team dependent"),
                    ("0.1", "Not really in place"),
                ],
            },
            {
                "name": "collects_candidate_feedback",
                "label": "Do you collect feedback from candidates about their experience — whether they got the job or not?",
                "options": [
                    ("1.0", "Yes, consistently"),
                    ("0.7", "Sometimes"),
                    ("0.4", "Rarely"),
                    ("0.1", "No"),
                ],
            },
        ],
    },
    {
        "title": "Ownership & capability",
        "subtitle": "Who's accountable and how equipped they are.",
        "kind": "questions",
        "questions": [
            {
                "name": "named_process_owner",
                "label": "Is there one person who owns the recruitment process end to end — someone who'd notice if things started slipping?",
                "options": [
                    ("1.0", "Yes, clearly named"),
                    ("0.7", "Sort of — it's shared"),
                    ("0.4", "It's unclear"),
                    ("0.1", "Not really"),
                ],
            },
            {
                "name": "hiring_manager_training",
                "label": "Have your hiring managers had any training on interviewing, assessing candidates, or managing a hiring process?",
                "options": [
                    ("1.0", "Yes, formally trained"),
                    ("0.7", "Some informal guidance"),
                    ("0.4", "Very little"),
                    ("0.1", "None"),
                ],
            },
        ],
    },
]


def yes_no_to_bool(value: str | None) -> bool:
    return str(value).strip().lower() in {"yes", "y", "true"}


def parse_tier_score(value: str | None) -> float | None:
    try:
        if value is None:
            return None
        text = str(value).strip()
        return float(text) if text else None
    except (TypeError, ValueError):
        return None


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
    weakest_index = min(range(len(SECTION_ORDER)), key=lambda index: data["section_scores"][index])
    weakest_title = SECTION_ORDER[weakest_index]
    weakest_score = data["section_scores"][weakest_index]
    rating_band = _rating_for_score(data["total_score"])
    recommendation = report.get("recommended_intervention", {})
    completed_at = datetime.now()
    tenant_id = os.environ.get("TENANT_ID", "").strip()
    client_id = os.environ.get("CLIENT_ID", "").strip()
    client_secret = os.environ.get("CLIENT_SECRET", "").strip()
    sending_from = os.environ.get("SENDING_FROM", "").strip()

    missing = [name for name, value in {
        "TENANT_ID": tenant_id,
        "CLIENT_ID": client_id,
        "CLIENT_SECRET": client_secret,
        "SENDING_FROM": sending_from,
    }.items() if not value]
    if missing:
        raise ValueError(f"Missing Microsoft Graph email environment variables: {', '.join(missing)}")

    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    attachment_bytes = base64.b64encode(pdf_path.read_bytes()).decode("ascii")
    text_body = "\n".join(
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
    )

    with httpx.Client(timeout=30.0) as client:
        token_response = client.post(
            token_url,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
            },
        )
        token_response.raise_for_status()
        access_token = token_response.json()["access_token"]

        send_response = client.post(
            f"https://graph.microsoft.com/v1.0/users/{sending_from}/sendMail",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "message": {
                    "subject": f"New Audit Completed — {data['company_name']} — {completed_at.strftime('%d %B %Y')}",
                    "body": {
                        "contentType": "Text",
                        "content": text_body,
                    },
                    "toRecipients": [{"emailAddress": {"address": address}} for address in NOTIFICATION_RECIPIENTS],
                    "attachments": [
                        {
                            "@odata.type": "#microsoft.graph.fileAttachment",
                            "name": _notification_attachment_name(data["company_name"], completed_at),
                            "contentType": "application/pdf",
                            "contentBytes": attachment_bytes,
                        }
                    ],
                },
                "saveToSentItems": True,
            },
        )
        send_response.raise_for_status()



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
                --panel: #ffffff;
                --panel-soft: #faf8f4;
                --ink: #142033;
                --muted: #5d6778;
                --line: rgba(20, 32, 51, 0.12);
                --line-strong: rgba(20, 32, 51, 0.22);
                --brand: #142033;
                --accent: #b88d57;
                --success: #166534;
                --success-soft: #e7f6ec;
                --error: #b91c1c;
                --error-soft: #fceceb;
                --shadow-lg: 0 18px 40px rgba(20, 32, 51, 0.08);
                --shadow-md: 0 8px 22px rgba(20, 32, 51, 0.05);
                --radius-lg: 12px;
                --radius-md: 10px;
                --radius-sm: 8px;
                --font-sans: "Aptos", "Inter", "Segoe UI", sans-serif;
                --font-display: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif;
            }}
            * {{ box-sizing: border-box; }}
            html, body {{
                margin: 0;
                padding: 0;
                min-height: 100%;
                background: #f1f3f5;
                color: var(--ink);
                font-family: var(--font-sans);
            }}
            body {{ min-height: 100vh; }}
            .shell {{ max-width: 960px; margin: 0 auto; padding: 24px 20px 64px; }}
            .topbar {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 16px;
                padding-bottom: 20px;
                margin-bottom: 24px;
                border-bottom: 1px solid #e5e7eb;
            }}
            .brand-name {{
                font-size: 14px;
                font-weight: 600;
                color: #1a2336;
                letter-spacing: 0.02em;
            }}
            .brand-name span {{ color: #9e7c3e; }}
            .trust-pill {{
                display: inline-flex;
                align-items: center;
                padding: 5px 12px;
                border: 1px solid #e5e7eb;
                border-radius: 999px;
                background: #fff;
                color: #6b7280;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.02em;
                text-transform: uppercase;
            }}
            .progress-shell {{ margin-bottom: 28px; }}
            .progress-bar {{ padding: 0; border: 0; background: transparent; box-shadow: none; }}
            .progress-top {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 16px;
                margin-bottom: 8px;
            }}
            .progress-title,
            .section-kicker,
            .sidebar-kicker,
            .completion-kicker {{
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 0.04em;
                text-transform: uppercase;
                color: #9e7c3e;
            }}
            .progress-stage-name {{
                margin-top: 4px;
                font-size: 20px;
                font-weight: 600;
                color: #1a2336;
            }}
            .progress-percent {{ font-size: 13px; font-weight: 500; color: #6b7280; }}
            .track {{
                width: 100%;
                height: 3px;
                margin-bottom: 28px;
                overflow: hidden;
                border-radius: 999px;
                background: #e5e7eb;
            }}
            .track-fill {{
                width: 0%;
                height: 100%;
                border-radius: 999px;
                background: #1a2336;
                transition: width 0.35s ease;
            }}
            .stepper {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 0;
                margin-bottom: 4px;
                overflow: hidden;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                background: #fff;
            }}
            .step {{
                appearance: none;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                padding: 12px;
                cursor: pointer;
                border: 0;
                border-right: 1px solid #e5e7eb;
                border-radius: 0;
                background: transparent;
                color: #9ca3af;
                text-align: center;
                position: relative;
            }}
            .step:last-child {{ border-right: none; }}
            .step-dot {{
                flex: 0 0 auto;
                display: grid;
                place-items: center;
                width: 20px;
                height: 20px;
                border-radius: 999px;
                background: #f3f4f6;
                color: #9ca3af;
                font-size: 11px;
                font-weight: 600;
            }}
            .step-copy {{ min-width: 0; }}
            .step-kicker {{ display: none; }}
            .step-title {{
                font-size: 13px;
                font-weight: 500;
            }}
            .step.active {{
                color: #1a2336;
                background: #fafbfc;
                font-weight: 600;
            }}
            .step.active .step-dot {{
                background: #1a2336;
                color: #fff;
            }}
            .step.active::after {{
                content: "";
                position: absolute;
                left: 16px;
                right: 16px;
                bottom: 0;
                height: 2px;
                border-radius: 1px;
                background: #1a2336;
            }}
            .step.complete {{
                color: #059669;
                background: transparent;
            }}
            .step.complete .step-dot {{
                background: #d1fae5;
                color: #059669;
            }}
            .panel {{
                border: 1px solid #e5e7eb;
                border-radius: var(--radius-lg);
                background: #fff;
                box-shadow: none;
                overflow: hidden;
            }}
            .assessment-panel {{ width: 100%; }}
            .wizard-body {{ padding: 0; }}
            .overview-card {{
                margin-bottom: 20px;
                padding: 18px;
            }}
            .overview-title {{
                margin: 0 0 8px;
                font-size: 16px;
                font-weight: 600;
                color: #1a2336;
            }}
            .sidebar-copy,
            .section-copy,
            .footer-copy,
            .loading-card p {{
                color: #6b7280;
                line-height: 1.6;
                font-size: 14px;
            }}
            .summary-list {{
                display: grid;
                grid-template-columns: repeat(5, minmax(0, 1fr));
                gap: 10px;
                margin-top: 18px;
            }}
            .summary-item {{
                display: flex;
                flex-direction: column;
                gap: 4px;
                padding: 11px 12px;
                border: 1px solid #e5e7eb;
                border-radius: var(--radius-sm);
                background: #fafbfc;
            }}
            .summary-label,
            .review-label {{
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.03em;
                text-transform: uppercase;
                color: #9ca3af;
            }}
            .summary-value,
            .review-value {{
                font-size: 14px;
                font-weight: 600;
                color: #1a2336;
                text-align: left;
            }}
            .stage,
            .wizard-step {{
                display: none;
                padding: 32px;
            }}
            .stage.active,
            .wizard-step.active {{ display: block; }}
            .section-head {{ margin-bottom: 28px; }}
            .section-kicker {{ margin-bottom: 6px; }}
            .section-title {{
                margin: 0 0 8px;
                font-size: 20px;
                font-weight: 600;
                color: #1a2336;
            }}
            @keyframes stageIn {{
                from {{ opacity: 0; transform: translateY(6px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            .step-panel {{
                padding: 0;
                border: 0;
                border-radius: 0;
                background: transparent;
            }}
            .step-fields {{
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 20px 16px;
            }}
            .field {{ display: flex; flex-direction: column; gap: 6px; }}
            .field.full {{ grid-column: 1 / -1; }}
            .field-error {{
                min-height: 18px;
                font-size: 12px;
                line-height: 1.4;
                color: #991b1b;
            }}
            label {{
                font-size: 13px;
                font-weight: 600;
                line-height: 1.45;
                color: #374151;
            }}
            input, select, textarea {{
                width: 100%;
                border: 1px solid #d1d5db;
                border-radius: var(--radius-sm);
                background: #fff;
                color: var(--ink);
                font: inherit;
                outline: none;
                padding: 11px 14px;
                transition: border-color 0.18s ease, box-shadow 0.18s ease;
            }}
            input:focus, select:focus, textarea:focus {{
                border-color: #1a2336;
                box-shadow: 0 0 0 3px rgba(26, 35, 54, 0.08);
            }}
            input:hover, select:hover, textarea:hover {{ border-color: #9ca3af; }}
            input::placeholder, textarea::placeholder {{ color: #c0c5cc; }}
            .input-wrap {{ position: relative; }}
            .input-wrap input {{ padding-right: 70px; }}
            .suffix {{
                position: absolute;
                top: 50%;
                right: 12px;
                transform: translateY(-50%);
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.03em;
                text-transform: uppercase;
                color: #9ca3af;
                pointer-events: none;
            }}
            .toggle-group {{
                display: inline-flex;
                gap: 0;
                overflow: hidden;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                flex-wrap: nowrap;
                flex: 0 0 116px;
            }}
            .discipline-grid {{
                display: grid;
                grid-template-columns: 1fr;
                gap: 8px;
            }}
            .discipline-item {{
                display: grid;
                grid-template-columns: minmax(0, 1fr) auto;
                align-items: center;
                gap: 12px;
                padding: 14px 16px;
                border: 1px solid #e5e7eb;
                border-radius: var(--radius-sm);
                background: #fff;
            }}
            .discipline-item.is-invalid {{
                border-color: rgba(185, 28, 28, 0.28);
                background: #fff7f7;
            }}
            .discipline-question {{
                font-size: 13px;
                font-weight: 500;
                line-height: 1.45;
                color: #374151;
            }}
            .stage-alert {{
                display: none;
                margin: 0 0 14px;
                padding: 10px 12px;
                border: 1px solid rgba(185, 28, 28, 0.18);
                border-radius: var(--radius-sm);
                background: #fff7f7;
                color: #991b1b;
                font-size: 13px;
                line-height: 1.45;
            }}
            .stage-alert.is-visible {{ display: block; }}
            .question-card {{
                padding: 20px;
                border: 1px solid #e5e7eb;
                border-radius: var(--radius-md);
                background: #fafbfc;
            }}
            .question-card + .question-card {{ margin-top: 16px; }}
            .question-card.is-invalid {{
                border-color: rgba(185, 28, 28, 0.28);
                background: #fff7f7;
            }}
            .question-label {{
                margin-bottom: 14px;
                font-size: 14px;
                font-weight: 600;
                line-height: 1.55;
                color: #1a2336;
            }}
            .option-grid {{
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 10px;
            }}
            .option-card {{
                position: relative;
                display: flex;
                align-items: flex-start;
                min-height: 68px;
                padding: 14px 16px;
                border: 1px solid #d1d5db;
                border-radius: var(--radius-sm);
                background: #fff;
                color: #374151;
                cursor: pointer;
                transition: border-color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
            }}
            .option-card:hover {{
                border-color: #9ca3af;
                background: #fff;
            }}
            .option-card span {{
                display: block;
                font-size: 13px;
                line-height: 1.5;
                font-weight: 500;
            }}
            .option-input {{
                position: absolute;
                inset: 0;
                opacity: 0;
                pointer-events: none;
            }}
            .option-input:checked + span {{
                color: #1a2336;
            }}
            .option-card:has(.option-input:checked) {{
                border-color: #1a2336;
                background: #f7f8fb;
                box-shadow: 0 0 0 3px rgba(26, 35, 54, 0.08);
            }}
            .toggle-option {{
                width: 58px;
                min-width: 58px;
                padding: 6px 12px;
                border: 0;
                border-right: 1px solid #e5e7eb;
                border-radius: 0;
                background: #fff;
                color: #9ca3af;
                font: inherit;
                font-size: 12px;
                font-weight: 600;
                cursor: pointer;
                transition: background 0.18s ease, border-color 0.18s ease, color 0.18s ease;
            }}
            .toggle-option:last-child {{ border-right: 0; }}
            .toggle-option:hover {{ background: #f9fafb; color: #6b7280; }}
            .toggle-option.is-active.is-yes {{
                background: #d1fae5;
                color: #047857;
            }}
            .toggle-option.is-active.is-no {{
                background: #fee2e2;
                color: #b91c1c;
            }}
            .toggle-group.is-invalid .toggle-option {{
                border-color: rgba(185, 28, 28, 0.4);
            }}
            .review-strip,
            .review-grid {{
                display: grid;
                gap: 12px;
            }}
            .review-strip {{
                grid-template-columns: repeat(4, minmax(0, 1fr));
                margin-bottom: 16px;
                gap: 0;
                overflow: hidden;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                background: #fafbfc;
            }}
            .review-grid {{
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 8px;
                margin-bottom: 20px;
            }}
            .review-strip .review-card {{
                border: 0;
                border-right: 1px solid #e5e7eb;
                border-radius: 0;
                background: transparent;
            }}
            .review-strip .review-card:last-child {{ border-right: 0; }}
            .review-card,
            .review-metric,
            .review-pill-card {{
                padding: 12px 14px;
                border: 1px solid #e5e7eb;
                border-radius: var(--radius-sm);
                background: #f9fafb;
            }}
            .review-pill-grid {{
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 6px;
                margin-top: 12px;
            }}
            .review-pill {{
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 8px 10px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 500;
                border: 0;
                background: #f3f4f6;
                color: #9ca3af;
            }}
            .review-pill.is-yes {{
                background: #d1fae5;
                color: #047857;
            }}
            .review-pill.is-no {{
                background: #fee2e2;
                color: #b91c1c;
            }}
            .confirmation-panel {{
                padding: 22px;
                border: 1px solid #e5e7eb;
                border-radius: var(--radius-md);
                background: #fafbfc;
            }}
            .confirmation-grid {{
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 10px;
            }}
            .confirmation-item {{
                padding: 12px 14px;
                border: 1px solid #e5e7eb;
                border-radius: var(--radius-sm);
                background: #fff;
            }}
            .confirmation-note {{
                margin-top: 16px;
                padding-top: 16px;
                border-top: 1px solid #e5e7eb;
                color: #6b7280;
                font-size: 13px;
                line-height: 1.6;
            }}
            .footer-bar {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 16px;
                padding: 20px 32px;
                border-top: 1px solid #e5e7eb;
                background: #fafbfc;
            }}
            .footer-copy {{ max-width: 44ch; font-size: 12px; color: #9ca3af; }}
            .button-row {{
                display: flex;
                gap: 8px;
                flex-wrap: wrap;
                justify-content: flex-end;
            }}
            .button {{
                appearance: none;
                border: 1px solid #d1d5db;
                border-radius: var(--radius-sm);
                padding: 10px 22px;
                font-size: 13px;
                font-weight: 600;
                cursor: pointer;
                text-decoration: none;
                background: #fff;
                color: #374151;
            }}
            .button:hover {{ background: #f9fafb; border-color: #9ca3af; opacity: 1; }}
            .button-primary {{
                background: #1a2336;
                color: #fff;
                border-color: #1a2336;
            }}
            .button-primary:hover {{ background: #263044; border-color: #263044; }}
            .button-secondary {{
                background: #fff;
                color: #374151;
                border-color: #d1d5db;
            }}
            .button-ghost {{
                background: #fff;
                color: #374151;
                border-color: #d1d5db;
            }}
            .button[hidden] {{ display: none !important; }}
            .loading-overlay {{
                position: fixed;
                inset: 0;
                z-index: 1000;
                display: none;
                align-items: center;
                justify-content: center;
                padding: 16px;
                background: rgba(244, 245, 247, 0.85);
            }}
            .loading-card {{
                width: min(420px, calc(100vw - 40px));
                padding: 28px;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
                background: #fff;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.10);
            }}
            .loading-head {{
                display: flex;
                align-items: center;
                gap: 8px;
                margin-bottom: 16px;
            }}
            .loading-pill {{
                background: transparent;
                padding: 0;
                border-radius: 0;
                color: #1a2336;
                font-size: 0;
            }}
            .spinner {{
                width: 28px;
                height: 28px;
                border: 2.5px solid #e5e7eb;
                border-top-color: #1a2336;
                border-radius: 999px;
                animation: spin 0.75s linear infinite;
            }}
            .loading-card h3,
            .completion-state h3 {{
                margin: 0 0 4px;
                font-size: 17px;
                font-weight: 600;
                color: #1a2336;
            }}
            .completion-state p,
            .loading-card p {{ color: #6b7280; line-height: 1.5; font-size: 13px; }}
            .loading-steps {{
                display: flex;
                flex-direction: column;
                gap: 10px;
                margin-top: 18px;
            }}
            .loading-step {{
                display: flex;
                align-items: center;
                justify-content: flex-start;
                gap: 10px;
                padding: 0;
                border: 0;
                border-radius: 0;
                background: transparent;
                color: #9ca3af;
                font-size: 13px;
            }}
            .loading-step-dot {{
                width: 20px;
                height: 20px;
                border-radius: 50%;
                flex-shrink: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 10px;
                font-weight: 700;
                border: 1.5px solid #e5e7eb;
                color: #d1d5db;
            }}
            .loading-step-state {{
                display: none;
            }}
            .loading-step.is-active {{
                color: #1a2336;
                font-weight: 600;
            }}
            .loading-step.is-active .loading-step-dot {{
                border-color: #1a2336;
                background: #1a2336;
                color: #fff;
            }}
            .loading-step.is-complete {{
                color: #059669;
            }}
            .loading-step.is-complete .loading-step-dot {{
                border-color: #059669;
                background: #d1fae5;
                color: #059669;
            }}
            .completion-state {{ display: none; }}
            .completion-list {{
                display: grid;
                gap: 10px;
                margin: 18px 0;
            }}
            .completion-item {{
                padding: 12px 14px;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                background: #f3faf5;
                color: #1a2336;
                font-size: 13px;
                line-height: 1.55;
            }}
            .completion-actions {{
                display: flex;
                justify-content: flex-end;
                gap: 10px;
                margin-top: 14px;
                flex-wrap: wrap;
            }}
            .completion-actions.is-stacked {{
                flex-direction: column;
                align-items: stretch;
            }}
            .completion-actions.is-stacked .button {{
                width: 100%;
                text-align: center;
            }}
            .status {{
                padding: 28px;
                border: 1px solid var(--line);
                border-radius: var(--radius-lg);
                background: var(--panel);
                box-shadow: var(--shadow-lg);
            }}
            .status.error {{ background: #fff7f7; }}
            .status h2 {{
                margin: 0 0 10px;
                font-size: 24px;
                letter-spacing: -0.01em;
            }}
            .status p {{ line-height: 1.6; }}
            .status pre {{
                overflow-x: auto;
                padding: 14px;
                border: 1px solid var(--line);
                border-radius: var(--radius-sm);
                background: #fff;
                font-size: 12px;
                line-height: 1.5;
            }}
            .back-link {{ display: inline-block; margin-top: 16px; color: var(--ink); font-weight: 700; text-decoration: none; }}
            @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
            @media (max-width: 980px) {{
                .shell {{ padding: 20px 18px 48px; }}
                .stepper,
                .step-fields,
                .option-grid,
                .confirmation-grid,
                .review-grid,
                .review-pill-grid {{
                    grid-template-columns: 1fr;
                }}
                .summary-list {{
                    grid-template-columns: 1fr;
                }}
                .review-strip {{
                    grid-template-columns: 1fr;
                }}
                .review-strip .review-card {{
                    border-right: 0;
                    border-bottom: 1px solid #e5e7eb;
                }}
                .review-strip .review-card:last-child {{ border-bottom: 0; }}
                .progress-top,
                .footer-bar,
                .topbar {{
                    flex-direction: column;
                    align-items: flex-start;
                }}
                .stepper {{ grid-template-columns: repeat(2, 1fr); }}
                .stage,
                .wizard-step,
                .footer-bar,
                .step-panel {{
                    padding-left: 20px;
                    padding-right: 20px;
                }}
                .button-row {{ width: 100%; }}
                .button {{ width: 100%; }}
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
                    </div>
                    <h3>Generating your audit report</h3>
                    <p>
                        Scoring the operating model, benchmarking against sector data and assembling the report.
                    </p>
                    <div class="loading-steps">
                        <div class="loading-step is-active"><span class="loading-step-dot">1</span><span>Scoring maturity model</span><span class="loading-step-state">In progress</span></div>
                        <div class="loading-step"><span class="loading-step-dot">2</span><span>Benchmarking against sector</span><span class="loading-step-state">Pending</span></div>
                        <div class="loading-step"><span class="loading-step-dot">3</span><span>Generating charts</span><span class="loading-step-state">Pending</span></div>
                        <div class="loading-step"><span class="loading-step-dot">4</span><span>Assembling report</span><span class="loading-step-state">Pending</span></div>
                    </div>
                </div>

                <div class="completion-state" id="completionState">
                    <div class="completion-kicker">Report ready</div>
                    <h3>Your Recruitment Audit is Ready</h3>
                    <p>Your report is ready. Download it below to complete the audit.</p>
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
                if (!form) return;
                const steps = Array.from(document.querySelectorAll(".wizard-step"));
                const nextBtn = document.querySelector("[data-next-step]");
                const prevBtn = document.querySelector("[data-prev-step]");
                const submitBtn = form.querySelector('button[type="submit"]');
                const progressFill = document.getElementById("progressFill");
                const progressPercent = document.getElementById("progressPercent");
                const progressStageLabel = document.getElementById("progressStageLabel");
                const progressStageName = document.getElementById("progressStageName");
                const stepFooterCopy = document.getElementById("stepFooterCopy");
                const downloadComplete = document.getElementById("downloadComplete");
                const loadingSteps = Array.from(document.querySelectorAll(".loading-step"));
                let currentStageIndex = 0;
                let isSubmitting = false;
                let latestDownloadUrl = "";
                let latestFilename = "recruitment_audit.pdf";

                function stepElement(index) {{
                    return steps[index] || null;
                }}

                function clearError(name) {{
                    const error = form.querySelector(`[data-error-for="${{name}}"]`);
                    if (error) error.textContent = "";
                }}

                function setError(name, message) {{
                    const error = form.querySelector(`[data-error-for="${{name}}"]`);
                    if (error) error.textContent = message;
                }}

                function inputValue(name) {{
                    const field = form.elements.namedItem(name);
                    if (!field) return "";
                    if (field instanceof RadioNodeList) return String(field.value || "").trim();
                    return String(field.value || "").trim();
                }}

                function updateConfirmation() {{
                    const email = inputValue("email_address") || "your email address";
                    const emailTarget = document.getElementById("confirmEmail");
                    if (emailTarget) emailTarget.textContent = email;
                    const companyTarget = document.getElementById("confirmCompany");
                    if (companyTarget) companyTarget.textContent = inputValue("company_name") || "Pending";
                    const nameTarget = document.getElementById("confirmName");
                    if (nameTarget) nameTarget.textContent = inputValue("contact_name") || "Pending";
                    const jobTitleTarget = document.getElementById("confirmJobTitle");
                    if (jobTitleTarget) jobTitleTarget.textContent = inputValue("job_title") || "Pending";
                    const phoneTarget = document.getElementById("confirmPhone");
                    if (phoneTarget) phoneTarget.textContent = inputValue("phone_number") || "Pending";
                }}

                function updateProgress() {{
                    const percentage = Math.round(((currentStageIndex + 1) / steps.length) * 100);
                    if (progressFill) progressFill.style.width = percentage + "%";
                    if (progressPercent) progressPercent.textContent = percentage + "%";
                    if (progressStageLabel) progressStageLabel.textContent = "Step " + (currentStageIndex + 1) + " of " + steps.length;
                    if (progressStageName) progressStageName.textContent = stepElement(currentStageIndex)?.getAttribute("data-step-title") || "";

                    steps.forEach((step, index) => {{
                        step.classList.toggle("active", index === currentStageIndex);
                    }});

                    if (prevBtn) prevBtn.hidden = currentStageIndex === 0;
                    if (nextBtn) nextBtn.hidden = currentStageIndex === steps.length - 1;
                    if (submitBtn) submitBtn.hidden = currentStageIndex !== steps.length - 1;
                    if (stepFooterCopy) {{
                        stepFooterCopy.textContent = "Your answers are confidential and used only to produce your audit report.";
                    }}
                    updateConfirmation();
                }}

                function showStage(stageIndex) {{
                    currentStageIndex = Math.max(0, Math.min(steps.length - 1, stageIndex));
                    updateProgress();
                    window.scrollTo({{ top: 0, behavior: "smooth" }});
                }}

                function validateStep(stepIndex) {{
                    const step = stepElement(stepIndex);
                    if (!step) return true;
                    let valid = true;
                    const alert = step.querySelector("[data-step-alert]");
                    if (alert) {{
                        alert.classList.remove("is-visible");
                        alert.textContent = "";
                    }}

                    step.querySelectorAll("input[type='text'], input[type='email'], input[type='tel']").forEach((field) => {{
                        clearError(field.name);
                        if (!field.checkValidity()) {{
                            valid = false;
                            setError(field.name, field.value.trim() ? "Enter a valid value." : "This field is required.");
                            if (valid === false && document.activeElement === document.body) field.focus();
                        }}
                    }});

                    step.querySelectorAll("[data-question-name]").forEach((questionCard) => {{
                        const fieldName = questionCard.getAttribute("data-question-name");
                        clearError(fieldName);
                        questionCard.classList.remove("is-invalid");
                        const checked = step.querySelector(`input[name="${{fieldName}}"]:checked`);
                        if (!checked) {{
                            valid = false;
                            questionCard.classList.add("is-invalid");
                            setError(fieldName, "Select one option to continue.");
                        }}
                    }});

                    if (!valid && alert) {{
                        alert.textContent = "Complete the current step before continuing.";
                        alert.classList.add("is-visible");
                    }}
                    return valid;
                }}

                if (nextBtn) {{
                    nextBtn.addEventListener("click", () => {{
                        if (!validateStep(currentStageIndex)) return;
                        showStage(currentStageIndex + 1);
                    }});
                }}

                if (prevBtn) {{
                    prevBtn.addEventListener("click", () => {{
                        showStage(currentStageIndex - 1);
                    }});
                }}

                form.querySelectorAll("input").forEach((field) => {{
                    field.addEventListener("input", () => {{
                        clearError(field.name);
                        const questionCard = field.closest("[data-question-name]");
                        if (questionCard) questionCard.classList.remove("is-invalid");
                        updateConfirmation();
                    }});
                    field.addEventListener("change", () => {{
                        clearError(field.name);
                        const questionCard = field.closest("[data-question-name]");
                        if (questionCard) questionCard.classList.remove("is-invalid");
                        updateConfirmation();
                    }});
                }});

                function setLoadingState(activeIndex) {{
                    const overlay = document.getElementById("loadingOverlay");
                    if (overlay) overlay.style.display = "flex";
                    loadingSteps.forEach((item, itemIndex) => {{
                        const state = item.querySelector(".loading-step-state");
                        item.classList.toggle("is-active", itemIndex === activeIndex);
                        item.classList.toggle("is-complete", itemIndex < activeIndex);
                        if (state) {{
                            state.textContent = itemIndex < activeIndex ? "Complete" : (itemIndex === activeIndex ? "In progress" : "Pending");
                        }}
                    }});
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

                function resetAuditJourney() {{
                    if (latestDownloadUrl) {{
                        window.URL.revokeObjectURL(latestDownloadUrl);
                        latestDownloadUrl = "";
                    }}
                    window.location.href = window.location.pathname;
                }}

                function showThankYouScreen() {{
                    const completionState = document.getElementById("completionState");
                    if (!completionState) return;
                    completionState.innerHTML = `
                        <div class="completion-kicker">Thank you</div>
                        <h3>Your Recruitment Audit Has Been Delivered</h3>
                        <p>Thank you for completing the Bradford &amp; Marsh Recruitment Operating Model Audit. Your report has now been downloaded successfully.</p>
                        <div class="completion-list">
                            <div class="completion-item">Your PDF report has been generated and downloaded</div>
                            <div class="completion-item">A copy has been prepared for internal review</div>
                            <div class="completion-item">If you would like to discuss the findings, Bradford &amp; Marsh can walk you through the audit and recommended next steps</div>
                        </div>
                        <div class="completion-actions is-stacked">
                            <a class="button button-primary" href="mailto:audit@bradfordandmarsh.co.uk?subject=Book%20a%20meeting%20to%20discuss%20my%20recruitment%20audit">Book a discussion</a>
                            <a class="button button-secondary" href="tel:01260544934">Call 01260 544934</a>
                            <a class="button button-secondary" href="https://www.bradfordandmarsh.co.uk/" target="_blank" rel="noopener noreferrer">Visit Bradford &amp; Marsh</a>
                        </div>
                    `;
                }}

                function resetOverlayState() {{
                    const overlay = document.getElementById("loadingOverlay");
                    const loadingState = document.getElementById("loadingState");
                    const completionState = document.getElementById("completionState");
                    if (overlay) overlay.style.display = "none";
                    if (loadingState) loadingState.style.display = "block";
                    if (completionState) completionState.style.display = "none";
                    setLoadingState(0);
                }}

                function triggerReportDownload() {{
                    if (!latestDownloadUrl) return;
                    const link = document.createElement("a");
                    link.href = latestDownloadUrl;
                    link.download = latestFilename;
                    document.body.appendChild(link);
                    link.click();
                    link.remove();
                    window.setTimeout(showThankYouScreen, 500);
                }}

                async function downloadReport(event) {{
                    if (isSubmitting) {{
                        event.preventDefault();
                        return;
                    }}
                    const allValid = steps.every((_, index) => validateStep(index));
                    if (!allValid) {{
                        event.preventDefault();
                        return;
                    }}
                    isSubmitting = true;
                    const buttons = Array.from(form.querySelectorAll('button[type="submit"], button[data-next-step], button[data-prev-step]'));
                    buttons.forEach((button) => button.disabled = true);

                    let phaseIndex = 0;
                    const startedAt = Date.now();
                    setLoadingState(0);
                    const timer = window.setInterval(() => {{
                        if (phaseIndex < loadingSteps.length - 1) {{
                            phaseIndex += 1;
                            setLoadingState(phaseIndex);
                        }}
                    }}, 500);

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

                        const blob = await response.blob();
                        const disposition = response.headers.get("Content-Disposition") || "";
                        const match = disposition.match(/filename=([^;]+)/i);
                        latestFilename = match ? match[1].trim().replace(/^\"|\"$/g, "") : "recruitment_audit.pdf";
                        setLoadingState(loadingSteps.length);

                        if (latestDownloadUrl) {{
                            window.URL.revokeObjectURL(latestDownloadUrl);
                        }}
                        latestDownloadUrl = window.URL.createObjectURL(blob);
                        const remainingDelay = Math.max(2200 - (Date.now() - startedAt), 0);
                        window.setTimeout(() => {{
                            showCompletionState(latestFilename);
                            isSubmitting = false;
                            buttons.forEach((button) => button.disabled = false);
                        }}, remainingDelay);
                    }} catch (error) {{
                        resetOverlayState();
                        isSubmitting = false;
                        buttons.forEach((button) => button.disabled = false);
                        window.alert("The report could not be generated. Please try again.");
                    }} finally {{
                        window.clearInterval(timer);
                    }}
                }}

                form.addEventListener("keydown", (event) => {{
                    if (event.key === "Enter" && event.target.tagName !== "TEXTAREA") {{
                        event.preventDefault();
                        if (submitBtn && !submitBtn.hidden) {{
                            submitBtn.click();
                        }} else if (nextBtn && !nextBtn.hidden) {{
                            nextBtn.click();
                        }}
                    }}
                }});

                form.addEventListener("submit", (event) => {{
                    event.preventDefault();
                    downloadReport(event);
                }});

                if (downloadComplete) {{
                    downloadComplete.addEventListener("click", triggerReportDownload);
                }}
                const startNewAudit = document.getElementById("startNewAudit");
                if (startNewAudit) {{
                    startNewAudit.addEventListener("click", resetAuditJourney);
                }}

                showStage(0);
            }})();
        </script>
    </body>
    </html>
    """



@app.route("/")
def form():
    def render_contact_field(field: dict) -> str:
        autocomplete = field.get("autocomplete", "")
        return f"""
        <div class="field">
            <label for="{field['name']}">{field['label']}</label>
            <input
                id="{field['name']}"
                name="{field['name']}"
                type="{field['type']}"
                placeholder="{field['placeholder']}"
                autocomplete="{autocomplete}"
                required
            >
            <div class="field-error" data-error-for="{field['name']}"></div>
        </div>
        """

    def render_question(question: dict) -> str:
        options_html = "\n".join(
            f"""
            <label class="option-card">
                <input class="option-input" type="radio" name="{question['name']}" value="{value}">
                <span>{label}</span>
            </label>
            """
            for value, label in question["options"]
        )
        return f"""
        <div class="question-card" data-question-name="{question['name']}">
            <div class="question-label">{question['label']}</div>
            <div class="option-grid">
                {options_html}
            </div>
            <div class="field-error" data-error-for="{question['name']}"></div>
        </div>
        """

    sections_html = []
    total_steps = len(WIZARD_STEPS) + 1
    for index, step in enumerate(WIZARD_STEPS, start=1):
        if step["kind"] == "contact":
            content_html = f'<div class="step-fields">{ "".join(render_contact_field(field) for field in step["fields"]) }</div>'
        else:
            content_html = "\n".join(render_question(question) for question in step["questions"])
        sections_html.append(
            f"""
            <section class="wizard-step{' active' if index == 1 else ''}" data-step-index="{index - 1}" data-step-title="{step['title']}" data-step-subtitle="{step['subtitle']}">
                <div class="section-head">
                    <div class="section-kicker">Step {index}</div>
                    <h2 class="section-title">{step['title']}</h2>
                    <p class="section-copy">{step['subtitle']}</p>
                </div>
                <div class="stage-alert" data-step-alert></div>
                {content_html}
            </section>
            """
        )

    sections_html.append(
        f"""
        <section class="wizard-step" data-step-index="{total_steps - 1}" data-step-title="Confirmation" data-step-subtitle="Everything is captured and ready for report generation.">
            <div class="section-head">
                <div class="section-kicker">Step {total_steps}</div>
                <h2 class="section-title">That's everything we need</h2>
                <p class="section-copy">We'll put your recruitment audit together and send it to <strong id="confirmEmail">your email address</strong> within 24 hours.</p>
            </div>
            <div class="confirmation-panel">
                <div class="confirmation-grid">
                    <div class="confirmation-item">
                        <div class="review-label">Company</div>
                        <div class="review-value" id="confirmCompany">Pending</div>
                    </div>
                    <div class="confirmation-item">
                        <div class="review-label">Full name</div>
                        <div class="review-value" id="confirmName">Pending</div>
                    </div>
                    <div class="confirmation-item">
                        <div class="review-label">Job title</div>
                        <div class="review-value" id="confirmJobTitle">Pending</div>
                    </div>
                    <div class="confirmation-item">
                        <div class="review-label">Phone number</div>
                        <div class="review-value" id="confirmPhone">Pending</div>
                    </div>
                </div>
                <div class="confirmation-note">
                    The report covers 12 recruitment operating areas benchmarked against UK sector data.
                </div>
            </div>
        </section>
        """
    )

    body = f"""
    <div class="topbar">
        <div class="brand-name">Bradford <span>&amp;</span> Marsh Consulting</div>
        <div class="trust-pill">Confidential assessment</div>
    </div>

    <form id="auditForm" method="post" action="/generate">
        <input type="hidden" name="office_address" value="">
        <input type="hidden" name="sector" value="Other">
        <input type="hidden" name="location" value="Not provided">
        <input type="hidden" name="headcount" value="Not provided">
        <input type="hidden" name="annual_hiring_volume" value="Not provided">
        <input type="hidden" name="key_roles_hired" value="Not provided">

        <div class="panel assessment-panel">
            <div class="progress-shell">
                <div class="progress-top">
                    <div>
                        <div class="progress-title" id="progressStageLabel">Step 1 of {total_steps}</div>
                        <div class="progress-stage-name" id="progressStageName">{WIZARD_STEPS[0]['title']}</div>
                    </div>
                    <div class="progress-percent" id="progressPercent">13%</div>
                </div>
                <div class="track"><div class="track-fill" id="progressFill"></div></div>
            </div>

            <div class="wizard-body">
                {"".join(sections_html)}
            </div>

            <div class="footer-bar">
                <div class="footer-copy" id="stepFooterCopy">Your answers are confidential and used only to produce your audit report.</div>
                <div class="button-row">
                    <button class="button button-ghost" type="button" data-prev-step>Back</button>
                    <button class="button button-secondary" type="button" data-next-step>Continue</button>
                    <button class="button button-primary" type="submit" hidden>Generate Audit Report</button>
                </div>
            </div>
        </div>
    </form>
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

        process_scores = {
            field_name: parse_tier_score(request.form.get(field_name))
            for step in WIZARD_STEPS
            if step["kind"] == "questions"
            for field_name in [question["name"] for question in step["questions"]]
        }

        data = {
            "company_name": request.form.get("company_name", "").strip(),
            "contact_name": request.form.get("contact_name", "").strip(),
            "job_title": request.form.get("job_title", "").strip(),
            "phone_number": request.form.get("phone_number", "").strip(),
            "email_address": request.form.get("email_address", "").strip(),
            "office_address": request.form.get("office_address", "").strip(),
            "sector": request.form.get("sector", "").strip() or "Other",
            "location": request.form.get("location", "").strip() or "Not provided",
            "headcount": request.form.get("headcount", "").strip() or "Not provided",
            "annual_hiring_volume": request.form.get("annual_hiring_volume", "").strip() or "Not provided",
            "key_roles_hired": request.form.get("key_roles_hired", "").strip() or "Not provided",
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
            "process_scores": process_scores,
            "process_flags": {
                field_name: (score is not None and score >= TIER_SCORE_THRESHOLD)
                for field_name, score in process_scores.items()
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
        benchmark_chart, benchmark_chart_item_count = create_benchmark_chart(
            data["company_name"], data["metrics"], benchmark, data["sector"], data["key_roles_hired"]
        )

        pdf_path = save_pdf_report(
            data=data,
            report=report,
            benchmark_summary=benchmark_summary,
            section_chart=section_chart,
            overall_chart=overall_chart,
            benchmark_chart=benchmark_chart,
            benchmark_chart_item_count=benchmark_chart_item_count,
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
