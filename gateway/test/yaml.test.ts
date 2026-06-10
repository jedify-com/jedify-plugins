import { describe, it, expect } from "vitest";
import { buildSchemaContextYaml } from "../src/yaml";

describe("buildSchemaContextYaml", () => {
  it("wraps tables with version/warehouse header and preserves key order", () => {
    const out = buildSchemaContextYaml(
      { tables: [{ name: "orders", label: "Customer Orders", semantic_type: "fact" }] },
      "postgres",
    );
    expect(out).toContain("# Schema Context — generated ");
    expect(out).toContain("version: '1.0'");
    expect(out).toContain("warehouse: postgres");
    expect(out).toContain("name: orders");
    expect(out).toContain("label: Customer Orders");
    expect(out.indexOf("name: orders")).toBeLessThan(out.indexOf("label: Customer Orders"));
  });

  it("accepts an empty tables array", () => {
    const out = buildSchemaContextYaml({ tables: [] }, "snowflake");
    expect(out).toContain("warehouse: snowflake");
    expect(out).toContain("tables: []");
  });
});
