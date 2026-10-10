from __future__ import annotations

import socket
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RESUME_DIR = ROOT / "resume"
OUT_DIR = ROOT / "out"
WEB_DIR = ROOT / "web"
MASTER_PDF = RESUME_DIR / "master.pdf"
PROFILE_PATH = DATA_DIR / "profile.json"
JOBS_PATH = DATA_DIR / "jobs.json"

HOST = "0.0.0.0"
PORT = 8787


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RESUME_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    WEB_DIR.mkdir(parents=True, exist_ok=True)


def lan_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except OSError:
        return "127.0.0.1"


def job_dir(job_id: str) -> Path:
    path = OUT_DIR / job_id
    path.mkdir(parents=True, exist_ok=True)
    return path
