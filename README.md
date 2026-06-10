# jedify-com/skills

Claude Code skills and MCP servers by [Jedify](https://jedify.com).

## Skills

### `schema-context`

Connect Claude to your data warehouse and generate rich semantic context YAML for every table and column — labels, descriptions, semantic types, and example questions.

**Works with**: Snowflake, BigQuery, PostgreSQL, Redshift.

#### Prerequisites

1. **[Claude Code](https://claude.com/claude-code)** — CLI, desktop app, or VS Code extension.
2. **[`uv`](https://docs.astral.sh/uv/)** — provides `uvx`, which Claude uses to run the `jedify-lens` server. Install it once:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh    # or: brew install uv
   ```
   You do **not** need to install `jedify-lens`, Python, or any of its dependencies by hand — `uvx` fetches them automatically on first run.
3. **A database MCP server** connected for your warehouse (Snowflake / BigQuery / PostgreSQL / Redshift). The skill reads your schema and sample rows **through this server** — `jedify-lens` itself never connects to your database or needs its credentials. See [skills/schema-context/REFERENCE.md](skills/schema-context/REFERENCE.md) for setup.

#### Install

In Claude Code, add the marketplace and install the plugin:

```text
/plugin marketplace add jedify-com/skills
/plugin install jedify-schema-context@jedify-com-skills
```

Installing the plugin brings both the **skill** (the guided workflow) and the **`jedify-lens` MCP server** (run via `uvx`). Once the plugin is listed in the Claude plugin catalog, you'll also be able to find it in the `/plugin` **Discover** tab.

#### Use

1. Make sure a **database MCP server** is connected (see REFERENCE.md).
2. Ask Claude:
   > *"Generate a schema context YAML for my warehouse and save it to `schema_context.yaml`"*
3. On the **first run**, a browser opens to **sign in / sign up** with Jedify (Descope). You may also be offered to share a bit of company context (a URL, a file, or a sentence) to make the descriptions and example questions more tailored — this is optional.

Claude then discovers your tables, samples a few rows, enriches everything, and writes the YAML.

#### Advanced: run the MCP server without the plugin

If you only want the `jedify-lens` MCP **tools** (without the skill's guided workflow), add it to `~/.claude/settings.json` directly:

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

Installing the plugin (above) is the recommended path, since it also includes the skill.

---

## Python MCP Server

The [`jedify-lens`](https://pypi.org/project/jedify-lens/) PyPI package powers this skill. It's a standalone MCP server with no dependency on Jedify's backend, and it needs no warehouse drivers — it works through your connected database MCP server. It's normally run automatically via `uvx` (above), but you can also install it directly:

```bash
pip install jedify-lens
```

Source: [server/](server/)

---

## License

MIT — [jedify.com](https://jedify.com)
