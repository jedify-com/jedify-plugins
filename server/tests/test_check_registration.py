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
        return_value=httpx.Response(200, json={"access_token": fresh, "id_token": fresh, "refresh_token": "rtok2"})
    )
    result = await registration.check_registration()
    assert result["registered"] is True
    assert result["email"] == "bob@acme.com"
    persisted = json.loads(state_file.read_text())
    assert persisted["access_token"] == fresh
    assert persisted["refresh_token"] == "rtok2"


async def test_expired_token_no_refresh_token_unregistered(monkeypatch, tmp_path):
    state_file = tmp_path / "state.json"
    expired = _make_jwt({"exp": int(time.time()) - 10})
    state_file.write_text(json.dumps({"access_token": expired, "email": "bob@acme.com"}))
    monkeypatch.setattr(registration, "_STATE_PATH", state_file)
    result = await registration.check_registration()
    assert result["registered"] is False
    assert "login_tool" in result["action"]


@respx.mock
async def test_expired_token_refresh_failure_unregistered(monkeypatch, tmp_path):
    monkeypatch.delenv("DESCOPE_BASE_URL", raising=False)
    monkeypatch.delenv("DESCOPE_CLIENT_ID", raising=False)
    state_file = tmp_path / "state.json"
    expired = _make_jwt({"exp": int(time.time()) - 10})
    state_file.write_text(
        json.dumps({"access_token": expired, "refresh_token": "rtok", "email": "bob@acme.com"})
    )
    monkeypatch.setattr(registration, "_STATE_PATH", state_file)
    respx.post("https://auth.app.jedify.com/oauth2/v1/apps/token").mock(
        return_value=httpx.Response(400, json={"error": "invalid_grant"})
    )
    result = await registration.check_registration()
    assert result["registered"] is False
