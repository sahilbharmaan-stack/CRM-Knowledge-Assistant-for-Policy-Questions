"""Turn an uploaded DOCX, PDF, TXT, or Markdown file into policy sections."""
import io
from pathlib import Path
from zipfile import BadZipFile

from backend.indexer import parse_policy_text

ALLOWED = {".docx", ".pdf", ".txt", ".md"}
MAX_BYTES = 8_000_000


class DocumentError(ValueError):
    """The upload cannot be read as a policy document."""


def extract_text(filename: str, data: bytes) -> str:
    if len(data) > MAX_BYTES:
        raise DocumentError("File is larger than 8 MB.")
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise DocumentError("Upload a DOCX, PDF, TXT, or MD file.")
    if ext in {".txt", ".md"}:
        return data.decode("utf-8", errors="replace")
    if ext == ".docx":
        try:
            from docx import Document
            from docx.opc.exceptions import PackageNotFoundError
        except ImportError as e:
            raise DocumentError("DOCX support is not installed (python-docx).") from e
        try:
            document = Document(io.BytesIO(data))
        except (BadZipFile, PackageNotFoundError) as e:
            raise DocumentError("The DOCX file is invalid or damaged.") from e
        try:
            lines = []
            for paragraph in document.paragraphs:
                text = paragraph.text.strip()
                if not text:
                    continue
                style = paragraph.style.name if paragraph.style is not None else ""
                if style.startswith("Heading 1"):
                    lines.append("# " + text)
                elif style.startswith("Heading"):
                    lines.append("## " + text)
                else:
                    lines.append(text)
        except (BadZipFile, PackageNotFoundError) as e:
            raise DocumentError("The DOCX file is invalid or damaged.") from e
        return "\n".join(lines)
    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
    except ImportError as e:
        raise DocumentError("PDF support is not installed (pypdf).") from e
    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as e:
                raise DocumentError("This PDF is password-protected. Remove the password and upload it again.") from e
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except DocumentError:
        raise
    except (PdfReadError, ValueError, TypeError, KeyError, IndexError, OSError) as e:
        raise DocumentError("The PDF file is invalid, damaged, or could not be processed.") from e
    except Exception as e:
        # Some PDFs trigger parser exceptions outside pypdf's documented error types.
        raise DocumentError("The PDF file could not be processed. Try saving it again as a standard PDF.") from e


def policy_from_upload(filename: str, data: bytes, doc_code: str, title: str, version: str) -> dict:
    text = extract_text(filename, data).strip()
    if not text:
        raise DocumentError("No readable text was found in that file.")
    parsed = parse_policy_text(text[:200_000], Path(filename).stem or "policy")
    parsed["doc_code"] = doc_code.strip()
    parsed["title"] = title.strip() or parsed["title"]
    parsed["version"] = version.strip()
    parsed["status"] = "draft"
    if not parsed["sections"]:
        raise DocumentError("The file has no policy text to index.")
    return parsed
