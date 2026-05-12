import json
import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger("jedify_lens.registration")

_STATE_PATH = Path.home() / ".jedify" / "state.json"
_REGISTER_URL = "https://app.jedify.com/api/v1/skills/register"


def _load_state() -> dict:
    try:
        return json.loads(_STATE_PATH.read_text())
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STATE_PATH.write_text(json.dumps(state, indent=2))


def is_registered() -> bool:
    return _load_state().get("registered", False)


async def check_registration() -> dict:
    """
    Check whether the user has registered. Call this first before any other tool.
    Returns a welcome message if already registered, or a prompt to register if not.
    """
    if is_registered():
        state = _load_state()
        return {
            "registered": True,
            "message": f"Welcome back! You're all set as {state.get('email', 'a registered user')}.",
        }
    return {
        "registered": False,
        "message": (
            "Welcome to jedify-lens! To get started, please share your email address "
            "(and optionally your company name) so we can register you. "
            "Then call the `register_user` tool with your details."
        ),
    }


async def register_user(email: str, company: str = "") -> dict:
    """
    Register the user with their email. Called once after check_registration returns registered=false.
    """
    if not email or "@" not in email:
        return {"success": False, "message": "Please provide a valid email address."}

    state = _load_state()
    state.update({"registered": True, "email": email, "company": company})
    _save_state(state)

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                _REGISTER_URL,
                json={
                    "email": email,
                    "company": company,
                    "skill": "schema-context",
                    "source": "mcp-first-use",
                    "version": "0.1.0",
                },
            )
    except Exception as e:
        logger.debug(f"Registration API call failed (non-blocking): {e}")

    return {
        "success": True,
        "message": f"You're registered! Let's explore your warehouse schema.",
    }
