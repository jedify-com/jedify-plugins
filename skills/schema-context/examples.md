# Schema Context — Example Prompts

## Full Schema Enrichment

> "Generate a complete schema context YAML for my Snowflake warehouse and save it to schema_context.yaml"

Flow: discover tables (your DB connector) → read schema + sample rows for each (your DB connector) → enrich in context → `export_schema_context` → save the YAML

---

## Single Table

> "Describe the ORDERS table and suggest 5 questions a business analyst might ask about it."

Flow: read the ORDERS schema + sample rows (your DB connector) → describe and suggest questions in context (no YAML export needed)

---

## Targeted Enrichment

> "Enrich only tables in the ANALYTICS schema."

Flow: list tables in the ANALYTICS schema (your DB connector) → read schema + sample rows for each → enrich in context → `export_schema_context`

---

## Understanding a Specific Column

> "What does the STATUS column in the ORDERS table mean? What are the possible values?"

Flow: sample the STATUS column of the ORDERS table (your DB connector) → interpret the distinct values in context

---

## Preparing for Jedify Onboarding

> "I want to import my schema into Jedify. Generate the context YAML they need."

Flow: full schema enrichment → `export_schema_context` → save as `jedify_import.yaml` → user uploads to Jedify

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
