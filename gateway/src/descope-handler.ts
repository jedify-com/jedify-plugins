import { Hono } from "hono";
import type { OAuthHelpers } from "@cloudflare/workers-oauth-provider";

const DESCOPE_BASE = "https://auth.app.jedify.com";
const DESCOPE_CLIENT_ID =
  "UDJmR3RzQW01emlBWnIwc3dEeU1ETzdUY2U4NzpUUEEzRXRxZDdhbE5oSjdEZTdTNmhycUx4RFZpczAj";
const SCOPES = "openid email";

type Bindings = {
  OAUTH_PROVIDER: OAuthHelpers;
  OAUTH_KV: KVNamespace;
  DESCOPE_CLIENT_SECRET: string;
};

const app = new Hono<{ Bindings: Bindings }>();

app.get("/authorize", async (c) => {
  const oauthReqInfo = await c.env.OAUTH_PROVIDER.parseAuthRequest(c.req.raw);
  const nonce = crypto.randomUUID();
  await c.env.OAUTH_KV.put(
    "authstate:" + nonce,
    JSON.stringify(oauthReqInfo),
    { expirationTtl: 600 },
  );
  const redirectUri = new URL("/callback", c.req.url).href;
  const url =
    `${DESCOPE_BASE}/oauth2/v1/apps/authorize?response_type=code` +
    `&client_id=${encodeURIComponent(DESCOPE_CLIENT_ID)}` +
    `&redirect_uri=${encodeURIComponent(redirectUri)}` +
    `&scope=${encodeURIComponent(SCOPES)}&state=${encodeURIComponent(nonce)}`;
  return c.redirect(url);
});

app.get("/callback", async (c) => {
  const code = c.req.query("code");
  const state = c.req.query("state");
  if (!code || !state) return c.text("Missing code/state", 400);

  const raw = await c.env.OAUTH_KV.get("authstate:" + state);
  if (!raw) return c.text("invalid or expired state", 400);
  const oauthReqInfo = JSON.parse(raw) as Awaited<
    ReturnType<OAuthHelpers["parseAuthRequest"]>
  >;
  await c.env.OAUTH_KV.delete("authstate:" + state);

  const tokenRes = await fetch(`${DESCOPE_BASE}/oauth2/v1/apps/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      code,
      redirect_uri: new URL("/callback", c.req.url).href,
      client_id: DESCOPE_CLIENT_ID,
      client_secret: c.env.DESCOPE_CLIENT_SECRET,
    }),
  });

  if (!tokenRes.ok) return c.text("Descope token exchange failed", 502);

  const tokens = (await tokenRes.json()) as {
    id_token?: string;
    access_token?: string;
  };

  const userinfoRes = await fetch(`${DESCOPE_BASE}/oauth2/v1/apps/userinfo`, {
    headers: { Authorization: `Bearer ${tokens.access_token}` },
  });
  const email = userinfoRes.ok
    ? (((await userinfoRes.json()) as { email?: string }).email ?? "")
    : "";

  const { redirectTo } = await c.env.OAUTH_PROVIDER.completeAuthorization({
    request: oauthReqInfo,
    userId: email || "unknown",
    metadata: { email },
    scope: oauthReqInfo.scope,
    props: { email },
  });

  return c.redirect(redirectTo);
});

/**
 * Fetch the email for an access token from Descope's userinfo endpoint.
 * Returns empty string if the request fails or the response contains no email.
 * Exported for unit testing.
 */
export async function fetchEmail(accessToken: string): Promise<string> {
  const res = await fetch(`${DESCOPE_BASE}/oauth2/v1/apps/userinfo`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) return "";
  const data = (await res.json()) as { email?: string };
  return data.email ?? "";
}

/**
 * A plain ExportedHandler-compatible wrapper around the Hono app.
 * OAuthProvider injects `env.OAUTH_PROVIDER` (OAuthHelpers) at runtime,
 * so the Hono app receives it through the normal env binding.
 *
 * The env parameter is widened to `unknown` so this object satisfies the
 * ExportedHandler shape required by OAuthProviderOptions.defaultHandler.
 * The cast to Bindings is safe because OAuthProvider always injects
 * OAUTH_PROVIDER and the worker wrangler config provides DESCOPE_CLIENT_SECRET.
 */
export const DescopeHandler = {
  fetch(request: Request, env: unknown, ctx: ExecutionContext): Promise<Response> {
    return Promise.resolve(app.fetch(request, env as Bindings, ctx));
  },
};
