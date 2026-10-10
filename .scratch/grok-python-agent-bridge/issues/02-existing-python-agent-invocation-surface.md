# Existing Python Agent invocation surface

Type: research
Status: resolved
Blocked by:

## Question

What does the current AutoApply Python Agent already expose for Grok to call? Inventory `python -m agent` commands, `agent/mcp_server.py` tools, `run-grok.ps1`, required local process, and `.env` keys. Cite this repo's source files. Do not propose a rewrite.

## Answer

Seven parallel surfaces: `python -m agent` subcommands (`status`, `pull`, `search`, `ingest`, `matches`, `tailor`, `push`) and matching FastMCP tools on streamable HTTP at `:8790/mcp`, both calling `agent.runner` in-process; bootstrap with `run-grok.ps1`, tunnel to Grok, and repo-root `.env` per `.env.example`.

Full inventory: [research/existing-python-agent-invocation-surface.md](../research/existing-python-agent-invocation-surface.md).
