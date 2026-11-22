import csv
import html
import json
from pathlib import Path


def save_json(report: dict, output_path: Path) -> None:
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def save_csv(report: dict, output_path: Path) -> None:
    fieldnames = ["site", "category", "grade", "evidence", "url"]
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in report.get("findings", []):
            writer.writerow({k: item.get(k, "") for k in fieldnames})


def save_html(report: dict, output_path: Path) -> None:
    rows_html = []
    for f in report.get("findings", []):
        site = html.escape(str(f.get("site", "")))
        category = html.escape(str(f.get("category", "")))
        grade = html.escape(str(f.get("grade", "")))
        evidence = html.escape(str(f.get("evidence", "")))
        url = html.escape(str(f.get("url", "")))
        rows_html.append(
            f"<tr><td>{site}</td><td>{category}</td><td><b>{grade}</b></td>"
            f"<td>{evidence}</td><td><a href=\"{url}\" target=\"_blank\">{url}</a></td></tr>"
        )

    target = html.escape(str(report.get("target_email", "")))
    pivot = html.escape(str(report.get("username_pivot", "")))
    domain = html.escape(str(report.get("domain", "")))
    score = html.escape(str(report.get("exposure_score", 0)))
    checked_at = html.escape(str(report.get("checked_at", "")))

    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>OSINT Report - {target}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #1f2937; }}
    .meta {{ background: #f3f4f6; padding: 14px; border-radius: 8px; margin-bottom: 20px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px 10px; text-align: left; font-size: 14px; }}
    th {{ background: #111827; color: #ffffff; }}
    tr:nth-child(even) {{ background: #f9fafb; }}
  </style>
</head>
<body>
  <h1>Email OSINT Report</h1>
  <div class="meta">
    <p><b>Target Email:</b> {target} | <b>Username Pivot:</b> {pivot}</p>
    <p><b>Domain:</b> {domain} | <b>Exposure Score:</b> {score}/100 | <b>Checked At:</b> {checked_at}</p>
  </div>
  <table>
    <thead>
      <tr>
        <th>Platform</th>
        <th>Category</th>
        <th>Grade</th>
        <th>Evidence</th>
        <th>URL</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows_html)}
    </tbody>
  </table>
</body>
</html>"""
    output_path.write_text(page, encoding="utf-8")
