# jedify-com/skills

Claude Code skills and MCP servers by [Jedify](https://jedify.com).

## Skills

### `schema-context`

Connect Claude to your data warehouse and generate rich semantic context YAML for every table and column — labels, descriptions, semantic types, and example questions.

**Works with**: Snowflake, PostgreSQL, Redshift

**Install via Claude Marketplace**: [claude.com/plugins/jedify-schema-context](https://claude.com/plugins/jedify-schema-context)

**Or install via CLI**:
```bash
npx skills add jedify-com/skills -s schema-context
```

**Or manually** — add to your `~/.claude/settings.json`:
```json
{
  "mcpServers": {
    "jedify-schema-context": {
      "command": "uvx",
      "args": ["jedify-lens[snowflake]"],
      "env": {
        "WAREHOUSE_TYPE": "snowflake",
        "SNOWFLAKE_ACCOUNT": "your-account.region",
        "SNOWFLAKE_USER": "your_user",
        "SNOWFLAKE_PASSWORD": "your_password",
        "SNOWFLAKE_DATABASE": "YOUR_DATABASE",
        "SNOWFLAKE_WAREHOUSE": "COMPUTE_WH"
      }
    }
  }
}
```

Then ask Claude: *"Generate a schema context YAML for my warehouse and save it to schema_context.yaml"*

See [skills/schema-context/REFERENCE.md](skills/schema-context/REFERENCE.md) for full credential setup and YAML output schema.

---

## Python MCP Server

The `jedify-lens` PyPI package powers this skill. It's a standalone MCP server with no dependency on Jedify's backend.

```bash
pip install jedify-lens[snowflake]   # Snowflake
pip install jedify-lens[postgres]    # PostgreSQL / Redshift
pip install jedify-lens[all]         # All warehouses
```

Source: [server/](server/)

---

## License

MIT — [jedify.com](https://jedify.com)
