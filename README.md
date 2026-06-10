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
      "args": ["jedify-lens"]
    }
  }
}
```

`jedify-lens` needs no warehouse credentials of its own — it reads your schema through whatever **database MCP server you already have connected** (Snowflake, BigQuery, or Postgres). See [skills/schema-context/REFERENCE.md](skills/schema-context/REFERENCE.md) for connecting a database MCP server and the YAML output schema.

Then ask Claude: *"Generate a schema context YAML for my warehouse and save it to schema_context.yaml"*

---

## Python MCP Server

The `jedify-lens` PyPI package powers this skill. It's a standalone MCP server with no dependency on Jedify's backend, and it needs no warehouse drivers — it works through your connected database MCP server.

```bash
pip install jedify-lens
```

Source: [server/](server/)

---

## License

MIT — [jedify.com](https://jedify.com)
