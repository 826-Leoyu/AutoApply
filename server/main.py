from __future__ import annotations

import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from server.apply import run_apply
from server.models import HighlightUpdate, NewJobRequest, Profile, ScanRequest
from server.paths import MASTER_PDF, PORT, WEB_DIR, ensure_dirs, lan_ip
from server.pipeline import add_demo_job, add_job, prepare_job, regenerate_from_highlights, scan_and_queue
from server.resume_pdf import master_exists
from server.store import get_job, load_jobs, load_profile, save_profile, upsert_job

ensure_dirs()
app = FastAPI(title="AutoApply")
_apply_lock = threading.Lock()


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/meta")
def meta() -> dict:
    ip = lan_ip()
    return {
        "port": PORT,
        "lan_ip": ip,
        "phone_url": f"http://{ip}:{PORT}",
        "local_url": f"http://127.0.0.1:{PORT}",
        "master_pdf": master_exists(),
        "master_path": str(MASTER_PDF),
    }


@app.get("/api/profile")
def read_profile() -> dict:
    data = load_profile().model_dump()
    if data.get("openai_api_key"):
        data["openai_api_key"] = "********"
        data["has_api_key"] = True
    else:
        data["has_api_key"] = False
    if data.get("password"):
        data["password"] = "********"
        data["has_password"] = True
    else:
        data["has_password"] = False
    return data


@app.put("/api/profile")
def write_profile(incoming: Profile) -> dict:
    current = load_profile()
    payload = incoming.model_dump()
    if payload.get("openai_api_key") in {"", "********"}:
        payload["openai_api_key"] = current.openai_api_key
    if payload.get("password") in {"", "********"}:
        payload["password"] = current.password
    saved = save_profile(Profile.model_validate(payload))
    return {"ok": True, "name": saved.full_name}


@app.get("/api/jobs")
def list_jobs() -> list[dict]:
    return [job.public_dict() for job in load_jobs()]


@app.post("/api/jobs")
def create_job(req: NewJobRequest) -> dict:
    if not req.url.strip():
        raise HTTPException(400, "需要岗位 URL")
    return add_job(req).public_dict()


@app.post("/api/jobs/demo")
def demo_job() -> dict:
    return add_demo_job().public_dict()


@app.post("/api/jobs/scan")
def scan_jobs(req: ScanRequest) -> dict:
    try:
        jobs = scan_and_queue(req.keywords, req.location, req.limit)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Job Bank 扫描失败：{exc}") from exc
    return {"count": len(jobs), "jobs": [job.public_dict() for job in jobs]}


@app.get("/api/jobs/{job_id}")
def read_job(job_id: str) -> dict:
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "岗位不存在")
    return job.public_dict()


@app.post("/api/jobs/{job_id}/prepare")
def prepare(job_id: str) -> dict:
    if not get_job(job_id):
        raise HTTPException(404, "岗位不存在")
    return prepare_job(job_id).public_dict()


@app.post("/api/jobs/{job_id}/highlights")
def update_highlights(job_id: str, body: HighlightUpdate) -> dict:
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "岗位不存在")
    job.highlights = body.highlights
    upsert_job(job)
    return regenerate_from_highlights(job_id).public_dict()


@app.post("/api/jobs/{job_id}/apply")
def apply(job_id: str) -> dict:
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "岗位不存在")
    if not job.resume_path:
        raise HTTPException(400, "请先生成简历")
    if not _apply_lock.acquire(blocking=False):
        raise HTTPException(409, "已有投递窗口在进行，请先完成或关闭它")

    def worker() -> None:
        try:
            run_apply(job, load_profile())
        finally:
            _apply_lock.release()

    threading.Thread(target=worker, daemon=True).start()
    return {"ok": True, "message": "正在打开浏览器，请切到弹出的窗口"}


@app.post("/api/jobs/{job_id}/mark")
def mark(job_id: str, status: str = "submitted") -> dict:
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "岗位不存在")
    job.status = status
    upsert_job(job)
    return job.public_dict()


@app.get("/api/jobs/{job_id}/files/{kind}")
def job_file(job_id: str, kind: str) -> FileResponse:
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "岗位不存在")
    path = job.resume_path if kind == "resume" else job.cover_path
    if kind not in {"resume", "cover"} or not path:
        raise HTTPException(404, "文件还不存在")
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(404, "文件还不存在")
    return FileResponse(file_path, media_type="application/pdf", filename=file_path.name)


app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
