from flask import Flask, request, send_file
from openai import OpenAI
import pandas as pd
import os

from recruitment_audit import (
    get_api_key,
    load_benchmarks,
    build_benchmark_summary,
    auto_score_sections,
    generate_report_json,
    save_word_report,
    create_section_score_chart,
    create_overall_score_chart,
    create_benchmark_chart,
)

app = Flask(__name__)

client = OpenAI(api_key=get_api_key())


BENCHMARK_FILE = "uk_recruitment_benchmark_framework.xlsx"


YES_NO_FIELDS = [
("has_hiring_plan","Formal recruitment or workforce plan"),
("tracks_metrics","Regular recruitment KPI tracking"),
("has_employer_brand","Defined employer brand / EVP"),
("standardised_job_specs","Standardised job adverts and job descriptions"),
("multi_channel_sourcing","Consistent use of multiple sourcing channels"),
("structured_screening","Consistent screening process"),
("structured_interviews","Structured interviews or scorecards"),
("fast_offer_process","Fast and consistent offer approval process"),
("formal_onboarding","Documented onboarding process"),
("collects_candidate_feedback","Candidate experience feedback collection"),
("named_process_owner","Clearly named recruitment process owner"),
("hiring_manager_training","Hiring manager interview / hiring training"),
]


def get_sector_options():
    try:
        df = pd.read_excel(BENCHMARK_FILE)
        return sorted(df["sector"].dropna().unique())
    except:
        return [
            "Technology",
            "Finance",
            "Professional Services",
            "Manufacturing",
            "Retail",
            "Healthcare",
            "Construction",
            "Education",
            "Logistics",
            "Energy",
        ]


def render_page(title, body):

    return f"""
<!doctype html>
<html>
<head>
<title>{title}</title>

<style>

body {{
font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
background:#f4f6fb;
margin:0;
}}

.container {{
max-width:1100px;
margin:auto;
padding:40px;
}}

.header {{
margin-bottom:40px;
}}

.brand {{
font-size:18px;
font-weight:700;
letter-spacing:1px;
}}

.subtitle {{
color:#666;
margin-top:6px;
}}

.hero {{
background:#0f172a;
color:white;
padding:40px;
border-radius:16px;
margin-bottom:40px;
}}

.hero h1 {{
margin:0 0 10px 0;
font-size:38px;
}}

.section {{
background:white;
padding:30px;
border-radius:14px;
margin-bottom:24px;
}}

.section h2 {{
margin-top:0;
}}

.grid {{
display:grid;
grid-template-columns:1fr 1fr;
gap:20px;
}}

input,select {{
width:100%;
padding:12px;
border-radius:8px;
border:1px solid #d1d5db;
}}

button {{
background:#111827;
color:white;
padding:16px 26px;
border-radius:10px;
border:none;
font-size:16px;
font-weight:700;
cursor:pointer;
}}

button:hover {{
background:#000;
}}

.loading {{
display:none;
position:fixed;
top:0;
left:0;
right:0;
bottom:0;
background:rgba(255,255,255,0.9);
align-items:center;
justify-content:center;
font-size:22px;
}}

</style>

</head>

<body>

<div class="container">

{body}

</div>

<div id="loading" class="loading">
Generating recruitment audit...
</div>

<script>
document.querySelector("form")?.addEventListener("submit",function(){{
document.getElementById("loading").style.display="flex";
}});
</script>

</body>
</html>
"""


@app.route("/")
def form():

    sectors = get_sector_options()

    sector_options = "".join(
        f'<option value="{s}">{s}</option>' for s in sectors
    )

    yes_no_html = ""

    for field,label in YES_NO_FIELDS:

        yes_no_html += f"""
<div>
<label>{label}</label>
<select name="{field}" required>
<option value="">Select</option>
<option value="Yes">Yes</option>
<option value="No">No</option>
</select>
</div>
"""

    body = f"""

<div class="header">
<div class="brand">Bradford & Marsh Consulting</div>
<div class="subtitle">Recruitment Advisory Platform</div>
</div>

<div class="hero">

<h1>Recruitment Operating Model Audit</h1>

<p>
Evaluate recruitment performance, funnel efficiency,
interview discipline and early-tenure risk.
</p>

</div>


<form method="post" action="/generate">

<div class="section">

<h2>Organisation Context</h2>

<div class="grid">

<div>
<label>Company name</label>
<input name="company_name" required>
</div>

<div>
<label>Sector</label>
<select name="sector" required>
<option value="">Select</option>
{sector_options}
</select>
</div>

<div>
<label>Location</label>
<input name="location" required>
</div>

<div>
<label>Number of employees</label>
<input name="headcount" required>
</div>

<div>
<label>Annual hiring volume</label>
<input name="annual_hiring_volume" required>
</div>

<div>
<label>Key roles hired</label>
<input name="key_roles_hired" required>
</div>

</div>

</div>



<div class="section">

<h2>Recruitment Performance</h2>

<div class="grid">

<div>
<label>Average time to hire (days)</label>
<input name="time_to_hire" required>
</div>

<div>
<label>Applications per role</label>
<input name="applications_per_role" required>
</div>

<div>
<label>Offer acceptance rate (%)</label>
<input name="offer_acceptance" required>
</div>

<div>
<label>First year attrition (%)</label>
<input name="first_year_attrition" required>
</div>

<div>
<label>Interview stages</label>
<input name="interview_stages" required>
</div>

<div>
<label>Interview feedback time (days)</label>
<input name="interview_feedback_time" required>
</div>

<div>
<label>Candidates reaching interview</label>
<input name="candidates_reaching_interview" required>
</div>

</div>

</div>



<div class="section">

<h2>Process Maturity</h2>

<div class="grid">

{yes_no_html}

</div>

</div>



<div style="text-align:center;margin-top:30px;">

<button type="submit">
Generate Recruitment Audit
</button>

</div>

</form>

"""

    return render_page("Recruitment Audit", body)


@app.route("/generate", methods=["POST"])
def generate():

    data = dict(request.form)

    data["process_flags"] = {
        field: data.get(field) == "Yes"
        for field,_ in YES_NO_FIELDS
    }

    benchmark = load_benchmarks(data["sector"])

    benchmark_summary = build_benchmark_summary({}, benchmark)

    scores, notes = auto_score_sections(data, benchmark)

    data["section_scores"] = scores
    data["section_notes"] = notes

    data["total_score"] = sum(scores)
    data["percentage_score"] = round((data["total_score"]/120)*100,1)

    report = generate_report_json(client,data,benchmark_summary)

    section_chart = create_section_score_chart(data["company_name"],scores)

    overall_chart = create_overall_score_chart(data["company_name"],data["total_score"])

    benchmark_chart = create_benchmark_chart(data["company_name"],{},benchmark)

    word_path = save_word_report(
        data,
        report,
        benchmark_summary,
        section_chart,
        overall_chart,
        benchmark_chart,
    )

    return send_file(
        word_path,
        as_attachment=True,
        download_name=f"{data['company_name']}_recruitment_audit.docx"
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
