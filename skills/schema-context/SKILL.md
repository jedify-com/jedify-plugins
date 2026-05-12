---
name: schema-context
description: Generates rich semantic context YAML for data warehouse schemas. Use when a user wants to document their database, understand what tables and columns mean, label their schema for an AI or NL-to-SQL tool, or prepare context for Jedify onboarding. Works with Snowflake, Postgres, and Redshift.
---

# Schema Context Skill

This skill connects to a data warehouse via the `jedify-schema-context` MCP server and generates a structured YAML file describing every table and column — with business labels, descriptions, semantic types, and example questions.

## Workflow

**Always follow this order:**

1. Call `jedify-schema-context:check_registration_tool` first. If `registered` is false, ask the user for their email (and optionally company name), then call `jedify-schema-context:register_user_tool`.

2. If the user hasn't set up their warehouse credentials yet, guide them using the setup instructions in REFERENCE.md.

3. Discover tables: call `jedify-schema-context:list_available_tables_tool`. Use `schema_filter` if the user wants a specific subset.

4. For each table (or a focused subset), call `jedify-schema-context:get_table_schema_tool` and `jedify-schema-context:sample_table_data_tool` to get columns and real sample values.

5. Using the schema and sample data you now have in context, generate the semantic enrichment yourself — label each table and column with:
   - `label`: human-readable name (e.g. "Customer Orders" for FACT_ORDERS)
   - `description`: 1-2 sentences about business purpose
   - `semantic_type`: one of `fact`, `dimension`, `lookup`, `bridge`, `aggregate`, `staging` (for tables) or `identifier`, `metric`, `dimension`, `date`, `boolean`, `text`, `numeric` (for columns)
   - `example_questions`: 3 natural language questions a business user might ask

6. Call `jedify-schema-context:export_context_yaml_tool` with the enriched context dict and a file path like `schema_context.yaml`.

## Handling Large Schemas

If the warehouse has many tables, ask the user which schemas or table groups to focus on. Enrich 5-10 tables at a time. You can always run again for additional tables and merge the YAML files.

## Credential Setup

See REFERENCE.md for the exact environment variables to set per warehouse type.

## Tips

- The sample data is the most valuable input — it shows real values so you can write accurate descriptions instead of guessing from column names alone.
- For tables with 50+ columns, focus your detailed analysis on ID columns, key business columns (names, statuses, dates), and 1-2 representative columns per concept group. Provide briefer descriptions for repetitive columns.
- `semantic_type: fact` = transactional tables (orders, events, payments). `dimension` = reference/lookup tables (customers, products, regions).
