import { describe, it, expect } from "vitest";
import { buildMcpServer } from "../src/mcp";

describe("buildMcpServer", () => {
  it("registers the export_schema_context tool", () => {
    const server = buildMcpServer();
    // Reach into the SDK's internal tool registry to confirm registration.
    // @ts-expect-error – internal registry access for the test
    const reg = server._registeredTools ?? server.tools ?? {};
    expect(Object.keys(reg)).toContain("export_schema_context");
  });
});
