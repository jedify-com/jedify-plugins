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
    assert qs["client_id"] == ["UDJmR3RzQW01emlBWnIwc3dEeU1ETzdUY2U4NzpUUEEzRXRxZDdhbE5oSjdEZTdTNmhycUx4RFZpczAj"]
    assert qs["redirect_uri"] == ["http://localhost:8765/callback"]
    assert qs["scope"] == ["openid email profile"]
    assert qs["code_challenge"] == ["CHALLENGE"]
    assert qs["code_challenge_method"] == ["S256"]
    assert qs["state"] == ["STATE123"]
    assert "prompt" not in qs
