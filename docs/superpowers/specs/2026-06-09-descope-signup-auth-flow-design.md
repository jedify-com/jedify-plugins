# Design: Descope Sign-up / Sign-in Auth Flow

**Date:** 2026-06-09
**Status:** Approved (pending spec review)
**Component:** `jedify-lens` MCP server — authentication (`server/jedify_lens/tools/registration.py`)

## 1. Goal

The `schema-context` plugin gives prospects a genuinely useful artifact (a semantic
schema-context YAML for their warehouse) and, in exchange, requires them to **sign up**
with Jedify first. Sign-up is lead capture: a new prospect's account lands in Jedify's
**prod** Descope project, and we learn their email.

This design fixes the currently-broken auth flow and turns it into a real
sign-up-or-sign-in gate. **A valid token = "okay from Descope" = the skill proceeds.**

## 2. Current state and problems

The existing `registration.py` implements an OAuth2 Authorization Code + PKCE flow with a
localhost callback, but it does not work as shipped:

1. **`DESCOPE_PROJECT_ID` is never set** — `.mcp.json` passes no env, so `_project_id()`
   raises `"DESCOPE_PROJECT_ID is not set"` and login dies immediately.
2. **Wrong endpoints** — it uses project-level OIDC (`/oauth2/v1/authorize`,
   `/oauth2/v1/token`). We are standardizing on the **Inbound App** endpoints
   (`/oauth2/v1/apps/...`), which is Descope's documented pattern for CLI/desktop tools
   and the only mode where our localhost redirect and (future) device flow are
   first-class.
3. **Wrong token-exchange auth** — it sends `Authorization: Bearer <project_id>` at the
   token step (the project-OIDC pattern). For a public PKCE client we send `client_id` +
   `code_verifier` in the body and **no secret**.
4. **Sign-in only** — `prompt=login` forces sign-in. We want sign-up-or-sign-in so new
   prospects can register.

## 3. Decisions (the "why")

| Decision | Choice | Rationale |
|---|---|---|
| Descope integration mode | **Inbound App** (`/oauth2/v1/apps/*`) | Documented CLI pattern; explicit redirect-URI allow-listing; device flow available later |
| Which project | **prod**, baked into the package | Prospects are real leads; their accounts must live in the project we monitor |
| Config delivery | Hardcoded prod defaults + env overrides | Client ID and base URL are **public** (like an OAuth client_id), safe to ship; env override lets us point at dev/staging |
| Client type | **Public client + PKCE**, no secret | The plugin is distributed; we cannot embed a secret. PKCE secures it. |
| Scopes | `openid email profile` | Minimal — we only need to identify the prospect (email is the lead). No permission scopes. |
| Flow type | **sign-up-or-in** | One door: new emails register, known emails sign in, no duplicate accounts |
| Gate | Valid token | Lowest friction; the user's own data never leaves their machine, so a verified identity is sufficient |
| Pop-up method | Browser-first, **manual-URL fallback** | Auto-open covers CLI/VS Code/desktop app (all local). If no browser can open, print the URL. True device-code deferred (see §9). |

### Concrete prod values (public, safe to commit)

```
DESCOPE_BASE_URL   = https://auth.app.jedify.com
DESCOPE_CLIENT_ID  = P2fGtsAm5ziAZr0swDyMDO7Tce87
Authorize endpoint = {BASE}/oauth2/v1/apps/authorize
Token endpoint     = {BASE}/oauth2/v1/apps/token
Issuer             = {BASE}/v1/apps/P2fGtsAm5ziAZr0swDyMDO7Tce87
Redirect URI       = http://localhost:8765/callback   (registered in Descope)
Scopes             = openid email profile
```

The Descope Inbound App is fully configured: Sign-up-or-in consent flow, redirect URI
registered, `full_access` permission scope made non-mandatory, an `email` user-info scope
added, PKCE supported automatically. The leaked client secret was rotated; we do not use it.

## 4. Where the plugin runs (scope of "works")

The plugin is an MCP server that runs as a **local process on the user's own machine**.
Claude Code launches it locally whether the user is on the **CLI, the VS Code extension,
or the desktop ("cowork") app** — so in all three the browser and the plugin share one
machine and the localhost callback works. Fully-cloud web and remote/SSH sessions are the
only environments localhost cannot serve; those are addressed by the deferred device-code
fallback (§9).

## 5. Configuration module

Introduce a small config helper (new file, e.g. `jedify_lens/config.py`) so the magic
values live in one place and are overridable:

```
DESCOPE_BASE_URL   env override → default "https://auth.app.jedify.com"
DESCOPE_CLIENT_ID  env override → default "P2fGtsAm5ziAZr0swDyMDO7Tce87"
REDIRECT_PORT      = 8765
REDIRECT_URI       = http://localhost:8765/callback
SCOPES             = "openid email profile"
```

Derived endpoint URLs (`authorize_url`, `token_url`, `issuer`) are computed from
`DESCOPE_BASE_URL`. No secret anywhere.

## 6. Auth flow (end-to-end)

```
check_registration()
  └─ valid token in ~/.jedify/state.json?  ── yes ─→ {registered: true, email}
        │ no / expired
        ▼
     refresh_token present? ── yes ─→ POST {token_url} grant=refresh_token
        │                                  success → save, {registered: true}
        │ no / refresh failed
        ▼
     {registered: false, action: "call login_tool"}

login_tool()  (browser_login)
  1. Generate PKCE verifier/challenge + state
  2. Build authorize URL:
       {authorize_url}?response_type=code&client_id={CLIENT_ID}
         &redirect_uri={REDIRECT_URI}&scope=openid email profile
         &state=...&code_challenge=...&code_challenge_method=S256
     (no prompt=login → sign-up-or-in flow runs)
  3. Start localhost:8765 callback server
  4. Try webbrowser.open(url):
        opened   → tell user "Opening sign-in in your browser…"
        failed   → print the URL: "Open this link to sign up/sign in: <url>"
  5. Wait (≤5 min) for the browser to hit /callback with ?code
  6. Validate returned state == sent state (CSRF guard)
  7. Exchange code at {token_url}:
       grant_type=authorization_code, code, redirect_uri,
       client_id={CLIENT_ID}, code_verifier   (NO client secret)
  8. Extract id_token → email; save {email, access_token, refresh_token}
  9. {success: true, registered: true, email}
```

The skill's Step 1 already calls `check_registration_tool` then `login_tool` on
`registered: false`, then proceeds. That sequencing is unchanged — only the server
internals change.

## 7. Token storage and refresh

- State file: `~/.jedify/state.json` (unchanged location): `{email, access_token,
  refresh_token, company_context}`.
- Validity: decode JWT `exp` with a 30s buffer (existing `_is_token_valid`).
- Refresh: `grant_type=refresh_token` against the **`/apps/token`** endpoint with
  `client_id` in the body (no secret). On failure → require re-auth.
- `state` parameter is validated on callback (new CSRF check; not currently enforced).

## 8. Error handling

- Browser can't open → print URL fallback (still completes via localhost).
- Timeout (5 min) → `{success: false, action: "sign-in timed out, retry"}`.
- `error` in callback / `state` mismatch / missing code → clear failure message, no token saved.
- Token exchange HTTP error → surface a readable message; do not write partial state.
- All user-facing returns keep the existing `{success, action}` shape the skill relies on.

## 9. Out of scope (future work)

- **True device-code fallback** for cloud-web / remote-SSH. The Inbound App grant panel
  showed Authorization Code / Client Credentials / JWT Bearer / CIBA but **no Device
  grant**; needs confirmation that Descope exposes a device grant for inbound apps before
  building. Until then, the manual-URL fallback is the answer for "no auto-open browser."
- The other repo gaps (dead `enrichment/prompts.py`, PyPI extras mismatch, missing tests,
  BigQuery doc inconsistencies) — to be tackled after auth works.

## 10. Testing

- Unit: PKCE challenge generation, authorize-URL construction, `state` validation,
  token validity/expiry parsing, email extraction from id_token, config env-override
  resolution. Mock `httpx` for token exchange + refresh (success and failure paths).
- Manual end-to-end: run the MCP server, trigger `login_tool`, complete real Descope
  sign-up in a browser, confirm a new account appears in the prod project and the skill
  proceeds. Repeat as a returning user (no duplicate account; silent token reuse).
```
