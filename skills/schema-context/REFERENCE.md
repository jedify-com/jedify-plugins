# Schema Context — Reference

## Credential Setup

Add the following block to your `~/.claude/settings.json` under `mcpServers`, then restart Claude Code.

### Snowflake

```json
{
  "mcpServers": {
    "jedify-schema-context": {
      "command": "uvx",
      "args": ["jedify-lens[snowflake]"],
      "env": {
        "WAREHOUSE_TYPE": "snowflake",
        "SNOWFLAKE_ACCOUNT": "your-account.region",
        "SNOWFLAKE_USER": "your_user",
        "SNOWFLAKE_PASSWORD": "your_password",
        "SNOWFLAKE_DATABASE": "YOUR_DATABASE",
        "SNOWFLAKE_SCHEMA": "PUBLIC",
        "SNOWFLAKE_WAREHOUSE": "COMPUTE_WH",
        "SNOWFLAKE_ROLE": ""
      }
    }
  }
}
```

For key-pair auth, set `SNOWFLAKE_PRIVATE_KEY` (PEM string) instead of `SNOWFLAKE_PASSWORD`, and optionally `SNOWFLAKE_PASSPHRASE`.

### PostgreSQL

```json
{
  "mcpServers": {
    "jedify-schema-context": {
      "command": "uvx",
      "args": ["jedify-lens[postgres]"],
      "env": {
        "WAREHOUSE_TYPE": "postgres",
        "POSTGRES_DSN": "postgresql://user:password@host:5432/database"
      }
    }
  }
}
```

### Redshift

```json
{
  "mcpServers": {
    "jedify-schema-context": {
      "command": "uvx",
      "args": ["jedify-lens[postgres]"],
      "env": {
        "WAREHOUSE_TYPE": "redshift",
        "REDSHIFT_DSN": "postgresql://user:password@cluster.region.redshift.amazonaws.com:5439/database"
      }
    }
  }
}
```

## YAML Output Schema

```yaml
version: "1.0"
generated_at: "2026-05-12T10:00:00+00:00"
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
        is_foreign_key: false
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

## MCP Tools Reference

| Tool | Description |
|---|---|
| `check_registration_tool` | First-run check — call before anything else |
| `register_user_tool(email, company)` | Register on first use |
| `list_available_tables_tool(schema_filter, include_views)` | Discover all tables/views |
| `get_table_schema_tool(table_names)` | Columns, types, constraints, row counts |
| `sample_table_data_tool(table_name, row_limit, column_filter)` | Random row sample |
| `export_context_yaml_tool(enriched_context, output_path, warehouse_type)` | Write YAML file |

## Troubleshooting

**Server not found**: Run `uvx jedify-lens --help` to verify installation. If missing, run `pip install jedify-lens`.

**Auth errors**: Check your env vars in `~/.claude/settings.json` under `mcpServers.jedify-schema-context.env`.

**Snowflake connection timeout**: Verify `SNOWFLAKE_ACCOUNT` format: `account.region` (e.g. `xy12345.us-east-1`). Check that your IP is whitelisted.

**Empty table list**: The connected user may lack `SHOW DATABASES` privilege. Grant `USAGE` on the relevant databases and schemas.
