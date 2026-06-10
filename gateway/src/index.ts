import { OAuthProvider } from "@cloudflare/workers-oauth-provider";
import { WebStandardStreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/webStandardStreamableHttp.js";
import { buildMcpServer } from "./mcp.js";
import { DescopeHandler } from "./descope-handler.js";

/**
 * MCP API handler — called by OAuthProvider only for requests under /mcp
 * that carry a valid access token. ctx.props contains the user email that
 * was stored during the Descope authorization flow.
 *
 * Each request gets its own stateless transport + server instance because
 * WebStandardStreamableHTTPServerTransport is stateful per-session and
 * McpServer can only be connected to one transport at a time.
 */
const mcpApiHandler = {
  async fetch(
    request: Request,
    _env: unknown,
    _ctx: ExecutionContext
  ): Promise<Response> {
    const transport = new WebStandardStreamableHTTPServerTransport({
      sessionIdGenerator: undefined, // stateless mode — no session tracking
    });
    const server = buildMcpServer();
    await server.connect(transport);
    return transport.handleRequest(request);
  },
};

export default new OAuthProvider({
  apiRoute: "/mcp",
  apiHandler: mcpApiHandler,
  defaultHandler: DescopeHandler,
  authorizeEndpoint: "/authorize",
  tokenEndpoint: "/oauth/token",
  clientRegistrationEndpoint: "/oauth/register",
});
