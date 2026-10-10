---
name: autoapply
description: Canadian job-search agent. Searches the web for roles, scores them against the user's GitHub resume, then tailors highlight wording to the JD. Use when the user asks Grok to find jobs, check fit, rewrite resume rhetoric, generate a cover letter, or sync resume files with GitHub.
---

# AutoApply Agent

Grok is the requester. This skill is the Cursor agent it should run. Prefer the CLI over the desktop GUI.

## Setup (once)

1. User copies `.env.example` → `.env` and fills `GITHUB_REPO`, `GITHUB_TOKEN`, resume path in their existing repo.
2. Run `python -m agent status`. If `configured` is false, stop and ask for repo + token.
3. Run `python -m agent pull` before matching or tailoring so `resume/master.pdf` is the GitHub original.

Use `.venv\Scripts\python.exe` on this Windows machine when the venv exists.

## Default workflow

When the user names keywords / city / a job URL:

1. `python -m agent pull`
2. Search or ingest:
   - Keywords: `python -m agent search --keywords "..." --location "Toronto, ON"`
   - A specific URL: `python -m agent ingest --url "..."`
3. Show `match_score` and `match_reasons`. Do not tailor jobs below `MATCH_MIN_SCORE` (default 55) unless the user forces it.
4. If they want a tailored resume: `python -m agent tailor --job-id <id>`
5. If they want it back on GitHub: `python -m agent push --job-id <id>`

CLI prints JSON. Read it; do not invent scores or file paths.

## Resume rules (until rhetoric is decided)

- Master file on GitHub is read-only. Never overwrite it.
- Only change Highlight / bullet wording to align with the JD.
- Do not invent employers, titles, dates, tools, or metrics.
- Do not change PDF layout.
- Cover letter only if the posting asks, or the user asks.

## Do not

- Mass-apply or submit forms unless the user clearly asks to open the apply flow.
- Put resume files in a public gist or chat them back in full.
- Skip GitHub pull when `.env` is configured.
