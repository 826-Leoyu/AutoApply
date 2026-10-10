from __future__ import annotations

import json
from datetime import datetime, timezone
from threading import Lock

from server.models import Job, Profile
from server.paths import JOBS_PATH, PROFILE_PATH, ensure_dirs

_lock = Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_profile() -> Profile:
    ensure_dirs()
    if not PROFILE_PATH.exists():
        return Profile()
    return Profile.model_validate_json(PROFILE_PATH.read_text(encoding="utf-8"))


def save_profile(profile: Profile) -> Profile:
    ensure_dirs()
    PROFILE_PATH.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
    return profile


def load_jobs() -> list[Job]:
    ensure_dirs()
    if not JOBS_PATH.exists():
        return []
    raw = json.loads(JOBS_PATH.read_text(encoding="utf-8"))
    return [Job.model_validate(item) for item in raw]


def save_jobs(jobs: list[Job]) -> None:
    ensure_dirs()
    payload = [job.model_dump() for job in jobs]
    JOBS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def upsert_job(job: Job) -> Job:
    with _lock:
        jobs = load_jobs()
        job.updated_at = _now()
        if not job.created_at:
            job.created_at = job.updated_at
        by_id = {item.id: item for item in jobs}
        by_id[job.id] = job
        ordered = sorted(by_id.values(), key=lambda item: item.created_at, reverse=True)
        save_jobs(ordered)
        return job


def get_job(job_id: str) -> Job | None:
    for job in load_jobs():
        if job.id == job_id:
            return job
    return None


def append_log(job: Job, message: str) -> Job:
    job.apply_log.append(f"{_now()}  {message}")
    return upsert_job(job)
