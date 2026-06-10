import yaml from "js-yaml";

export interface EnrichedContext {
  tables: unknown[];
  [k: string]: unknown;
}

/** Mirror of the Python export_yaml.py output: a versioned, dated YAML doc. */
export function buildSchemaContextYaml(
  enriched: EnrichedContext,
  warehouseType: string,
): string {
  const now = new Date();
  const doc = {
    version: "1.0",
    generated_at: now.toISOString(),
    warehouse: warehouseType || "unknown",
    tables: enriched.tables ?? [],
  };
  const body = yaml.dump(doc, { sortKeys: false, lineWidth: -1, noRefs: true });
  const header = `# Schema Context — generated ${now.toISOString().slice(0, 10)}\n`;
  return header + body;
}
