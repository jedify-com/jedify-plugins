# jedify-lens

MCP server for data warehouse schema context generation. Powers the `schema-context` Claude skill.

## Install

```bash
pip install jedify-lens[snowflake]   # Snowflake support
pip install jedify-lens[postgres]    # PostgreSQL / Redshift support
pip install jedify-lens[all]         # All warehouses
```

Or via uvx (recommended for MCP servers):
```bash
uvx jedify-lens[snowflake]
```

## Configuration

Set environment variables before running:

| Variable | Required for | Description |
|---|---|---|
| `WAREHOUSE_TYPE` | All | `snowflake`, `postgres`, or `redshift` |
| `SNOWFLAKE_ACCOUNT` | Snowflake | Account identifier, e.g. `xy12345.us-east-1` |
| `SNOWFLAKE_USER` | Snowflake | Username |
| `SNOWFLAKE_PASSWORD` | Snowflake | Password (or use `SNOWFLAKE_PRIVATE_KEY`) |
| `SNOWFLAKE_DATABASE` | Snowflake | Default database |
| `SNOWFLAKE_WAREHOUSE` | Snowflake | Compute warehouse |
| `SNOWFLAKE_ROLE` | Snowflake | Optional role |
| `POSTGRES_DSN` | Postgres | `postgresql://user:pass@host:5432/db` |
| `REDSHIFT_DSN` | Redshift | `postgresql://user:pass@host:5439/db` |

## Tools

- `check_registration_tool` — first-run registration check
- `register_user_tool(email, company)` — register on first use
- `list_available_tables_tool(schema_filter, include_views)` — discover tables
- `get_table_schema_tool(table_names)` — columns, types, constraints
- `sample_table_data_tool(table_name, row_limit, column_filter)` — random row sample
- `export_context_yaml_tool(enriched_context, output_path, warehouse_type)` — write YAML
