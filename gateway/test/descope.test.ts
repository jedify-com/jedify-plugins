import { describe, it, expect, vi, afterEach } from "vitest";
import { fetchEmail } from "../src/descope-handler";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("fetchEmail", () => {
  it("returns the email on a 200 response with email field", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ email: "user@example.com", sub: "abc123" }),
      }),
    );

    const email = await fetchEmail("test-access-token");
    expect(email).toBe("user@example.com");
  });

  it("returns empty string on a non-200 response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ error: "unauthorized" }),
      }),
    );

    const email = await fetchEmail("bad-token");
    expect(email).toBe("");
  });

  it("returns empty string when the response contains no email field", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ sub: "abc123" }),
      }),
    );

    const email = await fetchEmail("test-access-token");
    expect(email).toBe("");
  });

  it("calls the correct userinfo URL with the Bearer token", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ email: "omer@jedify.com" }),
    });
    vi.stubGlobal("fetch", mockFetch);

    await fetchEmail("my-token");

    expect(mockFetch).toHaveBeenCalledWith(
      "https://auth.app.jedify.com/oauth2/v1/apps/userinfo",
      { headers: { Authorization: "Bearer my-token" } },
    );
  });
});
