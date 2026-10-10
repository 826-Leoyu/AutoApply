from __future__ import annotations

import uuid
from urllib.parse import urlparse

from server import cover_letter, jd, jobbank, llm, resume_pdf
from server.models import Job, NewJobRequest
from server.paths import PORT, WEB_DIR
from server.store import append_log, get_job, load_profile, upsert_job


def new_id() -> str:
    return uuid.uuid4().hex[:10]


def add_job(req: NewJobRequest, source: str = "manual") -> Job:
    job = Job(
        id=new_id(),
        url=req.url.strip(),
        title=req.title.strip(),
        company=req.company.strip(),
        source=source,
        status="queued",
    )
    return upsert_job(job)


def add_demo_job() -> Job:
    return add_job(
        NewJobRequest(
            url=f"http://127.0.0.1:{PORT}/mock-ats.html",
            title="Software Developer (Local Test)",
            company="Northwind Labs",
        ),
        source="demo",
    )


def scan_and_queue(keywords: str, location: str, limit: int = 8) -> list[Job]:
    found = jobbank.scan_jobs(keywords, location, limit)
    jobs: list[Job] = []
    for item in found:
        apply_url = item["url"]
        try:
            apply_url = jobbank.resolve_apply_url(item["url"])
        except Exception:
            apply_url = item["url"]
        jobs.append(
            add_job(
                NewJobRequest(url=apply_url, title=item.get("title", ""), company=item.get("company", "")),
                source="jobbank",
            )
        )
    return jobs


def prepare_job(job_id: str) -> Job:
    job = get_job(job_id)
    if not job:
        raise KeyError(job_id)
    profile = load_profile()
    job.status = "preparing"
    job.error = ""
    append_log(job, "开始抓取岗位描述")
    try:
        html = _load_html(job)
        extracted = jd.extract_job_text(html, job.url)
        job.jd_text = extracted["jd_text"]
        job.company_blurb = extracted["company_blurb"]
        job.needs_cover_letter = True if job.source == "demo" else bool(extracted["needs_cover_letter"])
        job.title = job.title or extracted["title"] or _title_from_url(job.url)
        job.company = job.company or extracted["company"]
        if job.source == "demo":
            job.needs_cover_letter = True
        append_log(job, "已抽取 JD，开始改简历 Highlight")
        highlights = resume_pdf.extract_highlights()
        if not highlights:
            highlights = []
        rewritten = llm.rewrite_highlights(profile, job.jd_text, highlights) if highlights else highlights
        job.highlights = rewritten
        resume_path = resume_pdf.build_resume_pdf(job.id, profile, rewritten)
        job.resume_path = str(resume_path)
        append_log(job, f"已生成简历 {resume_path.name}")
        resume_text = resume_pdf.extract_resume_text(resume_path) or resume_pdf.extract_resume_text()
        letter = llm.write_cover_letter(profile, job.company, job.title, job.jd_text, resume_text)
        cover_path = cover_letter.build_cover_letter_pdf(job.id, profile, letter)
        job.cover_path = str(cover_path)
        append_log(job, f"已生成 Cover letter {cover_path.name}")
        job.status = "ready"
        append_log(job, "材料已就绪，可以开始投递（会打开浏览器窗口）")
    except Exception as exc:  # noqa: BLE001
        job.status = "error"
        job.error = str(exc)
        append_log(job, f"准备失败：{exc}")
    return upsert_job(job)


def regenerate_from_highlights(job_id: str) -> Job:
    job = get_job(job_id)
    if not job:
        raise KeyError(job_id)
    profile = load_profile()
    resume_path = resume_pdf.build_resume_pdf(job.id, profile, job.highlights)
    job.resume_path = str(resume_path)
    resume_text = resume_pdf.extract_resume_text(resume_path)
    letter = llm.write_cover_letter(profile, job.company, job.title, job.jd_text, resume_text)
    cover_path = cover_letter.build_cover_letter_pdf(job.id, profile, letter)
    job.cover_path = str(cover_path)
    job.status = "ready"
    append_log(job, "已按你改过的 Highlight 重新生成 PDF")
    return upsert_job(job)


def _title_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/").split("/")[-1]
    return path.replace("-", " ").replace("_", " ")[:120]


def _load_html(job: Job) -> str:
    mock = WEB_DIR / "mock-ats.html"
    if job.source == "demo" or job.url.rstrip("/").endswith("/mock-ats.html"):
        return mock.read_text(encoding="utf-8")
    _, html = jd.fetch_page(job.url)
    return html
