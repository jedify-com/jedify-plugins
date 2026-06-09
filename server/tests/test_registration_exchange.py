import httpx
import pytest
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
    header_names = {k.lower() for k in route.calls.last.request.headers.keys()}
    assert "authorization" not in header_names


@respx.mock
async def test_exchange_code_raises_on_http_error(monkeypatch):
    monkeypatch.delenv("DESCOPE_BASE_URL", raising=False)
    monkeypatch.delenv("DESCOPE_CLIENT_ID", raising=False)
    respx.post("https://auth.app.jedify.com/oauth2/v1/apps/token").mock(
        return_value=httpx.Response(400, json={"error": "invalid_grant"})
    )
    with pytest.raises(httpx.HTTPStatusError):
        await registration.exchange_code("BADCODE", "VERIFIER")
