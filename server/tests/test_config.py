from jedify_lens import config


def test_defaults_are_prod(monkeypatch):
    monkeypatch.delenv("DESCOPE_BASE_URL", raising=False)
    monkeypatch.delenv("DESCOPE_CLIENT_ID", raising=False)
    assert config.base_url() == "https://auth.app.jedify.com"
    assert config.client_id() == "UDJmR3RzQW01emlBWnIwc3dEeU1ETzdUY2U4NzpUUEEzRXRxZDdhbE5oSjdEZTdTNmhycUx4RFZpczAj"
    assert config.authorize_url() == "https://auth.app.jedify.com/oauth2/v1/apps/authorize"
    assert config.token_url() == "https://auth.app.jedify.com/oauth2/v1/apps/token"


def test_env_overrides_and_strip_trailing_slash(monkeypatch):
    monkeypatch.setenv("DESCOPE_BASE_URL", "https://auth.dev.jedify.com/")
    monkeypatch.setenv("DESCOPE_CLIENT_ID", "DEVCLIENT")
    assert config.base_url() == "https://auth.dev.jedify.com"
    assert config.client_id() == "DEVCLIENT"
    assert config.authorize_url() == "https://auth.dev.jedify.com/oauth2/v1/apps/authorize"
    assert config.token_url() == "https://auth.dev.jedify.com/oauth2/v1/apps/token"


def test_redirect_and_scope_constants():
    assert config.REDIRECT_PORT == 8765
    assert config.REDIRECT_URI == "http://localhost:8765/callback"
    assert config.SCOPES == "openid email"
