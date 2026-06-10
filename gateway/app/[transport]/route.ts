import { createMcpHandler, withMcpAuth } from "mcp-handler";
import type { AuthInfo } from "@modelcontextprotocol/sdk/server/auth/types.js";
import { createRemoteJWKSet, jwtVerify } from "jose";
import { z } from "zod";
import { buildSchemaContextYaml } from "@/lib/yaml";

// Descope project "Jedify Plugin (MCP)" — isolated from prod (jedify-production).
const DESCOPE_ISSUER =
  "https://api.descope.com/v1/apps/P3EwuWB0eAPKe8h4vvQ2QhinomOE";
const JWKS = createRemoteJWKSet(
  new URL(
    "https://api.descope.com/P3EwuWB0eAPKe8h4vvQ2QhinomOE/.well-known/jwks.json",
  ),
);

const handler = createMcpHandler(
  (server) => {
    server.registerTool(
      "export_schema_context",
      {
        title: "Export schema context",
        description:
          "Format an enriched data-warehouse schema context into Jedify's schema-context YAML. " +
          "Call after the schema has been read (via the user's warehouse connector) and enriched. " +
          "Returns the YAML as text for the user to save.",
        annotations: {
          readOnlyHint: true,
          openWorldHint: false,
        },
        inputSchema: {
          enriched_context: z
            .object({ tables: z.array(z.any()) })
            .passthrough()
            .describe(
              "Object with a `tables` array; each table has label, description, semantic_type, columns, etc.",
            ),
          warehouse_type: z
            .string()
            .default("")
            .describe('e.g. "snowflake", "bigquery", "postgres"'),
        },
      },
      async ({ enriched_context, warehouse_type }) => {
        try {
          const text = buildSchemaContextYaml(enriched_context, warehouse_type);
          return { content: [{ type: "text" as const, text }] };
        } catch (e) {
          return {
            isError: true,
            content: [
              {
                type: "text" as const,
                text: `Failed to build schema context YAML: ${e instanceof Error ? e.message : String(e)}`,
              },
            ],
          };
        }
      },
    );
  },
  {},
  { basePath: "" },
);

const verifyToken = async (
  _req: Request,
  bearerToken?: string,
): Promise<AuthInfo | undefined> => {
  if (!bearerToken) return undefined;
  try {
    const { payload } = await jwtVerify(bearerToken, JWKS, {
      issuer: DESCOPE_ISSUER,
    });
    const scope =
      typeof payload.scope === "string" ? payload.scope.split(" ") : [];
    const clientId =
      (payload.azp as string) ??
      (Array.isArray(payload.aud)
        ? payload.aud[0]
        : (payload.aud as string)) ??
      "";
    return {
      token: bearerToken,
      scopes: scope,
      clientId,
      expiresAt:
        typeof payload.exp === "number" ? payload.exp : undefined,
      extra: { email: (payload.email as string) ?? "" },
    };
  } catch {
    return undefined;
  }
};

const authHandler = withMcpAuth(handler, verifyToken, {
  required: true,
  resourceMetadataPath: "/.well-known/oauth-protected-resource",
});

export { authHandler as GET, authHandler as POST };
