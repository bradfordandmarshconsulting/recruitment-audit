
from __future__ import annotations

import getpass
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from openai import OpenAI


SYSTEM_PROMPT = """
You are a senior recruitment consultant producing a professional recruitment audit on behalf of Bradford & Marsh Consulting.

Write like an experienced consultant. The report must read like human advisory work, not generic AI copy.

Audit these 12 areas:
1. Recruitment strategy and workforce planning
2. Performance metrics and funnel conversion
3. Employer brand and market perception
4. Job adverts and job specifications
5. Sourcing and advertising process
6. Application handling and screening
7. Interview process quality
8. Decision making and offer process
9. Onboarding and early retention
10. Staff turnover risks
11. Candidate experience
12. Process ownership and accountability

For each section provide exactly these headings:
Score: X/10
Current State
Key Risks
Commercial Impact
Quick Wins
Medium Term Improvements

Then include exactly these final sections:
Executive Summary
Top 5 Strengths
Top 5 Problems
30 Day Plan
60 Day Plan
90 Day Plan
Overall Score
Final Verdict

Additional rules:
- Be commercially sharp and specific.
- Tie recommendations to likely business outcomes.
- Keep score rationale internally consistent.
- Use concise bullet points where helpful.
""".strip()

API_KEY_FILE = Path.home() / ".openai_api_key.txt"
DEFAULT_BENCHMARK_FILE = Path.cwd() / "uk_recruitment_benchmark_framework.xlsx"
DEFAULT_OUTPUT_DIR = Path.cwd() / "audit_outputs"

NAVY = RGBColor(15, 23, 42)
SLATE = RGBColor(51, 65, 85)
MUTED = RGBColor(100, 116, 139)
BORDER = "D7DEE7"
SOFT_FILL = "F8FAFC"
RED = "#B91C1C"
AMBER = "#D97706"
GREEN = "#15803D"


@dataclass
class ClientProfile:
    company: str
    sector: str
    location: str
    employees: str
    annual_hires: str
    key_roles: str
    time_to_hire: str
    applications_per_role: str
    offer_acceptance_rate: str
    first_year_attrition: str

    def as_prompt_block(self) -> str:
        return "\n".join([
            f"Company name: {self.company}",
            f"Industry / sector: {self.sector}",
            f"Location: {self.location}",
            f"Number of employees: {self.employees}",
            f"Annual Hiring Volume: {self.annual_hires}",
            f"Key Roles Hired: {self.key_roles}",
            f"Average time to hire: {self.time_to_hire}",
            f"Applications per role: {self.applications_per_role}",
            f"Offer acceptance rate: {self.offer_acceptance_rate}",
            f"First year attrition: {self.first_year_attrition}",
        ])


def clean_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_") or "recruitment_audit"


def normalise_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value)).lower().strip()


def parse_numeric_value(value: str | None) -> float | None:
    if not value:
        return None
    numbers = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", value)]
    if not numbers:
        return None
    if len(numbers) >= 2:
        return sum(numbers[:2]) / 2
    return numbers[0]


def prompt(question: str, example: str | None = None, required: bool = True) -> str:
    label = f"{question}"
    if example:
        label += f" [{example}]"
    label += ": "
    while True:
        value = input(label).strip()
        if value or not required:
            return value
        print("Please enter a value.")


def print_banner() -> None:
    print("\n" + "=" * 74)
    print("Bradford & Marsh Consulting | Recruitment Audit Generator")
    print("=" * 74)
    print("Provide the client profile below to generate a premium audit pack.\n")


def get_api_key() -> str:
    env_key = os.environ.get("OPENAI_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip()

    if API_KEY_FILE.exists():
        saved = API_KEY_FILE.read_text(encoding="utf-8").strip()
        if saved:
            return saved

    print("OpenAI API key not found.")
    key = getpass.getpass("Paste your API key: ").strip()
    if not key:
        raise RuntimeError("No API key provided.")

    save_choice = input("Save key locally for future runs? (y/n): ").strip().lower()
    if save_choice == "y":
        API_KEY_FILE.write_text(key, encoding="utf-8")
    return key


def load_benchmarks(sector: str, benchmark_file: Path = DEFAULT_BENCHMARK_FILE):
    if not benchmark_file.exists():
        return None

    df = pd.read_excel(benchmark_file, sheet_name="Benchmarks")
    if "sector" not in df.columns:
        return None

    df["_sector"] = df["sector"].astype(str).map(normalise_text)
    match = df[df["_sector"] == normalise_text(sector)]
    return None if match.empty else match.iloc[0]


def extract_metrics(client_data: str):
    patterns = {
        "time_to_hire": r"Average time to hire: (.*)",
        "applications": r"Applications per role: (.*)",
        "offer_acceptance": r"Offer acceptance rate: (.*)",
        "attrition": r"First year attrition: (.*)",
    }
    metrics = {}
    for key, pattern in patterns.items():
        m = re.search(pattern, client_data)
        metrics[key] = parse_numeric_value(m.group(1)) if m else None

    sector_match = re.search(r"Industry / sector: (.*)", client_data)
    sector = sector_match.group(1).strip() if sector_match else "Unknown"
    return sector, metrics


def build_benchmark_summary(sector: str, metrics: dict, benchmark) -> str:
    if benchmark is None:
        return "No benchmark data available."

    lines = [f"Sector benchmark: {benchmark.get('sector', sector)}"]
    mapping = {
        "time_to_hire": "avg_time_to_hire_days",
        "applications": "avg_applications_per_role",
        "offer_acceptance": "avg_offer_acceptance_pct",
        "attrition": "avg_attrition_pct",
    }

    for metric, column in mapping.items():
        company_value = metrics.get(metric)
        if company_value is None or column not in benchmark.index:
            continue
        sector_value = benchmark[column]
        if pd.isna(sector_value):
            continue
        diff = company_value - float(sector_value)
        lines.append(
            f"{metric}: client {company_value} vs sector {float(sector_value):.1f} "
            f"(difference {diff:+.1f})"
        )

    return "\n".join(lines)


def extract_scores(report: str) -> dict[str, float]:
    scores: dict[str, float] = {}
    current_section = None

    for line in report.splitlines():
        heading = re.match(r"^\s*\d+[\.\)]\s+(.*)", line)
        if heading:
            current_section = heading.group(1).strip()
            continue

        score_match = re.search(r"Score[: ]+([0-9]+(?:\.\d+)?)\/10", line)
        if score_match and current_section:
            scores[current_section] = float(score_match.group(1))

    return scores


def calculate_overall_score(scores: dict[str, float]) -> float | None:
    if not scores:
        return None
    return round((sum(scores.values()) / len(scores)) * 10, 1)


def score_colour(value: float, scale: float) -> str:
    pct = (value / scale) * 100
    if pct <= 40:
        return RED
    if pct <= 70:
        return AMBER
    return GREEN


def create_score_chart(company: str, scores: dict[str, float], output_dir: Path) -> Path | None:
    if not scores:
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    labels = list(scores.keys())
    values = list(scores.values())
    y_positions = range(len(labels))
    colours = [score_colour(v, 10) for v in values]

    fig, ax = plt.subplots(figsize=(11, 6.8))
    ax.barh(list(y_positions), values, color=colours, height=0.62)
    ax.set_yticks(list(y_positions))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlim(0, 10.5)
    ax.set_xlabel("Score / 10")
    ax.set_title("Audit Category Scores", fontsize=14, weight="bold", pad=14)
    ax.grid(axis="x", alpha=0.18)

    for i, value in enumerate(values):
        ax.text(value + 0.1, i, f"{value:.1f}/10", va="center", fontsize=9)

    plt.tight_layout()
    path = output_dir / f"{clean_filename(company)}_score_chart.png"
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()
    return path


def create_overall_chart(company: str, overall: float | None, output_dir: Path) -> Path | None:
    if overall is None:
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.5, 1.8))
    ax.barh(["Overall"], [overall], color=score_colour(overall, 100), height=0.5)
    ax.barh(["Overall"], [100 - overall], left=[overall], color="#E5E7EB", height=0.5)
    ax.set_xlim(0, 100)
    ax.set_title("Overall Audit Score", fontsize=13, weight="bold", pad=12)
    ax.grid(axis="x", alpha=0.15)
    ax.text(min(overall + 1.2, 95), 0, f"{overall:.1f}/100", va="center", fontsize=10)

    plt.tight_layout()
    path = output_dir / f"{clean_filename(company)}_overall_score_chart.png"
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()
    return path


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def add_horizontal_rule(paragraph) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    border = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "10")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), BORDER)
    border.append(bottom)
    p_pr.append(border)


def style_document(doc: Document) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = "Aptos"
    normal.font.size = Pt(10.5)

    for style_name, size, colour in [
        ("Title", 24, NAVY),
        ("Heading 1", 16, NAVY),
        ("Heading 2", 13, SLATE),
        ("Heading 3", 11, SLATE),
    ]:
        style = doc.styles[style_name]
        style.font.name = "Aptos"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = colour


def add_cover_page(doc: Document, company: str, sector: str, location: str) -> None:
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("Bradford & Marsh Consulting")
    run.bold = True
    run.font.size = Pt(24)
    run.font.color.rgb = NAVY

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run("Recruitment Audit Report")
    run.bold = True
    run.font.size = Pt(18)
    run.font.color.rgb = SLATE

    doc.add_paragraph("")
    meta = doc.add_table(rows=3, cols=2)
    meta.style = "Table Grid"
    rows = [("Client", company), ("Sector", sector), ("Location", location)]
    for i, (left, right) in enumerate(rows):
        meta.cell(i, 0).text = left
        meta.cell(i, 1).text = right
        meta.cell(i, 0).vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        meta.cell(i, 1).vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_shading(meta.cell(i, 0), "EEF2F7")
        for p in meta.cell(i, 0).paragraphs:
            for r in p.runs:
                r.bold = True

    doc.add_paragraph("")
    note = doc.add_paragraph()
    note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = note.add_run("Confidential advisory report")
    run.italic = True
    run.font.color.rgb = MUTED

    doc.add_section(WD_SECTION.NEW_PAGE)


def add_snapshot_table(doc: Document, profile: ClientProfile, overall: float | None) -> None:
    doc.add_heading("Client Snapshot", level=1)

    table = doc.add_table(rows=0, cols=2)
    table.style = "Table Grid"

    rows = [
        ("Company", profile.company),
        ("Sector", profile.sector),
        ("Location", profile.location),
        ("Employees", profile.employees),
        ("Annual hires", profile.annual_hires),
        ("Key roles", profile.key_roles),
        ("Average time to hire", profile.time_to_hire),
        ("Applications per role", profile.applications_per_role),
        ("Offer acceptance rate", profile.offer_acceptance_rate),
        ("First year attrition", profile.first_year_attrition),
    ]
    if overall is not None:
        rows.insert(1, ("Overall score", f"{overall:.1f}/100"))

    for left, right in rows:
        row_cells = table.add_row().cells
        row_cells[0].text = left
        row_cells[1].text = right
        set_cell_shading(row_cells[0], SOFT_FILL)
        for p in row_cells[0].paragraphs:
            for r in p.runs:
                r.bold = True

    doc.add_paragraph("")


def add_kpi_tiles(doc: Document, scores: dict[str, float]) -> None:
    if not scores:
        return

    best = max(scores.items(), key=lambda kv: kv[1])
    worst = min(scores.items(), key=lambda kv: kv[1])
    avg = sum(scores.values()) / len(scores)

    doc.add_heading("Score Highlights", level=1)
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    headers = [("Highest scoring area", f"{best[0]}\n{best[1]:.1f}/10"),
               ("Lowest scoring area", f"{worst[0]}\n{worst[1]:.1f}/10"),
               ("Average category score", f"{avg:.1f}/10")]
    for idx, (label, value) in enumerate(headers):
        cell = table.rows[0].cells[idx]
        cell.text = f"{label}\n{value}"
        set_cell_shading(cell, "F8FAFC")
    doc.add_paragraph("")


def add_report_body(doc: Document, report: str) -> None:
    doc.add_heading("Detailed Audit", level=1)
    important = re.compile(
        r"^(Score|Current State|Key Risks|Commercial Impact|Quick Wins|Medium Term Improvements|"
        r"Executive Summary|Top 5 Strengths|Top 5 Problems|30 Day Plan|60 Day Plan|90 Day Plan|"
        r"Overall Score|Final Verdict)$",
        re.IGNORECASE,
    )

    for line in report.splitlines():
        stripped = line.strip()
        if not stripped:
            doc.add_paragraph("")
            continue

        if stripped.startswith("# "):
            p = doc.add_paragraph(style="Heading 1")
            p.add_run(stripped[2:])
            add_horizontal_rule(p)
        elif stripped.startswith("## "):
            doc.add_heading(stripped[3:], level=2)
        elif re.match(r"^\d+[\.\)]\s+", stripped):
            p = doc.add_heading(stripped, level=2)
            add_horizontal_rule(p)
        elif important.match(stripped):
            doc.add_heading(stripped, level=3)
        elif stripped.startswith("- "):
            doc.add_paragraph(stripped[2:], style="List Bullet")
        else:
            doc.add_paragraph(stripped)


def save_word_report(
    profile: ClientProfile,
    report: str,
    overall: float | None,
    scores: dict[str, float],
    output_dir: Path,
    score_chart: Path | None = None,
    overall_chart: Path | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{clean_filename(profile.company)}_recruitment_audit.docx"

    doc = Document()
    style_document(doc)
    add_cover_page(doc, profile.company, profile.sector, profile.location)
    add_snapshot_table(doc, profile, overall)
    add_kpi_tiles(doc, scores)

    if overall_chart:
        doc.add_heading("Overall Score Visual", level=1)
        doc.add_picture(str(overall_chart), width=Inches(6.8))
        doc.add_paragraph("")

    if score_chart:
        doc.add_heading("Category Score Visual", level=1)
        doc.add_picture(str(score_chart), width=Inches(6.8))
        doc.add_paragraph("")

    add_report_body(doc, report)
    doc.save(path)
    return path


def collect_client_data() -> ClientProfile:
    print_banner()
    print("Stage 1 of 3 | Organisation profile")
    company = prompt("Company name", "Acme Ltd")
    sector = prompt("Industry / sector", "Professional Services")
    location = prompt("Location", "London")
    employees = prompt("Number of employees", "125")
    annual_hires = prompt("Annual hires", "40")

    print("\nStage 2 of 3 | Recruitment performance")
    key_roles = prompt("Key roles hired", "Sales, Operations, Account Management")
    time_to_hire = prompt("Average time to hire", "35 days")
    applications_per_role = prompt("Applications per role", "42")
    offer_acceptance_rate = prompt("Offer acceptance rate", "78%")
    first_year_attrition = prompt("First year attrition", "18%")

    print("\nStage 3 of 3 | Review")
    print(f"- Company: {company}")
    print(f"- Sector: {sector}")
    print(f"- Location: {location}")
    print(f"- Employees: {employees}")
    print(f"- Annual hires: {annual_hires}")
    print(f"- Key roles: {key_roles}")
    print(f"- Average time to hire: {time_to_hire}")
    print(f"- Applications per role: {applications_per_role}")
    print(f"- Offer acceptance rate: {offer_acceptance_rate}")
    print(f"- First year attrition: {first_year_attrition}")

    confirm = input("\nProceed with report generation? (y/n): ").strip().lower()
    if confirm not in {"y", "yes"}:
        raise SystemExit("Cancelled.")

    return ClientProfile(
        company=company,
        sector=sector,
        location=location,
        employees=employees,
        annual_hires=annual_hires,
        key_roles=key_roles,
        time_to_hire=time_to_hire,
        applications_per_role=applications_per_role,
        offer_acceptance_rate=offer_acceptance_rate,
        first_year_attrition=first_year_attrition,
    )


def build_prompt(profile: ClientProfile, benchmark_summary: str) -> str:
    return f"""
Conduct a recruitment audit.

Client data:
{profile.as_prompt_block()}

Benchmark context:
{benchmark_summary}
""".strip()


def call_openai(prompt_text: str, api_key: str, model: str = "gpt-4o-mini") -> str:
    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=model,
        input=f"{SYSTEM_PROMPT}\n\n{prompt_text}",
    )
    return response.output_text


def save_text_report(company: str, report: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{clean_filename(company)}_recruitment_audit.txt"
    path.write_text(report, encoding="utf-8")
    return path


def print_completion_summary(paths: Iterable[Path | None], overall: float | None) -> None:
    print("\n" + "=" * 74)
    print("Audit complete")
    print("=" * 74)
    for path in paths:
        if path:
            print(f"Saved: {path}")
    if overall is not None:
        print(f"Overall score: {overall:.1f}/100")
    print("")


def run_audit() -> None:
    try:
        api_key = get_api_key()
    except Exception as exc:
        print(f"Could not load OpenAI API key: {exc}")
        sys.exit(1)

    try:
        profile = collect_client_data()
        sector, metrics = extract_metrics(profile.as_prompt_block())
        benchmark = load_benchmarks(sector)
        benchmark_summary = build_benchmark_summary(sector, metrics, benchmark)

        print("\nGenerating audit narrative...")
        report = call_openai(build_prompt(profile, benchmark_summary), api_key=api_key)

        scores = extract_scores(report)
        overall = calculate_overall_score(scores)
        output_dir = DEFAULT_OUTPUT_DIR / clean_filename(profile.company)

        text_report_path = save_text_report(profile.company, report, output_dir)
        score_chart = create_score_chart(profile.company, scores, output_dir)
        overall_chart = create_overall_chart(profile.company, overall, output_dir)
        word_report_path = save_word_report(
            profile=profile,
            report=report,
            overall=overall,
            scores=scores,
            output_dir=output_dir,
            score_chart=score_chart,
            overall_chart=overall_chart,
        )

        print_completion_summary(
            [text_report_path, word_report_path, score_chart, overall_chart],
            overall,
        )
    except KeyboardInterrupt:
        print("\nStopped by user.")
        sys.exit(1)
    except Exception as exc:
        print(f"\nAudit generation failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    run_audit()
