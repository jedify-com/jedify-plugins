import logging

from jedify_lens.connectors.base import DataClient
from jedify_lens.connectors.ds_types import QueryOk, QueryFailed

logger = logging.getLogger("jedify_lens.tools")


async def sample_table_data(
    connector: DataClient,
    table_name: str,
    row_limit: int = 25,
    column_filter: list[str] | None = None,
) -> dict:
    """
    Fetch a random sample of rows from a table so Claude can see real values.

    Args:
        table_name: Fully qualified table name
        row_limit: Number of rows to sample (default 25, max 200)
        column_filter: Optional list of column names to include (all columns if omitted)
    """
    row_limit = min(row_limit, 200)

    col_clause = "*"
    if column_filter:
        col_clause = ", ".join(f'"{c}"' for c in column_filter)

    query = f"SELECT {col_clause} FROM {table_name} LIMIT {row_limit}"

    result = await connector.query(query, max_results=row_limit, timeout_sec=30)

    if isinstance(result, QueryFailed):
        return {
            "table_name": table_name,
            "error": result.message,
            "rows": [],
            "row_count": 0,
            "columns": [],
        }

    rows = result.data
    columns = list(rows[0].keys()) if rows else []

    # Serialize values for JSON safety
    safe_rows = []
    for row in rows:
        safe_rows.append({k: _safe_value(v) for k, v in row.items()})

    return {
        "table_name": table_name,
        "row_count": len(safe_rows),
        "columns": columns,
        "rows": safe_rows,
    }


def _safe_value(v):
    if v is None:
        return None
    if isinstance(v, (str, int, float, bool)):
        return v
    return str(v)
