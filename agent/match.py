from __future__ import annotations

import re

from server.models import Job, Profile

STOP = {
    "and", "the", "for", "with", "you", "your", "our", "are", "will", "this",
    "that", "from", "have", "has", "job", "role", "team", "work", "working",
    "experience", "skills", "plus", "ability", "including", "canada", "canadian",
}


def score_job(profile: Profile, resume_text: str, job: Job) -> tuple[float, list[str]]:
    hay = " ".join(
        part for part in [resume_text, profile.skills, profile.target_titles, profile.summary] if part
    ).lower()
    jd = " ".join(part for part in [job.title, job.company, job.jd_text] if part).lower()
    if not jd.strip():
        return 0.0, ["还没有 JD，无法打分"]

    reasons: list[str] = []
    score = 20.0

    titles = _tokens(profile.target_titles)
    title_hits = [t for t in titles if t in job.title.lower() or t in jd]
    if title_hits:
        score += min(25.0, 8.0 * len(title_hits))
        reasons.append("职位方向接近：" + ", ".join(title_hits[:6]))
    elif profile.target_titles:
        reasons.append("目标职位词没有明显出现在标题里")

    skills = _tokens(profile.skills)
    skill_hits = [s for s in skills if _contains(jd, s)]
    if skill_hits:
        score += min(40.0, 6.0 * len(skill_hits))
        reasons.append("技能命中：" + ", ".join(skill_hits[:8]))
    elif skills:
        reasons.append("档案里的技能词几乎没在 JD 出现")

    resume_hits = [s for s in skills if _contains(hay, s) and _contains(jd, s)]
    if resume_hits:
        score += min(15.0, 3.0 * len(resume_hits))

    if profile.work_status and any(word in jd for word in ("canada", "canadian", "toronto", "vancouver", "ontario")):
        score += 5
        reasons.append("岗位与加拿大地区相关")

    score = max(0.0, min(100.0, round(score, 1)))
    if score >= 75:
        reasons.insert(0, "匹配度较高，值得改简历")
    elif score >= 55:
        reasons.insert(0, "部分匹配，改简历前建议你过一眼")
    else:
        reasons.insert(0, "匹配偏弱，默认跳过改简历")
    return score, reasons


def _tokens(text: str) -> list[str]:
    parts = re.split(r"[,;/|\n]+", text or "")
    tokens: list[str] = []
    for part in parts:
        word = part.strip().lower()
        if len(word) < 2 or word in STOP:
            continue
        if word not in tokens:
            tokens.append(word)
    return tokens


def _contains(hay: str, needle: str) -> bool:
    if " " in needle:
        return needle in hay
    return re.search(rf"\b{re.escape(needle)}\b", hay) is not None
