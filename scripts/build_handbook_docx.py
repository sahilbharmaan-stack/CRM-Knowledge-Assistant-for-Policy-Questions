"""Builds docs/CRM_Policy_Handbook_Synthetic.docx from data/policies/*.md (single source of truth)."""
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
files = sorted((ROOT / "data" / "policies").glob("CL-*.md"))
order = ["PROG", "REFUND", "ATT", "SUPPORT", "ASSESS", "FREELANCE", "SCHOLAR"]
files.sort(key=lambda f: (order.index(f.name.split("-")[1]), f.name))


def parse(path):
    meta, body = {}, []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(Doc-Code|Version|Status|Category|Effective):\s*(.+)$", line)
        if m:
            meta[m.group(1)] = m.group(2)
        elif line.startswith("# "):
            meta["Title"] = line[2:]
        else:
            body.append(line)
    return meta, body


doc = Document()
doc.styles["Normal"].font.name = "Calibri"
doc.styles["Normal"].font.size = Pt(11)

def para(text, bold=False, size=None, color=None, align=None, style=None):
    p = doc.add_paragraph(style=style)
    r = p.add_run(text)
    r.bold = bold
    if size: r.font.size = Pt(size)
    if color: r.font.color.rgb = RGBColor(*color)
    if align: p.alignment = align
    return p

para("CAREER LAB CONSULTING (SYNTHETIC DEMO)", True, 12, (90, 90, 90), WD_ALIGN_PARAGRAPH.CENTER)
doc.add_heading("CRM Knowledge Assistant - Policy Handbook", 0)
para("Data & AI Professional Programme | Version 1.0 | 18 November 2026", size=11)

doc.add_heading("Important notice", 1)
para("This handbook is fictional, synthetic sample data created only to build, test and demonstrate the "
     "Project 037 CRM Knowledge Assistant. The rules, fees, timelines and thresholds are illustrative and are "
     "not real Career Lab Consulting policies. The sample text was generated with ChatGPT and accepted by the "
     "instructor for this purpose. The only exception is the freelancing progression section, which restates "
     "conditions from the project allocation brief. Do not use this document to advise real learners.")

doc.add_heading("Document register", 1)
t = doc.add_table(rows=1, cols=5)
t.style = "Light Grid Accent 1"
for i, h in enumerate(["Document ID", "Title", "Version", "Status", "Used for answers"]):
    t.rows[0].cells[i].text = h
for f in files:
    m, _ = parse(f)
    row = t.add_row().cells
    row[0].text, row[1].text, row[2].text, row[3].text = m["Doc-Code"], m["Title"], m["Version"], m["Status"]
    row[4].text = "Yes" if m["Status"] == "approved" else "No (" + m["Status"] + ")"

doc.add_heading("How the assistant uses this handbook", 1)
for b in ["Only documents with status approved are retrieved. Draft and retired documents are never used.",
          "Every answer cites the document ID, version and section.",
          "If no relevant passage is found, the assistant abstains and refers the user to the policy owner.",
          "The assistant only suggests. It never approves refunds, changes attendance, grades learners, issues "
          "certificates or sends messages. A human reviewer approves every answer."]:
    doc.add_paragraph(b, style="List Bullet")

for f in files:
    m, body = parse(f)
    doc.add_page_break()
    doc.add_heading(f"{m['Title']}", 1)
    mt = doc.add_table(rows=0, cols=2)
    mt.style = "Light List Accent 1"
    for k in ["Doc-Code", "Version", "Status", "Category", "Effective"]:
        r = mt.add_row().cells
        r[0].text, r[1].text = {"Doc-Code": "Document ID", "Effective": "Effective date"}.get(k, k), m[k]
    if m["Status"] != "approved":
        para(f"Status {m['Status'].upper()}: this document is excluded from retrieval.", True, color=(170, 0, 0))
    for line in body:
        if not line.strip():
            continue
        if line.startswith("## "):
            doc.add_heading(line[3:], 2)
        elif line.startswith("- "):
            doc.add_paragraph(line[2:], style="List Bullet")
        elif re.match(r"^\d+\. ", line):
            doc.add_paragraph(re.sub(r"^\d+\. ", "", line), style="List Number")
        else:
            doc.add_paragraph(line)

doc.add_page_break()
doc.add_heading("Document control", 1)
for line in ["Prepared by: Sahil Sharma (Project 037 trainee), synthetic sample.",
             "Reviewed / approved by: instructor accepted use as demo data (18 Nov 2026).",
             "Replace every section with company-approved policy text before any real use."]:
    doc.add_paragraph(line, style="List Bullet")

out = ROOT / "docs" / "CRM_Policy_Handbook_Synthetic.docx"
doc.save(out)
print("saved", out)
