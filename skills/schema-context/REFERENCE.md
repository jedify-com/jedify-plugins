# Schema Context — Reference

## Setup

Jedify Schema Context works with your existing database MCP server. You do **not** need to configure separate credentials — just connect your database MCP server and sign in to the Jedify connector.

### 1. Install the Jedify Connector

Search for **Jedify** in the Claude plugin/connector directory, or install directly:

```
/plugin install jedify@jedify-com-skills
```

Sign in once when prompted — that is the only authentication step. The connector handles Jedify's OAuth flow automatically.

### 2. Connect Your Database MCP Server

Add one of the following to `mcpServers` in your `~/.claude/settings.json`:

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

## Jedify Connector Tool

The Jedify connector exposes a single tool:

| Tool | Description |
|---|---|
| `export_schema_context(enriched_context, warehouse_type)` | Format an enriched data-warehouse schema context into Jedify's schema-context YAML. Returns the YAML as text. |

**Parameters:**

- `enriched_context` — object with a `tables` array; each table has `label`, `description`, `semantic_type`, `columns`, etc. (see YAML Output Schema below).
- `warehouse_type` — string identifying the warehouse, e.g. `"snowflake"`, `"bigquery"`, `"postgres"`.

Typical workflow: read the schema from your connected database MCP server, enrich the table and column metadata, then call `export_schema_context` to produce the YAML for Jedify.

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

## Troubleshooting

**"No database tools found"**: You need a database MCP server connected. See the setup section above.

**Catalog query returns empty**: The connected DB user may lack read access on `information_schema` or system catalog views. Grant `USAGE` on the relevant schemas.

**Snowflake SHOW TABLES returns nothing**: Try `SHOW SCHEMAS IN DATABASE <db>` first, then `SHOW TABLES IN SCHEMA <db>.<schema>`.

**BigQuery INFORMATION_SCHEMA access denied**: Your service account needs `roles/bigquery.metadataViewer` and `roles/bigquery.dataViewer` on the relevant datasets.

---

## Authentication

Sign-in is handled by the Jedify connector's OAuth flow. When you first use the connector, you will be prompted to sign in via your browser — complete the sign-in once and the connector manages the session from that point on.

No manual auth configuration is required by end users. The connector's OAuth client is pre-configured with Jedify's identity provider.
