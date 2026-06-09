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


async def _do_refresh(refresh_tok: str, pid: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _TOKEN_ENDPOINT,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Bearer {pid}",
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_tok,
                "client_id": pid,
            },
        )
        resp.raise_for_status()
        return resp.json()


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
            pid = config.client_id()
            data = await _do_refresh(refresh_tok, pid)
            new_token = _extract_token(data)
            state["access_token"] = new_token
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


async def browser_login() -> dict:
    pid = config.client_id()

    # PKCE
    code_verifier = secrets.token_urlsafe(32)
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    state_param = secrets.token_urlsafe(32)

    auth_url = f"{_AUTH_ENDPOINT}?" + urlencode({
        "response_type": "code",
        "client_id": pid,
        "redirect_uri": _REDIRECT_URI,
        "scope": "openid",
        "state": state_param,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "prompt": "login",
    })

    loop = asyncio.get_event_loop()
    callback_event = asyncio.Event()
    callback_data: dict = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/callback":
                qs = parse_qs(parsed.query)
                error = qs.get("error", [None])[0]
                code = qs.get("code", [None])[0]

                if error:
                    callback_data["error"] = error
                    body = (
                        f"<html><body style='font-family:sans-serif;text-align:center;padding:60px'>"
                        f"<h2>Authentication error</h2><p>{error}</p></body></html>"
                    ).encode()
                    self.send_response(400)
                elif code:
                    callback_data["code"] = code
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

    server = HTTPServer(("localhost", _CALLBACK_PORT), CallbackHandler)
    Thread(target=server.serve_forever, daemon=True).start()

    webbrowser.open(auth_url)
    logger.info("Opened Descope OAuth login")

    try:
        await asyncio.wait_for(callback_event.wait(), timeout=300)
    except asyncio.TimeoutError:
        server.shutdown()
        return {"success": False, "action": "Tell the user: 'Sign-in timed out — please try again.'"}
    finally:
        server.shutdown()

    if "error" in callback_data:
        auth_error = callback_data["error"]
        return {"success": False, "action": f"Tell the user: 'Auth error — {auth_error}'"}

    code = callback_data.get("code")
    if not code:
        return {"success": False, "action": "Tell the user: 'No auth code received — please try again.'"}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _TOKEN_ENDPOINT,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": f"Bearer {pid}",
                },
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": _REDIRECT_URI,
                    "client_id": pid,
                    "code_verifier": code_verifier,
                },
            )
            resp.raise_for_status()
            data = resp.json()

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


async def save_company_context(context: str) -> dict:
    state = _load_state()
    state["company_context"] = context.strip()
    _save_state(state)
    return {
        "success": True,
        "message": "Company context saved. It will be used to enrich table and column descriptions.",
    }
