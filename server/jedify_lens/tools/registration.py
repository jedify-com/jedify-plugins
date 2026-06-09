import asyncio
import base64
import hashlib
import html
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


# ---------------------------------------------------------------------------
# State storage
# ---------------------------------------------------------------------------

def _load_state() -> dict:
    try:
        return json.loads(_STATE_PATH.read_text())
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STATE_PATH.write_text(json.dumps(state, indent=2))


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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_token(data: dict) -> str:
    """Prefer id_token over access_token (mirrors the TS implementation)."""
    return data.get("id_token") or data.get("access_token", "")


def _token_email(token: str) -> str:
    try:
        payload = token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload)).get("email", "")
    except Exception:
        return ""


def _is_token_valid(token: str) -> bool:
    import time
    try:
        payload = token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        exp = json.loads(base64.urlsafe_b64decode(payload)).get("exp", 0)
        return int(exp) > time.time() + 30  # 30s buffer
    except Exception:
        return False


async def _post_token(data: dict) -> dict:
    """POST a form-encoded request to the Descope token endpoint and return JSON."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            config.token_url(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=data,
        )
    resp.raise_for_status()
    return resp.json()


async def exchange_code(code: str, code_verifier: str) -> dict:
    """Exchange an authorization code for tokens (public PKCE client — no secret)."""
    return await _post_token({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config.REDIRECT_URI,
        "client_id": config.client_id(),
        "code_verifier": code_verifier,
    })


async def _do_refresh(refresh_tok: str) -> dict:
    """Refresh tokens for a public PKCE client (no secret)."""
    return await _post_token({
        "grant_type": "refresh_token",
        "refresh_token": refresh_tok,
        "client_id": config.client_id(),
    })


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

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
            updated = {
                **state,
                "access_token": _extract_token(data),
                **({"refresh_token": data["refresh_token"]} if data.get("refresh_token") else {}),
            }
            _save_state(updated)
            logger.debug("Token refreshed successfully")
            return {
                "registered": True,
                "email": email,
                "company_context": state.get("company_context", ""),
                "message": f"Signed in as {email}.",
            }
        except Exception as e:
            logger.warning(f"Token refresh failed: {e}")

    return {
        "registered": False,
        "action": "Session expired. Call login_tool to re-authenticate in the browser.",
    }


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


async def browser_login() -> dict:
    code_verifier, code_challenge = _generate_pkce()
    state_param = secrets.token_urlsafe(32)
    auth_url = build_authorize_url(code_challenge, state_param)

    loop = asyncio.get_running_loop()
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
                        f"<h2>Authentication error</h2><p>{html.escape(callback_data['error'])}</p></body></html>"
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
    if not opened:
        logger.warning("No browser could be opened automatically. Sign in here: %s", auth_url)
    else:
        logger.debug("Opened browser for OAuth sign-in.")

    try:
        await asyncio.wait_for(callback_event.wait(), timeout=300)
    except asyncio.TimeoutError:
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
        _save_state({
            **state,
            "email": email,
            "access_token": access_token,
            "refresh_token": refresh_tok,
        })

        return {
            "success": True,
            "registered": True,
            "email": email,
            "action": f"Tell the user: 'You're signed in as {email}.' Then proceed to the company context step.",
        }
    except Exception as e:
        logger.error(f"Token exchange failed: {e}")
        return {"success": False, "action": f"Tell the user: 'Authentication failed — {e}'"}


async def save_company_context(context: str) -> dict:
    state = _load_state()
    _save_state({**state, "company_context": context.strip()})
    return {
        "success": True,
        "message": "Company context saved. It will be used to enrich table and column descriptions.",
    }
