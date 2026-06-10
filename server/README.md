# jedify-lens

MCP server that connects Claude to your data warehouse and generates rich **semantic context YAML** for every table and column — business labels, descriptions, semantic types, and example questions. Powers the [`schema-context`](https://github.com/jedify-com/skills) Claude skill. Standalone — no dependency on Jedify's backend.

## Install

```bash
pip install jedify-lens
```

Or, recommended for MCP servers, run it on demand with uvx:

```bash
uvx jedify-lens
```

## How it works

`jedify-lens` does **not** connect to your warehouse itself, so it needs no warehouse credentials. It works through whatever **database MCP server you already have connected** (Snowflake, BigQuery, PostgreSQL/Redshift): Claude reads your schema and sample rows through that database server, generates the semantic enrichment, and `jedify-lens` writes the structured YAML to disk.

## Tools

- `check_registration_tool` — check sign-in state (call this first)
- `login_tool` — open the Descope sign-up / sign-in page in the browser
- `save_company_context_tool(context)` — save optional company/dataset context to improve enrichment
- `export_context_yaml_tool(enriched_context, output_path, warehouse_type)` — write the schema-context YAML file

## Authentication

Sign-in uses Jedify's Descope inbound app via a public-client OAuth Authorization Code + PKCE flow — there is **no client secret**. The production project is baked in, so end users need no auth configuration. Developers can point at a non-prod project with the `DESCOPE_BASE_URL` and `DESCOPE_CLIENT_ID` environment variables (both are public identifiers).

## License

MIT — [jedify.com](https://jedify.com)
