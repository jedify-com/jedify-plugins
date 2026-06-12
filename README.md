# jedify-com/jedify-plugins

**Jedify's plugins for Claude.** This is the Jedify marketplace — install it once, then add any Jedify plugin from it.

The first plugin, **schema-context**, connects Claude to your data warehouse and generates rich semantic **schema-context YAML** for every table and column: business labels, descriptions, semantic types, and example questions.

This repo is a **marketplace** that can hold many plugins. Today it holds one:

1. **The `schema-context` plugin** a user installs (its skill + a pointer to our hosted MCP server).
2. **The MCP server** (`gateway/`) that powers it, deployed as a remote connector.

Jedify never connects to your database directly and never holds DB credentials — Claude reads your schema **through a database connector you already have**, and Jedify only formats and returns the result.

---

## Repository structure

The repo root is the **marketplace**; each **plugin** lives in its own folder.

```
.
├── .claude-plugin/
│   └── marketplace.json     # Marketplace "jedify" — lists the plugins it offers
├── schema-context/          # ── PLUGIN: schema-context ───────────────────
│   ├── .claude-plugin/
│   │   └── plugin.json      #   Plugin manifest (name "schema-context")
│   ├── .mcp.json            #   Pointer to the hosted MCP server (sign-in)
│   └── skills/
│       └── schema-context/
│           ├── SKILL.md     #   The step-by-step flow Claude follows
│           ├── REFERENCE.md #   Setup, the tool, YAML output schema, troubleshooting
│           └── examples.md  #   Example prompts
├── gateway/                 # Shared MCP server (Next.js + mcp-handler, hosted on Vercel)
│   ├── app/
│   │   ├── [transport]/route.ts                      # The MCP endpoint (/mcp) + auth
│   │   └── .well-known/oauth-protected-resource/...  # OAuth metadata (points Claude at Jedify sign-in)
│   ├── lib/yaml.ts          # Builds the schema-context YAML from enriched input
│   ├── test/yaml.test.ts    # Tests for the YAML builder
│   └── package.json
└── README.md
```

**To add another plugin:** create a sibling folder (e.g. `cost-analysis/`) with its own `.claude-plugin/plugin.json`, `.mcp.json`, and `skills/`, then add an entry to `marketplace.json`. `gateway/` stays at the root as shared deploy infrastructure (it isn't part of any installed plugin).

### How it connects

```
  User installs the plugin                       Claude calls the hosted server
  ──────────────────────────                     ──────────────────────────────
  schema-context/skills/…    ── guides ──►        Claude runs the skill
  schema-context/.mcp.json   ── points at ──►     gateway/  (the /mcp endpoint on Vercel)
```

- **The plugin** (`schema-context/` — its `plugin.json` + `skills/` + `.mcp.json`) is what a user downloads. The skill tells Claude *what to do*; `.mcp.json` tells Claude *where the server is*.
- **The server** (`gateway/`) is the live thing that does the work. It exposes a single tool, `export_schema_context`, which takes Claude's enriched schema and returns the formatted YAML.
- **Sign-in** is handled by the server's OAuth flow (Jedify as the identity provider). Connecting the Jedify connector is the one-time sign-in — there's no separate registration.

---

## The `schema-context` skill

Connect Claude to your data warehouse and generate rich semantic context YAML for every table and column — labels, descriptions, semantic types, and example questions.

**Works with**: Snowflake, BigQuery, PostgreSQL, Redshift (through your existing connector).

### Prerequisites

1. **[Claude Code](https://claude.com/claude-code)** or **[claude.ai](https://claude.ai)** — CLI, desktop app, VS Code extension, or web.
2. **A database MCP server or connector** for your warehouse (Snowflake / BigQuery / PostgreSQL / Redshift). The skill reads your schema and sample rows **through this connector** — Jedify never connects to your database directly and never holds DB credentials. See [schema-context/skills/schema-context/REFERENCE.md](schema-context/skills/schema-context/REFERENCE.md) for setup.

### Install

```text
/plugin marketplace add jedify-com/jedify-plugins
/plugin install schema-context@jedify
```

### Use

1. Make sure a **database MCP server or connector** is connected (see [REFERENCE.md](schema-context/skills/schema-context/REFERENCE.md)).
2. Ask Claude:
   > *"Generate a schema context YAML for my warehouse and save it to `schema_context.yaml`"*
3. On **first use**, sign in to Jedify when prompted — this is the one-time sign-up / sign-in. Connecting the Jedify connector is all it takes.

Claude then discovers your tables, samples a few rows, enriches everything, and returns the YAML for you to save. See [schema-context/skills/schema-context/SKILL.md](schema-context/skills/schema-context/SKILL.md) for the full flow and [examples.md](schema-context/skills/schema-context/examples.md) for prompt examples.

---

## The gateway (MCP server)

The `gateway/` directory is the remote MCP server that backs the connector.

- **Stack**: Next.js (App Router) + [`mcp-handler`](https://www.npmjs.com/package/mcp-handler), `jose` (JWT verification), `js-yaml`, `zod`. Hosted on Vercel.
- **Endpoint**: `/mcp` (Streamable HTTP).
- **Tool**: `export_schema_context(enriched_context, warehouse_type)` — read-only; formats enriched schema into YAML and returns it as text.
- **Auth**: validates Jedify-issued OAuth tokens and advertises OAuth metadata at `/.well-known/oauth-protected-resource`, so Claude knows where to sign the user in.

### Local development

```bash
cd gateway
npm install
npm run dev        # run the server locally
npm run typecheck  # type-check
npm run test       # run the YAML-builder tests
npm run build      # production build
```

---

## License

MIT — [jedify.com](https://jedify.com)
