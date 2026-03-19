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
    "Accounting",
    "Administration",
    "Advertising",
    "Agriculture",
    "Architecture",
    "Automotive",
    "Banking",
    "Business Development",
    "Charity",
    "Civil Engineering",
    "Cleaning Services",
    "Construction",
    "Consulting",
    "Customer Service",
    "Cyber Security",
    "Ecommerce",
    "Education",
    "Energy",
    "Engineering",
    "Facilities Management",
    "Financial Services",
    "FinTech",
    "Food & Beverage",
    "Gaming & Entertainment",
    "Healthcare",
    "Hospitality",
    "HR",
    "Insurance",
    "Legal",
    "Life Sciences",
    "Logistics",
    "Manufacturing",
    "Marketing",
    "Media",
    "Pharmaceutical",
    "Procurement",
    "Property",
    "Public Sector",
    "Recruitment",
    "Retail",
    "SaaS",
    "Sales",
    "Security Services",
    "Sports & Leisure",
    "Supply Chain",
    "Technology",
    "Telecommunications",
    "Transport",
    "Travel & Tourism",
    "Utilities",
]

TIER_SCORE_THRESHOLD = 0.55
STAGE_LABELS = [
    "Business Context",
    "Hiring Performance",
    "Process Control",
    "Review & Submit",
]

WIZARD_STEPS = [
    {
        "stage": 1,
        "title": "Tell us about your business",
        "subtitle": "This sets the benchmark position and shapes the report.",
        "kind": "fields",
        "fields": [
            {"name": "company_name", "label": "Company name", "placeholder": "e.g. Acme Telecom", "type": "text", "autocomplete": "organization", "required": True},
            {"name": "sector", "label": "Sector", "type": "select", "required": True, "options": FALLBACK_SECTORS},
        ],
    },
    {
        "stage": 1,
        "title": "Where is the business based?",
        "subtitle": "This establishes the operating location for benchmarking.",
        "kind": "fields",
        "fields": [
            {"name": "location", "label": "Location (city/town)", "placeholder": "e.g. Manchester", "type": "text", "autocomplete": "address-level2", "required": True},
            {"name": "office_address", "label": "Office address", "placeholder": "e.g. 1 Piccadilly, Manchester, M1 1RG", "type": "text", "autocomplete": "street-address", "required": False},
        ],
    },
    {
        "stage": 1,
        "title": "What does your hiring demand look like?",
        "subtitle": "This helps us understand the load on your recruitment process.",
        "kind": "fields",
        "fields": [
            {"name": "headcount", "label": "Number of employees", "placeholder": "e.g. 120", "type": "number", "suffix": "employees", "required": True},
            {"name": "annual_hiring_volume", "label": "Annual hires", "placeholder": "e.g. 15", "type": "number", "suffix": "hires", "required": True},
            {"name": "key_roles_hired", "label": "Key roles hired", "placeholder": "e.g. Network Engineers, Project Managers, Customer Service Advisors", "type": "textarea", "required": True, "full": True},
        ],
    },
    {
        "stage": 1,
        "title": "Who should we send the report to?",
        "subtitle": "We'll use these details for report delivery and any follow-up.",
        "kind": "fields",
        "fields": [
            {"name": "contact_name", "label": "Full name", "placeholder": "e.g. Max Powell", "type": "text", "autocomplete": "name", "required": True},
            {"name": "job_title", "label": "Job title", "placeholder": "e.g. Head of People", "type": "text", "autocomplete": "organization-title", "required": True},
            {"name": "phone_number", "label": "Phone number", "placeholder": "e.g. 07700 900123", "type": "tel", "autocomplete": "tel", "required": True},
            {"name": "email_address", "label": "Email address", "placeholder": "e.g. max@company.com", "type": "email", "autocomplete": "email", "required": True},
        ],
    },
    {
        "stage": 2,
        "title": "Pace and volume",
        "subtitle": "How quickly roles are filled and how much interest they generate.",
        "kind": "fields",
        "fields": [
            {
                "name": "time_to_hire",
                "label": "Time to hire",
                "placeholder": "e.g. 36",
                "type": "number",
                "suffix": "days",
                "required": True,
                "helper": "From the role opening to an accepted offer. If you're not sure of the exact number, give your best estimate.",
                "estimate_flag": "is_estimate_time_to_hire",
                "estimate_options": [("15", "Under 20 days"), ("25", "20–30 days"), ("37.5", "30–45 days"), ("52.5", "45–60 days"), ("75", "Over 60 days")],
            },
            {
                "name": "applications_per_role",
                "label": "Applications per role",
                "placeholder": "e.g. 52",
                "type": "number",
                "suffix": "applications",
                "required": True,
                "helper": "Across all channels. A rough average is fine.",
                "estimate_flag": "is_estimate_applications_per_role",
                "estimate_options": [("10", "Under 15"), ("22.5", "15–30"), ("40", "30–50"), ("65", "50–80"), ("90", "Over 80")],
            },
        ],
    },
    {
        "stage": 2,
        "title": "Offers and retention",
        "subtitle": "Whether you're landing the right people — and keeping them.",
        "kind": "fields",
        "fields": [
            {
                "name": "offer_acceptance",
                "label": "Offer acceptance rate",
                "placeholder": "e.g. 78",
                "type": "number",
                "suffix": "%",
                "required": True,
                "helper": "What percentage of offers made are accepted? Estimate if needed.",
                "estimate_flag": "is_estimate_offer_acceptance",
                "estimate_options": [("95", "Over 90%"), ("82.5", "75–90%"), ("67.5", "60–75%"), ("50", "Under 60%")],
            },
            {
                "name": "first_year_attrition",
                "label": "First-year attrition",
                "placeholder": "e.g. 18",
                "type": "number",
                "suffix": "%",
                "required": True,
                "helper": "What percentage of new hires leave within 12 months?",
                "estimate_flag": "is_estimate_first_year_attrition",
                "estimate_options": [("5", "Under 10%"), ("15", "10–20%"), ("27.5", "20–35%"), ("40", "Over 35%")],
            },
        ],
    },
    {
        "stage": 2,
        "title": "Interview process",
        "subtitle": "How much friction sits between application and decision.",
        "kind": "fields",
        "fields": [
            {"name": "interview_stages", "label": "Interview stages", "placeholder": "e.g. 2", "type": "number", "suffix": "stages", "required": True, "helper": "How many separate interview rounds does a typical candidate go through?"},
            {"name": "interview_feedback_time", "label": "Feedback turnaround time", "placeholder": "e.g. 5", "type": "number", "suffix": "days", "required": True, "helper": "How long after an interview before the candidate hears back?"},
        ],
    },
    {
        "stage": 2,
        "title": "Shortlist quality and channels",
        "subtitle": "Whether the funnel is producing enough viable candidates and where you're looking.",
        "kind": "fields",
        "fields": [
            {"name": "candidates_reaching_interview", "label": "Candidates reaching interview per role", "placeholder": "e.g. 5", "type": "number", "suffix": "candidates", "required": True},
            {"name": "advertising_channels", "label": "Where do you currently advertise your roles?", "placeholder": "e.g. Indeed, LinkedIn, company website, local job boards", "type": "textarea", "required": True, "full": True},
        ],
    },
    {
        "stage": 3,
        "title": "Planning and visibility",
        "subtitle": "Whether hiring is being managed with structure or running on instinct.",
        "kind": "questions",
        "questions": [
            {"name": "has_hiring_plan", "label": "When a new role opens, is there a workforce plan or headcount forecast behind it — or does hiring tend to be reactive?", "options": [("1.0", "Always planned"), ("0.7", "Mostly planned"), ("0.4", "Sometimes planned"), ("0.1", "Usually reactive")]},
            {"name": "tracks_metrics", "label": "Do you track hiring metrics like time to hire, cost per hire, or offer acceptance — and actually review them?", "options": [("1.0", "Yes, reviewed regularly"), ("0.7", "Tracked but rarely reviewed"), ("0.4", "Loosely tracked"), ("0.1", "Not really")]},
            {"name": "has_employer_brand", "label": "If a candidate Googled your company right now, would they find a clear picture of what it's like to work there?", "options": [("1.0", "Yes, it's well defined"), ("0.7", "Partially — some content exists"), ("0.4", "Not much out there"), ("0.1", "Probably not")]},
        ],
    },
    {
        "stage": 3,
        "title": "Before candidates enter the process",
        "subtitle": "Whether sourcing and screening are consistent enough to support good decisions.",
        "kind": "questions",
        "questions": [
            {"name": "standardised_job_specs", "label": "Are your job adverts written to a consistent standard, or does it depend on who drafts them?", "options": [("1.0", "Consistent standard"), ("0.7", "Mostly consistent"), ("0.4", "Varies quite a bit"), ("0.1", "No real standard")]},
            {"name": "multi_channel_sourcing", "label": "How do you find candidates — same channels every time, or does it change depending on the role?", "options": [("1.0", "Multi-channel, tailored per role"), ("0.7", "A few go-to channels"), ("0.4", "Mostly one channel"), ("0.1", "Whatever works at the time")]},
            {"name": "structured_screening", "label": "When applications land, is there a set process for reviewing them — or does each manager do it their own way?", "options": [("1.0", "Standard process, consistently followed"), ("0.7", "Process exists but not always followed"), ("0.4", "Informal — manager dependent"), ("0.1", "No set process")]},
        ],
    },
    {
        "stage": 3,
        "title": "Interviews, offers and decisions",
        "subtitle": "Where good candidates are either secured or lost.",
        "kind": "questions",
        "questions": [
            {"name": "structured_interviews", "label": "Do your interviews follow a set structure — same questions, same scorecard — or is it more of a conversation?", "options": [("1.0", "Structured with scorecards"), ("0.7", "Mostly structured"), ("0.4", "Semi-structured"), ("0.1", "Mainly conversational")]},
            {"name": "fast_offer_process", "label": "Once you've found the right person, how quickly does an offer actually get out the door?", "options": [("1.0", "Within 24–48 hours"), ("0.7", "Within a week"), ("0.4", "It varies — sometimes longer"), ("0.1", "It often gets held up")]},
            {"name": "formal_onboarding", "label": "Is there a documented onboarding process every new starter goes through, or does it depend on the team?", "options": [("1.0", "Fully documented and consistent"), ("0.7", "Documented but inconsistent"), ("0.4", "Informal — team dependent"), ("0.1", "Not really in place")]},
        ],
    },
    {
        "stage": 3,
        "title": "Ownership and accountability",
        "subtitle": "Who's responsible — and whether they're equipped for it.",
        "kind": "questions",
        "questions": [
            {"name": "collects_candidate_feedback", "label": "Do you collect feedback from candidates about their experience — whether they got the job or not?", "options": [("1.0", "Yes, consistently"), ("0.7", "Sometimes"), ("0.4", "Rarely"), ("0.1", "No")]},
            {"name": "named_process_owner", "label": "Is there one person who owns recruitment end to end — someone who'd notice if things started slipping?", "options": [("1.0", "Yes, clearly named"), ("0.7", "Sort of — it's shared"), ("0.4", "It's unclear"), ("0.1", "Not really")]},
            {"name": "hiring_manager_training", "label": "Have your hiring managers had any training on interviewing or managing a hiring process?", "options": [("1.0", "Yes, formally trained"), ("0.7", "Some informal guidance"), ("0.4", "Very little"), ("0.1", "None")]},
        ],
    },
    {
        "stage": 4,
        "title": "Review & submit",
        "subtitle": "Check the full input set before generating the report.",
        "kind": "review",
    },
]
def parse_tier_score(value: str | None) -> float | None:
    try:
        if value is None:
            return None
        text = str(value).strip()
        return float(text) if text else None
    except (TypeError, ValueError):
        return None


def parse_estimate_flag(value: str | None) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _missing_required_fields(form_data) -> tuple[list[str], int]:
    checks = [
        (0, "company_name", bool(str(form_data.get("company_name", "")).strip())),
        (0, "sector", bool(str(form_data.get("sector", "")).strip())),
        (1, "location", bool(str(form_data.get("location", "")).strip())),
        (2, "headcount", parse_numeric_value(form_data.get("headcount")) is not None),
        (2, "annual_hiring_volume", parse_numeric_value(form_data.get("annual_hiring_volume")) is not None),
        (2, "key_roles_hired", bool(str(form_data.get("key_roles_hired", "")).strip())),
        (3, "contact_name", bool(str(form_data.get("contact_name", "")).strip())),
        (3, "job_title", bool(str(form_data.get("job_title", "")).strip())),
        (3, "phone_number", bool(str(form_data.get("phone_number", "")).strip())),
        (3, "email_address", bool(str(form_data.get("email_address", "")).strip())),
        (4, "time_to_hire", parse_numeric_value(form_data.get("time_to_hire")) is not None),
        (4, "applications_per_role", parse_numeric_value(form_data.get("applications_per_role")) is not None),
        (5, "offer_acceptance", parse_numeric_value(form_data.get("offer_acceptance")) is not None),
        (5, "first_year_attrition", parse_numeric_value(form_data.get("first_year_attrition")) is not None),
        (6, "interview_stages", parse_numeric_value(form_data.get("interview_stages")) is not None),
        (6, "interview_feedback_time", parse_numeric_value(form_data.get("interview_feedback_time")) is not None),
        (7, "candidates_reaching_interview", parse_numeric_value(form_data.get("candidates_reaching_interview")) is not None),
        (7, "advertising_channels", bool(str(form_data.get("advertising_channels", "")).strip())),
        (8, "has_hiring_plan", parse_tier_score(form_data.get("has_hiring_plan")) is not None),
        (8, "tracks_metrics", parse_tier_score(form_data.get("tracks_metrics")) is not None),
        (8, "has_employer_brand", parse_tier_score(form_data.get("has_employer_brand")) is not None),
        (9, "standardised_job_specs", parse_tier_score(form_data.get("standardised_job_specs")) is not None),
        (9, "multi_channel_sourcing", parse_tier_score(form_data.get("multi_channel_sourcing")) is not None),
        (9, "structured_screening", parse_tier_score(form_data.get("structured_screening")) is not None),
        (10, "structured_interviews", parse_tier_score(form_data.get("structured_interviews")) is not None),
        (10, "fast_offer_process", parse_tier_score(form_data.get("fast_offer_process")) is not None),
        (10, "formal_onboarding", parse_tier_score(form_data.get("formal_onboarding")) is not None),
        (11, "collects_candidate_feedback", parse_tier_score(form_data.get("collects_candidate_feedback")) is not None),
        (11, "named_process_owner", parse_tier_score(form_data.get("named_process_owner")) is not None),
        (11, "hiring_manager_training", parse_tier_score(form_data.get("hiring_manager_training")) is not None),
    ]
    missing = [field_name for _, field_name, is_present in checks if not is_present]
    first_missing_step = next((step_index for step_index, _, is_present in checks if not is_present), 0)
    return missing, first_missing_step
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
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
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

            html, body {{
                background: linear-gradient(160deg, #1b2a3d 0%, #0f1f2e 100%);
                color: #e8e6e1;
                font-family: "DM Sans", sans-serif;
            }}
            .shell {{
                max-width: 980px;
                padding: 28px 20px 64px;
            }}
            .topbar {{
                margin-bottom: 18px;
                border-bottom: 1px solid #374a5e;
            }}
            .brand-name {{
                color: #c9a84c;
                font-size: 10px;
                text-transform: uppercase;
                letter-spacing: 3px;
            }}
            .trust-pill {{
                border-color: #374a5e;
                background: rgba(30, 48, 64, 0.5);
                color: #9ca3af;
            }}
            .hero-copy {{
                margin-bottom: 24px;
            }}
            .hero-kicker {{
                color: #c9a84c;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.18em;
                text-transform: uppercase;
            }}
            .hero-title {{
                margin: 8px 0 0;
                color: #e8e6e1;
                font-family: "DM Serif Display", serif;
                font-size: 28px;
                font-weight: 400;
                line-height: 1.18;
            }}
            .panel {{
                border: 1px solid #374a5e;
                background: #243447;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
            }}
            .progress-shell {{
                padding: 24px 24px 0;
                margin-bottom: 0;
            }}
            .stage-segments {{
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 8px;
                margin-bottom: 20px;
            }}
            .stage-segment {{
                padding: 10px 12px;
                border: 1px solid #374a5e;
                border-radius: 12px;
                background: #2d4054;
                color: #6b7280;
                font-size: 12px;
                font-weight: 600;
                text-align: center;
            }}
            .stage-segment.is-active {{
                background: #c9a84c;
                border-color: #c9a84c;
                color: #1b2a3d;
            }}
            .stage-segment.is-complete {{
                background: rgba(201, 168, 76, 0.22);
                border-color: rgba(201, 168, 76, 0.5);
                color: #e8e6e1;
            }}
            .progress-title,
            .section-kicker,
            .completion-kicker {{
                color: #c9a84c;
            }}
            .progress-stage-name,
            .section-title,
            .loading-card h3,
            .completion-state h3,
            .review-group h3 {{
                color: #e8e6e1;
                font-family: "DM Serif Display", serif;
                font-weight: 400;
            }}
            .progress-percent,
            .section-copy,
            .footer-copy,
            .field-hint,
            .loading-card p,
            .completion-state p,
            .confirmation-note,
            .review-label,
            .summary-label {{
                color: #9ca3af;
            }}
            .track {{
                height: 2px;
                background: #374a5e;
            }}
            .track-fill {{
                background: #c9a84c;
            }}
            .wizard-body {{
                padding: 0 24px 8px;
            }}
            .wizard-step {{
                padding: 24px 0;
            }}
            .field label,
            label {{
                color: #e8e6e1;
            }}
            .field-hint {{
                font-size: 12px;
                line-height: 1.5;
            }}
            input, select, textarea {{
                border-color: #374a5e;
                background: #1e3040;
                color: #e8e6e1;
            }}
            input:focus, select:focus, textarea:focus {{
                border-color: #c9a84c;
                box-shadow: 0 0 0 3px rgba(201, 168, 76, 0.12);
            }}
            input:hover, select:hover, textarea:hover {{
                border-color: #c9a84c;
            }}
            input::placeholder, textarea::placeholder {{
                color: #6b7280;
            }}
            .suffix {{
                color: #9ca3af;
            }}
            .field.is-invalid input,
            .field.is-invalid select,
            .field.is-invalid textarea {{
                border-color: #ef6b6b;
            }}
            .field-error {{
                color: #ef6b6b;
            }}
            .stage-alert {{
                border-color: rgba(239, 107, 107, 0.28);
                background: rgba(239, 107, 107, 0.08);
                color: #ef6b6b;
            }}
            .question-card {{
                border-color: #374a5e;
                background: rgba(30, 48, 64, 0.5);
            }}
            .question-card.is-invalid {{
                border-color: #ef6b6b;
                background: rgba(239, 107, 107, 0.08);
            }}
            .question-label {{
                color: #e8e6e1;
            }}
            .option-grid {{
                grid-template-columns: 1fr;
            }}
            .option-card {{
                align-items: center;
                gap: 12px;
                min-height: 56px;
                border-color: #374a5e;
                background: transparent;
                color: #e8e6e1;
            }}
            .option-card:hover {{
                border-color: #c9a84c;
                background: rgba(201, 168, 76, 0.08);
            }}
            .option-card.is-selected,
            .option-card:has(.option-input:checked) {{
                border-color: #c9a84c;
                background: rgba(201, 168, 76, 0.12);
                box-shadow: none;
            }}
            .option-indicator {{
                width: 18px;
                height: 18px;
                border: 1px solid #374a5e;
                border-radius: 999px;
                background: transparent;
                flex: 0 0 auto;
                position: relative;
            }}
            .option-card.is-selected .option-indicator::after,
            .option-card:has(.option-input:checked) .option-indicator::after {{
                content: "";
                position: absolute;
                inset: 4px;
                border-radius: 999px;
                background: #c9a84c;
            }}
            .option-copy {{
                display: block;
                color: #e8e6e1;
                font-size: 13px;
                line-height: 1.5;
            }}
            .estimate-toggle {{
                margin-top: 10px;
                border: 1px solid #374a5e;
                border-radius: 8px;
                background: transparent;
                color: #9ca3af;
                padding: 10px 12px;
                font: inherit;
                font-size: 12px;
                font-weight: 600;
                cursor: pointer;
            }}
            .estimate-toggle.is-active {{
                border-color: #c9a84c;
                background: rgba(201, 168, 76, 0.12);
                color: #c9a84c;
            }}
            .estimate-panel {{
                display: none;
                margin-top: 10px;
                padding: 12px;
                border: 1px solid #374a5e;
                border-radius: 10px;
                background: rgba(15, 31, 46, 0.45);
            }}
            .estimate-panel.is-visible {{
                display: block;
            }}
            .estimate-grid {{
                display: grid;
                grid-template-columns: 1fr;
                gap: 8px;
            }}
            .estimate-option {{
                border: 1px solid #374a5e;
                border-radius: 8px;
                background: transparent;
                color: #e8e6e1;
                padding: 10px 12px;
                text-align: left;
                font: inherit;
                cursor: pointer;
            }}
            .estimate-option.is-selected {{
                border-color: #c9a84c;
                background: rgba(201, 168, 76, 0.12);
                color: #c9a84c;
            }}
            .review-sections {{
                display: grid;
                gap: 16px;
            }}
            .review-group {{
                padding: 18px;
                border: 1px solid #374a5e;
                border-radius: 12px;
                background: rgba(30, 48, 64, 0.5);
            }}
            .review-list {{
                display: grid;
                gap: 8px;
            }}
            .review-item {{
                display: flex;
                justify-content: space-between;
                gap: 12px;
                padding: 10px 0;
                border-bottom: 1px solid rgba(156, 163, 175, 0.15);
            }}
            .review-item:last-child {{
                border-bottom: 0;
            }}
            .review-item .review-value {{
                color: #e8e6e1;
            }}
            .review-item.is-missing .review-value {{
                color: #ef6b6b;
            }}
            .footer-bar {{
                border-top-color: #374a5e;
                background: rgba(15, 31, 46, 0.3);
            }}
            .button {{
                border-color: #374a5e;
                background: transparent;
                color: #e8e6e1;
            }}
            .button:hover {{
                border-color: #c9a84c;
                background: rgba(201, 168, 76, 0.08);
                color: #e8e6e1;
            }}
            .button-primary {{
                background: #c9a84c;
                border-color: #c9a84c;
                color: #1b2a3d;
                box-shadow: 0 8px 24px rgba(201, 168, 76, 0.18);
            }}
            .button-primary:hover {{
                background: #d6b45a;
                border-color: #d6b45a;
                color: #1b2a3d;
            }}
            .button-ghost {{
                background: transparent;
            }}
            .loading-overlay {{
                background: rgba(11, 19, 29, 0.78);
            }}
            .loading-card {{
                border-color: #374a5e;
                background: #243447;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
            }}
            .loading-step {{
                color: #9ca3af;
            }}
            .loading-step.is-active {{
                color: #e8e6e1;
            }}
            .loading-step.is-active .loading-step-dot {{
                border-color: #c9a84c;
                background: #c9a84c;
                color: #1b2a3d;
            }}
            .loading-step.is-complete {{
                color: #c9a84c;
            }}
            .loading-step.is-complete .loading-step-dot {{
                border-color: #c9a84c;
                background: rgba(201, 168, 76, 0.12);
                color: #c9a84c;
            }}
            .completion-item {{
                border-color: #374a5e;
                background: rgba(30, 48, 64, 0.5);
                color: #e8e6e1;
            }}
            @media (max-width: 980px) {{
                .shell {{ padding: 20px 18px 48px; }}
                .stage-segments {{
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }}
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
                    <h3>Your audit is being built</h3>
                    <p>
                        We'll send the full report to your email within 24 hours. The report covers 12 areas of your recruitment model, benchmarked against UK sector data, with clear recommendations on where to focus first.
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
                const stageSegments = Array.from(document.querySelectorAll(".stage-segment"));
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
                const reviewGroups = {{
                    business: document.getElementById("reviewBusiness"),
                    contact: document.getElementById("reviewContact"),
                    metrics: document.getElementById("reviewMetrics"),
                    process: document.getElementById("reviewProcessControl"),
                }};
                let currentStepIndex = Number(form.getAttribute("data-initial-step") || 0);
                let isSubmitting = false;
                let latestDownloadUrl = "";
                let latestFilename = "recruitment_audit.pdf";

                const reviewConfig = {{
                    business: [
                        ["Company", "company_name"],
                        ["Sector", "sector"],
                        ["Location", "location"],
                        ["Office address", "office_address"],
                        ["Number of employees", "headcount"],
                        ["Annual hires", "annual_hiring_volume"],
                        ["Key roles hired", "key_roles_hired"],
                    ],
                    contact: [
                        ["Full name", "contact_name"],
                        ["Job title", "job_title"],
                        ["Phone number", "phone_number"],
                        ["Email address", "email_address"],
                    ],
                    metrics: [
                        ["Time to hire", "time_to_hire", "days", "is_estimate_time_to_hire"],
                        ["Applications per role", "applications_per_role", "applications", "is_estimate_applications_per_role"],
                        ["Offer acceptance rate", "offer_acceptance", "%", "is_estimate_offer_acceptance"],
                        ["First-year attrition", "first_year_attrition", "%", "is_estimate_first_year_attrition"],
                        ["Interview stages", "interview_stages", "stages"],
                        ["Feedback turnaround time", "interview_feedback_time", "days"],
                        ["Candidates reaching interview", "candidates_reaching_interview", "candidates"],
                        ["Advertising channels", "advertising_channels"],
                    ],
                    process: [
                        ["Workforce planning", "has_hiring_plan"],
                        ["Metrics review", "tracks_metrics"],
                        ["Employer brand", "has_employer_brand"],
                        ["Job advert standard", "standardised_job_specs"],
                        ["Sourcing mix", "multi_channel_sourcing"],
                        ["Screening process", "structured_screening"],
                        ["Interview structure", "structured_interviews"],
                        ["Offer speed", "fast_offer_process"],
                        ["Onboarding process", "formal_onboarding"],
                        ["Candidate feedback", "collects_candidate_feedback"],
                        ["Process owner", "named_process_owner"],
                        ["Hiring manager training", "hiring_manager_training"],
                    ],
                }};

                function stepElement(index) {{
                    return steps[index] || null;
                }}

                function inputValue(name) {{
                    const field = form.elements.namedItem(name);
                    if (!field) return "";
                    if (field instanceof RadioNodeList) return String(field.value || "").trim();
                    return String(field.value || "").trim();
                }}

                function isEstimate(name) {{
                    return ["true", "1", "yes", "on"].includes(inputValue(name).toLowerCase());
                }}

                function setError(name, message) {{
                    const error = form.querySelector(`[data-error-for="${{name}}"]`);
                    if (error) error.textContent = message || "";
                }}

                function clearFieldState(name) {{
                    setError(name, "");
                    const fieldCard = form.querySelector(`[data-field-name="${{name}}"]`);
                    if (fieldCard) fieldCard.classList.remove("is-invalid");
                    const questionCard = form.querySelector(`[data-question-name="${{name}}"]`);
                    if (questionCard) questionCard.classList.remove("is-invalid");
                }}

                function formatDisplayValue(name, suffix, estimateFlag) {{
                    const value = inputValue(name);
                    if (!value) return "—";
                    const estimateSuffix = estimateFlag && isEstimate(estimateFlag) ? " (estimated)" : "";
                    return suffix ? `${{value}} ${{suffix}}${{estimateSuffix}}` : `${{value}}${{estimateSuffix}}`;
                }}

                function selectedOptionText(name) {{
                    const checked = form.querySelector(`input[name="${{name}}"]:checked`);
                    if (!checked) return "—";
                    const label = checked.closest(".option-card");
                    const copy = label ? label.querySelector(".option-copy") : null;
                    return copy ? copy.textContent.trim() : "—";
                }}

                function renderReviewList(target, items, type) {{
                    if (!target) return;
                    target.innerHTML = items.map((item) => {{
                        const label = item[0];
                        const name = item[1];
                        const suffix = item[2] || "";
                        const estimateFlag = item[3] || "";
                        const value = type === "process" ? selectedOptionText(name) : formatDisplayValue(name, suffix, estimateFlag);
                        const missing = value === "—";
                        return `
                            <div class="review-item${{missing ? ' is-missing' : ''}}">
                                <div class="review-label">${{label}}</div>
                                <div class="review-value">${{value}}</div>
                            </div>
                        `;
                    }}).join("");
                }}

                function updateReview() {{
                    renderReviewList(reviewGroups.business, reviewConfig.business, "business");
                    renderReviewList(reviewGroups.contact, reviewConfig.contact, "contact");
                    renderReviewList(reviewGroups.metrics, reviewConfig.metrics, "metrics");
                    renderReviewList(reviewGroups.process, reviewConfig.process, "process");
                }}

                function updateSelectedOptions(groupName) {{
                    form.querySelectorAll(`input[name="${{groupName}}"]`).forEach((input) => {{
                        const option = input.closest(".option-card");
                        if (option) option.classList.toggle("is-selected", input.checked);
                    }});
                }}

                function activeStageIndex() {{
                    const step = stepElement(currentStepIndex);
                    return Number(step?.getAttribute("data-stage-index") || 0);
                }}

                function updateStageSegments() {{
                    const activeStage = activeStageIndex();
                    stageSegments.forEach((segment, index) => {{
                        segment.classList.toggle("is-active", index === activeStage);
                        segment.classList.toggle("is-complete", index < activeStage);
                    }});
                }}

                function updateProgress() {{
                    const percentage = Math.round(((currentStepIndex + 1) / steps.length) * 100);
                    if (progressFill) progressFill.style.width = percentage + "%";
                    if (progressPercent) progressPercent.textContent = percentage + "%";
                    if (progressStageLabel) progressStageLabel.textContent = "Step " + (currentStepIndex + 1) + " of " + steps.length;
                    if (progressStageName) progressStageName.textContent = stepElement(currentStepIndex)?.getAttribute("data-step-title") || "";
                    steps.forEach((step, index) => step.classList.toggle("active", index === currentStepIndex));
                    if (prevBtn) prevBtn.hidden = currentStepIndex === 0;
                    if (nextBtn) nextBtn.hidden = currentStepIndex === steps.length - 1;
                    if (submitBtn) submitBtn.hidden = currentStepIndex !== steps.length - 1;
                    if (stepFooterCopy) stepFooterCopy.textContent = "Your answers are confidential and used only to produce your audit report.";
                    updateStageSegments();
                    updateReview();
                }}

                function showStep(index) {{
                    currentStepIndex = Math.max(0, Math.min(steps.length - 1, index));
                    updateProgress();
                    window.scrollTo({{ top: 0, behavior: "smooth" }});
                }}

                function validateFieldCard(fieldCard) {{
                    const input = fieldCard.querySelector("input:not([type='hidden']), select, textarea");
                    if (!input) return true;
                    const name = fieldCard.getAttribute("data-field-name");
                    clearFieldState(name);
                    const value = String(input.value || "").trim();
                    let valid = true;
                    if (input.hasAttribute("required") && !value) valid = false;
                    if (valid && input.type === "email" && value && !input.checkValidity()) valid = false;
                    if (valid && input.getAttribute("inputmode") === "decimal" && value && Number.isNaN(Number(value))) valid = false;
                    if (!valid) {{
                        fieldCard.classList.add("is-invalid");
                        setError(name, "We need a value here before we can generate your report.");
                    }}
                    return valid;
                }}

                function validateQuestionCard(questionCard) {{
                    const name = questionCard.getAttribute("data-question-name");
                    clearFieldState(name);
                    const checked = questionCard.querySelector("input:checked");
                    if (checked) return true;
                    questionCard.classList.add("is-invalid");
                    setError(name, "Select one option to continue.");
                    return false;
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
                    step.querySelectorAll("[data-field-name]").forEach((fieldCard) => {{
                        if (!validateFieldCard(fieldCard)) valid = false;
                    }});
                    step.querySelectorAll("[data-question-name]").forEach((questionCard) => {{
                        if (!validateQuestionCard(questionCard)) valid = false;
                    }});
                    if (!valid && alert) {{
                        alert.textContent = "We need a few more details before we can generate your report.";
                        alert.classList.add("is-visible");
                    }}
                    return valid;
                }}

                function firstInvalidStep() {{
                    for (let index = 0; index < steps.length - 1; index += 1) {{
                        if (!validateStep(index)) return index;
                    }}
                    return -1;
                }}

                form.querySelectorAll("input, select, textarea").forEach((field) => {{
                    field.addEventListener("input", () => {{
                        clearFieldState(field.name);
                        if (field.type !== "radio") {{
                            const estimateFlag = field.closest("[data-field-name]")?.querySelector("input[type='hidden'][name^='is_estimate_']");
                            if (estimateFlag && String(field.value || "").trim()) {{
                                estimateFlag.value = "false";
                                const fieldName = field.name;
                                form.querySelectorAll(`[data-estimate-option="${{fieldName}}"]`).forEach((button) => button.classList.remove("is-selected"));
                                const toggle = form.querySelector(`[data-estimate-toggle="${{fieldName}}"]`);
                                const panel = form.querySelector(`[data-estimate-panel="${{fieldName}}"]`);
                                if (toggle) toggle.classList.remove("is-active");
                                if (panel) panel.classList.remove("is-visible");
                            }}
                        }}
                        updateReview();
                    }});
                    field.addEventListener("change", () => {{
                        clearFieldState(field.name);
                        if (field.type === "radio") updateSelectedOptions(field.name);
                        updateReview();
                    }});
                }});

                form.querySelectorAll("[data-estimate-toggle]").forEach((button) => {{
                    button.addEventListener("click", () => {{
                        const fieldName = button.getAttribute("data-estimate-toggle");
                        const flagName = button.getAttribute("data-estimate-flag");
                        const panel = form.querySelector(`[data-estimate-panel="${{fieldName}}"]`);
                        const active = !button.classList.contains("is-active");
                        button.classList.toggle("is-active", active);
                        if (panel) panel.classList.toggle("is-visible", active);
                        const flag = document.getElementById(flagName);
                        if (flag) flag.value = active ? "true" : "false";
                    }});
                }});

                form.querySelectorAll("[data-estimate-option]").forEach((button) => {{
                    button.addEventListener("click", () => {{
                        const fieldName = button.getAttribute("data-estimate-option");
                        const value = button.getAttribute("data-estimate-value") || "";
                        const flagName = button.getAttribute("data-estimate-flag");
                        const input = form.elements.namedItem(fieldName);
                        const flag = document.getElementById(flagName);
                        if (input) input.value = value;
                        if (flag) flag.value = "true";
                        form.querySelectorAll(`[data-estimate-option="${{fieldName}}"]`).forEach((option) => option.classList.remove("is-selected"));
                        button.classList.add("is-selected");
                        const toggle = form.querySelector(`[data-estimate-toggle="${{fieldName}}"]`);
                        const panel = form.querySelector(`[data-estimate-panel="${{fieldName}}"]`);
                        if (toggle) toggle.classList.add("is-active");
                        if (panel) panel.classList.add("is-visible");
                        clearFieldState(fieldName);
                        updateReview();
                    }});
                }});

                if (nextBtn) {{
                    nextBtn.addEventListener("click", () => {{
                        if (!validateStep(currentStepIndex)) return;
                        showStep(currentStepIndex + 1);
                    }});
                }}

                if (prevBtn) {{
                    prevBtn.addEventListener("click", () => showStep(currentStepIndex - 1));
                }}

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
                    const invalidStep = firstInvalidStep();
                    if (invalidStep !== -1) {{
                        event.preventDefault();
                        showStep(invalidStep);
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

                Array.from(new Set(Array.from(form.querySelectorAll("input[type='radio']")).map((input) => input.name))).forEach(updateSelectedOptions);
                showStep(currentStepIndex);
            }})();
        </script>
    </body>
    </html>
    """



@app.route("/")
def form():
    return _render_audit_form()


def _render_audit_form(
    error_message: str | None = None,
    initial_step_index: int = 0,
    values: dict[str, str] | None = None,
    missing_fields: list[str] | None = None,
) -> str:
    values = values or {}
    missing_fields = set(missing_fields or [])

    def value_for(name: str) -> str:
        return html.escape(str(values.get(name, "") or ""))

    def is_missing(name: str) -> bool:
        return name in missing_fields

    def render_field(field: dict) -> str:
        field_name = field["name"]
        classes = ["field"]
        if field.get("full"):
            classes.append("full")
        if field.get("type") in {"number"} and field.get("suffix"):
            classes.append("has-suffix")
        if is_missing(field_name):
            classes.append("is-invalid")
        field_class = " ".join(classes)
        required_attr = " required" if field.get("required") else ""
        helper_html = f'<div class="field-hint">{html.escape(field["helper"])}</div>' if field.get("helper") else ""
        error_message_html = "We need a value here before we can generate your report." if is_missing(field_name) else ""
        error_html = f'<div class="field-error" data-error-for="{field_name}">{error_message_html}</div>'
        suffix = field.get("suffix")
        estimate_html = ""

        if field["type"] == "select":
            options_html = ['<option value="">Select sector</option>'] + [
                f'<option value="{html.escape(option)}"{" selected" if values.get(field_name, "") == option else ""}>{html.escape(option)}</option>'
                for option in field["options"]
            ]
            input_html = f"""
            <select id="{field_name}" name="{field_name}"{required_attr}>
                {''.join(options_html)}
            </select>
            """
        elif field["type"] == "textarea":
            input_html = f"""
            <textarea id="{field_name}" name="{field_name}" placeholder="{html.escape(field.get('placeholder', ''))}"{required_attr}>{value_for(field_name)}</textarea>
            """
        else:
            input_type = "text" if field["type"] == "number" else field["type"]
            inputmode = ' inputmode="decimal"' if field["type"] == "number" else ""
            autocomplete = f' autocomplete="{html.escape(field.get("autocomplete", ""))}"' if field.get("autocomplete") else ""
            input_core = f'<input id="{field_name}" name="{field_name}" type="{input_type}" placeholder="{html.escape(field.get("placeholder", ""))}" value="{value_for(field_name)}"{autocomplete}{inputmode}{required_attr}>'
            if suffix:
                input_html = f'<div class="input-wrap">{input_core}<span class="suffix">{html.escape(suffix)}</span></div>'
            else:
                input_html = input_core

        if field.get("estimate_options"):
            estimate_flag = field["estimate_flag"]
            estimate_active = parse_estimate_flag(values.get(estimate_flag))
            estimate_html = f"""
            <input type="hidden" name="{estimate_flag}" id="{estimate_flag}" value="{'true' if estimate_active else 'false'}">
            <button class="estimate-toggle{' is-active' if estimate_active else ''}" type="button" data-estimate-toggle="{field_name}" data-estimate-flag="{estimate_flag}">
                Not sure — help me estimate
            </button>
            <div class="estimate-panel{' is-visible' if estimate_active else ''}" data-estimate-panel="{field_name}">
                <div class="estimate-grid">
                    {
                        ''.join(
                            f'<button class="estimate-option{" is-selected" if estimate_active and values.get(field_name, "") == option_value else ""}" '
                            f'type="button" data-estimate-option="{field_name}" data-estimate-value="{option_value}" data-estimate-flag="{estimate_flag}">{html.escape(option_label)}</button>'
                            for option_value, option_label in field["estimate_options"]
                        )
                    }
                </div>
            </div>
            """

        return f"""
        <div class="{field_class}" data-field-name="{field_name}">
            <label for="{field_name}">{html.escape(field['label'])}</label>
            {input_html}
            {helper_html}
            {estimate_html}
            {error_html}
        </div>
        """

    def render_question(question: dict) -> str:
        question_name = question["name"]
        current_value = values.get(question_name, "")
        card_class = "question-card is-invalid" if is_missing(question_name) else "question-card"
        options_html = "\n".join(
            f"""
            <label class="option-card{' is-selected' if current_value == option_value else ''}">
                <input class="option-input" type="radio" name="{question_name}" value="{option_value}"{' checked' if current_value == option_value else ''}>
                <span class="option-indicator"></span>
                <span class="option-copy">{html.escape(option_label)}</span>
            </label>
            """
            for option_value, option_label in question["options"]
        )
        error_html = "Select one option to continue." if is_missing(question_name) else ""
        return f"""
        <div class="{card_class}" data-question-name="{question_name}">
            <div class="question-label">{html.escape(question['label'])}</div>
            <div class="option-grid">
                {options_html}
            </div>
            <div class="field-error" data-error-for="{question_name}">{error_html}</div>
        </div>
        """

    sections_html: list[str] = []
    total_steps = len(WIZARD_STEPS)
    for index, step in enumerate(WIZARD_STEPS):
        if step["kind"] == "fields":
            content_html = f'<div class="step-fields">{"".join(render_field(field) for field in step["fields"])}</div>'
        elif step["kind"] == "questions":
            content_html = "".join(render_question(question) for question in step["questions"])
        else:
            content_html = """
            <div class="review-sections">
                <div class="review-group">
                    <h3>Business Details</h3>
                    <div class="review-list" id="reviewBusiness"></div>
                </div>
                <div class="review-group">
                    <h3>Contact</h3>
                    <div class="review-list" id="reviewContact"></div>
                </div>
                <div class="review-group">
                    <h3>Hiring Metrics</h3>
                    <div class="review-list" id="reviewMetrics"></div>
                </div>
                <div class="review-group">
                    <h3>Process Control</h3>
                    <div class="review-list" id="reviewProcessControl"></div>
                </div>
            </div>
            """
        step_alert = error_message if error_message and index == initial_step_index else ""
        sections_html.append(
            f"""
            <section class="wizard-step{' active' if index == initial_step_index else ''}" data-step-index="{index}" data-stage-index="{step['stage'] - 1}" data-step-title="{html.escape(step['title'])}" data-step-subtitle="{html.escape(step['subtitle'])}">
                <div class="section-head">
                    <div class="section-kicker">Stage {step['stage']} / Step {index + 1}</div>
                    <h2 class="section-title">{html.escape(step['title'])}</h2>
                    <p class="section-copy">{html.escape(step['subtitle'])}</p>
                </div>
                <div class="stage-alert{' is-visible' if step_alert else ''}" data-step-alert>{html.escape(step_alert)}</div>
                {content_html}
            </section>
            """
        )

    stage_segments_html = "".join(
        f'<div class="stage-segment" data-stage-segment="{index}"><span>{html.escape(label)}</span></div>'
        for index, label in enumerate(STAGE_LABELS)
    )

    body = f"""
    <div class="topbar">
        <div class="brand-name">Bradford &amp; Marsh Consulting</div>
        <div class="trust-pill">Confidential assessment</div>
    </div>

    <div class="hero-copy">
        <div class="hero-kicker">Recruitment Operating Model Audit</div>
        <h1 class="hero-title">Audit the operating model behind your hiring results.</h1>
    </div>

    <form id="auditForm" method="post" action="/generate" data-initial-step="{initial_step_index}">
        <div class="panel assessment-panel">
            <div class="progress-shell">
                <div class="stage-segments">
                    {stage_segments_html}
                </div>
                <div class="progress-top">
                    <div>
                        <div class="progress-title" id="progressStageLabel">Step {initial_step_index + 1} of {total_steps}</div>
                        <div class="progress-stage-name" id="progressStageName">{html.escape(WIZARD_STEPS[initial_step_index]['title'])}</div>
                    </div>
                    <div class="progress-percent" id="progressPercent">0%</div>
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
                    <button class="button button-primary" type="button" data-next-step>Continue</button>
                    <button class="button button-primary" type="submit" hidden>Generate Report</button>
                </div>
            </div>
        </div>
    </form>
    """

    return render_page("Recruitment Operating Model Audit", body)


@app.route("/generate", methods=["POST"])
def generate():
    try:
        form_values = request.form.to_dict(flat=True)
        missing_fields, first_missing_step = _missing_required_fields(request.form)
        if missing_fields:
            return _render_audit_form(
                error_message="We need a few more details before we can generate your report.",
                initial_step_index=first_missing_step,
                values=form_values,
                missing_fields=missing_fields,
            ), 400

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
            "sector": request.form.get("sector", "").strip(),
            "location": request.form.get("location", "").strip(),
            "headcount": request.form.get("headcount", "").strip(),
            "annual_hiring_volume": request.form.get("annual_hiring_volume", "").strip(),
            "key_roles_hired": request.form.get("key_roles_hired", "").strip(),
            "advertising_channels": request.form.get("advertising_channels", "").strip(),
            "estimate_flags": {
                "time_to_hire": parse_estimate_flag(request.form.get("is_estimate_time_to_hire")),
                "applications_per_role": parse_estimate_flag(request.form.get("is_estimate_applications_per_role")),
                "offer_acceptance": parse_estimate_flag(request.form.get("is_estimate_offer_acceptance")),
                "first_year_attrition": parse_estimate_flag(request.form.get("is_estimate_first_year_attrition")),
            },
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
