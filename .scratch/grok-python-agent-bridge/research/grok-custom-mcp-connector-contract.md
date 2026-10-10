# Grok custom MCP connector contract

Question: what must a custom MCP server provide for Grok's official custom connector at [grok.com/connectors](https://grok.com/connectors)? Public URL shape, transport (Streamable HTTP vs SSE), authentication, localhost vs tunnel, and how Grok discovers tools.

Primary sources only: first-party xAI / Grok docs, fetched 2026-10-10.

## Surfaces (do not mix)

| Surface | What it is | Used for this ticket |
|---------|------------|----------------------|
| Grok custom MCP connector | User adds a Custom connector at grok.com/connectors; Grok chat then calls that server | **Primary** |
| xAI API Remote MCP Tools | Developer `tools: [{ type: "mcp", server_url, ... }]` on `api.x.ai` / the xAI SDK | Supporting: transport names, HTTPS, bearer header, tool injection |
| Cookbook “Database over MCP” | First-party recipe for the **API**, not the grok.com dialog | Supporting: Streamable HTTP wire shape, `tools/list`, Cloudflare + `/mcp` |
| Grok CLI `grok mcp` | Local CLI / TUI (`~/.grok/config.toml`) | Out of scope for grok.com/connectors; cited only to mark the boundary |

## Summary

Grok's custom connector needs a **public HTTPS MCP URL**. Grok's servers reject `localhost` and private IPs; a local process must sit behind a tunnel (ngrok or Cloudflare). The grok.com docs treat **Streamable HTTP and SSE** as valid transports; Cloudflare quick tunnels do not support SSE, so Streamable HTTP is the path that works with `cloudflared`. After you paste the URL, Grok completes **whatever auth the server requires** (docs name OAuth and API keys). Grok then **discovers the tools the server exposes** and offers them in chat. The grok.com pages do not prescribe a path suffix; first-party API examples commonly use `https://…/mcp`.

## Public URL shape

**Must be publicly reachable.** “Your MCP server must be reachable over the public internet.” If it runs on the local machine, use a tunnel. Source: [Connectors](https://docs.x.ai/grok/connectors).

**Private / loopback URLs are rejected.** Grok's servers need to reach the MCP server over the public internet. Servers on `localhost` or a private address (`127.0.0.1`, `10.x.x.x`, `172.16.x.x`, `192.168.x.x`) “are not directly reachable, and Grok will reject these URLs.” Source: [Custom MCP Server Tunneling](https://docs.x.ai/grok/connectors/custom-mcp-tunneling).

**What you paste in the dialog.** Setup is: grok.com/connectors → New Connector → Custom → “Enter the MCP server URL and complete any required authentication.” Source: [Connectors](https://docs.x.ai/grok/connectors).

**HTTPS public host; no required path in the grok.com pages.** Tunneling docs show the public origin as the connector URL:

- Diagram: `Grok ──► https://your-tunnel.example.com ──► tunnel provider ──► localhost:3001`
- ngrok: copy the `Forwarding` URL (e.g. `https://a1b2c3d4.ngrok-free.app`) and use it as the server URL
- Cloudflare: copy the generated `*.trycloudflare.com` URL and use it as the server URL

Source: [Custom MCP Server Tunneling](https://docs.x.ai/grok/connectors/custom-mcp-tunneling). Those examples do **not** append `/mcp`. The grok.com connector pages do not document a required path, query string, or port.

**API examples usually end in `/mcp`.** Remote MCP Tools examples use `https://mcp.deepwiki.com/mcp` and `https://your-custom-tools.com/mcp`. Best practice: “Always use HTTPS URLs.” Source: [Remote MCP Tools](https://docs.x.ai/developers/tools/remote-mcp). The cookbook's Streamable HTTP server posts every JSON-RPC message to one URL, “here `/mcp`.” Source: [Database over MCP](https://docs.x.ai/cookbook/examples/database-over-mcp).

**Implication for this repo:** the public URL Grok needs is `https://<public-host>` plus whatever path the local MCP process actually serves. If the process only handles `/mcp`, the connector URL must include `/mcp` even when the tunnel docs show only the origin.

## Transport (Streamable HTTP vs SSE)

**Grok.com custom connectors: both.** Tunneling caution: “Cloudflare quick tunnels do not support Server-Sent Events (SSE). If your MCP server uses the SSE transport, use ngrok instead. Servers using the newer Streamable HTTP transport work fine with Cloudflare.” Source: [Custom MCP Server Tunneling](https://docs.x.ai/grok/connectors/custom-mcp-tunneling). That is first-party confirmation that Grok will talk **SSE or Streamable HTTP** to a custom connector.

**Developer API: the same two, named “Streaming HTTP and SSE”.** `server_url` description: “Only Streaming HTTP and SSE transports are supported.” Source: [Remote MCP Tools](https://docs.x.ai/developers/tools/remote-mcp). “Streaming HTTP” here matches the MCP Streamable HTTP transport named on the tunneling page.

**Streamable HTTP wire shape (API cookbook, not grok.com UI).** A minimal tools-only server implements four JSON-RPC methods: `initialize`, `ping`, `tools/list`, `tools/call`. “In Streamable HTTP, every message is a POST to one URL, here `/mcp`. Requests get a JSON reply and notifications get a 202 with no body.” A GET can return 405 if the server never streams. “Plain JSON replies also work through Cloudflare's quick tunnels, which don't support server-sent events.” Source: [Database over MCP](https://docs.x.ai/cookbook/examples/database-over-mcp).

**stdio is not a grok.com custom-connector transport.** The grok.com connector and Remote MCP Tools pages only discuss HTTP(S) servers Grok's cloud can call. Local stdio appears on the Grok **CLI** page (`grok mcp add filesystem -- npx …`), which is a different product surface. Source: [MCP Servers](https://docs.x.ai/build/features/mcp-servers) (CLI only).

## Authentication

**Grok.com custom connector.** After the URL, “complete any required authentication.” You “control authentication and access on your own infrastructure.” Source: [Connectors](https://docs.x.ai/grok/connectors).

**Named mechanisms: OAuth or API keys.** “If your MCP server requires OAuth or API keys, you will still complete that flow in Grok after providing the tunnel URL. The tunnel only handles network reachability.” Source: [Custom MCP Server Tunneling](https://docs.x.ai/grok/connectors/custom-mcp-tunneling). Built-in / catalog connectors use OAuth; that is not required of a custom server. Source: [Connectors](https://docs.x.ai/grok/connectors).

**The grok.com pages do not specify** the exact dialog fields, header names, or whether an unauthenticated public URL is accepted. They only say you complete required auth in Grok after the URL.

**API Remote MCP (supporting).** Optional `authorization`: “A token that will be set in the Authorization header on requests to the MCP server.” Optional `headers` / SDK `extra_headers`. Best practice: HTTPS plus “proper authentication mechanisms on your MCP server.” Source: [Remote MCP Tools](https://docs.x.ai/developers/tools/remote-mcp). Cookbook: `authorization` arrives as `Authorization: Bearer <token>`. Source: [Database over MCP](https://docs.x.ai/cookbook/examples/database-over-mcp).

## Localhost vs tunnel

**Grok cannot call localhost.** Rejects loopback and RFC1918-style private ranges listed above. Source: [Custom MCP Server Tunneling](https://docs.x.ai/grok/connectors/custom-mcp-tunneling).

**Tunnel is reachability only.** A tunnel “creates a secure, temporary public URL that forwards traffic to a port on your machine.” “Your MCP server code requires no changes; only the URL you provide to Grok differs.” Source: [Custom MCP Server Tunneling](https://docs.x.ai/grok/connectors/custom-mcp-tunneling).

**Documented tunnel recipes** (same page):

| Provider | Command (docs example, local port 3001) | URL you paste |
|----------|-----------------------------------------|---------------|
| ngrok | `ngrok http 3001` | `Forwarding` HTTPS URL, e.g. `https://a1b2c3d4.ngrok-free.app` |
| Cloudflare quick tunnel | `cloudflared tunnel --url http://localhost:3001` | generated `*.trycloudflare.com` URL |

Use ngrok if the server is SSE-only. Streamable HTTP works with Cloudflare. Source: [Custom MCP Server Tunneling](https://docs.x.ai/grok/connectors/custom-mcp-tunneling).

**Operational constraints** (same page):

- Free-tier tunnel URLs typically change on restart; remove the old connector and add a new one with the new URL.
- Keep the MCP process **and** the tunnel running. Grok calls on demand; if either is down, tool calls fail.
- Auth is still completed in Grok after the tunnel URL.

The cookbook repeats the same network model for the API: SpaceXAI connects from its side; a Cloudflare quick tunnel gives the machine a public URL; DNS must resolve before SpaceXAI can reach it. Source: [Database over MCP](https://docs.x.ai/cookbook/examples/database-over-mcp).

## Tool discovery

**Grok.com:** “Grok will discover the tools your MCP server exposes and make them available in conversations, just like the built-in and catalog connectors.” Source: [Connectors](https://docs.x.ai/grok/connectors). The grok.com page does not name the MCP method.

**API Remote MCP:** if you omit `allowed_tools`, “all tool definitions exposed by the MCP server are automatically injected into the model's context.” The model can call any of them. `allowed_tools` / SDK `allowed_tool_names` restricts that set. Source: [Remote MCP Tools](https://docs.x.ai/developers/tools/remote-mcp).

**API cookbook (explicit list step):** SpaceXAI “opens one MCP session to list the tools before Grok starts and another for Grok's calls.” A tools-only server must implement `tools/list` (plus `initialize`, `ping`, `tools/call`). Tools appear to the model with the server label prefixed, e.g. `store___run_query`. Source: [Database over MCP](https://docs.x.ai/cookbook/examples/database-over-mcp).

For the grok.com custom connector, first-party wording is “discover the tools your MCP server exposes.” The API/cookbook pages are the only first-party write-up that names `tools/list` and a pre-chat listing session. Do not treat `allowed_tools` or `server_label` prefixing as documented grok.com/connectors UI fields; those are API parameters.

## Documented gaps

The first-party grok.com connector docs do **not** specify:

- A required URL path (`/mcp` vs origin).
- Exact connector-dialog fields (headers, bearer vs OAuth client IDs).
- Whether an unauthenticated server is accepted.
- Protocol version, session headers, or JSON-RPC method list for grok.com (the cookbook lists methods for the API recipe only).
- Timeouts, payload limits, or how Grok.com namespaces custom-connector tool names.

## Sources

1. [Connectors](https://docs.x.ai/grok/connectors) — custom connector setup, public-internet requirement, tool discovery.
2. [Custom MCP Server Tunneling](https://docs.x.ai/grok/connectors/custom-mcp-tunneling) — rejected private URLs, ngrok/Cloudflare, SSE vs Streamable HTTP, OAuth/API keys after URL.
3. [Remote MCP Tools](https://docs.x.ai/developers/tools/remote-mcp) — API: Streaming HTTP + SSE, HTTPS, `authorization` header, inject all exposed tools.
4. [Database over MCP](https://docs.x.ai/cookbook/examples/database-over-mcp) — API cookbook: Streamable HTTP POST `/mcp`, `tools/list`, Cloudflare, Bearer token.
5. [MCP Servers](https://docs.x.ai/build/features/mcp-servers) — Grok **CLI** only; not the grok.com custom connector.
