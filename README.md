# jedify-com/skills

Claude Code skills by [Jedify](https://jedify.com).

## Skills

### `schema-context`

Connect Claude to your data warehouse and generate rich semantic context YAML for every table and column — labels, descriptions, semantic types, and example questions.

**Works with**: Snowflake, BigQuery, PostgreSQL, Redshift.

#### Prerequisites

1. **[Claude Code](https://claude.com/claude-code)** or **[claude.ai/workspaces](https://claude.ai)** — CLI, desktop app, VS Code extension, or Cowork.
2. **A database MCP server or connector** connected for your warehouse (Snowflake / BigQuery / PostgreSQL / Redshift). The skill reads your schema and sample rows **through this connector** — Jedify never connects to your database directly and never holds DB credentials. See [skills/schema-context/REFERENCE.md](skills/schema-context/REFERENCE.md) for setup.

#### Install

Search for **Jedify** in your connectors or Directory, or install via the CLI:

```text
/plugin marketplace add jedify-com/skills
/plugin install jedify@jedify-com-skills
```

#### Use

1. Make sure a **database MCP server or connector** is connected (see REFERENCE.md).
2. Ask Claude:
   > *"Generate a schema context YAML for my warehouse and save it to `schema_context.yaml`"*
3. On **first use**, sign in to Jedify when prompted — this is the one-time sign-up / sign-in step. No separate registration is needed; connecting the Jedify connector is all it takes.

Claude then discovers your tables, samples a few rows, enriches everything, and returns the YAML for you to save.

---

## License

MIT — [jedify.com](https://jedify.com)

See also: [skills/schema-context/REFERENCE.md](skills/schema-context/REFERENCE.md)
