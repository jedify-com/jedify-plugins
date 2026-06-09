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
