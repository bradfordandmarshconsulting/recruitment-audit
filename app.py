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
            .shell {{ max-width: 1080px; margin: 0 auto; padding: 24px 28px 56px; }}
            .topbar {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 16px;
                margin-bottom: 18px;
            }}
            .brand-name {{
                font-family: var(--font-display);
                font-size: 20px;
                font-weight: 700;
            }}
            .trust-pill {{
                display: inline-flex;
                align-items: center;
                padding: 7px 12px;
                border: 1px solid var(--line);
                border-radius: 999px;
                background: var(--panel-soft);
                color: var(--muted);
                font-size: 12px;
                font-weight: 700;
            }}
            .progress-shell {{ position: sticky; top: 12px; z-index: 20; margin-bottom: 18px; }}
            .progress-bar {{
                padding: 16px 18px;
                border: 1px solid var(--line);
                border-radius: var(--radius-lg);
                background: var(--panel);
                box-shadow: var(--shadow-md);
            }}
            .progress-top {{
                display: flex;
                align-items: flex-start;
                justify-content: space-between;
                gap: 16px;
                margin-bottom: 14px;
            }}
            .progress-title,
            .section-kicker,
            .sidebar-kicker,
            .completion-kicker {{
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 0.06em;
                text-transform: uppercase;
                color: var(--muted);
            }}
            .progress-stage-name {{
                margin-top: 4px;
                font-family: var(--font-display);
                font-size: 20px;
                font-weight: 700;
            }}
            .progress-percent {{ margin-top: 4px; font-size: 13px; font-weight: 700; color: var(--brand); }}
            .track {{
                width: 100%;
                height: 3px;
                margin-bottom: 14px;
                overflow: hidden;
                border-radius: 999px;
                background: #e7e2da;
            }}
            .track-fill {{
                width: 0%;
                height: 100%;
                border-radius: 999px;
                background: var(--brand);
                transition: width 0.24s ease;
            }}
            .stepper {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }}
            .step {{
                appearance: none;
                display: flex;
                align-items: center;
                gap: 12px;
                min-width: 0;
                padding: 12px;
                cursor: pointer;
                border: 1px solid var(--line);
                border-radius: var(--radius-md);
                background: var(--panel-soft);
                text-align: left;
            }}
            .step-dot {{
                flex: 0 0 auto;
                display: grid;
                place-items: center;
                width: 30px;
                height: 30px;
                border-radius: 999px;
                background: #e6e9ef;
                color: var(--muted);
                font-size: 12px;
                font-weight: 800;
            }}
            .step-copy {{ min-width: 0; }}
            .step-kicker {{ margin-bottom: 3px; }}
            .step-title {{
                overflow: hidden;
                font-size: 13px;
                font-weight: 700;
                text-overflow: ellipsis;
                white-space: nowrap;
            }}
            .step.active {{
                border-color: var(--line-strong);
                background: var(--panel);
            }}
            .step.active .step-dot {{
                background: var(--brand);
                color: #fff;
            }}
            .step.complete {{
                border-color: rgba(22, 101, 52, 0.16);
                background: #f3faf5;
            }}
            .step.complete .step-dot {{
                background: var(--success-soft);
                color: var(--success);
            }}
            .assessment-layout {{
                display: grid;
                grid-template-columns: minmax(0, 1fr) 280px;
                gap: 18px;
                align-items: start;
            }}
            .assessment-layout form {{ min-width: 0; }}
            .panel {{
                border: 1px solid var(--line);
                border-radius: var(--radius-lg);
                background: var(--panel);
                box-shadow: var(--shadow-lg);
                overflow: hidden;
            }}
            .assessment-panel {{ width: 100%; }}
            .sidebar-card {{
                position: sticky;
                top: 126px;
                padding: 20px;
            }}
            .sidebar-title {{
                margin: 0 0 8px;
                font-family: var(--font-display);
                font-size: 20px;
                font-weight: 700;
            }}
            .sidebar-copy,
            .section-copy,
            .step-support,
            .footer-copy,
            .loading-card p {{
                color: var(--muted);
                line-height: 1.6;
                font-size: 14px;
            }}
            .summary-list {{ display: grid; gap: 10px; margin-top: 18px; }}
            .summary-item {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 10px;
                padding: 11px 12px;
                border: 1px solid var(--line);
                border-radius: var(--radius-sm);
                background: var(--panel-soft);
            }}
            .summary-label,
            .review-label {{
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.04em;
                text-transform: uppercase;
                color: var(--muted);
            }}
            .summary-value,
            .review-value {{
                font-size: 13px;
                font-weight: 700;
                color: var(--brand);
                text-align: right;
            }}
            .stage {{
                display: none;
                min-height: 460px;
                padding: 24px 24px 8px;
            }}
            .stage.active {{ display: block; }}
            .section-head {{ margin-bottom: 24px; }}
            .section-kicker {{ margin-bottom: 8px; color: var(--accent); }}
            .section-title {{
                margin: 0 0 8px;
                font-family: var(--font-display);
                font-size: 20px;
                font-weight: 700;
            }}
            @keyframes stageIn {{
                from {{ opacity: 0; transform: translateY(6px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            .step-panel {{
                padding: 24px;
                border: 1px solid var(--line);
                border-radius: var(--radius-md);
                background: var(--panel-soft);
            }}
            .step-fields {{
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 20px 16px;
            }}
            .field {{ display: flex; flex-direction: column; gap: 6px; }}
            .field.full {{ grid-column: 1 / -1; }}
            label {{
                font-size: 12px;
                font-weight: 700;
                line-height: 1.45;
                color: var(--brand);
            }}
            input, select, textarea {{
                width: 100%;
                border: 1px solid var(--line);
                border-radius: var(--radius-sm);
                background: #fff;
                color: var(--ink);
                font: inherit;
                outline: none;
                padding: 14px 14px;
                transition: border-color 0.18s ease, box-shadow 0.18s ease;
            }}
            input:focus, select:focus, textarea:focus {{
                border-color: var(--line-strong);
                box-shadow: 0 0 0 4px rgba(20, 32, 51, 0.06);
            }}
            .input-wrap {{ position: relative; }}
            .input-wrap input {{ padding-right: 78px; }}
            .suffix {{
                position: absolute;
                top: 50%;
                right: 12px;
                transform: translateY(-50%);
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.04em;
                text-transform: uppercase;
                color: var(--muted);
                pointer-events: none;
            }}
            .toggle-group {{
                display: inline-flex;
                gap: 8px;
                flex-wrap: wrap;
            }}
            .discipline-grid {{
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 14px 16px;
            }}
            .discipline-item {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 12px;
                padding: 14px;
                border: 1px solid var(--line);
                border-radius: var(--radius-sm);
                background: #fff;
            }}
            .discipline-question {{
                flex: 1 1 auto;
                font-size: 13px;
                font-weight: 700;
                line-height: 1.45;
                color: var(--brand);
            }}
            .toggle-option {{
                min-width: 72px;
                padding: 11px 14px;
                border: 1px solid var(--line);
                border-radius: 999px;
                background: #fff;
                color: var(--muted);
                font: inherit;
                font-size: 13px;
                font-weight: 700;
                cursor: pointer;
                transition: background 0.18s ease, border-color 0.18s ease, color 0.18s ease;
            }}
            .toggle-option.is-active.is-yes {{
                border-color: rgba(22, 101, 52, 0.24);
                background: var(--success-soft);
                color: var(--success);
            }}
            .toggle-option.is-active.is-no {{
                border-color: rgba(185, 28, 28, 0.22);
                background: var(--error-soft);
                color: var(--error);
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
            }}
            .review-grid {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
                margin-bottom: 16px;
            }}
            .review-card,
            .review-metric,
            .review-pill-card {{
                padding: 14px;
                border: 1px solid var(--line);
                border-radius: var(--radius-sm);
                background: #fff;
            }}
            .review-pill-grid {{
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin-top: 12px;
            }}
            .review-pill {{
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 8px 10px;
                border-radius: 999px;
                font-size: 12px;
                font-weight: 700;
                border: 1px solid var(--line);
                background: var(--panel-soft);
                color: var(--muted);
            }}
            .review-pill.is-yes {{
                border-color: rgba(22, 101, 52, 0.24);
                background: var(--success-soft);
                color: var(--success);
            }}
            .review-pill.is-no {{
                border-color: rgba(185, 28, 28, 0.22);
                background: var(--error-soft);
                color: var(--error);
            }}
            .footer-bar {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 16px;
                padding: 18px 24px 24px;
                border-top: 1px solid var(--line);
                background: var(--panel-soft);
            }}
            .footer-copy {{ max-width: 54ch; }}
            .button-row {{
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
                justify-content: flex-end;
            }}
            .button {{
                appearance: none;
                border: 1px solid transparent;
                border-radius: var(--radius-sm);
                padding: 13px 18px;
                font-size: 14px;
                font-weight: 700;
                cursor: pointer;
                text-decoration: none;
            }}
            .button:hover {{ opacity: 0.96; }}
            .button-primary {{
                background: var(--brand);
                color: #fff;
            }}
            .button-secondary {{
                background: #fff;
                color: var(--brand);
                border-color: var(--line);
            }}
            .button-ghost {{
                background: var(--panel-soft);
                color: var(--muted);
                border-color: var(--line);
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
                background: rgba(20, 32, 51, 0.18);
            }}
            .loading-card {{
                width: min(540px, calc(100vw - 32px));
                padding: 28px;
                border: 1px solid var(--line);
                border-radius: var(--radius-lg);
                background: var(--panel);
                box-shadow: var(--shadow-lg);
            }}
            .loading-head {{
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 10px;
            }}
            .loading-pill {{
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 8px 12px;
                border-radius: 999px;
                background: var(--panel-soft);
                color: var(--brand);
                font-size: 12px;
                font-weight: 800;
                text-transform: uppercase;
            }}
            .spinner {{
                width: 16px;
                height: 16px;
                border: 2px solid rgba(20, 32, 51, 0.16);
                border-top-color: var(--brand);
                border-radius: 999px;
                animation: spin 0.9s linear infinite;
            }}
            .loading-card h3,
            .completion-state h3 {{
                margin: 0 0 10px;
                font-family: var(--font-display);
                font-size: 20px;
                font-weight: 700;
            }}
            .completion-state p {{ color: var(--muted); line-height: 1.6; font-size: 14px; }}
            .loading-steps {{
                display: grid;
                gap: 10px;
                margin-top: 18px;
            }}
            .loading-step {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 12px;
                padding: 12px 14px;
                border: 1px solid var(--line);
                border-radius: var(--radius-sm);
                background: var(--panel-soft);
                color: var(--muted);
                font-size: 13px;
            }}
            .loading-step-state {{
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 0.04em;
                text-transform: uppercase;
            }}
            .loading-step.is-active {{
                border-color: var(--line-strong);
                color: var(--brand);
                background: #fff;
            }}
            .loading-step.is-complete {{
                border-color: rgba(22, 101, 52, 0.16);
                color: var(--success);
                background: #f3faf5;
            }}
            .completion-state {{ display: none; }}
            .completion-list {{
                display: grid;
                gap: 10px;
                margin: 18px 0;
            }}
            .completion-item {{
                padding: 12px 14px;
                border: 1px solid rgba(22, 101, 52, 0.16);
                border-radius: var(--radius-sm);
                background: #f3faf5;
                color: var(--brand);
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
                .assessment-layout,
                .stepper,
                .discipline-grid,
                .step-fields,
                .review-strip,
                .review-grid {{
                    grid-template-columns: 1fr;
                }}
                .sidebar-card {{ position: static; order: 2; }}
                .progress-top,
                .footer-bar,
                .topbar {{
                    flex-direction: column;
                    align-items: flex-start;
                }}
                .stage,
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
                    <h3>Analysing your recruitment model…</h3>
                    <p>
                        Reviewing process control, hiring performance and benchmark positioning
                    </p>
                    <div class="loading-steps">
                        <div class="loading-step is-active"><span>Scoring maturity model</span><span class="loading-step-state">In progress</span></div>
                        <div class="loading-step"><span>Benchmarking against sector</span><span class="loading-step-state">Pending</span></div>
                        <div class="loading-step"><span>Generating charts</span><span class="loading-step-state">Pending</span></div>
                        <div class="loading-step"><span>Assembling report</span><span class="loading-step-state">Pending</span></div>
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
                const stages = Array.from(document.querySelectorAll(".stage"));
                const tabs = Array.from(document.querySelectorAll(".step"));
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
                const summaryMappings = [
                    ["summaryCompany", "company_name"],
                    ["summarySector", "sector"],
                    ["summaryLocation", "location"],
                    ["summaryHiringDemand", "annual_hiring_volume"],
                    ["summaryKeyRoles", "key_roles_hired"],
                    ["reviewCompanyName", "company_name"],
                    ["reviewContact", "contact_name"],
                    ["reviewSector", "sector"],
                    ["reviewLocation", "location"],
                    ["reviewHeadcount", "headcount"],
                    ["reviewAnnualHiringVolume", "annual_hiring_volume"],
                    ["reviewKeyRoles", "key_roles_hired"],
                    ["reviewTimeToHire", "time_to_hire"],
                    ["reviewApplicationsPerRole", "applications_per_role"],
                    ["reviewOfferAcceptance", "offer_acceptance"],
                    ["reviewFirstYearAttrition", "first_year_attrition"],
                    ["reviewInterviewStages", "interview_stages"],
                    ["reviewInterviewFeedbackTime", "interview_feedback_time"],
                    ["reviewCandidatesReachingInterview", "candidates_reaching_interview"],
                ];
                let currentStageIndex = 0;
                let isSubmitting = false;
                let latestDownloadUrl = "";
                let latestFilename = "recruitment_audit.pdf";

                function fieldFilled(field) {{
                    return String(field.value || "").trim() !== "";
                }}

                function stageFields(stageIndex) {{
                    const stage = stages[stageIndex];
                    if (!stage) return [];
                    return Array.from(stage.querySelectorAll("input, select, textarea"));
                }}

                function stageIsComplete(stageIndex) {{
                    const fields = stageFields(stageIndex);
                    return fields.length > 0 && fields.every(fieldFilled);
                }}

                function inputValue(name) {{
                    const field = form.elements.namedItem(name);
                    return field ? String(field.value || "").trim() : "";
                }}

                function displayValue(value) {{
                    return value || "Pending";
                }}

                function renderReviewControls() {{
                    const container = document.getElementById("reviewControlPills");
                    if (!container) return;
                    container.innerHTML = Array.from(document.querySelectorAll(".yes-no-field")).map((field) => {{
                        const label = field.querySelector(".discipline-question");
                        const input = field.querySelector('input[data-yes-no="true"]');
                        const value = input ? String(input.value || "").trim() : "";
                        const tone = value === "Yes" ? " is-yes" : (value === "No" ? " is-no" : "");
                        return `<span class="review-pill${{tone}}">${{label ? label.textContent : ""}}: ${{value || "Pending"}}</span>`;
                    }}).join("");
                }}

                function updateSummaries() {{
                    summaryMappings.forEach(([targetId, fieldName]) => {{
                        const target = document.getElementById(targetId);
                        if (target) target.textContent = displayValue(inputValue(fieldName));
                    }});
                    renderReviewControls();
                }}

                function setToggleValue(targetName, value) {{
                    const input = document.getElementById(targetName);
                    const group = document.querySelector(`[data-toggle-group="${{targetName}}"]`);
                    if (!input || !group) return;
                    input.value = value;
                    group.classList.remove("is-invalid");
                    Array.from(group.querySelectorAll(".toggle-option")).forEach((button) => {{
                        const active = button.getAttribute("data-value") === value;
                        button.classList.toggle("is-active", active);
                        button.setAttribute("aria-pressed", active ? "true" : "false");
                    }});
                    updateProgress();
                }}

                function updateProgress() {{
                    const completedCount = stages.filter((_, index) => stageIsComplete(index)).length;
                    const percentage = Math.round((completedCount / stages.length) * 100);
                    if (progressFill) progressFill.style.width = percentage + "%";
                    if (progressPercent) progressPercent.textContent = percentage + "% complete";
                    if (progressStageLabel) progressStageLabel.textContent = "Stage " + (currentStageIndex + 1) + " of " + stages.length;
                    if (progressStageName) progressStageName.textContent = stages[currentStageIndex].getAttribute("data-stage-title") || "";

                    stages.forEach((stage, index) => {{
                        stage.classList.toggle("active", index === currentStageIndex);
                    }});

                    tabs.forEach((tab, index) => {{
                        const complete = stageIsComplete(index);
                        const dot = tab.querySelector(".step-dot");
                        tab.classList.toggle("active", index === currentStageIndex);
                        tab.classList.toggle("complete", complete);
                        if (dot) dot.textContent = complete && index !== currentStageIndex ? "✓" : String(index + 1).padStart(2, "0");
                    }});

                    if (prevBtn) prevBtn.hidden = currentStageIndex === 0;
                    if (nextBtn) nextBtn.hidden = currentStageIndex === stages.length - 1;
                    if (submitBtn) submitBtn.hidden = currentStageIndex !== stages.length - 1;
                    if (stepFooterCopy) {{
                        stepFooterCopy.textContent = stages[currentStageIndex].getAttribute("data-stage-summary") || "Complete each stage to build the final recruitment audit report.";
                    }}
                    updateSummaries();
                }}

                function showStage(stageIndex) {{
                    currentStageIndex = Math.max(0, Math.min(stages.length - 1, stageIndex));
                    updateProgress();
                }}

                function validateFields(fields) {{
                    for (const field of fields) {{
                        if (field.matches('[data-yes-no="true"]')) {{
                            if (!fieldFilled(field)) {{
                                const group = document.querySelector(`[data-toggle-group="${{field.id}}"]`);
                                if (group) {{
                                    group.classList.add("is-invalid");
                                    const firstButton = group.querySelector(".toggle-option");
                                    if (firstButton) firstButton.focus();
                                }}
                                return false;
                            }}
                            continue;
                        }}
                        if (!field.checkValidity()) {{
                            field.reportValidity();
                            field.focus();
                            return false;
                        }}
                    }}
                    return true;
                }}

                function validateCurrentStage() {{
                    return validateFields(stageFields(currentStageIndex));
                }}

                function validateAllStages() {{
                    return validateFields(Array.from(form.querySelectorAll("input, select, textarea")));
                }}

                Array.from(form.querySelectorAll("input, select, textarea")).forEach((field) => {{
                    field.addEventListener("input", updateProgress);
                    field.addEventListener("change", updateProgress);
                }});

                Array.from(document.querySelectorAll(".toggle-option")).forEach((button) => {{
                    button.addEventListener("click", () => {{
                        setToggleValue(button.getAttribute("data-target"), button.getAttribute("data-value"));
                    }});
                }});

                tabs.forEach((tab) => {{
                    tab.addEventListener("click", () => {{
                        const targetIndex = Number(tab.getAttribute("data-stage-index"));
                        if (Number.isNaN(targetIndex) || targetIndex === currentStageIndex) return;
                        if (targetIndex > currentStageIndex && !validateCurrentStage()) return;
                        showStage(targetIndex);
                    }});
                }});

                if (nextBtn) {{
                    nextBtn.addEventListener("click", () => {{
                        if (!validateCurrentStage()) return;
                        showStage(currentStageIndex + 1);
                    }});
                }}

                if (prevBtn) {{
                    prevBtn.addEventListener("click", () => {{
                        showStage(currentStageIndex - 1);
                    }});
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
                            <div class="completion-item">You can start a new audit at any time</div>
                        </div>
                        <div class="completion-actions">
                            <button class="button button-primary" type="button" id="thankYouStartNewAudit">Start New Audit</button>
                            <a class="button button-secondary" href="https://www.bradfordandmarsh.co.uk/" target="_blank" rel="noopener noreferrer">Visit Bradford &amp; Marsh</a>
                        </div>
                    `;
                    const thankYouStartNewAudit = document.getElementById("thankYouStartNewAudit");
                    if (thankYouStartNewAudit) {{
                        thankYouStartNewAudit.addEventListener("click", resetAuditJourney);
                    }}
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
                    if (!validateAllStages()) {{
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

                updateSummaries();
                showStage(0);
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
        <div class="discipline-item yes-no-field">
            <div class="discipline-question">{label}</div>
            <input id="{field_name}" name="{field_name}" type="hidden" data-yes-no="true">
            <div class="toggle-group" data-toggle-group="{field_name}" role="group" aria-label="{label}">
                <button class="toggle-option is-yes" type="button" data-target="{field_name}" data-value="Yes">Yes</button>
                <button class="toggle-option is-no" type="button" data-target="{field_name}" data-value="No">No</button>
            </div>
        </div>
        """

    discipline_fields_html = "\n".join(
        render_yes_no_field(field_name, label) for field_name, label in YES_NO_FIELDS
    )

    body = f"""
    <div class="topbar">
        <div class="brand-name">Bradford &amp; Marsh Consulting</div>
        <div class="trust-pill">Confidential assessment</div>
    </div>

    <div class="progress-shell">
        <div class="progress-bar">
            <div class="progress-top">
                <div>
                    <div class="progress-title" id="progressStageLabel">Stage 1 of 4</div>
                    <div class="progress-stage-name" id="progressStageName">Organisation</div>
                </div>
                <div class="progress-percent" id="progressPercent">0% complete</div>
            </div>
            <div class="track"><div class="track-fill" id="progressFill"></div></div>
            <div class="stepper">
                <button class="step active" type="button" data-stage-index="0">
                    <div class="step-dot">01</div>
                    <div class="step-copy">
                        <div class="step-kicker">Stage 1</div>
                        <div class="step-title">Organisation</div>
                    </div>
                </button>
                <button class="step" type="button" data-stage-index="1">
                    <div class="step-dot">02</div>
                    <div class="step-copy">
                        <div class="step-kicker">Stage 2</div>
                        <div class="step-title">Performance</div>
                    </div>
                </button>
                <button class="step" type="button" data-stage-index="2">
                    <div class="step-dot">03</div>
                    <div class="step-copy">
                        <div class="step-kicker">Stage 3</div>
                        <div class="step-title">Discipline</div>
                    </div>
                </button>
                <button class="step" type="button" data-stage-index="3">
                    <div class="step-dot">04</div>
                    <div class="step-copy">
                        <div class="step-kicker">Stage 4</div>
                        <div class="step-title">Review</div>
                    </div>
                </button>
            </div>
        </div>
    </div>

    <div class="assessment-layout">
        <aside class="panel sidebar-card">
            <div class="sidebar-kicker">Assessment overview</div>
            <h3 class="sidebar-title">Live profile</h3>
            <p class="sidebar-copy">This summary updates as the assessment is completed.</p>
            <div class="summary-list">
                <div class="summary-item"><span class="summary-label">Company</span><span class="summary-value" id="summaryCompany">Pending</span></div>
                <div class="summary-item"><span class="summary-label">Sector</span><span class="summary-value" id="summarySector">Pending</span></div>
                <div class="summary-item"><span class="summary-label">Location</span><span class="summary-value" id="summaryLocation">Pending</span></div>
                <div class="summary-item"><span class="summary-label">Hiring demand</span><span class="summary-value" id="summaryHiringDemand">Pending</span></div>
                <div class="summary-item"><span class="summary-label">Key roles</span><span class="summary-value" id="summaryKeyRoles">Pending</span></div>
            </div>
        </aside>

        <form id="auditForm" method="post" action="/generate">
            <div class="panel assessment-panel">
                <section class="stage active" data-stage="1" data-stage-title="Organisation" data-stage-summary="Capture the organisation profile used to anchor the audit and benchmark selection.">
                    <div class="section-head">
                        <div>
                            <div class="section-kicker">Stage 1</div>
                            <h2 class="section-title">Organisation</h2>
                            <p class="section-copy">Capture the organisation profile used to anchor the audit and benchmark selection.</p>
                        </div>
                    </div>
                    <div class="step-panel">
                        <div class="step-fields">
                            <div class="field">
                                <label for="company_name">What is the name of your company?</label>
                                <input id="company_name" name="company_name" required>
                            </div>
                            <div class="field">
                                <label for="contact_name">What is the name of the audit contact?</label>
                                <input id="contact_name" name="contact_name" autocomplete="name" required>
                            </div>
                            <div class="field">
                                <label for="sector">Which sector does your business operate in?</label>
                                <select id="sector" name="sector" required>
                                    <option value="">Select…</option>
                                    {sector_options}
                                </select>
                            </div>
                            <div class="field">
                                <label for="location">Where is the business based?</label>
                                <input id="location" name="location" autocomplete="address-level2" required>
                            </div>
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
                            <div class="field full">
                                <label for="key_roles_hired">Which roles or job titles do you hire for most often?</label>
                                <input id="key_roles_hired" name="key_roles_hired" placeholder="e.g. Sales Managers, Service Engineers, Finance Business Partners" required>
                            </div>
                        </div>
                    </div>
                </section>

                <section class="stage" data-stage="2" data-stage-title="Performance" data-stage-summary="Capture the operating metrics that show pace, conversion and early retention performance.">
                    <div class="section-head">
                        <div>
                            <div class="section-kicker">Stage 2</div>
                            <h2 class="section-title">Performance</h2>
                            <p class="section-copy">Capture the operating metrics that show pace, conversion and early retention performance.</p>
                        </div>
                    </div>
                    <div class="step-panel">
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
                            <div class="field full has-suffix">
                                <label for="candidates_reaching_interview">How many candidates typically reach interview for each role?</label>
                                <div class="input-wrap">
                                    <input id="candidates_reaching_interview" name="candidates_reaching_interview" placeholder="e.g. 5" inputmode="decimal" pattern="[0-9., ]+" title="Use numbers only." required>
                                    <span class="suffix">candidates</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                <section class="stage" data-stage="3" data-stage-title="Discipline" data-stage-summary="Assess whether recruitment is planned, controlled and governed consistently in practice.">
                    <div class="section-head">
                        <div>
                            <div class="section-kicker">Stage 3</div>
                            <h2 class="section-title">Discipline</h2>
                            <p class="section-copy">Assess whether recruitment is planned, controlled and governed consistently in practice.</p>
                        </div>
                    </div>
                    <div class="step-panel">
                        <div class="discipline-grid">
                            {discipline_fields_html}
                        </div>
                    </div>
                </section>

                <section class="stage" data-stage="4" data-stage-title="Review" data-stage-summary="Review the completed input set before generating the audit report.">
                    <div class="section-head">
                        <div>
                            <div class="section-kicker">Stage 4</div>
                            <h2 class="section-title">Review</h2>
                            <p class="section-copy">Check the final input set before generating the audit report.</p>
                        </div>
                    </div>
                    <div class="step-panel">
                        <div class="review-strip">
                            <div class="review-card"><div class="review-label">Company</div><div class="review-value" id="reviewCompanyName">Pending</div></div>
                            <div class="review-card"><div class="review-label">Contact</div><div class="review-value" id="reviewContact">Pending</div></div>
                            <div class="review-card"><div class="review-label">Sector</div><div class="review-value" id="reviewSector">Pending</div></div>
                            <div class="review-card"><div class="review-label">Location</div><div class="review-value" id="reviewLocation">Pending</div></div>
                        </div>
                        <div class="review-grid">
                            <div class="review-metric"><div class="review-label">Employees</div><div class="review-value" id="reviewHeadcount">Pending</div></div>
                            <div class="review-metric"><div class="review-label">Annual hiring volume</div><div class="review-value" id="reviewAnnualHiringVolume">Pending</div></div>
                            <div class="review-metric"><div class="review-label">Key roles</div><div class="review-value" id="reviewKeyRoles">Pending</div></div>
                            <div class="review-metric"><div class="review-label">Time to hire</div><div class="review-value" id="reviewTimeToHire">Pending</div></div>
                            <div class="review-metric"><div class="review-label">Applications per role</div><div class="review-value" id="reviewApplicationsPerRole">Pending</div></div>
                            <div class="review-metric"><div class="review-label">Offer acceptance</div><div class="review-value" id="reviewOfferAcceptance">Pending</div></div>
                            <div class="review-metric"><div class="review-label">First-year attrition</div><div class="review-value" id="reviewFirstYearAttrition">Pending</div></div>
                            <div class="review-metric"><div class="review-label">Interview stages</div><div class="review-value" id="reviewInterviewStages">Pending</div></div>
                            <div class="review-metric"><div class="review-label">Feedback time</div><div class="review-value" id="reviewInterviewFeedbackTime">Pending</div></div>
                            <div class="review-metric"><div class="review-label">Candidates reaching interview</div><div class="review-value" id="reviewCandidatesReachingInterview">Pending</div></div>
                        </div>
                        <div class="review-pill-card">
                            <div class="review-label">Process controls</div>
                            <div class="review-pill-grid" id="reviewControlPills"></div>
                        </div>
                    </div>
                </section>

                <div class="footer-bar">
                    <div class="footer-copy" id="stepFooterCopy">Complete each step to build the final recruitment audit report.</div>
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
