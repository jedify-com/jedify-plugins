import json

from jedify_lens.tools import registration


async def test_save_company_context_strips_and_preserves(monkeypatch, tmp_path):
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"email": "bob@acme.com", "access_token": "tok"}))
    monkeypatch.setattr(registration, "_STATE_PATH", state_file)
    result = await registration.save_company_context("  we sell shoes  ")
    assert result["success"] is True
    persisted = json.loads(state_file.read_text())
    assert persisted["company_context"] == "we sell shoes"
    assert persisted["email"] == "bob@acme.com"
    assert persisted["access_token"] == "tok"


def test_load_state_corrupt_returns_empty(monkeypatch, tmp_path):
    state_file = tmp_path / "state.json"
    state_file.write_text("{ not valid json ")
    monkeypatch.setattr(registration, "_STATE_PATH", state_file)
    assert registration._load_state() == {}


def test_load_state_missing_returns_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(registration, "_STATE_PATH", tmp_path / "nope.json")
    assert registration._load_state() == {}
