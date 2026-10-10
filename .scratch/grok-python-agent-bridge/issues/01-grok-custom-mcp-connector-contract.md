# Grok custom MCP connector contract

Type: research
Status: resolved
Blocked by:

## Question

What must a custom MCP server provide for Grok's official custom connector (grok.com/connectors): public URL shape, transport (Streamable HTTP vs SSE), authentication, localhost vs tunnel, and how Grok discovers tools? Cite only first-party xAI / Grok docs.

## Answer

Grok needs a public HTTPS MCP URL (localhost/private IPs rejected; tunnel required). Streamable HTTP or SSE; Cloudflare quick tunnels only work with Streamable HTTP. Auth is whatever the server requires (docs name OAuth or API keys), completed in Grok after the URL. Grok discovers the tools the server exposes.

Write-up: [research/grok-custom-mcp-connector-contract.md](../research/grok-custom-mcp-connector-contract.md).
