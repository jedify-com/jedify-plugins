import logging

from jedify_lens.connectors.base import DataClient
from jedify_lens.connectors.ds_types import QueryFailed

logger = logging.getLogger("jedify_lens.tools")


async def get_table_schema(connector: DataClient, table_names: list[str]) -> dict:
    """
    Retrieve structural metadata for one or more tables.
    Returns column names, SQL types, nullability, constraints, row count, and partition info.

    Args:
        table_names: List of fully qualified table names (e.g. ["DB.SCHEMA.ORDERS"])
    """
    results = {}
    errors = []

    for table_name in table_names:
        try:
            schema = await connector.get_table_metadata(table_name)
            results[table_name] = {
                "columns": [
                    {
                        "column_name": col.column_name,
                        "type": col.type,
                        "is_nullable": col.is_nullable,
                        "comment": col.comment,
                    }
                    for col in schema.columns_schema
                ],
                "constraints": {
                    "primary_key": schema.constraints.primary_key,
                    "foreign_keys": [
                        {
                            "source_column": fk.source_column,
                            "target_column": fk.target_column,
                            "target_table": fk.target_table,
                        }
                        for fk in schema.constraints.foreign_keys
                    ],
                    "unique_keys": schema.constraints.unique_keys,
                    "not_null": schema.constraints.not_null,
                },
                "partition": {
                    "partitioning_type": schema.partition.partitioning_type,
                    "partitioning_field": schema.partition.partitioning_field,
                },
                "row_count": schema.row_count,
                "is_view": schema.is_view,
                "comment": schema.comment,
            }
        except Exception as e:
            logger.warning(f"Failed to get schema for {table_name}: {e}")
            errors.append({"table": table_name, "error": str(e)})

    return {"tables": results, "errors": errors}
