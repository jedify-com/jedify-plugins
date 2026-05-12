import fnmatch
import logging

from jedify_lens.connectors.base import DataClient

logger = logging.getLogger("jedify_lens.tools")


async def list_available_tables(
    connector: DataClient,
    schema_filter: str = "",
    include_views: bool = True,
) -> dict:
    """
    Discover all accessible tables (and optionally views) in the connected warehouse.

    Args:
        schema_filter: Optional glob pattern to filter tables, e.g. "analytics.*" or "*.orders"
        include_views: Whether to include views in results (default True)
    """
    tables = await connector.get_potential_tables()

    if not include_views:
        tables = [t for t in tables if not t.lower().endswith("_view")]

    if schema_filter:
        tables = [t for t in tables if fnmatch.fnmatch(t.lower(), schema_filter.lower())]

    return {
        "tables": tables,
        "total_count": len(tables),
        "warehouse_type": type(connector).__name__.replace("Connector", "").lower(),
    }
