from __future__ import annotations

import base64
from pathlib import Path

import httpx

from agent import config
from server.paths import MASTER_PDF, PROFILE_PATH, ensure_dirs
from server.store import save_profile
from server.models import Profile

API = "https://api.github.com"


class GitHubError(RuntimeError):
    pass


def _headers() -> dict[str, str]:
    if not config.GITHUB_TOKEN:
        raise GitHubError("还没有 GITHUB_TOKEN。复制 .env.example 为 .env 后填入。")
    return {
        "Authorization": f"Bearer {config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "AutoApply-Agent",
    }


def _repo_url(path: str) -> str:
    owner, name = config.repo_parts()
    return f"{API}/repos/{owner}/{name}/{path.lstrip('/')}"


def get_file(repo_path: str) -> bytes:
    params = {"ref": config.GITHUB_BRANCH}
    with httpx.Client(timeout=45.0, follow_redirects=True, headers=_headers()) as client:
        response = client.get(_repo_url(f"contents/{repo_path}"), params=params)
        if response.status_code == 404:
            raise GitHubError(f"仓库里找不到 {repo_path}（分支 {config.GITHUB_BRANCH}）")
        if response.status_code >= 400:
            raise GitHubError(f"读取 GitHub 失败 {response.status_code}: {response.text[:400]}")
        payload = response.json()
        if payload.get("encoding") == "base64" and payload.get("content"):
            return base64.b64decode(payload["content"])
        download = payload.get("download_url")
        if not download:
            raise GitHubError(f"无法下载 {repo_path}")
        raw = client.get(download)
        raw.raise_for_status()
        return raw.content


def put_file(repo_path: str, content: bytes, message: str) -> dict:
    sha = None
    with httpx.Client(timeout=45.0, headers=_headers()) as client:
        existing = client.get(
            _repo_url(f"contents/{repo_path}"),
            params={"ref": config.GITHUB_BRANCH},
        )
        if existing.status_code == 200:
            sha = existing.json().get("sha")
        body = {
            "message": message,
            "content": base64.b64encode(content).decode("ascii"),
            "branch": config.GITHUB_BRANCH,
        }
        if sha:
            body["sha"] = sha
        response = client.put(_repo_url(f"contents/{repo_path}"), json=body)
        if response.status_code >= 400:
            raise GitHubError(f"写入 GitHub 失败 {response.status_code}: {response.text[:400]}")
        return response.json()


def pull() -> dict:
    if not config.configured():
        raise GitHubError("请先在 .env 填写 GITHUB_REPO 和 GITHUB_TOKEN")
    ensure_dirs()
    resume_bytes = get_file(config.GITHUB_RESUME_PATH)
    MASTER_PDF.write_bytes(resume_bytes)
    profile_note = "仓库没有 profile.json，沿用本地档案"
    try:
        raw = get_file(config.GITHUB_PROFILE_PATH)
        PROFILE_PATH.write_bytes(raw)
        save_profile(Profile.model_validate_json(raw.decode("utf-8")))
        profile_note = f"已同步 {config.GITHUB_PROFILE_PATH}"
    except GitHubError:
        pass
    return {
        "repo": config.GITHUB_REPO,
        "branch": config.GITHUB_BRANCH,
        "resume": str(MASTER_PDF),
        "resume_bytes": len(resume_bytes),
        "profile": profile_note,
    }


def push_application(job_id: str, files: dict[str, Path]) -> list[str]:
    uploaded: list[str] = []
    for label, path in files.items():
        if not path or not Path(path).exists():
            continue
        dest = f"{config.GITHUB_OUT_PREFIX}/{job_id}/{Path(path).name}"
        put_file(dest, Path(path).read_bytes(), f"AutoApply: {label} for {job_id}")
        uploaded.append(dest)
    return uploaded


def status() -> dict:
    return {
        "configured": config.configured(),
        "repo": config.GITHUB_REPO or None,
        "branch": config.GITHUB_BRANCH,
        "resume_path": config.GITHUB_RESUME_PATH,
        "profile_path": config.GITHUB_PROFILE_PATH,
        "out_prefix": config.GITHUB_OUT_PREFIX,
        "local_master_exists": MASTER_PDF.exists(),
        "min_score": config.MATCH_MIN_SCORE,
    }
