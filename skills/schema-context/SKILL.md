---
name: schema-context
description: Generates rich semantic context YAML for data warehouse schemas. Use when a user wants to document their database, understand what tables and columns mean, label their schema for an AI or NL-to-SQL tool, or prepare context for Jedify onboarding. Works with any connected database MCP server (Snowflake, BigQuery, PostgreSQL).
---

# Schema Context Skill

This skill generates a structured YAML file describing every table and column with business labels, descriptions, semantic types, and example questions. It works by using whatever database MCP server you already have connected — it does not create its own connection.

## Step 1 — Authentication

1. Call `jedify-schema-context:check_registration_tool`.
   - If `registered: true` → note the `company_context` field (may be empty) and proceed to Step 1b.
   - If `registered: false` → call `jedify-schema-context:login_tool` immediately. Tell the user: "Opening the sign-in page in your browser — complete it there and come back."

2. `login_tool` opens Descope in the user's browser and blocks until they finish signing in. When it returns:
   - If `success: true` → follow the `action` field, then continue to Step 1b.
   - If `success: false` → follow the `action` field (usually just retry).

## Step 1b — Company Context (optional, first run only)

After a successful sign-in — or if `check_registration_tool` returned `registered: true` but `company_context` is empty — offer this step once:

> "To make your schema descriptions more accurate, I can use some context about your company or data. You can share any of the following (or skip this):
> - A URL (e.g. your website, a data catalog, or internal docs page)
> - A file path to a README, data dictionary, or onboarding doc
> - A short description in your own words"

- If the user shares a **URL**: fetch and summarize the relevant content yourself, then call `jedify-schema-context:save_company_context_tool(context)` with your summary.
- If the user shares a **file path**: read the file, extract the relevant context, and call `save_company_context_tool` with it.
- If the user shares **free text**: pass it directly to `save_company_context_tool`.
- If the user skips: move on — this step is optional.

On future runs, `check_registration_tool` returns the saved `company_context` automatically. Skip this step if it's already non-empty.

## Step 2 — Detect the Connected Database MCP Server

Look at your available tools and identify a SQL-capable tool. Work through these checks in order:

**Known patterns (check first):**

| If you see these tools… | Server | DB type |
|---|---|---|
| `read_query` + `list_tables` + `describe_table` | mcp-snowflake-server | Snowflake |
| `execute_query` | Snowflake community server | Snowflake |
| Tool name contains `snowflake` | other Snowflake server | Snowflake |
| `execute-query` + `list-tables` | mcp-server-bigquery | BigQuery |
| Tool name contains `bigquery` or `bq-` | other BigQuery server | BigQuery |
| `query` with a `sql` parameter | server-postgres | PostgreSQL |
| Tool name contains `postgres` | other Postgres server | PostgreSQL |

**Broad fallback (if nothing matched above):**

Look for any tool whose name contains any of: `sql`, `query`, `execute`, `run_sql`, `read`. If you find one, use it — try a probe query (`SELECT 1`) to confirm it works and to understand its parameter names. Infer the DB type from the tool's description, MCP server name, or the probe result.

**If still nothing**, ask the user:

> I can't find a database tool in my available tools. Which database MCP server do you have connected, and what is the tool name I should use to run SQL queries?

Only stop if the user confirms no database is connected, then say:

> To use Jedify Schema Context, please connect a database MCP server and restart Claude Code:
>
> - **Snowflake**: `uvx mcp-snowflake-server` — see REFERENCE.md
> - **BigQuery**: `uvx mcp-server-bigquery` — see REFERENCE.md
> - **PostgreSQL**: `npx @modelcontextprotocol/server-postgres` — see REFERENCE.md

## Step 3 — Discover Tables

Use the approach that matches the server you detected.

### mcp-snowflake-server (preferred Snowflake path)

Use the dedicated tools — no raw SQL needed:

1. Call `list_databases` to see available databases
2. Call `list_schemas` with the target database
3. Call `list_tables` with the target database and schema

### Other Snowflake servers (execute_query / raw SQL)

```sql
SHOW SCHEMAS IN DATABASE <database>;
SHOW TABLES IN SCHEMA <database>.<schema>;
```

### BigQuery (execute-query or raw SQL)

```sql
SELECT table_name, table_type
FROM `<project>.<dataset>.INFORMATION_SCHEMA.TABLES`
ORDER BY table_name;
```

### PostgreSQL (query tool)

```sql
SELECT table_schema, table_name, table_type
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY table_schema, table_name;
```

If the schema has many tables, ask the user which schemas or table groups to focus on. Process 5–10 tables at a time.

## Step 4 — Get Schema and Sample Data

For each table, get columns and a row sample.

### mcp-snowflake-server

Call `describe_table` with the table name — it returns columns, types, and constraints directly.

Then get sample rows:
```sql
SELECT * FROM <database>.<schema>.<table> LIMIT 10;
```
(use `read_query` with this SQL)

### Other Snowflake servers

```sql
DESCRIBE TABLE <database>.<schema>.<table>;
SELECT * FROM <database>.<schema>.<table> LIMIT 10;
```

### BigQuery

```sql
SELECT column_name, data_type, is_nullable
FROM `<project>.<dataset>.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = '<table>'
ORDER BY ordinal_position;

SELECT * FROM `<project>.<dataset>.<table>` LIMIT 10;
```

### PostgreSQL

```sql
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = '<schema>' AND table_name = '<table>'
ORDER BY ordinal_position;

SELECT * FROM <schema>.<table> LIMIT 10;
```

## Step 5 — Enrich

Using the column definitions, sample rows, and any company context you collected, generate semantic enrichment for each table and column. If company context is available, use it to write more accurate descriptions and generate more relevant example questions — for example, if the company is in e-commerce, frame questions around revenue, orders, and customers rather than generic terms.

**Table-level:**
- `label`: human-readable name (e.g. "Customer Orders" for FACT_ORDERS)
- `description`: 1–2 sentences on business purpose
- `semantic_type`: `fact` | `dimension` | `lookup` | `bridge` | `aggregate` | `staging`
- `primary_entity`: the main business object (e.g. "Order", "Customer")
- `example_questions`: 3 natural language questions a business user might ask

**Column-level:**
- `label`: human-readable name
- `description`: what this column contains
- `semantic_type`: `identifier` | `metric` | `dimension` | `date` | `boolean` | `text` | `numeric`
- `example_values`: up to 5 distinct real values from your sample (for non-sensitive columns)
- `suggested_aggregations`: for metric columns — `SUM`, `AVG`, `COUNT`, etc.

**Relationships:** if you see foreign key columns (e.g. `customer_id`), infer the likely join and record it.

## Step 6 — Export

Call `jedify-schema-context:export_context_yaml_tool` with:
- `enriched_context`: the full dict you assembled
- `output_path`: `"schema_context.yaml"` (or ask the user for a preferred path)
- `warehouse_type`: `"snowflake"` / `"bigquery"` / `"postgres"` based on what you detected

## Tips

- Sample data is the most valuable input — real values let you write accurate descriptions instead of guessing from column names.
- For wide tables (50+ columns), focus on ID columns, key business columns (names, statuses, dates, amounts), and provide briefer descriptions for repetitive columns.
- `semantic_type: fact` = transactional tables (orders, events, payments). `dimension` = reference/lookup tables (customers, products, regions).
- If you get a permissions error, try `SELECT * FROM <table> LIMIT 0` to infer columns from the empty result set.
