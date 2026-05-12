import logging
from mcp.server.fastmcp import FastMCP

from jedify_lens.connectors.factory import connector_from_env
from jedify_lens.tools.registration import check_registration, register_user
from jedify_lens.tools.list_tables import list_available_tables
from jedify_lens.tools.get_schema import get_table_schema
from jedify_lens.tools.sample_data import sample_table_data
from jedify_lens.tools.export_yaml import export_context_yaml

logging.basicConfig(level=logging.WARNING)

mcp = FastMCP("jedify-schema-context")

# Connector is created lazily on first use so startup errors surface as tool errors.
_connector = None


def _get_connector():
    global _connector
    if _connector is None:
        _connector = connector_from_env()
    return _connector


@mcp.tool()
async def check_registration_tool() -> dict:
    """
    Check if the user is registered. ALWAYS call this first before any other tool.
    If not registered, ask the user for their email and call register_user_tool.
    """
    return await check_registration()


@mcp.tool()
async def register_user_tool(email: str, company: str = "") -> dict:
    """
    Register the user. Call this after check_registration_tool returns registered=false.

    Args:
        email: User's email address
        company: Optional company name
    """
    return await register_user(email=email, company=company)


@mcp.tool()
async def list_available_tables_tool(
    schema_filter: str = "",
    include_views: bool = True,
) -> dict:
    """
    Discover all accessible tables and views in the connected warehouse.

    Args:
        schema_filter: Optional glob pattern, e.g. "analytics.*" or "*.orders"
        include_views: Whether to include views (default true)
    """
    return await list_available_tables(
        connector=_get_connector(),
        schema_filter=schema_filter,
        include_views=include_views,
    )


@mcp.tool()
async def get_table_schema_tool(table_names: list[str]) -> dict:
    """
    Get structural metadata for one or more tables: columns, types, constraints, row counts.

    Args:
        table_names: Fully qualified table names, e.g. ["DB.SCHEMA.ORDERS", "DB.SCHEMA.USERS"]
    """
    return await get_table_schema(connector=_get_connector(), table_names=table_names)


@mcp.tool()
async def sample_table_data_tool(
    table_name: str,
    row_limit: int = 25,
    column_filter: list[str] | None = None,
) -> dict:
    """
    Fetch a random sample of rows from a table so you can see real values before generating descriptions.

    Args:
        table_name: Fully qualified table name
        row_limit: Rows to sample (default 25, max 200)
        column_filter: Optional list of column names to include
    """
    return await sample_table_data(
        connector=_get_connector(),
        table_name=table_name,
        row_limit=row_limit,
        column_filter=column_filter,
    )


@mcp.tool()
async def export_context_yaml_tool(
    enriched_context: dict,
    output_path: str = "",
    warehouse_type: str = "",
) -> dict:
    """
    Write the enriched schema context Claude has generated to a YAML file.
    Call this after you have analyzed all tables and produced the enriched context dict.

    Args:
        enriched_context: The schema context you generated (tables with labels, descriptions, etc.)
        output_path: File path to write to (e.g. "schema_context.yaml"). Empty = return as string.
        warehouse_type: Label for the YAML header (e.g. "snowflake")
    """
    return await export_context_yaml(
        enriched_context=enriched_context,
        output_path=output_path,
        warehouse_type=warehouse_type,
    )


def main():
    mcp.run()


if __name__ == "__main__":
    main()
