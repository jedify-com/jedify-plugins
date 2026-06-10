import { defineWorkersConfig } from "@cloudflare/vitest-pool-workers/config";
import { defineConfig } from "vitest/config";

// The MCP server imports @modelcontextprotocol/sdk which depends on ajv (JSON imports).
// The Cloudflare Workers vitest pool cannot load JSON modules, so the mcp test runs in
// the standard Node.js forks pool while everything else runs in the Workers pool.
export default defineConfig({
  test: {
    projects: [
      // Workers pool — all tests except mcp
      defineWorkersConfig({
        test: {
          name: "workers",
          include: ["test/**/*.test.ts"],
          exclude: ["test/mcp.test.ts", "test/descope.test.ts"],
          poolOptions: {
            workers: { wrangler: { configPath: "./wrangler.jsonc" } },
          },
        },
      }),
      // Node.js forks pool — mcp test (needs ajv JSON imports) and descope test (needs vi.stubGlobal)
      {
        test: {
          name: "node",
          include: ["test/mcp.test.ts", "test/descope.test.ts"],
          pool: "forks",
          environment: "node",
        },
      },
    ],
  },
});
