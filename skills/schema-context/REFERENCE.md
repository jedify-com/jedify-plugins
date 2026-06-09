# Schema Context — Reference

## Setup

Jedify Schema Context works with your existing database MCP server. You do **not** need to configure separate credentials — just connect your database MCP server and jedify-lens handles the rest.

### 1. Add jedify-lens to Claude Code

Add this to your `~/.claude/settings.json` under `mcpServers`:

```json
{
  "mcpServers": {
    "jedify-schema-context": {
      "command": "uvx",
      "args": ["jedify-lens"]
    }
  }
}
```

### 2. Connect Your Database MCP Server

Add one of the following to `mcpServers` as well:

#### Snowflake

```json
"snowflake": {
  "command": "uvx",
  "args": ["mcp-server-snowflake"],
  "env": {
    "SNOWFLAKE_ACCOUNT": "your-account.region",
    "SNOWFLAKE_USER": "your_user",
    "SNOWFLAKE_PASSWORD": "your_password",
    "SNOWFLAKE_DATABASE": "YOUR_DATABASE",
    "SNOWFLAKE_SCHEMA": "PUBLIC",
    "SNOWFLAKE_WAREHOUSE": "COMPUTE_WH"
  }
}
```

See: [Snowflake MCP Server](https://github.com/Snowflake-Labs/mcp)

#### BigQuery

```json
"bigquery": {
  "command": "npx",
  "args": ["-y", "mcp-server-bigquery"],
  "env": {
    "BIGQUERY_PROJECT": "your-gcp-project",
    "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/service-account.json"
  }
}
```

See: [mcp-server-bigquery](https://github.com/LucasHild/mcp-server-bigquery)

#### PostgreSQL

```json
"postgres": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://user:password@host:5432/database"]
}
```

See: [@modelcontextprotocol/server-postgres](https://github.com/modelcontextprotocol/servers/tree/main/src/postgres)

---

## YAML Output Schema

```yaml
version: "1.0"
generated_at: "2026-05-20T10:00:00+00:00"
warehouse: snowflake

tables:
  - name: "DB.PUBLIC.ORDERS"
    label: "Customer Orders"
    description: "Tracks all customer purchase orders including status lifecycle and totals."
    semantic_type: fact           # fact | dimension | lookup | bridge | aggregate | staging
    primary_entity: "Order"
    row_count: 1500000
    is_view: false
    partition_column: "CREATED_AT"

    example_questions:
      - "What is the total revenue by month?"
      - "How many orders were placed last week?"
      - "What is the average order value by region?"

    columns:
      - name: "ORDER_ID"
        label: "Order ID"
        description: "Unique surrogate key for each order record."
        semantic_type: identifier   # identifier | metric | dimension | date | boolean | text | numeric
        is_primary_key: true
        is_nullable: false
        sql_type: "NUMBER(38,0)"
        example_values: []

      - name: "TOTAL_AMOUNT"
        label: "Order Total (USD)"
        description: "Total monetary value of the order net of discounts."
        semantic_type: metric
        sql_type: "FLOAT"
        example_values: ["49.99", "129.00", "12.50"]
        suggested_aggregations: ["SUM", "AVG", "MEDIAN"]

    relationships:
      - related_table: "DB.PUBLIC.CUSTOMERS"
        join_type: "many-to-one"
        join_columns: {"CUSTOMER_ID": "CUSTOMER_ID"}
        description: "Each order belongs to one customer"
```

---

## jedify-lens MCP Tools

These are the only tools jedify-lens registers. All database queries go through your connected DB MCP server.

| Tool | Description |
|---|---|
| `check_registration_tool` | First-run check — call before anything else (returns `registered` and any saved `company_context`) |
| `login_tool` | Opens the Descope sign-up / sign-in page in the browser; blocks until the user completes it |
| `save_company_context_tool(context)` | Save optional company/dataset context to improve enrichment |
| `export_context_yaml_tool(enriched_context, output_path, warehouse_type)` | Write YAML file to disk |

---

## Troubleshooting

**"No database tools found"**: You need a database MCP server connected. See the setup section above.

**Catalog query returns empty**: The connected DB user may lack read access on `information_schema` or system catalog views. Grant `USAGE` on the relevant schemas.

**Snowflake SHOW TABLES returns nothing**: Try `SHOW SCHEMAS IN DATABASE <db>` first, then `SHOW TABLES IN SCHEMA <db>.<schema>`.

**BigQuery INFORMATION_SCHEMA access denied**: Your service account needs `roles/bigquery.metadataViewer` and `roles/bigquery.dataViewer` on the relevant datasets.

**jedify-lens not found**: Run `uvx jedify-lens --help` to verify installation. If missing, run `pip install jedify-lens`.

---

## Authentication (Descope)

Sign-in is handled by Jedify's Descope **Inbound App**. The prod project is baked into
the package, so end users need no auth configuration — the first run opens a browser to
sign up / sign in.

**Developers only** — point the plugin at a non-prod Descope project with env overrides:

| Variable | Default (prod) | Purpose |
|---|---|---|
| `DESCOPE_BASE_URL` | `https://auth.app.jedify.com` | Descope base URL (custom domain) |
| `DESCOPE_CLIENT_ID` | `P2fGtsAm5ziAZr0swDyMDO7Tce87` | Inbound App client_id (public) |

Both values are **public identifiers** (like an OAuth `client_id`) — there is no client
secret. The flow is a public-client Authorization Code + PKCE exchange with a
`http://localhost:8765/callback` redirect, which must be allow-listed in the Descope
Inbound App.
