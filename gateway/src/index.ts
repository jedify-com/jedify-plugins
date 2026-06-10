import { OAuthProvider } from "@cloudflare/workers-oauth-provider";
import { JedifyMCP } from "./mcp.js";
import { DescopeHandler } from "./descope-handler.js";

/**
 * Export the Durable Object class so Cloudflare can resolve the DO binding.
 * The wrangler.jsonc binding "MCP_OBJECT" → "JedifyMCP" must match this name.
 */
export { JedifyMCP };

/**
 * JedifyMCP.serve("/mcp") returns a { fetch } handler that routes MCP
 * requests to the Durable Object. OAuthProvider authenticates every
 * request under /mcp before forwarding to this handler, injecting
 * ctx.props (set in DescopeHandler.completeAuthorization) onto the agent.
 */
export default new OAuthProvider({
  apiRoute: "/mcp",
  apiHandler: JedifyMCP.serve("/mcp"),
  defaultHandler: DescopeHandler,
  authorizeEndpoint: "/authorize",
  tokenEndpoint: "/oauth/token",
  clientRegistrationEndpoint: "/oauth/register",
});
