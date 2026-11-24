"""Parse approved policy markdown files and index them into SQLite.

File format:
    # Title
    Doc-Code: REF-001
    Version: 1.2
    Status: approved | draft | retired
    Category: refund | attendance | programme | support | assessment | freelancing  (optional)
    ## Section heading
    paragraph text...
"""
import re
from pathlib import Path

from backend import db
from backend.nlp.classifier import classify_topic

META_RE = re.compile(r"^(Doc-Code|Version|Status|Category|Effective):\s*(.+)$", re.IGNORECASE)


def parse_policy_text(text: str, fallback_name: str) -> dict:
    """Parse handbook text. Headings become sections. Metadata lines are optional."""
    lines = text.splitlines()
    meta = {"title": fallback_name, "doc_code": fallback_name.upper(), "version": "1.0", "status": "draft"}
    sections: list[tuple[str, list[str]]] = []
    heading, buf = None, []
    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            meta["title"] = line[2:].strip()
        elif META_RE.match(line):
            k, v = META_RE.match(line).groups()
            meta[{"doc-code": "doc_code"}.get(k.lower(), k.lower())] = v.strip()
        elif line.startswith("## "):
            if heading is not None:
                sections.append((heading, buf))
            heading, buf = line[3:].strip(), []
        elif heading is not None:
            buf.append(line)
    if heading is not None:
        sections.append((heading, buf))
    meta["sections"] = [(h, " ".join(b).strip()) for h, b in sections if " ".join(b).strip()]
    if not meta["sections"]:
        body = " ".join(line.strip() for line in lines if line.strip() and not line.startswith("# ") and not META_RE.match(line))
        if body:
            meta["sections"] = [("Document", body)]
    return meta


def parse_policy_file(path: Path) -> dict:
    return parse_policy_text(path.read_text(encoding="utf-8"), path.stem)


def index_policies(conn, policy_dir: Path) -> int:
    """Index every *.md policy in policy_dir. Returns number of chunks stored."""
    total = 0
    for path in sorted(Path(policy_dir).glob("*.md")):
        doc = parse_policy_file(path)
        doc_id = db.upsert_document(
            conn, doc["doc_code"], doc["title"], doc["version"], path.name, doc["status"]
        )
        for i, (heading, text) in enumerate(doc["sections"]):
            topic = doc.get("category") or classify_topic(f"{doc['title']} {heading} {text}")[0]
            db.add_chunk(conn, doc_id, i, heading, text, topic)
            total += 1
    return total
