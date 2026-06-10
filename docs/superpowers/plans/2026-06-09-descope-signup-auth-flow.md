# Descope Sign-up / Sign-in Auth Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the `jedify-lens` MCP server authenticate prospects through the prod Descope **Inbound App** with a working public-PKCE sign-up-or-sign-in flow, so a valid token gates the schema-context skill.

**Architecture:** Replace the broken project-level OIDC code in `registration.py` with Inbound App endpoints (`/oauth2/v1/apps/*`). Magic values move into a new `config.py` with hardcoded **public** prod defaults (base URL + client_id) and env overrides for dev/staging. The token exchange becomes a public-client PKCE exchange (no secret). Add a CSRF `state` check and a manual-URL fallback when no browser opens.

**Tech Stack:** Python 3.11, `mcp` (FastMCP), `httpx`, Poetry. Tests: `pytest` + `pytest-asyncio` (auto mode) + `respx` for httpx mocking.

**Reference spec:** `docs/superpowers/specs/2026-06-09-descope-signup-auth-flow-design.md`

> **All commands below run from the `server/` directory** (where `pyproject.toml` lives), e.g. `cd server`.

---

### Task 1: Dev tooling — pytest, pytest-asyncio, respx

**Files:**
- Modify: `server/pyproject.toml`

- [ ] **Step 1: Add a dev dependency group and pytest config**

Add these two blocks to `server/pyproject.toml` (after the existing `[tool.poetry.scripts]` block):

```toml
[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
pytest-asyncio = "^0.23"
respx = "^0.21"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Install dev deps**

Run: `poetry install --with dev`
Expected: completes; `pytest`, `pytest-asyncio`, `respx` installed.

- [ ] **Step 3: Verify pytest collects nothing yet**

Run: `poetry run pytest -q`
Expected: `no tests ran` (exit code 5) — confirms pytest is wired up.

- [ ] **Step 4: Commit**

```bash
git add server/pyproject.toml
git commit -m "chore: add pytest, pytest-asyncio, respx dev deps"
```

---

### Task 2: Config module

**Files:**
- Create: `server/jedify_lens/config.py`
- Test: `server/tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

Create `server/tests/test_config.py`:

```python
from jedify_lens import config


def test_defaults_are_prod(monkeypatch):
    monkeypatch.delenv("DESCOPE_BASE_URL", raising=False)
    monkeypatch.delenv("DESCOPE_CLIENT_ID", raising=False)
    assert config.base_url() == "https://auth.app.jedify.com"
    assert config.client_id() == "P2fGtsAm5ziAZr0swDyMDO7Tce87"
    assert config.authorize_url() == "https://auth.app.jedify.com/oauth2/v1/apps/authorize"
    assert config.token_url() == "https://auth.app.jedify.com/oauth2/v1/apps/token"
    assert config.issuer() == "https://auth.app.jedify.com/v1/apps/P2fGtsAm5ziAZr0swDyMDO7Tce87"


def test_env_overrides_and_strip_trailing_slash(monkeypatch):
    monkeypatch.setenv("DESCOPE_BASE_URL", "https://auth.dev.jedify.com/")
    monkeypatch.setenv("DESCOPE_CLIENT_ID", "DEVCLIENT")
    assert config.base_url() == "https://auth.dev.jedify.com"
    assert config.client_id() == "DEVCLIENT"
    assert config.authorize_url() == "https://auth.dev.jedify.com/oauth2/v1/apps/authorize"
    assert config.issuer() == "https://auth.dev.jedify.com/v1/apps/DEVCLIENT"


def test_redirect_and_scope_constants():
    assert config.REDIRECT_PORT == 8765
    assert config.REDIRECT_URI == "http://localhost:8765/callback"
    assert config.SCOPES == "openid email profile"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'jedify_lens.config'`

- [ ] **Step 3: Write the config module**

Create `server/jedify_lens/config.py`:

```python
"""Descope auth configuration.

All values are PUBLIC (a client_id and a hostname — like an OAuth client_id),
so the prod defaults are safe to ship inside the distributed package.
Set DESCOPE_BASE_URL / DESCOPE_CLIENT_ID to point at dev/staging while developing.
There is no client secret anywhere — this is a public PKCE client.
"""

import os

_DEFAULT_BASE_URL = "https://auth.app.jedify.com"
_DEFAULT_CLIENT_ID = "P2fGtsAm5ziAZr0swDyMDO7Tce87"

REDIRECT_PORT = 8765
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"
SCOPES = "openid email profile"


def base_url() -> str:
    return os.environ.get("DESCOPE_BASE_URL", _DEFAULT_BASE_URL).rstrip("/")


def client_id() -> str:
    return os.environ.get("DESCOPE_CLIENT_ID", _DEFAULT_CLIENT_ID)


def authorize_url() -> str:
    return f"{base_url()}/oauth2/v1/apps/authorize"


def token_url() -> str:
    return f"{base_url()}/oauth2/v1/apps/token"


def issuer() -> str:
    return f"{base_url()}/v1/apps/{client_id()}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest tests/test_config.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add server/jedify_lens/config.py server/tests/test_config.py
git commit -m "feat: add Descope auth config module with prod defaults and env overrides"
```

---

### Task 3: PKCE generation + authorize-URL builder

**Files:**
- Modify: `server/jedify_lens/tools/registration.py`
- Test: `server/tests/test_registration_pkce.py`

- [ ] **Step 1: Write the failing tests**

Create `server/tests/test_registration_pkce.py`:

```python
import base64
import hashlib
from urllib.parse import urlparse, parse_qs

from jedify_lens.tools import registration


def test_generate_pkce_challenge_matches_verifier():
    verifier, challenge = registration._generate_pkce()
    expected = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    assert challenge == expected
    assert "=" not in challenge


def test_build_authorize_url(monkeypatch):
    monkeypatch.delenv("DESCOPE_BASE_URL", raising=False)
    monkeypatch.delenv("DESCOPE_CLIENT_ID", raising=False)
    url = registration.build_authorize_url("CHALLENGE", "STATE123")
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    assert parsed.path == "/oauth2/v1/apps/authorize"
    assert qs["response_type"] == ["code"]
    assert qs["client_id"] == ["P2fGtsAm5ziAZr0swDyMDO7Tce87"]
    assert qs["redirect_uri"] == ["http://localhost:8765/callback"]
    assert qs["scope"] == ["openid email profile"]
    assert qs["code_challenge"] == ["CHALLENGE"]
    assert qs["code_challenge_method"] == ["S256"]
    assert qs["state"] == ["STATE123"]
    assert "prompt" not in qs  # sign-up-or-in flow, not forced login
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest tests/test_registration_pkce.py -v`
Expected: FAIL — `AttributeError: module ... has no attribute '_generate_pkce'`

- [ ] **Step 3: Add the helpers and update imports/constants**

In `server/jedify_lens/tools/registration.py`, replace the top imports + module constants block (lines 1-23, ending at `_TOKEN_ENDPOINT = ...`) with:

```python
import asyncio
import base64
import hashlib
import json
import logging
import secrets
import webbrowser

from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from jedify_lens import config

logger = logging.getLogger("jedify_lens.registration")

_STATE_PATH = Path.home() / ".jedify" / "state.json"
```

Then add these two helpers right after the `_save_state` function:

```python
def _generate_pkce() -> tuple[str, str]:
    """Return (code_verifier, code_challenge) for an S256 PKCE exchange."""
    verifier = secrets.token_urlsafe(32)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    return verifier, challenge


def build_authorize_url(code_challenge: str, state: str) -> str:
    """Build the Descope Inbound App authorize URL (sign-up-or-sign-in)."""
    return f"{config.authorize_url()}?" + urlencode({
        "response_type": "code",
        "client_id": config.client_id(),
        "redirect_uri": config.REDIRECT_URI,
        "scope": config.SCOPES,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    })
```

Then **delete the now-orphaned `_project_id()` function** (the `def _project_id() -> str:` block that reads `DESCOPE_PROJECT_ID` from `os.environ`). Nothing should reference it anymore.

> Note: `import os`, `_project_id()`, `_CALLBACK_PORT`, `_REDIRECT_URI`, `_AUTH_ENDPOINT`, `_TOKEN_ENDPOINT` are intentionally removed. `_extract_token`, `_token_email`, `_is_token_valid`, `_load_state`, `_save_state` remain unchanged. Later tasks (5, 6, 7) update the functions that referenced the removed constants — until then the module still imports fine (those names are only referenced inside not-yet-called functions).

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest tests/test_registration_pkce.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add server/jedify_lens/tools/registration.py server/tests/test_registration_pkce.py
git commit -m "feat: add PKCE generation and Inbound App authorize-URL builder"
```

---

### Task 4: Token validity & email extraction tests (pin existing behavior)

**Files:**
- Test: `server/tests/test_registration_token.py`

> `_is_token_valid`, `_token_email`, `_extract_token` already exist and are correct. Pin them with tests before later tasks touch surrounding code.

- [ ] **Step 1: Write the tests**

Create `server/tests/test_registration_token.py`:

```python
import base64
import json
import time

from jedify_lens.tools import registration


def _make_jwt(payload: dict) -> str:
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"header.{body}.sig"


def test_token_valid_future_exp():
    assert registration._is_token_valid(_make_jwt({"exp": int(time.time()) + 3600})) is True


def test_token_invalid_past_exp():
    assert registration._is_token_valid(_make_jwt({"exp": int(time.time()) - 10})) is False


def test_token_invalid_garbage():
    assert registration._is_token_valid("not-a-jwt") is False


def test_token_email_extracted():
    assert registration._token_email(_make_jwt({"email": "bob@acme.com"})) == "bob@acme.com"


def test_extract_token_prefers_id_token():
    assert registration._extract_token({"id_token": "ID", "access_token": "AC"}) == "ID"
    assert registration._extract_token({"access_token": "AC"}) == "AC"
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `poetry run pytest tests/test_registration_token.py -v`
Expected: 5 passed.

- [ ] **Step 3: Commit**

```bash
git add server/tests/test_registration_token.py
git commit -m "test: pin token validity and email-extraction behavior"
```

---

### Task 5: Public-PKCE token exchange + refresh

**Files:**
- Modify: `server/jedify_lens/tools/registration.py`
- Test: `server/tests/test_registration_exchange.py`

- [ ] **Step 1: Write the failing tests**

Create `server/tests/test_registration_exchange.py`:

```python
import httpx
import respx

from jedify_lens.tools import registration


@respx.mock
async def test_exchange_code_posts_pkce_without_secret(monkeypatch):
    monkeypatch.delenv("DESCOPE_BASE_URL", raising=False)
    monkeypatch.delenv("DESCOPE_CLIENT_ID", raising=False)
    route = respx.post("https://auth.app.jedify.com/oauth2/v1/apps/token").mock(
        return_value=httpx.Response(
            200, json={"id_token": "idtok", "access_token": "atok", "refresh_token": "rtok"}
        )
    )
    data = await registration.exchange_code("THECODE", "THEVERIFIER")
    assert data["access_token"] == "atok"

    body = route.calls.last.request.content.decode()
    assert "grant_type=authorization_code" in body
    assert "code=THECODE" in body
    assert "code_verifier=THEVERIFIER" in body
    assert "client_id=P2fGtsAm5ziAZr0swDyMDO7Tce87" in body
    assert "client_secret" not in body
    header_names = {k.lower() for k in route.calls.last.request.headers.keys()}
    assert "authorization" not in header_names


@respx.mock
async def test_do_refresh_uses_client_id_without_secret(monkeypatch):
    monkeypatch.delenv("DESCOPE_BASE_URL", raising=False)
    monkeypatch.delenv("DESCOPE_CLIENT_ID", raising=False)
    route = respx.post("https://auth.app.jedify.com/oauth2/v1/apps/token").mock(
        return_value=httpx.Response(200, json={"access_token": "new", "id_token": "new"})
    )
    data = await registration._do_refresh("REFRESHTOK")
    assert data["access_token"] == "new"

    body = route.calls.last.request.content.decode()
    assert "grant_type=refresh_token" in body
    assert "refresh_token=REFRESHTOK" in body
    assert "client_id=P2fGtsAm5ziAZr0swDyMDO7Tce87" in body
    assert "client_secret" not in body
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest tests/test_registration_exchange.py -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'exchange_code'` (and `_do_refresh` signature mismatch).

- [ ] **Step 3: Replace `_do_refresh` and add `exchange_code`**

In `server/jedify_lens/tools/registration.py`, replace the existing `_do_refresh` function (the old `async def _do_refresh(refresh_tok, pid)` that posts with an `Authorization: Bearer {pid}` header) with these two functions:

```python
async def exchange_code(code: str, code_verifier: str) -> dict:
    """Exchange an authorization code for tokens (public PKCE client — no secret)."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            config.token_url(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": config.REDIRECT_URI,
                "client_id": config.client_id(),
                "code_verifier": code_verifier,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def _do_refresh(refresh_tok: str) -> dict:
    """Refresh tokens for a public PKCE client (no secret)."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            config.token_url(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_tok,
                "client_id": config.client_id(),
            },
        )
        resp.raise_for_status()
        return resp.json()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest tests/test_registration_exchange.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add server/jedify_lens/tools/registration.py server/tests/test_registration_exchange.py
git commit -m "feat: public-PKCE token exchange and refresh (no client secret)"
```

---

### Task 6: `check_registration` uses config (drop DESCOPE_PROJECT_ID)

**Files:**
- Modify: `server/jedify_lens/tools/registration.py`
- Test: `server/tests/test_check_registration.py`

- [ ] **Step 1: Write the failing tests**

Create `server/tests/test_check_registration.py`:

```python
import base64
import json
import time

import httpx
import respx

from jedify_lens.tools import registration


def _make_jwt(payload: dict) -> str:
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"header.{body}.sig"


async def test_no_token_returns_unregistered(monkeypatch, tmp_path):
    monkeypatch.setattr(registration, "_STATE_PATH", tmp_path / "state.json")
    result = await registration.check_registration()
    assert result["registered"] is False
    assert "login_tool" in result["action"]


async def test_valid_token_returns_registered(monkeypatch, tmp_path):
    state_file = tmp_path / "state.json"
    token = _make_jwt({"exp": int(time.time()) + 3600})
    state_file.write_text(
        json.dumps({"access_token": token, "email": "bob@acme.com", "company_context": "ctx"})
    )
    monkeypatch.setattr(registration, "_STATE_PATH", state_file)
    result = await registration.check_registration()
    assert result["registered"] is True
    assert result["email"] == "bob@acme.com"
    assert result["company_context"] == "ctx"


@respx.mock
async def test_expired_token_refreshes(monkeypatch, tmp_path):
    monkeypatch.delenv("DESCOPE_BASE_URL", raising=False)
    monkeypatch.delenv("DESCOPE_CLIENT_ID", raising=False)
    state_file = tmp_path / "state.json"
    expired = _make_jwt({"exp": int(time.time()) - 10})
    fresh = _make_jwt({"exp": int(time.time()) + 3600})
    state_file.write_text(
        json.dumps({"access_token": expired, "refresh_token": "rtok", "email": "bob@acme.com"})
    )
    monkeypatch.setattr(registration, "_STATE_PATH", state_file)
    respx.post("https://auth.app.jedify.com/oauth2/v1/apps/token").mock(
        return_value=httpx.Response(200, json={"access_token": fresh, "id_token": fresh})
    )
    result = await registration.check_registration()
    assert result["registered"] is True
    # new token persisted
    assert json.loads(state_file.read_text())["access_token"] == fresh
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest tests/test_check_registration.py -v`
Expected: FAIL — the current `check_registration` calls `_project_id()` / `_do_refresh(refresh_tok, pid)`, raising `RuntimeError("DESCOPE_PROJECT_ID is not set.")` or a TypeError.

- [ ] **Step 3: Update `check_registration`**

In `server/jedify_lens/tools/registration.py`, replace the whole `check_registration` function with:

```python
async def check_registration() -> dict:
    state = _load_state()
    access_token = state.get("access_token", "")
    refresh_tok = state.get("refresh_token", "")
    email = state.get("email", "")

    if not access_token:
        return {
            "registered": False,
            "action": "Call login_tool to open the sign-in page in the user's browser.",
        }

    if _is_token_valid(access_token):
        return {
            "registered": True,
            "email": email,
            "company_context": state.get("company_context", ""),
            "message": f"Signed in as {email}.",
        }

    # Token expired — try refresh
    if refresh_tok:
        try:
            data = await _do_refresh(refresh_tok)
            state["access_token"] = _extract_token(data)
            if data.get("refresh_token"):
                state["refresh_token"] = data["refresh_token"]
            _save_state(state)
            logger.debug("Token refreshed successfully")
            return {
                "registered": True,
                "email": email,
                "company_context": state.get("company_context", ""),
                "message": f"Signed in as {email}.",
            }
        except Exception as e:
            logger.debug(f"Token refresh failed: {e}")

    return {
        "registered": False,
        "action": "Session expired. Call login_tool to re-authenticate in the browser.",
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest tests/test_check_registration.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add server/jedify_lens/tools/registration.py server/tests/test_check_registration.py
git commit -m "feat: check_registration uses Inbound App config, no DESCOPE_PROJECT_ID"
```

---

### Task 7: `browser_login` — helpers, state CSRF check, manual-URL fallback

**Files:**
- Modify: `server/jedify_lens/tools/registration.py`
- Test: `server/tests/test_callback_validation.py`

- [ ] **Step 1: Write the failing tests for the callback validator**

Create `server/tests/test_callback_validation.py`:

```python
from jedify_lens.tools import registration


def test_validate_callback_success():
    code, err = registration.validate_callback({"code": "c", "state": "RIGHT"}, "RIGHT")
    assert code == "c"
    assert err is None


def test_validate_callback_state_mismatch():
    code, err = registration.validate_callback({"code": "c", "state": "WRONG"}, "RIGHT")
    assert code is None
    assert err["success"] is False
    assert "verif" in err["action"].lower()


def test_validate_callback_provider_error():
    code, err = registration.validate_callback({"error": "access_denied"}, "RIGHT")
    assert code is None
    assert err["success"] is False
    assert "access_denied" in err["action"]


def test_validate_callback_missing_code():
    code, err = registration.validate_callback({"state": "RIGHT"}, "RIGHT")
    assert code is None
    assert err["success"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest tests/test_callback_validation.py -v`
Expected: FAIL — `AttributeError: ... has no attribute 'validate_callback'`

- [ ] **Step 3: Add `validate_callback` and rewrite `browser_login`**

In `server/jedify_lens/tools/registration.py`, add this pure helper just above `browser_login`:

```python
def validate_callback(callback_data: dict, sent_state: str) -> tuple[str | None, dict | None]:
    """Validate the OAuth callback. Returns (code, error_result).

    On success: (code, None). On failure: (None, error_dict) ready to return to the skill.

    The callback handler always sets callback_data["error"] (None when absent), so this
    checks truthiness with .get() rather than key presence.
    """
    if callback_data.get("error"):
        return None, {
            "success": False,
            "action": f"Tell the user: 'Auth error — {callback_data['error']}'",
        }
    if callback_data.get("state") != sent_state:
        return None, {
            "success": False,
            "action": "Tell the user: 'Sign-in could not be verified (state mismatch) — please try again.'",
        }
    code = callback_data.get("code")
    if not code:
        return None, {
            "success": False,
            "action": "Tell the user: 'No auth code received — please try again.'",
        }
    return code, None
```

Then replace the entire `browser_login` function with:

```python
async def browser_login() -> dict:
    code_verifier, code_challenge = _generate_pkce()
    state_param = secrets.token_urlsafe(32)
    auth_url = build_authorize_url(code_challenge, state_param)

    loop = asyncio.get_event_loop()
    callback_event = asyncio.Event()
    callback_data: dict = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/callback":
                qs = parse_qs(parsed.query)
                callback_data["error"] = qs.get("error", [None])[0]
                callback_data["code"] = qs.get("code", [None])[0]
                callback_data["state"] = qs.get("state", [None])[0]

                if callback_data["error"]:
                    body = (
                        f"<html><body style='font-family:sans-serif;text-align:center;padding:60px'>"
                        f"<h2>Authentication error</h2><p>{callback_data['error']}</p></body></html>"
                    ).encode()
                    self.send_response(400)
                elif callback_data["code"]:
                    body = (
                        b"<html><body style='font-family:sans-serif;text-align:center;padding:60px'>"
                        b"<h2>&#10003; Signed in!</h2>"
                        b"<p>You can close this tab and return to Claude.</p>"
                        b"<script>setTimeout(()=>window.close(),2000)</script>"
                        b"</body></html>"
                    )
                    self.send_response(200)
                else:
                    body = b""
                    self.send_response(400)

                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(body)
                loop.call_soon_threadsafe(callback_event.set)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *args):
            pass

    server = HTTPServer(("localhost", config.REDIRECT_PORT), CallbackHandler)
    Thread(target=server.serve_forever, daemon=True).start()

    opened = webbrowser.open(auth_url)
    # Manual-URL fallback: if no browser could open (headless / remote), surface the URL.
    logger.warning("If your browser did not open, sign in here: %s", auth_url)
    if not opened:
        logger.warning("No browser could be opened automatically; use the URL above.")

    try:
        await asyncio.wait_for(callback_event.wait(), timeout=300)
    except asyncio.TimeoutError:
        server.shutdown()
        return {"success": False, "action": "Tell the user: 'Sign-in timed out — please try again.'"}
    finally:
        server.shutdown()

    code, error = validate_callback(callback_data, state_param)
    if error:
        return error

    try:
        data = await exchange_code(code, code_verifier)
        access_token = _extract_token(data)
        refresh_tok = data.get("refresh_token", "")
        email = _token_email(data.get("id_token", access_token))

        state = _load_state()
        state.update({
            "email": email,
            "access_token": access_token,
            "refresh_token": refresh_tok,
        })
        _save_state(state)

        return {
            "success": True,
            "registered": True,
            "email": email,
            "action": f"Tell the user: 'You're signed in as {email}.' Then proceed to the company context step.",
        }
    except Exception as e:
        logger.error(f"Token exchange failed: {e}")
        return {"success": False, "action": f"Tell the user: 'Authentication failed — {e}'"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest tests/test_callback_validation.py -v`
Expected: 4 passed.

- [ ] **Step 5: Run the full suite**

Run: `poetry run pytest -v`
Expected: all tests pass (config 3, pkce 2, token 5, exchange 2, check 3, callback 4).

- [ ] **Step 6: Commit**

```bash
git add server/jedify_lens/tools/registration.py server/tests/test_callback_validation.py
git commit -m "feat: browser_login state CSRF check, PKCE helpers, manual-URL fallback"
```

---

### Task 8: Docs — document the dev/staging override; confirm `.mcp.json`

**Files:**
- Modify: `skills/schema-context/REFERENCE.md`
- Verify (no change expected): `.mcp.json`

- [ ] **Step 1: Confirm `.mcp.json` needs no change**

Run: `cat ../.mcp.json` (from `server/`) — confirm it is:
```json
{
  "jedify-schema-context": {
    "command": "uvx",
    "args": ["jedify-lens"]
  }
}
```
Because prod defaults are baked into `config.py`, **no `env` block is required** for end users. Leave it as-is.

- [ ] **Step 2: Append an auth-override note to REFERENCE.md**

Append this section to the end of `skills/schema-context/REFERENCE.md`:

```markdown
## Authentication (Descope)

Sign-in is handled by Jedify's Descope **Inbound App**. The prod project is baked into
the package, so end users need no auth configuration — the first run opens a browser to
sign up / sign in.

**Developers only** — point the plugin at a non-prod Descope project with env overrides:

| Variable | Default (prod) | Purpose |
|---|---|---|
| `DESCOPE_BASE_URL` | `https://auth.app.jedify.com` | Descope base URL (custom domain) |
| `DESCOPE_CLIENT_ID` | `P2fGtsAm5ziAZr0swDyMDO7Tce87` | Inbound App client_id (public) |

Both values are **public identifiers** (like an OAuth `client_id`) — there is no client
secret. The flow is a public-client Authorization Code + PKCE exchange with a
`http://localhost:8765/callback` redirect, which must be allow-listed in the Descope
Inbound App.
```

- [ ] **Step 3: Commit**

```bash
git add skills/schema-context/REFERENCE.md
git commit -m "docs: document Descope dev/staging auth overrides"
```

---

### Task 9: Manual end-to-end verification

> No automated test can cover the real browser round-trip. Do this manually once.

- [ ] **Step 1: Run the server against prod and trigger login**

From `server/`, run the MCP server (or point a Claude Code session at it via `.mcp.json`)
and invoke `login_tool`. Expected: browser opens to the Jedify Descope **Sign up or in**
page.

- [ ] **Step 2: Complete sign-up as a NEW email**

Sign up with a fresh email. Expected: tab shows "✓ Signed in!", `login_tool` returns
`success: true` with that email, and `~/.jedify/state.json` contains `access_token` +
`refresh_token`. Confirm a **new user appears in the prod Descope project**.

- [ ] **Step 3: Re-run as a RETURNING user**

Call `check_registration` again. Expected: `registered: true` **without** opening a
browser (token reused). Then sign in with the same email in a fresh state (delete
`~/.jedify/state.json` first) and confirm **no duplicate account** is created in Descope.

- [ ] **Step 4: Confirm the skill proceeds**

In a Claude Code session with a database MCP connected, run the `schema-context` skill
end-to-end. Expected: auth gate passes, then the skill discovers tables and exports YAML.

---

## Notes / Out of scope (per spec §9)
- True device-code fallback (cloud-web / SSH) — pending confirmation Descope exposes a
  device grant for Inbound Apps. Manual-URL logging is the interim fallback.
- Publishing `jedify-lens` to PyPI so `uvx jedify-lens` resolves — separate task.
- Dead `enrichment/prompts.py`, PyPI extras mismatch, BigQuery doc inconsistencies,
  broader test coverage — separate cleanup pass.
