import logging
from datetime import datetime, timezone
from pathlib import Path

import yaml

logger = logging.getLogger("jedify_lens.tools")


async def export_context_yaml(
    enriched_context: dict,
    output_path: str = "",
    warehouse_type: str = "",
) -> dict:
    """
    Serialize enriched schema context to YAML. Pass the analysis Claude has generated.

    Args:
        enriched_context: Dict with tables list, each table having label, description,
                          semantic_type, columns, example_questions, etc.
        output_path: Absolute file path to write the YAML. If empty, returns YAML string only.
        warehouse_type: Warehouse type label for the YAML header (e.g. "snowflake")
    """
    doc = {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "warehouse": warehouse_type or "unknown",
        "tables": enriched_context.get("tables", enriched_context),
    }

    yaml_str = yaml.dump(doc, allow_unicode=True, default_flow_style=False, sort_keys=False)
    header = f"# Schema Context — generated {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n"
    full_yaml = header + yaml_str

    result: dict = {
        "success": True,
        "table_count": len(doc["tables"]) if isinstance(doc["tables"], list) else len(doc["tables"]),
        "yaml_preview": full_yaml[:500] + ("..." if len(full_yaml) > 500 else ""),
    }

    if output_path:
        try:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(full_yaml, encoding="utf-8")
            result["output_path"] = str(path.resolve())
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
    else:
        result["yaml"] = full_yaml

    return result
