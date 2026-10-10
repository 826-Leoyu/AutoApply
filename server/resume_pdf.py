from __future__ import annotations

import re
from pathlib import Path

import pymupdf as fitz

from server.models import Highlight, Profile
from server.paths import MASTER_PDF, job_dir

BULLET_PREFIX = tuple("•●▪◦-–—*·")
CALIBRI = Path(r"C:\Windows\Fonts\calibri.ttf")
CALIBRI_BOLD = Path(r"C:\Windows\Fonts\calibrib.ttf")


def master_exists() -> bool:
    return MASTER_PDF.exists()


def extract_resume_text(pdf_path: Path | None = None) -> str:
    path = pdf_path or MASTER_PDF
    if not path.exists():
        return ""
    with fitz.open(path) as doc:
        return "\n".join(page.get_text("text") for page in doc)


def extract_highlights(pdf_path: Path | None = None) -> list[Highlight]:
    path = pdf_path or MASTER_PDF
    if not path.exists():
        return []
    highlights: list[Highlight] = []
    with fitz.open(path) as doc:
        for page_index, page in enumerate(doc):
            data = page.get_text("dict")
            for block in data.get("blocks", []):
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    if not spans:
                        continue
                    text = "".join(span.get("text", "") for span in spans).strip()
                    if not _is_highlight(text):
                        continue
                    bbox = list(line.get("bbox") or spans[0].get("bbox") or [0, 0, 0, 0])
                    size = float(spans[0].get("size") or 10)
                    font = spans[0].get("font") or ""
                    highlights.append(
                        Highlight(
                            original=text,
                            rewritten=text,
                            page=page_index,
                            bbox=[float(v) for v in bbox],
                            font_size=size,
                            font_name=font,
                        )
                    )
    return highlights[:24]


def build_resume_pdf(job_id: str, profile: Profile, highlights: list[Highlight]) -> Path:
    out_path = job_dir(job_id) / "resume.pdf"
    if MASTER_PDF.exists():
        _rewrite_from_master(out_path, highlights)
        return out_path
    _write_plain_resume(out_path, profile, highlights)
    return out_path


def _rewrite_from_master(out_path: Path, highlights: list[Highlight]) -> None:
    doc = fitz.open(MASTER_PDF)
    by_page: dict[int, list[Highlight]] = {}
    for item in highlights:
        if item.rewritten.strip() and item.rewritten.strip() != item.original.strip():
            by_page.setdefault(item.page, []).append(item)
    for page_index, items in by_page.items():
        if page_index >= len(doc):
            continue
        page = doc[page_index]
        for item in items:
            if len(item.bbox) != 4:
                continue
            rect = fitz.Rect(*item.bbox)
            rect = fitz.Rect(rect.x0, rect.y0 - 0.4, rect.x1, rect.y1 + 0.4)
            page.add_redact_annot(rect, fill=(1, 1, 1))
        page.apply_redactions(images=0)
        fontfile = str(CALIBRI) if CALIBRI.exists() else None
        for item in items:
            rect = fitz.Rect(*item.bbox)
            rect = fitz.Rect(rect.x0, rect.y0 - 0.6, min(page.rect.x1 - 18, rect.x1 + 8), rect.y1 + 1.2)
            kwargs = {
                "fontsize": max(7.5, item.font_size * 0.98),
                "color": (0.08, 0.08, 0.08),
                "align": fitz.TEXT_ALIGN_LEFT,
            }
            if fontfile:
                kwargs["fontfile"] = fontfile
            else:
                kwargs["fontname"] = "helv"
            page.insert_textbox(rect, item.rewritten, **kwargs)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)
    doc.close()


def _write_plain_resume(out_path: Path, profile: Profile, highlights: list[Highlight]) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    y = 48
    fontfile = str(CALIBRI) if CALIBRI.exists() else None
    bold = str(CALIBRI_BOLD) if CALIBRI_BOLD.exists() else fontfile

    def write(text: str, size: float, y_pos: float, *, bold_font: bool = False) -> float:
        kwargs: dict = {"fontsize": size, "color": (0.1, 0.1, 0.12)}
        if bold_font and bold:
            kwargs["fontfile"] = bold
        elif fontfile:
            kwargs["fontfile"] = fontfile
        else:
            kwargs["fontname"] = "hebo" if bold_font else "helv"
        page.insert_text((48, y_pos), text, **kwargs)
        return y_pos + size + 8

    y = write(profile.full_name or "Your Name", 22, y, bold_font=True)
    contact = "  |  ".join(
        part
        for part in [
            profile.email,
            profile.phone,
            ", ".join(p for p in [profile.city, profile.province] if p),
            profile.linkedin,
        ]
        if part
    )
    if contact:
        y = write(contact, 9.5, y)
    y += 6
    if profile.summary:
        y = write("SUMMARY", 12, y, bold_font=True)
        rect = fitz.Rect(48, y, 564, y + 70)
        box_kwargs = {"fontsize": 10, "color": (0.1, 0.1, 0.12)}
        box_kwargs.update({"fontfile": fontfile} if fontfile else {"fontname": "helv"})
        page.insert_textbox(rect, profile.summary, **box_kwargs)
        y += 78
    y = write("HIGHLIGHTS", 12, y, bold_font=True)
    bullets = highlights or [
        Highlight(original=line, rewritten=line)
        for line in (profile.skills or "Add your master.pdf to preserve your real layout.").split(",")
        if line.strip()
    ]
    for item in bullets[:12]:
        text = "• " + (item.rewritten or item.original).strip().lstrip("•- ")
        rect = fitz.Rect(48, y, 564, y + 36)
        box_kwargs = {"fontsize": 10, "color": (0.1, 0.1, 0.12)}
        box_kwargs.update({"fontfile": fontfile} if fontfile else {"fontname": "helv"})
        page.insert_textbox(rect, text, **box_kwargs)
        y += 32
        if y > 740:
            break
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)
    doc.close()


def _is_highlight(text: str) -> bool:
    if len(text) < 28 or len(text) > 320:
        return False
    stripped = text.lstrip()
    if stripped.startswith(BULLET_PREFIX):
        return True
    if stripped[:2].isdigit() and "." in stripped[:4]:
        return False
    if stripped.isupper() and len(stripped) < 48:
        return False
    # Sentence-like experience bullets without a glyph.
    return bool(re_search_verb(stripped))


def re_search_verb(text: str) -> bool:
    return bool(
        re.match(
            r"^(Led|Built|Designed|Developed|Implemented|Managed|Created|Improved|"
            r"Owned|Reduced|Increased|Launched|Delivered|Partnered|Optimized|"
            r"Automated|Supported|Coordinated|Analyzed|Wrote|Shipped)\b",
            text,
        )
    )
