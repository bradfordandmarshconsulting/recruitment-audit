from __future__ import annotations

import os
import traceback
from pathlib import Path

import pandas as pd
from flask import Flask, request, send_file
from openai import OpenAI

from recruitment_audit import (
    get_api_key,
    load_benchmarks,
    build_benchmark_summary,
    auto_score_sections,
    generate_report_json,
    create_section_score_chart,
    create_overall_score_chart,
    create_benchmark_chart,
    save_word_report,
    parse_time_to_hire_days,
    parse_numeric_value,
)

app = Flask(__name__)

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
    ("has_hiring_plan", "Formal recruitment or workforce plan"),
    ("tracks_metrics", "Regular recruitment KPI tracking"),
    ("has_employer_brand", "Defined employer brand / EVP"),
    ("standardised_job_specs", "Standardised job adverts and job descriptions"),
    ("multi_channel_sourcing", "Consistent use of multiple sourcing channels"),
    ("structured_screening", "Consistent screening process"),
    ("structured_interviews", "Structured interviews or scorecards"),
    ("fast_offer_process", "Fast and consistent offer approval process"),
    ("formal_onboarding", "Documented onboarding process"),
    ("collects_candidate_feedback", "Candidate experience feedback collection"),
    ("named_process_owner", "Clearly named recruitment process owner"),
    ("hiring_manager_training", "Hiring manager interview / hiring training"),
]


def yes_no_to_bool(value: str | None) -> bool:
    return str(value).strip().lower() in {"yes", "y", "true"}


def get_sector_options() -> list[str]:
    candidates = [
        Path("uk_recruitment_benchmark_framework.xlsx"),
        Path.cwd() / "uk_recruitment_benchmark_framework.xlsx",
    ]

    for file_path in candidates:
        if file_path.exists():
            try:
                df = pd.read_excel(file_path, sheet_name="Benchmarks")
                if "sector" in df.columns:
                    sectors = (
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
                    if sectors:
                        return sectors
            except Exception:
                pass

    return FALLBACK_SECTORS


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
                --bg: #f5f7fb;
                --panel: #ffffff;
                --ink: #111827;
                --muted: #6b7280;
                --line: #e5e7eb;
                --line-dark: #d1d5db;
                --brand: #111827;
                --brand-2: #1f2937;
                --accent: #a16207;
                --success-bg: #ecfdf5;
                --success-line: #a7f3d0;
                --error-bg: #fef2f2;
                --error-line: #fecaca;
                --shadow: 0 14px 40px rgba(17, 24, 39, 0.08);
                --radius: 16px;
            }}

            * {{
                box-sizing: border-box;
            }}

            html, body {{
                margin: 0;
                padding: 0;
                background: linear-gradient(180deg, #f8fafc 0%, var(--bg) 100%);
                color: var(--ink);
                font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI",
                             Roboto, Helvetica, Arial, sans-serif;
            }}

            .shell {{
                max-width: 1080px;
                margin: 48px auto;
                padding: 0 20px 48px;
            }}

            .hero {{
                margin-bottom: 24px;
            }}

            .eyebrow {{
                display: inline-block;
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: var(--accent);
                margin-bottom: 10px;
            }}

            h1 {{
                margin: 0 0 10px;
                font-size: 36px;
                line-height: 1.05;
                letter-spacing: -0.02em;
            }}

            .sub {{
                margin: 0;
                max-width: 760px;
                color: var(--muted);
                font-size: 16px;
                line-height: 1.6;
            }}

            .panel {{
                background: var(--panel);
                border: 1px solid rgba(229, 231, 235, 0.8);
                border-radius: var(--radius);
                box-shadow: var(--shadow);
                overflow: hidden;
            }}

            .section {{
                padding: 28px;
                border-top: 1px solid var(--line);
            }}

            .section:first-child {{
                border-top: 0;
            }}

            .section-head {{
                margin-bottom: 18px;
            }}

            .section-title {{
                margin: 0 0 6px;
                font-size: 20px;
                letter-spacing: -0.01em;
            }}

            .section-copy {{
                margin: 0;
                color: var(--muted);
                line-height: 1.55;
                font-size: 14px;
            }}

            .grid {{
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 18px 20px;
            }}

            .yn-grid {{
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 18px 20px;
            }}

            .field {{
                display: flex;
                flex-direction: column;
                gap: 8px;
            }}

            .field.full {{
                grid-column: 1 / -1;
            }}

            label {{
                font-size: 13px;
                font-weight: 700;
                color: var(--ink);
            }}

            .input-wrap {{
                position: relative;
                display: flex;
                align-items: center;
            }}

            input,
            select {{
                width: 100%;
                min-height: 48px;
                padding: 12px 14px;
                border: 1px solid var(--line-dark);
                border-radius: 12px;
                font-size: 14px;
                color: var(--ink);
                background: #fff;
                transition: border-color 0.15s ease, box-shadow 0.15s ease;
            }}

            .has-suffix input {{
                padding-right: 74px;
            }}

            .suffix {{
                position: absolute;
                right: 12px;
                font-size: 12px;
                font-weight: 700;
                color: var(--muted);
                background: #f9fafb;
                border: 1px solid var(--line);
                border-radius: 999px;
                padding: 6px 10px;
                pointer-events: none;
            }}

            input:focus,
            select:focus {{
                outline: none;
                border-color: #9ca3af;
                box-shadow: 0 0 0 4px rgba(17, 24, 39, 0.06);
            }}

            .hint {{
                margin-top: -2px;
                color: var(--muted);
                font-size: 12px;
                line-height: 1.45;
            }}

            .actions {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 16px;
                padding: 24px 28px 28px;
                border-top: 1px solid var(--line);
                background: linear-gradient(180deg, rgba(249,250,251,0.6) 0%, rgba(255,255,255,1) 100%);
            }}

            .actions-copy {{
                color: var(--muted);
                font-size: 13px;
                line-height: 1.5;
            }}

            .button {{
                border: 0;
                background: linear-gradient(180deg, var(--brand-2) 0%, var(--brand) 100%);
                color: #fff;
                padding: 14px 20px;
                min-width: 260px;
                border-radius: 12px;
                font-size: 15px;
                font-weight: 700;
                cursor: pointer;
                box-shadow: 0 10px 24px rgba(17, 24, 39, 0.18);
                transition: transform 0.1s ease;
            }}

            .button:hover {{
                transform: translateY(-1px);
            }}

            .card-list {{
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 16px;
                margin-top: 22px;
            }}

            .mini-card {{
                border: 1px solid var(--line);
                background: #fcfcfd;
                border-radius: 14px;
                padding: 16px;
            }}

            .mini-label {{
                font-size: 12px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                color: var(--muted);
                margin-bottom: 8px;
            }}

            .mini-value {{
                font-size: 15px;
                line-height: 1.45;
                color: var(--ink);
            }}

            .status {{
                border-radius: 16px;
                padding: 28px;
                border: 1px solid var(--line);
                background: var(--panel);
                box-shadow: var(--shadow);
            }}

            .status.success {{
                background: var(--success-bg);
                border-color: var(--success-line);
            }}

            .status.error {{
                background: var(--error-bg);
                border-color: var(--error-line);
            }}

            .status h2 {{
                margin: 0 0 10px;
                font-size: 28px;
                letter-spacing: -0.02em;
            }}

            .status p {{
                margin: 8px 0;
                line-height: 1.6;
            }}

            .status pre {{
                white-space: pre-wrap;
                background: rgba(255,255,255,0.75);
                border: 1px solid rgba(209, 213, 219, 0.8);
                padding: 16px;
                border-radius: 12px;
                overflow-x: auto;
                font-size: 12px;
                line-height: 1.5;
                margin-top: 18px;
            }}

            .back-link {{
                display: inline-block;
                margin-top: 18px;
                color: var(--ink);
                font-weight: 700;
                text-decoration: none;
            }}

            .loading-overlay {{
                position: fixed;
                inset: 0;
                background: rgba(255,255,255,0.86);
                backdrop-filter: blur(3px);
                display: none;
                align-items: center;
                justify-content: center;
                z-index: 1000;
            }}

            .loading-card {{
                width: min(460px, calc(100vw - 32px));
                background: white;
                border: 1px solid var(--line);
                border-radius: 18px;
                box-shadow: var(--shadow);
                padding: 28px;
                text-align: center;
            }}

            .spinner {{
                width: 42px;
                height: 42px;
                border-radius: 999px;
                margin: 0 auto 16px;
                border: 4px solid #e5e7eb;
                border-top-color: #111827;
                animation: spin 0.9s linear infinite;
            }}

            @keyframes spin {{
                to {{ transform: rotate(360deg); }}
            }}

            @media (max-width: 860px) {{
                .grid,
                .yn-grid,
                .card-list {{
                    grid-template-columns: 1fr;
                }}

                .actions {{
                    flex-direction: column;
                    align-items: stretch;
                }}

                .button {{
                    width: 100%;
                    min-width: 0;
                }}

                h1 {{
                    font-size: 30px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="shell">
            {body}
        </div>

        <div class="loading-overlay" id="loadingOverlay">
            <div class="loading-card">
                <div class="spinner"></div>
                <h3 style="margin:0 0 10px; font-size:22px;">Generating recruitment audit</h3>
                <p style="margin:0; color:#6b7280; line-height:1.6;">
                    Calculating diagnostics, benchmarking performance and building the Word report.
                </p>
            </div>
        </div>

        <script>
            const form = document.getElementById("auditForm");
            if (form) {{
                form.addEventListener("submit", function() {{
                    const overlay = document.getElementById("loadingOverlay");
                    if (overlay) {{
                        overlay.style.display = "flex";
                    }}
                }});
            }}
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

    yes_no_html = "\n".join(
        f"""
        <div class="field">
            <label for="{field_name}">{label}</label>
            <select id="{field_name}" name="{field_name}" required>
                <option value="">Select…</option>
                <option value="Yes">Yes</option>
                <option value="No">No</option>
            </select>
        </div>
        """
        for field_name, label in YES_NO_FIELDS
    )

    body = f"""
    <div class="hero">
        <div class="eyebrow">Bradford & Marsh Consulting</div>
        <h1>Recruitment Audit Diagnostic</h1>
        <p class="sub">
            Structured recruitment process assessment with diagnostics, benchmark comparison,
            charting and a downloadable Word report.
        </p>

        <div class="card-list">
            <div class="mini-card">
                <div class="mini-label">Output</div>
                <div class="mini-value">Client-ready Word audit with charts and section scoring</div>
            </div>
            <div class="mini-card">
                <div class="mini-label">Analysis</div>
                <div class="mini-value">Funnel diagnostics, process risk signals and retention analysis</div>
            </div>
            <div class="mini-card">
                <div class="mini-label">Delivery</div>
                <div class="mini-value">Report downloads directly after generation</div>
            </div>
        </div>
    </div>

    <form id="auditForm" method="post" action="/generate">
        <div class="panel">
            <div class="section">
                <div class="section-head">
                    <h2 class="section-title">Company profile</h2>
                    <p class="section-copy">
                        Core operating context used to interpret the recruitment environment and frame the audit.
                    </p>
                </div>

                <div class="grid">
                    <div class="field">
                        <label for="company_name">Company name</label>
                        <input id="company_name" name="company_name" required>
                    </div>

                    <div class="field">
                        <label for="sector">Sector</label>
                        <select id="sector" name="sector" required>
                            <option value="">Select…</option>
                            {sector_options}
                        </select>
                    </div>

                    <div class="field">
                        <label for="location">Location</label>
                        <input id="location" name="location" required>
                    </div>

                    <div class="field has-suffix">
                        <label for="headcount">Number of employees</label>
                        <div class="input-wrap">
                            <input id="headcount" name="headcount" required>
                            <span class="suffix">employees</span>
                        </div>
                    </div>

                    <div class="field has-suffix">
                        <label for="annual_hiring_volume">Annual hiring volume</label>
                        <div class="input-wrap">
                            <input id="annual_hiring_volume" name="annual_hiring_volume" required>
                            <span class="suffix">hires</span>
                        </div>
                    </div>

                    <div class="field full">
                        <label for="key_roles_hired">Key roles hired</label>
                        <input id="key_roles_hired" name="key_roles_hired" required>
                    </div>
                </div>
            </div>

            <div class="section">
                <div class="section-head">
                    <h2 class="section-title">Recruitment metrics</h2>
                    <p class="section-copy">
                        These inputs drive speed, conversion, offer and retention diagnostics.
                    </p>
                </div>

                <div class="grid">
                    <div class="field has-suffix">
                        <label for="time_to_hire">Average time to hire</label>
                        <div class="input-wrap">
                            <input id="time_to_hire" name="time_to_hire" placeholder="e.g. 42" required>
                            <span class="suffix">days</span>
                        </div>
                        <div class="hint">You can also enter formats like “6 weeks”.</div>
                    </div>

                    <div class="field has-suffix">
                        <label for="applications_per_role">Applications per role</label>
                        <div class="input-wrap">
                            <input id="applications_per_role" name="applications_per_role" placeholder="e.g. 36" required>
                            <span class="suffix">applications</span>
                        </div>
                    </div>

                    <div class="field has-suffix">
                        <label for="offer_acceptance">Offer acceptance rate</label>
                        <div class="input-wrap">
                            <input id="offer_acceptance" name="offer_acceptance" placeholder="e.g. 72" required>
                            <span class="suffix">%</span>
                        </div>
                    </div>

                    <div class="field has-suffix">
                        <label for="first_year_attrition">First-year attrition</label>
                        <div class="input-wrap">
                            <input id="first_year_attrition" name="first_year_attrition" placeholder="e.g. 18" required>
                            <span class="suffix">%</span>
                        </div>
                    </div>

                    <div class="field has-suffix">
                        <label for="interview_stages">Number of interview stages</label>
                        <div class="input-wrap">
                            <input id="interview_stages" name="interview_stages" placeholder="e.g. 2" required>
                            <span class="suffix">stages</span>
                        </div>
                    </div>

                    <div class="field has-suffix">
                        <label for="interview_feedback_time">Average interview feedback time</label>
                        <div class="input-wrap">
                            <input id="interview_feedback_time" name="interview_feedback_time" placeholder="e.g. 2" required>
                            <span class="suffix">days</span>
                        </div>
                    </div>

                    <div class="field has-suffix">
                        <label for="candidates_reaching_interview">Candidates reaching interview per role</label>
                        <div class="input-wrap">
                            <input id="candidates_reaching_interview" name="candidates_reaching_interview" placeholder="e.g. 5" required>
                            <span class="suffix">candidates</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="section">
                <div class="section-head">
                    <h2 class="section-title">Process maturity</h2>
                    <p class="section-copy">
                        These controls determine process maturity, operating discipline and governance strength.
                    </p>
                </div>

                <div class="yn-grid">
                    {yes_no_html}
                </div>
            </div>

            <div class="actions">
                <div class="actions-copy">
                    The generated report will download directly as a Word document.
                </div>
                <button class="button" type="submit">Generate recruitment audit</button>
            </div>
        </div>
    </form>
    """

    return render_page("Recruitment Audit Diagnostic", body)


@app.route("/generate", methods=["POST"])
def generate():
    try:
        client = OpenAI(api_key=get_api_key())

        data = {
            "company_name": request.form.get("company_name", "").strip(),
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

        benchmark = load_benchmarks(data["sector"])
        benchmark_summary = build_benchmark_summary(data["metrics"], benchmark)

        section_scores, section_notes = auto_score_sections(data, benchmark)
        data["section_scores"] = section_scores
        data["section_notes"] = section_notes
        data["total_score"] = sum(section_scores)
        data["percentage_score"] = round((data["total_score"] / 120) * 100, 1)

        report = generate_report_json(client, data, benchmark_summary)

        section_chart = create_section_score_chart(data["company_name"], data["section_scores"])
        overall_chart = create_overall_score_chart(data["company_name"], data["total_score"])
        benchmark_chart = create_benchmark_chart(data["company_name"], data["metrics"], benchmark)

        word_path = save_word_report(
            data=data,
            report=report,
            benchmark_summary=benchmark_summary,
            section_chart=section_chart,
            overall_chart=overall_chart,
            benchmark_chart=benchmark_chart,
        )

        download_name = f"{data['company_name'].strip().replace(' ', '_')}_recruitment_audit.docx"

        return send_file(
            word_path,
            as_attachment=True,
            download_name=download_name,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    except Exception as exc:
        traceback_text = traceback.format_exc()

        body = f"""
        <div class="hero">
            <div class="eyebrow">Bradford & Marsh Consulting</div>
            <h1>Report generation failed</h1>
            <p class="sub">
                The audit engine returned an exception while processing the report.
            </p>
        </div>

        <div class="status error">
            <h2>Generation error</h2>
            <p><strong>Error type:</strong> {type(exc).__name__}</p>
            <p><strong>Error:</strong> {exc!r}</p>
            <pre>{traceback_text}</pre>
            <a class="back-link" href="/">Return to the form</a>
        </div>
        """

        return render_page("Report generation failed", body), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
