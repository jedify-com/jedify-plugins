import logging
from mcp.server.fastmcp import FastMCP

from jedify_lens.tools.registration import (
    check_registration,
    browser_login,
    save_company_context,
)
from jedify_lens.tools.export_yaml import export_context_yaml

logging.basicConfig(level=logging.WARNING)

mcp = FastMCP("jedify-schema-context")


@mcp.tool()
async def check_registration_tool() -> dict:
    """
    Check if the user is signed in. ALWAYS call this first.
    Returns registered=true (with saved company context) or registered=false with an action to take.
    """
    return await check_registration()


@mcp.tool()
async def login_tool() -> dict:
    """
    Open the Jedify sign-in page in the user's browser and wait for them to complete authentication.
    Call this when check_registration_tool returns registered=false.
    This tool blocks until the user finishes signing in (up to 5 minutes).
    No input needed — everything happens in the browser.
    """
    return await browser_login()


@mcp.tool()
async def save_company_context_tool(context: str) -> dict:
    """
    Save optional context about the company or dataset to improve enrichment quality.
    Claude should assemble this from whatever the user provides (URL, file, or free text)
    before calling this tool. Saved context is reused automatically on future runs.

    Args:
        context: Free-text description of the company, its data, or the purpose of the warehouse
    """
    return await save_company_context(context=context)


@mcp.tool()
async def export_context_yaml_tool(
    enriched_context: dict,
    output_path: str = "",
    warehouse_type: str = "",
) -> dict:
    """
    Write the enriched schema context to a YAML file.
    Call this after all tables have been analyzed and enriched.

    Args:
        enriched_context: The schema context dict (tables with labels, descriptions, etc.)
        output_path: File path to write to (e.g. "schema_context.yaml"). Empty = return as string.
        warehouse_type: Label for the YAML header (e.g. "snowflake", "bigquery", "postgres")
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
