from __future__ import annotations

from pathlib import Path

from agent import config, github_store, match
from server import jd, resume_pdf
from server.models import Job, NewJobRequest
from server.pipeline import add_job, prepare_job, scan_and_queue
from server.store import get_job, load_jobs, load_profile, upsert_job


def pull_resume() -> dict:
    return github_store.pull()


def search_jobs(keywords: str, location: str = "Canada", limit: int = 8) -> list[dict]:
    jobs = scan_and_queue(keywords, location, limit)
    return [_enrich_and_score(job) for job in jobs]


def ingest_url(url: str, title: str = "", company: str = "") -> dict:
    job = add_job(NewJobRequest(url=url, title=title, company=company), source="agent")
    return _enrich_and_score(job)


def list_matches(min_score: float | None = None) -> list[dict]:
    floor = config.MATCH_MIN_SCORE if min_score is None else min_score
    jobs = sorted(load_jobs(), key=lambda item: item.match_score, reverse=True)
    return [_public(job) for job in jobs if job.match_score >= floor]


def tailor(job_id: str, force: bool = False) -> dict:
    job = get_job(job_id)
    if not job:
        raise KeyError(job_id)
    if not force and job.match_score and job.match_score < config.MATCH_MIN_SCORE:
        return {
            "skipped": True,
            "reason": f"匹配分 {job.match_score} 低于 {config.MATCH_MIN_SCORE}，未改简历",
            "job": _public(job),
        }
    prepared = prepare_job(job_id)
    return {"skipped": False, "job": _public(prepared)}


def push_job(job_id: str) -> dict:
    job = get_job(job_id)
    if not job:
        raise KeyError(job_id)
    files = {
        "resume": Path(job.resume_path) if job.resume_path else None,
        "cover-letter": Path(job.cover_path) if job.cover_path else None,
    }
    uploaded = github_store.push_application(job_id, {k: v for k, v in files.items() if v})
    return {"job_id": job_id, "uploaded": uploaded}


def _enrich_and_score(job: Job) -> dict:
    try:
        html = _html_for(job)
        extracted = jd.extract_job_text(html, job.url)
        job.jd_text = extracted["jd_text"]
        job.company_blurb = extracted["company_blurb"]
        job.title = job.title or extracted["title"]
        job.company = job.company or extracted["company"]
        job.needs_cover_letter = bool(extracted["needs_cover_letter"])
    except Exception as exc:  # noqa: BLE001
        job.error = str(exc)
    profile = load_profile()
    resume_text = resume_pdf.extract_resume_text()
    job.match_score, job.match_reasons = match.score_job(profile, resume_text, job)
    job.status = "matched" if job.match_score >= config.MATCH_MIN_SCORE else "low_match"
    upsert_job(job)
    return _public(job)


def _html_for(job: Job) -> str:
    from server.pipeline import _load_html

    return _load_html(job)


def _public(job: Job) -> dict:
    data = job.public_dict()
    data["jd_text"] = (job.jd_text or "")[:1200]
    return data
