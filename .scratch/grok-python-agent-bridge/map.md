# Grok calls the Python Agent

Label: `wayfinder:map`

## Destination

A locked decision plus a thin spec for Grok (grok.com / Grok app) to call the existing AutoApply Agent through an official custom MCP connector, reusing `python -m agent`. The next session can implement the bridge without rewriting the Agent.

## Notes

- Domain: AutoApply Canadian job search. Consult `GLOSSARY.md` and `.cursor/skills/autoapply/SKILL.md`.
- Planning only. Do not implement the connector or change Agent behavior unless a ticket is a `task` that unblocks a decision.
- Reuse `python -m agent` and the existing Python MCP wrapper if it fits. Do not start a Node agent.
- Tracker is local markdown under `.scratch/grok-python-agent-bridge/`.

## Decisions so far

- Destination artifact: decision + thin spec, not a finished live connection.
- Grok means grok.com / Grok app via official custom MCP connector, not Cursor chat.
- This map covers only the Grok → existing CLI invocation path.
- [Existing Python Agent invocation surface](issues/02-existing-python-agent-invocation-surface.md): CLI and FastMCP share seven ops via `agent.runner`; Grok uses HTTP MCP on port 8790 after `run-grok.ps1` and cloudflared.

## Not yet specified

- Exact Grok-side wording / connector instructions after the spec exists.
- What Grok should do when this laptop is asleep or the Agent process is down.
- Whether the MCP process should stay a thin wrapper that shells out to `python -m agent`, or keep the current in-process FastMCP that imports `agent.runner` (depends on the invocation-surface research).

## Out of scope

- Resume highlight rhetoric rules.
- Real ATS auto-submit and the desktop GUI.
- Rebuilding the Agent in Node.js / TypeScript.
- Using Cursor chat as the place the user talks to Grok.
