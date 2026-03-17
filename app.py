from __future__ import annotations

import html
import os
import traceback

from flask import Flask, request, send_file
from openai import OpenAI

from recruitment_audit import (
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
            .shell {{ max-width: 1160px; margin: 0 auto; padding: 28px 30px 72px; }}
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
            .progress-percent {{ font-size: 14px; font-weight: 800; color: var(--brand); }}
            .track {{ width: 100%; height: 10px; border-radius: 999px; background: rgba(148, 163, 184, 0.18); overflow: hidden; margin-bottom: 14px; }}
            .track-fill {{ width: 0%; height: 100%; border-radius: 999px; background: #142033; transition: width 0.28s ease; }}
            .stepper {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
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

            .app-grid {{ display: grid; grid-template-columns: minmax(0, 1.3fr) 330px; gap: 22px; align-items: start; }}
            .panel {{
                background: rgba(255,255,255,0.9);
                border: 1px solid rgba(20, 32, 51, 0.08); backdrop-filter: blur(10px);
                border-radius: var(--radius-2xl); box-shadow: var(--shadow-lg); overflow: hidden;
            }}
            .stage {{ display: none; padding: 38px; animation: stageIn 0.22s ease; }}
            .stage.active {{ display: block; }}
            @keyframes stageIn {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: translateY(0); }} }}

            .section-head {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 24px; margin-bottom: 34px; }}
            .section-kicker {{ display: inline-flex; align-items: center; gap: 8px; margin-bottom: 10px; color: var(--accent); font-size: 12px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; }}
            .section-title {{ margin: 0 0 8px; font-size: 30px; letter-spacing: -0.04em; line-height: 1.08; font-family: var(--font-display); font-weight: 700; }}
            .section-copy {{ margin: 0; max-width: 56ch; color: var(--muted); line-height: 1.6; font-size: 14px; }}
            .section-aside {{ min-width: 200px; background: rgba(15, 23, 42, 0.025); border: 1px solid rgba(15, 23, 42, 0.05); border-radius: 18px; padding: 14px 16px; color: var(--muted); line-height: 1.7; font-size: 12px; }}
            .stage-indicators {{ display: flex; flex-wrap: wrap; gap: 10px; margin: -6px 0 26px; }}
            .stage-indicator {{
                display: inline-flex; align-items: center; gap: 8px; padding: 10px 14px;
                border-radius: 999px; background: rgba(15, 23, 42, 0.04);
                border: 1px solid rgba(15, 23, 42, 0.07); color: var(--brand);
                font-size: 12px; font-weight: 800; letter-spacing: 0.02em;
            }}
            .stage-indicator-label {{ color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; font-size: 11px; }}

            .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 24px 20px; }}
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

            .note {{ margin-top: 28px; padding: 15px 18px; border-radius: 18px; background: rgba(15, 23, 42, 0.03); border: 1px solid rgba(15, 23, 42, 0.05); color: var(--muted); line-height: 1.7; font-size: 13px; }}
            .note strong {{ color: var(--brand); }}

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
                .app-grid {{ grid-template-columns: 1fr; }}
                .sidebar {{ position: static; }}
            }}
            @media (max-width: 980px) {{
                .grid, .stepper {{ grid-template-columns: 1fr; }}
                .topbar, .section-head, .footer-bar, .progress-top {{ flex-direction: column; align-items: flex-start; }}
                .section-aside {{ min-width: 0; width: 100%; }}
                .stage, .footer-bar {{ padding-left: 22px; padding-right: 22px; }}
                .button-row {{ width: 100%; }}
                .button {{ width: 100%; }}
                .hero {{ padding: 22px; }}
                .hero h1 {{ font-size: 24px; max-width: none; }}
                .shell {{ padding-top: 20px; }}
                .brand-lockup {{ align-items: flex-start; }}
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
                        <div class="loading-pill"><span class="spinner"></span> Generating report</div>
                        <div id="loadingPercent">0%</div>
                    </div>
                    <div class="brand-overline" style="margin-bottom: 8px;">Bradford &amp; Marsh Consulting</div>
                    <h3>Building the recruitment audit report</h3>
                    <p>
                        Reviewing your inputs, comparing benchmark position, and assembling the final recruitment audit report.
                    </p>

                    <div class="loading-track">
                        <div class="loading-fill" id="loadingFill"></div>
                    </div>

                    <div class="loading-meta">
                        <div id="loadingStatus">Preparing submission</div>
                        <div>Preparing download</div>
                    </div>

                    <div class="loading-list">
                        <div class="loading-list-item is-active"><span>Reviewing company information</span><span>01</span></div>
                        <div class="loading-list-item"><span>Scoring recruitment process maturity</span><span>02</span></div>
                        <div class="loading-list-item"><span>Building charts and benchmark comparison</span><span>03</span></div>
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
                const nextBtns = Array.from(document.querySelectorAll("[data-next-step]"));
                const prevBtns = Array.from(document.querySelectorAll("[data-prev-step]"));
                const progressFill = document.getElementById("progressFill");
                const progressPercent = document.getElementById("progressPercent");
                const summaryFields = Array.from(document.querySelectorAll("[data-summary-target]"));
                const captureRows = Array.from(document.querySelectorAll("[data-capture-step]"));
                const stageReadiness = document.getElementById("stageReadiness");
                const summaryCompany = document.getElementById("summaryCompany");
                const summarySector = document.getElementById("summarySector");
                const summaryLocation = document.getElementById("summaryLocation");
                const summaryHiring = document.getElementById("summaryHiring");
                const summaryRoles = document.getElementById("summaryRoles");
                const summaryContact = document.getElementById("summaryContact");
                const downloadComplete = document.getElementById("downloadComplete");
                const startNewAudit = document.getElementById("startNewAudit");
                const yesNoFields = Array.from(document.querySelectorAll(".yes-no-field select"));
                let isSubmitting = false;
                let currentStep = 1;
                let latestDownloadUrl = "";
                let latestFilename = "recruitment_audit.pdf";

                function fieldsForStep(step) {{
                    return Array.from(document.querySelectorAll('.stage[data-step="' + step + '"] input, .stage[data-step="' + step + '"] select, .stage[data-step="' + step + '"] textarea'));
                }}
                function stageEl(step) {{
                    return document.querySelector('.stage[data-step="' + step + '"]');
                }}
                function fieldFilled(field) {{ return String(field.value || "").trim() !== ""; }}
                function groupsForStep(step) {{
                    const stage = stageEl(step);
                    if (!stage) return [];
                    return Array.from(new Set(
                        fieldsForStep(step)
                            .map((field) => Number(field.getAttribute("data-stage-group") || 1))
                            .filter((group) => Number.isFinite(group) && group > 0)
                    )).sort((a, b) => a - b);
                }}
                function groupFields(step, group) {{
                    return fieldsForStep(step).filter((field) => Number(field.getAttribute("data-stage-group") || 1) === group);
                }}
                function groupIsComplete(step, group) {{
                    const fields = groupFields(step, group);
                    return !!fields.length && fields.every(fieldFilled);
                }}
                function currentGroupForStep(step) {{
                    const groups = groupsForStep(step);
                    if (!groups.length) return 1;
                    const nextOpenGroup = groups.find((group) => !groupIsComplete(step, group));
                    return nextOpenGroup || groups[groups.length - 1];
                }}
                function completionForStep(step) {{
                    const fields = fieldsForStep(step);
                    if (!fields.length) return 0;
                    const filled = fields.filter(fieldFilled).length;
                    return Math.round((filled / fields.length) * 100);
                }}
                function stepIsComplete(step) {{ return completionForStep(step) === 100; }}

                function updateCaptureRows() {{
                    captureRows.forEach((row) => {{
                        const step = Number(row.getAttribute("data-capture-step"));
                        const percent = completionForStep(step);
                        row.classList.toggle("complete", percent === 100);
                        const state = row.querySelector(".capture-state");
                        if (state) state.textContent = percent === 100 ? "Captured" : percent + "% ready";
                    }});
                }}

                function updateSummary() {{
                    const getVal = (id, fallback = "Pending") => {{
                        const el = document.getElementById(id);
                        const raw = el ? String(el.value || "").trim() : "";
                        return raw || fallback;
                    }};
                    if (summaryCompany) summaryCompany.textContent = getVal("company_name");
                    if (summarySector) summarySector.textContent = getVal("sector");
                    if (summaryLocation) summaryLocation.textContent = getVal("location");
                    if (summaryHiring) {{
                        const volume = getVal("annual_hiring_volume", "");
                        summaryHiring.textContent = volume ? volume + " hires / year" : "Pending";
                    }}
                    if (summaryRoles) summaryRoles.textContent = getVal("key_roles_hired");
                    if (summaryContact) {{
                        const name = getVal("contact_name", "");
                        const title = getVal("job_title", "");
                        summaryContact.textContent = name && title ? name + " · " + title : name || title || "Pending";
                    }}

                    const current = completionForStep(currentStep);
                    if (stageReadiness) {{
                        const labels = {{1: "Business Context", 2: "Hiring Performance", 3: "Process Control"}};
                        stageReadiness.textContent = labels[currentStep] + ": " + current + "% complete";
                    }}

                    const yesCount = yesNoFields.filter((field) => String(field.value || "").trim().toLowerCase() === "yes").length;
                    const answered = yesNoFields.filter(fieldFilled).length;
                    const disciplineChip = document.getElementById("disciplineChip");
                    if (disciplineChip) disciplineChip.textContent = answered ? (yesCount + " / " + answered + " positive controls") : "Controls pending";
                }}

                function updateStageIndicators() {{
                    stages.forEach((stage, index) => {{
                        const step = index + 1;
                        const stageIndicator = stage.querySelector("[data-stage-indicator]");
                        const stepIndicator = stage.querySelector("[data-step-indicator]");
                        const totalGroups = Math.max(1, groupsForStep(step).length);
                        const currentGroup = Math.min(currentGroupForStep(step), totalGroups);
                        if (stageIndicator) stageIndicator.textContent = "Stage " + step + " of " + stages.length;
                        if (stepIndicator) stepIndicator.textContent = "Step " + currentGroup + " of " + totalGroups;
                    }});
                }}

                function updateProgress() {{
                    const base = (currentStep - 1) * 33.33;
                    const fractional = completionForStep(currentStep) / 3;
                    const total = Math.max(6, Math.min(100, Math.round(base + fractional)));
                    if (progressFill) progressFill.style.width = total + "%";
                    if (progressPercent) progressPercent.textContent = total + "% complete";

                    stepEls.forEach((el, index) => {{
                        const step = index + 1;
                        el.classList.toggle("active", step === currentStep);
                        el.classList.toggle("complete", step < currentStep || stepIsComplete(step));
                    }});

                    updateCaptureRows();
                    updateSummary();
                    updateStageIndicators();
                }}

                function showStep(step) {{
                    currentStep = Math.max(1, Math.min(stages.length, step));
                    stages.forEach((stage) => {{
                        stage.classList.toggle("active", Number(stage.getAttribute("data-step")) === currentStep);
                    }});
                    updateProgress();
                }}

                function validateStep(step) {{
                    const fields = fieldsForStep(step);
                    for (const field of fields) {{
                        if (!field.checkValidity()) {{
                            field.reportValidity();
                            field.focus();
                            return false;
                        }}
                    }}
                    return true;
                }}

                nextBtns.forEach((btn) => {{
                    btn.addEventListener("click", () => {{
                        if (validateStep(currentStep)) showStep(currentStep + 1);
                    }});
                }});
                prevBtns.forEach((btn) => {{
                    btn.addEventListener("click", () => showStep(currentStep - 1));
                }});

                summaryFields.forEach((field) => {{
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
                    const phases = [
                        {{ target: 18, text: "Reviewing company information", index: 0 }},
                        {{ target: 42, text: "Scoring recruitment process maturity", index: 1 }},
                        {{ target: 71, text: "Building charts and benchmark comparison", index: 2 }},
                        {{ target: 92, text: "Preparing final report", index: 3 }},
                    ];

                    setLoadingState(0, "Preparing submission", 0);
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
                        setLoadingState(100, "Report ready. Starting download", 3);

                        if (latestDownloadUrl) {{
                            window.URL.revokeObjectURL(latestDownloadUrl);
                        }}
                        latestDownloadUrl = window.URL.createObjectURL(blob);
                        triggerReportDownload();
                        window.setTimeout(() => {{
                            showCompletionState(filename);
                            isSubmitting = false;
                            submitButtons.forEach((button) => button.disabled = false);
                        }}, 500);
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
                    form.addEventListener("submit", function(event) {{
                        if (!validateStep(currentStep)) {{
                            event.preventDefault();
                            return;
                        }}
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
                showStep(1);
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

    yes_no_html = "\n".join(
        f"""
        <div class="field yes-no-field">
            <label for="{field_name}">{label}</label>
            <select id="{field_name}" name="{field_name}" data-summary-target data-stage-group="{((index - 1) // 3) + 1}" required>
                <option value="">Select…</option>
                <option value="Yes">Yes</option>
                <option value="No">No</option>
            </select>
        </div>
        """
        for index, (field_name, label) in enumerate(YES_NO_FIELDS, start=1)
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
                <div class="progress-title">Assessment progress</div>
                <div class="progress-percent" id="progressPercent">0% complete</div>
            </div>
            <div class="track"><div class="track-fill" id="progressFill"></div></div>

            <div class="stepper">
                <div class="step active">
                    <div class="step-dot">01</div>
                    <div class="step-copy">
                        <div class="step-kicker">Stage 1</div>
                        <div class="step-title">Business Context</div>
                    </div>
                </div>
                <div class="step">
                    <div class="step-dot">02</div>
                    <div class="step-copy">
                        <div class="step-kicker">Stage 2</div>
                        <div class="step-title">Hiring Performance</div>
                    </div>
                </div>
                <div class="step">
                    <div class="step-dot">03</div>
                    <div class="step-copy">
                        <div class="step-kicker">Stage 3</div>
                        <div class="step-title">Process Control</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="app-grid">
        <form id="auditForm" method="post" action="/generate">
            <div class="panel">
                <section class="stage active" data-step="1">
                    <div class="section-head">
                        <div>
                            <div class="section-kicker">Stage 1: Business Context</div>
                            <h2 class="section-title">Set the business context for the assessment.</h2>
                            <p class="section-copy">
                                Capture the organisation profile, hiring demand and roles that frame the audit.
                            </p>
                        </div>
                        <div class="section-aside">
                            Stakeholder details<br>
                            Organisation profile<br>
                            Hiring demand
                        </div>
                    </div>

                    <div class="stage-indicators">
                        <div class="stage-indicator"><span class="stage-indicator-label">Stage</span><span data-stage-indicator>Stage 1 of 3</span></div>
                        <div class="stage-indicator"><span class="stage-indicator-label">Step</span><span data-step-indicator>Step 1 of 4</span></div>
                    </div>

                    <div class="grid">
                        <div class="field">
                            <label for="company_name">What is the name of your company?</label>
                            <input id="company_name" name="company_name" data-summary-target data-stage-group="1" required>
                        </div>

                        <div class="field">
                            <label for="contact_name">What is the name of the person completing this audit?</label>
                            <input id="contact_name" name="contact_name" autocomplete="name" data-summary-target data-stage-group="1" required>
                        </div>

                        <div class="field">
                            <label for="job_title">What is their job title?</label>
                            <input id="job_title" name="job_title" autocomplete="organization-title" data-summary-target data-stage-group="1" required>
                        </div>

                        <div class="field">
                            <label for="phone_number">What is the best phone number to use?</label>
                            <input id="phone_number" name="phone_number" type="tel" autocomplete="tel" inputmode="tel" pattern="[0-9+()\\-\\s]{{7,}}" title="Enter a valid phone number." data-summary-target data-stage-group="2" required>
                        </div>

                        <div class="field">
                            <label for="email_address">What is the best email address to use?</label>
                            <input id="email_address" name="email_address" type="email" autocomplete="email" data-summary-target data-stage-group="2" required>
                        </div>

                        <div class="field">
                            <label for="sector">Which sector does your business operate in?</label>
                            <select id="sector" name="sector" data-summary-target data-stage-group="3" required>
                                <option value="">Select…</option>
                                {sector_options}
                            </select>
                        </div>

                        <div class="field">
                            <label for="location">Where is the business based?</label>
                            <input id="location" name="location" autocomplete="address-level2" data-summary-target data-stage-group="3" required>
                        </div>

                        <div class="field has-suffix">
                            <label for="headcount">How many employees does the business have?</label>
                            <div class="input-wrap">
                                <input id="headcount" name="headcount" inputmode="numeric" pattern="[0-9, ]+" title="Use numbers only." data-summary-target data-stage-group="3" required>
                                <span class="suffix">employees</span>
                            </div>
                        </div>

                        <div class="field has-suffix">
                            <label for="annual_hiring_volume">How many hires do you typically make each year?</label>
                            <div class="input-wrap">
                                <input id="annual_hiring_volume" name="annual_hiring_volume" inputmode="numeric" pattern="[0-9, ]+" title="Use numbers only." data-summary-target data-stage-group="3" required>
                                <span class="suffix">hires</span>
                            </div>
                        </div>

                        <div class="field full">
                            <label for="key_roles_hired">Which roles or job titles do you hire for most often?</label>
                            <input id="key_roles_hired" name="key_roles_hired" placeholder="e.g. Sales Managers, Service Engineers, Finance Business Partners" data-summary-target data-stage-group="4" required>
                            <div class="hint">Use representative job titles, not a numeric count.</div>
                        </div>

                        <div class="field full">
                            <label for="office_address">What is the office address?</label>
                            <textarea id="office_address" name="office_address" rows="3" autocomplete="street-address" data-summary-target data-stage-group="4" required></textarea>
                        </div>
                    </div>

                    <div class="note">
                        <strong>Use current-state information.</strong> The closer this is to live hiring conditions, the more reliable the report will be.
                    </div>
                </section>

                <section class="stage" data-step="2">
                    <div class="section-head">
                        <div>
                            <div class="section-kicker">Stage 2: Hiring Performance</div>
                            <h2 class="section-title">Capture the metrics that show where hiring is under pressure.</h2>
                            <p class="section-copy">
                                These measures show pace, conversion, decision quality and early retention performance.
                            </p>
                        </div>
                        <div class="section-aside">
                            Time to hire<br>
                            Conversion performance<br>
                            Retention indicators
                        </div>
                    </div>

                    <div class="stage-indicators">
                        <div class="stage-indicator"><span class="stage-indicator-label">Stage</span><span data-stage-indicator>Stage 2 of 3</span></div>
                        <div class="stage-indicator"><span class="stage-indicator-label">Step</span><span data-step-indicator>Step 1 of 4</span></div>
                    </div>

                    <div class="grid">
                        <div class="field has-suffix">
                            <label for="time_to_hire">What is your average time to hire?</label>
                            <div class="input-wrap">
                                <input id="time_to_hire" name="time_to_hire" placeholder="e.g. 42" data-summary-target data-stage-group="1" required>
                                <span class="suffix">days</span>
                            </div>
                        </div>

                        <div class="field has-suffix">
                            <label for="applications_per_role">How many applications do you receive per role on average?</label>
                            <div class="input-wrap">
                                <input id="applications_per_role" name="applications_per_role" placeholder="e.g. 36" inputmode="decimal" pattern="[0-9., ]+" title="Use numbers only." data-summary-target data-stage-group="1" required>
                                <span class="suffix">applications</span>
                            </div>
                        </div>

                        <div class="field has-suffix">
                            <label for="offer_acceptance">What percentage of offers are accepted?</label>
                            <div class="input-wrap">
                                <input id="offer_acceptance" name="offer_acceptance" placeholder="e.g. 72" inputmode="decimal" pattern="[0-9., ]+" title="Use numbers only." data-summary-target data-stage-group="2" required>
                                <span class="suffix">%</span>
                            </div>
                        </div>

                        <div class="field has-suffix">
                            <label for="first_year_attrition">What percentage of hires leave within the first year?</label>
                            <div class="input-wrap">
                                <input id="first_year_attrition" name="first_year_attrition" placeholder="e.g. 18" inputmode="decimal" pattern="[0-9., ]+" title="Use numbers only." data-summary-target data-stage-group="2" required>
                                <span class="suffix">%</span>
                            </div>
                        </div>

                        <div class="field has-suffix">
                            <label for="interview_stages">How many interview stages are typically used?</label>
                            <div class="input-wrap">
                                <input id="interview_stages" name="interview_stages" placeholder="e.g. 2" inputmode="numeric" pattern="[0-9 ]+" title="Use numbers only." data-summary-target data-stage-group="3" required>
                                <span class="suffix">stages</span>
                            </div>
                        </div>

                        <div class="field has-suffix">
                            <label for="interview_feedback_time">How long does interview feedback usually take?</label>
                            <div class="input-wrap">
                                <input id="interview_feedback_time" name="interview_feedback_time" placeholder="e.g. 2" data-summary-target data-stage-group="3" required>
                                <span class="suffix">days</span>
                            </div>
                        </div>

                        <div class="field has-suffix">
                            <label for="candidates_reaching_interview">How many candidates typically reach interview for each role?</label>
                            <div class="input-wrap">
                                <input id="candidates_reaching_interview" name="candidates_reaching_interview" placeholder="e.g. 5" inputmode="decimal" pattern="[0-9., ]+" title="Use numbers only." data-summary-target data-stage-group="4" required>
                                <span class="suffix">candidates</span>
                            </div>
                        </div>
                    </div>

                    <div class="note">
                        These figures are used to identify bottlenecks, conversion loss and retention pressure.
                    </div>
                </section>

                <section class="stage" data-step="3">
                    <div class="section-head">
                        <div>
                            <div class="section-kicker">Stage 3: Process Control</div>
                            <h2 class="section-title">Assess how consistently the hiring process is controlled.</h2>
                            <p class="section-copy">
                                These controls show where governance, ownership and standardisation are strong or weak.
                            </p>
                        </div>
                        <div class="section-aside">
                            Governance<br>
                            Ownership<br>
                            Standardisation
                        </div>
                    </div>

                    <div class="stage-indicators">
                        <div class="stage-indicator"><span class="stage-indicator-label">Stage</span><span data-stage-indicator>Stage 3 of 3</span></div>
                        <div class="stage-indicator"><span class="stage-indicator-label">Step</span><span data-step-indicator>Step 1 of 4</span></div>
                    </div>

                    <div class="grid">
                        {yes_no_html}
                    </div>

                    <div class="note">
                        Answer based on what is used consistently in day-to-day hiring.
                    </div>
                </section>

                <div class="footer-bar">
                    <div class="footer-copy">
                        Each stage feeds directly into the scorecard, benchmark comparison and final report.
                    </div>
                    <div class="button-row">
                        <button class="button button-ghost" type="button" data-prev-step>Back</button>
                        <button class="button button-secondary" type="button" data-next-step>Next Stage</button>
                        <button class="button button-primary" type="submit">Generate Report</button>
                    </div>
                </div>
            </div>
        </form>

        <aside class="sidebar">
            <div class="sidebar-card brand-card">
                <div class="sidebar-mark">B&amp;M</div>
                <div class="sidebar-kicker">Bradford & Marsh</div>
                <h3 class="sidebar-title">Structured review of recruitment performance and control</h3>
                <p>
                    This assessment reviews how recruitment is being run in practice.
                </p>
                <div class="sidebar-rule"></div>
                <p class="sidebar-copy">The output is a fixed-layout report showing where hiring is working, where control is weak and what should be addressed first.</p>
            </div>

            <div class="sidebar-card">
                <div class="sidebar-kicker">Report preview</div>
                <h3 class="sidebar-title">What leadership will receive</h3>
                <div class="preview-list">
                    <div class="preview-row"><div class="preview-index">01</div><div class="preview-copy"><strong>Executive overview</strong><span>A concise written summary of overall recruitment performance, pressure points and leadership implications.</span></div></div>
                    <div class="preview-row"><div class="preview-index">02</div><div class="preview-copy"><strong>Scorecard and charts</strong><span>Twelve scored areas, overall rating, benchmark visuals and section-by-section performance profile.</span></div></div>
                    <div class="preview-row"><div class="preview-index">03</div><div class="preview-copy"><strong>Priority actions</strong><span>Commercially relevant recommendations showing what should be fixed first and why.</span></div></div>
                </div>
            </div>

            <div class="sidebar-card">
                <div class="sidebar-kicker">Assessment summary</div>
                <h3 class="sidebar-title">Current operating profile</h3>
                <p id="stageReadiness">Business Context: 0% complete</p>

                <div class="summary-list">
                    <div class="summary-item"><div class="summary-label">Company</div><div class="summary-value" id="summaryCompany">Pending</div></div>
                    <div class="summary-item"><div class="summary-label">Contact</div><div class="summary-value" id="summaryContact">Pending</div></div>
                    <div class="summary-item"><div class="summary-label">Sector</div><div class="summary-value" id="summarySector">Pending</div></div>
                    <div class="summary-item"><div class="summary-label">Location</div><div class="summary-value" id="summaryLocation">Pending</div></div>
                    <div class="summary-item"><div class="summary-label">Hiring demand</div><div class="summary-value" id="summaryHiring">Pending</div></div>
                    <div class="summary-item"><div class="summary-label">Key roles / job titles</div><div class="summary-value" id="summaryRoles">Pending</div></div>
                </div>

                <div class="metric-chip-row">
                    <div class="chip"><span class="chip-dot"></span> Multi-factor scoring</div>
                    <div class="chip"><span class="chip-dot"></span> Benchmark comparison</div>
                    <div class="chip" id="disciplineChip"><span class="chip-dot"></span> Controls pending</div>
                </div>

                <div class="source-note">
                    Benchmark comparisons are drawn from UK recruitment benchmark data and applied where the selected sector and submitted metrics provide a relevant basis for comparison.
                </div>
            </div>

            <div class="sidebar-card">
                <div class="sidebar-kicker">Completion status</div>
                <h3 class="sidebar-title">Assessment progress by stage</h3>
                <div class="capture-list">
                    <div class="capture-item" data-capture-step="1"><strong>Business context</strong><span class="capture-state">0% ready</span></div>
                    <div class="capture-item" data-capture-step="2"><strong>Hiring performance</strong><span class="capture-state">0% ready</span></div>
                    <div class="capture-item" data-capture-step="3"><strong>Process control</strong><span class="capture-state">0% ready</span></div>
                </div>
            </div>

            <div class="sidebar-card">
                <div class="sidebar-kicker">Benchmark basis</div>
                <h3 class="sidebar-title">How the comparison is used</h3>
                <div class="cred-row"><div class="cred-label">Coverage</div><div class="cred-value">Sector-led UK reference points</div></div>
                <div class="cred-row"><div class="cred-label">Used for</div><div class="cred-value">Time to hire, applications, offer acceptance and attrition</div></div>
                <div class="cred-row"><div class="cred-label">Purpose</div><div class="cred-value">Show where performance is aligned, behind or ahead</div></div>
            </div>

            <div class="sidebar-card">
                <div class="sidebar-kicker">What the audit delivers</div>
                <h3 class="sidebar-title">Included in the final report</h3>
                <div class="trust-grid">
                    <div class="trust-row"><div class="trust-mark">✓</div><div>Section-by-section scoring across strategy, delivery performance and process control.</div></div>
                    <div class="trust-row"><div class="trust-mark">✓</div><div>Benchmark comparison, chart output and written interpretation of submitted performance data.</div></div>
                    <div class="trust-row"><div class="trust-mark">✓</div><div>Priority actions designed to improve hiring speed, decision quality, process consistency and retention outcomes.</div></div>
                </div>
            </div>
        </aside>
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

        section_chart = create_section_score_chart(data["company_name"], data["section_scores"])
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
