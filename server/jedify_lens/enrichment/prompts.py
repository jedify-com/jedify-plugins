"""Table analysis prompts — extracted from Jedify's taxonomy builder."""

import json
from typing import Any


def analyze_table_structure(
    table_name: str,
    sample_rows: list[dict[str, Any]],
    row_count: int,
    total_rows: int,
) -> str:
    """Prompt for slim table analysis (concept-focused, fast)."""
    column_count = len(sample_rows[0].keys()) if sample_rows else 0
    is_wide = column_count > 50

    wide_note = f"""
## Wide Table Optimization
This table has {column_count} columns. Focus on:
- ALL ID columns (ending with _id, _key, or containing "id")
- 1-2 representative columns per concept prefix
- Key business columns (names, statuses, dates)
For repetitive columns, provide brief descriptions and group by concept.
""" if is_wide else ""

    return f"""You are a data analyst analyzing a database table to understand its structure and business purpose.

## Table Information
- **Table Name**: {table_name}
- **Sample Size**: {row_count} rows (out of {total_rows} total)
- **Column Count**: {column_count} columns{wide_note}

## Sample Data
```json
{_format_sample_rows(sample_rows)}
```

## Analysis Requirements

### 1. Table Summary
2-3 sentence summary of the table's business purpose. What does it represent? What process does it track?

### 2. Column Analysis
For EACH column:
- **column_name**: exact column name
- **data_type**: string, integer, float, boolean, date, timestamp, array, object
- **scope**: business concept this column belongs to (e.g. "User", "Order", "Product")
- **description**: {"5-10 word description" if is_wide else "clear description of what this column represents"}
- **is_id_column**: true if ID/key column (ends with _id, _key, contains "id", or is unique identifier)

### 3. Concept Hints
Group columns by business entity (NOT dimensions like geography, industry, demographics — fold those into the parent entity):
- **concept_name**: simple noun ("Gift", "User", "Order")
- **columns**: list of column names
- **description**: how these columns relate to the concept

### 4. ID Columns
List ALL identifier/key columns.

## Output Format
```json
{{
  "table_summary": "2-3 sentence summary",
  "columns": [
    {{"column_name": "order_id", "data_type": "string", "scope": "Order", "description": "Unique order identifier", "is_id_column": true}}
  ],
  "concept_hints": [
    {{"concept_name": "Order", "columns": ["order_id", "order_status"], "description": "Order entity columns"}}
  ],
  "id_columns": ["order_id", "user_id"]
}}
```
Ensure valid JSON output. Analyze ALL columns.
"""


def analyze_table_structure_detailed(
    table_name: str,
    sample_rows: list[dict[str, Any]],
    row_count: int,
    total_rows: int,
) -> str:
    """Prompt for detailed table analysis including statistics and relationships."""
    column_count = len(sample_rows[0].keys()) if sample_rows else 0

    return f"""You are a data analyst analyzing a database table in detail.

## Table Information
- **Table Name**: {table_name}
- **Sample Size**: {row_count} rows (out of {total_rows} total)
- **Column Count**: {column_count} columns

## Sample Data
```json
{_format_sample_rows(sample_rows)}
```

## Analysis Requirements

### 1. Table Summary
2-3 sentence summary of business purpose.

### 2. Column Analysis
For EACH column:
- **column_name**, **data_type**, **scope**, **description**, **is_id_column**
- **statistics**: {{"unique_count": int, "null_count": int, "sample_values": [4 values]}}

### 3. Concept Hints
Business entity groupings (exclude dimension groups like geography, demographics).

### 4. ID Columns

### 5. Relationships
- **related_table**, **relationship_type** (one-to-many / many-to-one / many-to-many), **join_columns**, **description**

### 6. Data Quality Notes
Missing values, inconsistent formatting, suspicious patterns.

## Output Format
```json
{{
  "table_summary": "summary",
  "columns": [
    {{"column_name": "order_id", "data_type": "string", "scope": "Order", "description": "Unique order ID",
      "is_id_column": true, "statistics": {{"unique_count": 1000, "null_count": 0, "sample_values": ["1","2","3","4"]}}}}
  ],
  "concept_hints": [{{"concept_name": "Order", "columns": ["order_id"], "description": "Order columns"}}],
  "id_columns": ["order_id"],
  "relationships": [{{"related_table": "users", "relationship_type": "many-to-one", "join_columns": ["user_id"], "description": "Each order belongs to one user"}}],
  "data_quality_notes": []
}}
```
"""


def _format_sample_rows(sample_rows: list[dict[str, Any]], max_chars: int = 200_000) -> str:
    try:
        full = json.dumps(sample_rows, indent=2, default=str)
    except Exception:
        full = json.dumps([{k: str(v) for k, v in r.items()} for r in sample_rows], indent=2)

    if len(full) <= max_chars:
        return full

    display: list = []
    size = 0
    for row in sample_rows:
        try:
            row_text = json.dumps(row, default=str)
        except Exception:
            row_text = json.dumps({k: str(v) for k, v in row.items()})
        if size + len(row_text) > max_chars:
            break
        display.append(row)
        size += len(row_text)

    return json.dumps(display, indent=2, default=str)
