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
