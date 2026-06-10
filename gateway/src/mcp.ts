import { McpAgent } from "agents/mcp";
import { buildMcpServer } from "./mcp-server.js";

type UserProps = { email: string };

// The project uses @modelcontextprotocol/sdk@1.29.0 while agents bundles 1.23.0.
// Declaring server as `any` avoids the type incompatibility between the two versions.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AgentMcpServer = any;

/**
 * Jedify MCP Durable Object — serves the MCP protocol over Streamable HTTP.
 * Receives authenticated user props (email) from OAuthProvider via this.props.
 */
export class JedifyMCP extends McpAgent<Cloudflare.Env, unknown, UserProps> {
  server: AgentMcpServer = buildMcpServer();

  async init(): Promise<void> {
    // Tools are registered by buildMcpServer() at construction time.
    // init() is called by the agents runtime after onStart — nothing extra needed.
  }
}

// Re-export buildMcpServer so existing import paths keep working.
export { buildMcpServer } from "./mcp-server.js";
