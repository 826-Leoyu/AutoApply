from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from server.paths import ROOT

load_dotenv(ROOT / ".env")


def _get(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


GITHUB_REPO = _get("GITHUB_REPO")
GITHUB_TOKEN = _get("GITHUB_TOKEN")
GITHUB_BRANCH = _get("GITHUB_BRANCH", "main")
GITHUB_RESUME_PATH = _get("GITHUB_RESUME_PATH", "resume/master.pdf")
GITHUB_PROFILE_PATH = _get("GITHUB_PROFILE_PATH", "profile.json")
GITHUB_OUT_PREFIX = _get("GITHUB_OUT_PREFIX", "applications")
MATCH_MIN_SCORE = float(_get("MATCH_MIN_SCORE", "55") or 55)


def configured() -> bool:
    return bool(GITHUB_REPO and GITHUB_TOKEN)


def repo_parts() -> tuple[str, str]:
    if "/" not in GITHUB_REPO:
        raise ValueError("GITHUB_REPO 应为 owner/name，例如 alice/resume")
    owner, name = GITHUB_REPO.split("/", 1)
    return owner, name


def cache_dir() -> Path:
    path = ROOT / ".cache" / "github"
    path.mkdir(parents=True, exist_ok=True)
    return path
