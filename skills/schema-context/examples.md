# Schema Context — Example Prompts

## Full Schema Enrichment

> "Generate a complete schema context YAML for my Snowflake warehouse and save it to schema_context.yaml"

Flow: check_registration → list_available_tables → get_table_schema (all) → sample_table_data (all) → enrich in context → export_context_yaml

---

## Single Table

> "Describe the ORDERS table and suggest 5 questions a business analyst might ask about it."

Flow: check_registration → get_table_schema(["DB.PUBLIC.ORDERS"]) → sample_table_data("DB.PUBLIC.ORDERS") → generate description in context (no YAML export needed)

---

## Targeted Enrichment

> "Enrich only tables in the ANALYTICS schema."

Flow: list_available_tables(schema_filter="*.ANALYTICS.*") → get_table_schema + sample_table_data for each → export_context_yaml

---

## Understanding a Specific Column

> "What does the STATUS column in the ORDERS table mean? What are the possible values?"

Flow: sample_table_data("DB.PUBLIC.ORDERS", column_filter=["STATUS"]) → interpret values in context

---

## Preparing for Jedify Onboarding

> "I want to import my schema into Jedify. Generate the context YAML they need."

Flow: full schema enrichment → export_context_yaml("jedify_import.yaml") → user uploads to Jedify

---

## Expected Output Excerpt

```yaml
# Schema Context — generated 2026-05-12
version: '1.0'
generated_at: '2026-05-12T10:00:00+00:00'
warehouse: snowflake

tables:
- name: DB.PUBLIC.ORDERS
  label: Customer Orders
  description: Tracks all customer purchase orders from placement through fulfillment,
    including status lifecycle and financial totals.
  semantic_type: fact
  primary_entity: Order
  row_count: 1500000
  example_questions:
  - What is the total revenue by month?
  - How many orders were placed last week?
  - What is the average order value by region?
  columns:
  - name: ORDER_ID
    label: Order ID
    description: Unique surrogate key for each order record.
    semantic_type: identifier
    is_nullable: false
    sql_type: NUMBER(38,0)
  - name: TOTAL_AMOUNT
    label: Order Total (USD)
    description: Total monetary value of the order in US dollars, net of discounts.
    semantic_type: metric
    example_values:
    - '49.99'
    - '129.00'
    - '12.50'
    suggested_aggregations:
    - SUM
    - AVG
    - MEDIAN
```
