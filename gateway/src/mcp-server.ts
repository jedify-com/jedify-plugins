import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { buildSchemaContextYaml } from "./yaml.js";

/**
 * Creates a standalone configured McpServer.
 * Used by JedifyMCP.init() and directly by unit tests (no Durable Object runtime needed).
 */
export function buildMcpServer(): McpServer {
  const server = new McpServer({ name: "Jedify", version: "0.1.0" });

  server.registerTool(
    "export_schema_context",
    {
      description:
        "Format an enriched data-warehouse schema context into Jedify's schema-context YAML. " +
        "Call after the schema has been read (via the user's warehouse connector) and enriched. " +
        "Returns the YAML as text for the user to save.",
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
        const yamlText = buildSchemaContextYaml(enriched_context, warehouse_type);
        return { content: [{ type: "text" as const, text: yamlText }] };
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

  return server;
}
