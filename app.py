from flask import Flask, request
from openai import OpenAI
import traceback

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


def yes_no_to_bool(value):
    return str(value).strip().lower() == "yes"


@app.route("/")
def form():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Recruitment Audit Diagnostic</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f4f6fb;
            margin: 0;
            padding: 40px;
            color: #111827;
        }
        .container {
            max-width: 950px;
            margin: auto;
            background: white;
            padding: 50px;
            border-radius: 12px;
            box-shadow: 0 15px 40px rgba(0,0,0,0.08);
        }
        .header {
            margin-bottom: 40px;
        }
        .header h1 {
            margin: 0;
            font-size: 30px;
        }
        .header p {
            margin-top: 8px;
            color: #6b7280;
        }
        .section {
            margin-top: 35px;
            padding-top: 10px;
            border-top: 1px solid #e5e7eb;
        }
        .section h2 {
            margin-bottom: 18px;
            font-size: 20px;
        }
        label {
            font-size: 14px;
            font-weight: 600;
        }
        input, select {
            width: 100%;
            padding: 12px;
            margin-top: 6px;
            margin-bottom: 16px;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            font-size: 14px;
            box-sizing: border-box;
        }
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        button {
            background: #111827;
            color: white;
            padding: 16px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            width: 100%;
            margin-top: 30px;
        }
        button:hover {
            background: #000;
        }
        .footer {
            margin-top: 30px;
            font-size: 12px;
            color: #6b7280;
            text-align: center;
        }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>Recruitment Audit Diagnostic</h1>
        <p>Bradford & Marsh Consulting</p>
    </div>

    <form method="post" action="/generate">

        <div class="section">
            <h2>Company profile</h2>
            <div class="grid">
                <div>
                    <label>Company name</label>
                    <input name="company_name">
                </div>
                <div>
                    <label>Sector</label>
                    <input name="sector">
                </div>
                <div>
                    <label>Location</label>
                    <input name="location">
                </div>
                <div>
                    <label>Headcount</label>
                    <input name="headcount">
                </div>
                <div>
                    <label>Annual hiring volume</label>
                    <input name="annual_hiring_volume">
                </div>
                <div>
                    <label>Key roles hired</label>
                    <input name="key_roles_hired">
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Recruitment metrics</h2>
            <div class="grid">
                <div>
                    <label>Average time to hire</label>
                    <input name="time_to_hire">
                </div>
                <div>
                    <label>Applications per role</label>
                    <input name="applications_per_role">
                </div>
                <div>
                    <label>Offer acceptance rate</label>
                    <input name="offer_acceptance">
                </div>
                <div>
                    <label>First-year attrition</label>
                    <input name="first_year_attrition">
                </div>
                <div>
                    <label>Interview stages</label>
                    <input name="interview_stages">
                </div>
                <div>
                    <label>Interview feedback time</label>
                    <input name="interview_feedback_time">
                </div>
                <div>
                    <label>Candidates reaching interview</label>
                    <input name="candidates_reaching_interview">
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Process maturity</h2>
            <div class="grid">
                <div>
                    <label>Formal hiring plan</label>
                    <select name="has_hiring_plan"><option>Yes</option><option>No</option></select>
                </div>
                <div>
                    <label>Recruitment KPIs tracked</label>
                    <select name="tracks_metrics"><option>Yes</option><option>No</option></select>
                </div>
                <div>
                    <label>Defined employer brand</label>
                    <select name="has_employer_brand"><option>Yes</option><option>No</option></select>
                </div>
                <div>
                    <label>Standardised job specifications</label>
                    <select name="standardised_job_specs"><option>Yes</option><option>No</option></select>
                </div>
                <div>
                    <label>Multiple sourcing channels</label>
                    <select name="multi_channel_sourcing"><option>Yes</option><option>No</option></select>
                </div>
                <div>
                    <label>Structured screening</label>
                    <select name="structured_screening"><option>Yes</option><option>No</option></select>
                </div>
                <div>
                    <label>Structured interviews</label>
                    <select name="structured_interviews"><option>Yes</option><option>No</option></select>
                </div>
                <div>
                    <label>Fast offer decision process</label>
                    <select name="fast_offer_process"><option>Yes</option><option>No</option></select>
                </div>
                <div>
                    <label>Formal onboarding</label>
                    <select name="formal_onboarding"><option>Yes</option><option>No</option></select>
                </div>
                <div>
                    <label>Candidate feedback collected</label>
                    <select name="collects_candidate_feedback"><option>Yes</option><option>No</option></select>
                </div>
                <div>
                    <label>Recruitment process owner</label>
                    <select name="named_process_owner"><option>Yes</option><option>No</option></select>
                </div>
                <div>
                    <label>Hiring manager interview training</label>
                    <select name="hiring_manager_training"><option>Yes</option><option>No</option></select>
                </div>
            </div>
        </div>

        <button type="submit">Generate Recruitment Audit</button>
    </form>

    <div class="footer">
        Recruitment Audit Diagnostic — Bradford & Marsh Consulting
    </div>
</div>
</body>
</html>
"""


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

        return f"""
        <h1>Audit Complete</h1>
        <p><strong>Company:</strong> {data['company_name']}</p>
        <p><strong>Score:</strong> {data['total_score']} / 120 ({data['percentage_score']}%)</p>
        <p><strong>Saved to:</strong> {word_path}</p>
        <p><a href="/">Run another audit</a></p>
        """

    except Exception:
        return f"""
        <h1>Report generation failed</h1>
        <pre>{traceback.format_exc()}</pre>
        """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
