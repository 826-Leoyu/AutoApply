from __future__ import annotations

import argparse
import json
import sys

from agent import github_store, runner


def _print(data) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="AutoApply agent — Grok 在 Cursor 里调用的工具入口")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="看 GitHub / 本地简历是否已接好")
    sub.add_parser("pull", help="从 GitHub 拉取主简历和档案")

    search = sub.add_parser("search", help="上网搜岗并打匹配分")
    search.add_argument("--keywords", required=True)
    search.add_argument("--location", default="Canada")
    search.add_argument("--limit", type=int, default=8)

    ingest = sub.add_parser("ingest", help="加入一条岗位 URL 并打分")
    ingest.add_argument("--url", required=True)
    ingest.add_argument("--title", default="")
    ingest.add_argument("--company", default="")

    listed = sub.add_parser("matches", help="列出达到分数线的岗位")
    listed.add_argument("--min-score", type=float, default=None)

    tailor = sub.add_parser("tailor", help="按 JD 改简历措辞并生成 PDF")
    tailor.add_argument("--job-id", required=True)
    tailor.add_argument("--force", action="store_true")

    push = sub.add_parser("push", help="把该岗生成的 PDF 推回 GitHub")
    push.add_argument("--job-id", required=True)

    args = parser.parse_args()
    try:
        if args.cmd == "status":
            _print(github_store.status())
        elif args.cmd == "pull":
            _print(runner.pull_resume())
        elif args.cmd == "search":
            _print(runner.search_jobs(args.keywords, args.location, args.limit))
        elif args.cmd == "ingest":
            _print(runner.ingest_url(args.url, args.title, args.company))
        elif args.cmd == "matches":
            _print(runner.list_matches(args.min_score))
        elif args.cmd == "tailor":
            _print(runner.tailor(args.job_id, force=args.force))
        elif args.cmd == "push":
            _print(runner.push_job(args.job_id))
        return 0
    except Exception as exc:  # noqa: BLE001
        _print({"error": str(exc)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
