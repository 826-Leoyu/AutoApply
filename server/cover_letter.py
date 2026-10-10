from __future__ import annotations

from pathlib import Path

import pymupdf as fitz

from server.models import Profile
from server.paths import job_dir

CALIBRI = Path(r"C:\Windows\Fonts\calibri.ttf")
CALIBRI_BOLD = Path(r"C:\Windows\Fonts\calibrib.ttf")


def build_cover_letter_pdf(job_id: str, profile: Profile, letter: str) -> Path:
    out_path = job_dir(job_id) / "cover-letter.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    fontfile = str(CALIBRI) if CALIBRI.exists() else None
    bold = str(CALIBRI_BOLD) if CALIBRI_BOLD.exists() else fontfile

    def font_args(bold_font: bool = False) -> dict:
        chosen = bold if bold_font else fontfile
        if chosen:
            return {"fontfile": chosen}
        return {"fontname": "hebo" if bold_font else "helv"}

    y = 56
    name = profile.full_name or "Applicant"
    page.insert_text((72, y), name, fontsize=16, color=(0.12, 0.16, 0.14), **font_args(True))
    y += 22
    contact = "  ·  ".join(
        part
        for part in [
            profile.email,
            profile.phone,
            ", ".join(p for p in [profile.city, profile.province, profile.country] if p),
        ]
        if part
    )
    if contact:
        page.insert_text((72, y), contact, fontsize=9.5, color=(0.25, 0.28, 0.26), **font_args())
        y += 18
    page.draw_line(fitz.Point(72, y), fitz.Point(540, y), color=(0.75, 0.78, 0.74), width=0.6)
    y += 24
    body = letter.strip() or "Please see my attached resume."
    rect = fitz.Rect(72, y, 540, 740)
    page.insert_textbox(rect, body, fontsize=11, color=(0.12, 0.12, 0.12), **font_args())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)
    doc.close()
    return out_path
