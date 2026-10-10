from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Profile(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    city: str = ""
    province: str = "ON"
    postal_code: str = ""
    country: str = "Canada"
    work_status: str = "Permanent Resident"
    linkedin: str = ""
    website: str = ""
    password: str = ""
    skills: str = ""
    target_titles: str = ""
    summary: str = ""
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"


class Highlight(BaseModel):
    original: str
    rewritten: str
    page: int = 0
    bbox: list[float] = Field(default_factory=list)
    font_size: float = 10.0
    font_name: str = ""


class Job(BaseModel):
    id: str
    url: str
    title: str = ""
    company: str = ""
    location: str = ""
    source: str = "manual"
    status: str = "queued"
    jd_text: str = ""
    company_blurb: str = ""
    needs_cover_letter: bool = True
    highlights: list[Highlight] = Field(default_factory=list)
    resume_path: str = ""
    cover_path: str = ""
    apply_log: list[str] = Field(default_factory=list)
    error: str = ""
    match_score: float = 0.0
    match_reasons: list[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def public_dict(self) -> dict[str, Any]:
        return self.model_dump()


class NewJobRequest(BaseModel):
    url: str
    title: str = ""
    company: str = ""


class ScanRequest(BaseModel):
    keywords: str
    location: str = "Canada"
    limit: int = 8


class HighlightUpdate(BaseModel):
    highlights: list[Highlight]
