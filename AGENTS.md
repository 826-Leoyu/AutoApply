# AutoApply Agent

This repo is a Cursor agent for Canadian job search and resume tailoring. Grok should use the project skill `autoapply` and the CLI `python -m agent`, not the old desktop window, unless the user explicitly asks for the local GUI.

Resume source of truth is the user's existing GitHub repo (see `.env`). Do not invent work history. Rhetoric/style of highlight rewrites is still being decided with the user — keep current highlight-only edits until they specify otherwise.
