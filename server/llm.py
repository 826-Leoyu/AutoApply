from __future__ import annotations

import json
import re
from typing import Any

import httpx

from server.models import Highlight, Profile

TIMEOUT = 90.0


class LLMError(RuntimeError):
    pass


def _headers(profile: Profile) -> dict[str, str]:
    key = (profile.openai_api_key or "").strip()
    if not key:
        raise LLMError("还没有填写 API Key。先到「档案」里填 OpenAI 兼容接口，或先不填 Key 做本地过账测试。")
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def chat_json(profile: Profile, system: str, user: str) -> Any:
    base = (profile.openai_base_url or "https://api.openai.com/v1").rstrip("/")
    model = profile.openai_model or "gpt-4o-mini"
    payload = {
        "model": model,
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    with httpx.Client(timeout=TIMEOUT) as client:
        response = client.post(f"{base}/chat/completions", headers=_headers(profile), json=payload)
        if response.status_code >= 400 and "response_format" in payload:
            payload.pop("response_format", None)
            response = client.post(f"{base}/chat/completions", headers=_headers(profile), json=payload)
        if response.status_code >= 400:
            raise LLMError(f"LLM 请求失败 {response.status_code}: {response.text[:500]}")
        content = response.json()["choices"][0]["message"]["content"]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.S)
        if not match:
            raise LLMError("LLM 没有返回 JSON")
        return json.loads(match.group(0))


def rewrite_highlights(profile: Profile, jd_text: str, highlights: list[Highlight]) -> list[Highlight]:
    if not highlights:
        return []
    if not (profile.openai_api_key or "").strip():
        return highlights
    payload = chat_json(
        profile,
        system=(
            "You tailor resume bullet highlights for a Canadian job application. "
            "Return JSON {\"items\":[{\"original\":\"...\",\"rewritten\":\"...\"}]}. "
            "Keep the same number of items in the same order. "
            "Do not invent employers, titles, dates, tools, or metrics. "
            "Only rephrase existing facts so they align with the job description. "
            "Keep each rewritten bullet similar in length to the original (max +15% characters). "
            "Do not add new bullets."
        ),
        user=json.dumps(
            {
                "job_description": jd_text[:8000],
                "candidate_skills": profile.skills,
                "bullets": [{"original": item.original} for item in highlights],
            },
            ensure_ascii=False,
        ),
    )
    items = payload.get("items") or []
    rewritten = []
    for index, highlight in enumerate(highlights):
        text = highlight.original
        if index < len(items) and isinstance(items[index], dict):
            candidate = (items[index].get("rewritten") or "").strip()
            if candidate:
                text = _fit_length(highlight.original, candidate)
        rewritten.append(highlight.model_copy(update={"rewritten": text}))
    return rewritten


def write_cover_letter(
    profile: Profile,
    company: str,
    title: str,
    jd_text: str,
    resume_text: str,
) -> str:
    fallback = _fallback_cover(profile, company, title)
    if not (profile.openai_api_key or "").strip():
        return fallback
    payload = chat_json(
        profile,
        system=(
            "Write a one-page professional cover letter for a Canadian job application. "
            "Return JSON {\"letter\":\"...\"}. Use only facts from the resume. "
            "No fabricated experience. Keep it under 380 words. "
            "Address the company and role. Mention 2-3 matching accomplishments."
        ),
        user=json.dumps(
            {
                "candidate": profile.model_dump(exclude={"openai_api_key", "password"}),
                "company": company,
                "title": title,
                "job_description": jd_text[:8000],
                "resume_text": resume_text[:8000],
            },
            ensure_ascii=False,
        ),
    )
    letter = (payload.get("letter") or "").strip()
    return letter or fallback


def _fit_length(original: str, rewritten: str) -> str:
    limit = max(40, int(len(original) * 1.15))
    if len(rewritten) <= limit:
        return rewritten
    clipped = rewritten[: limit - 1].rsplit(" ", 1)[0]
    return clipped.rstrip(" ,;:") + "."


def _fallback_cover(profile: Profile, company: str, title: str) -> str:
    name = profile.full_name or "Applicant"
    role = title or "this role"
    firm = company or "your team"
    skills = profile.skills or "the skills listed on my resume"
    summary = profile.summary or "I would welcome the chance to contribute to your team."
    return (
        f"Dear Hiring Manager,\n\n"
        f"I am writing to apply for the {role} position at {firm}. "
        f"{summary} "
        f"My background includes {skills}. "
        f"I would be glad to discuss how my experience can support your team.\n\n"
        f"Sincerely,\n{name}"
    )
