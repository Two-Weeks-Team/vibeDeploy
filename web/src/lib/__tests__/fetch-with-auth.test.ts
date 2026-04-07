import { describe, it, expect, vi, beforeEach } from "vitest";

// Must mock process.env before importing the module
const MOCK_API_KEY = "test-api-key-123";

describe("fetch-with-auth", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllEnvs();
  });

  describe("authHeaders", () => {
    it("includes Content-Type by default", async () => {
      vi.stubEnv("VIBEDEPLOY_API_KEY", "");
      const { authHeaders } = await import("../fetch-with-auth");
      const headers = authHeaders();
      expect(headers["Content-Type"]).toBe("application/json");
    });

    it("includes X-API-Key when env var is set", async () => {
      vi.stubEnv("VIBEDEPLOY_API_KEY", MOCK_API_KEY);
      const { authHeaders } = await import("../fetch-with-auth");
      const headers = authHeaders();
      expect(headers["X-API-Key"]).toBe(MOCK_API_KEY);
    });

    it("omits X-API-Key when env var is empty", async () => {
      vi.stubEnv("VIBEDEPLOY_API_KEY", "");
      const { authHeaders } = await import("../fetch-with-auth");
      const headers = authHeaders();
      expect(headers["X-API-Key"]).toBeUndefined();
    });

    it("merges extra headers", async () => {
      vi.stubEnv("VIBEDEPLOY_API_KEY", "");
      const { authHeaders } = await import("../fetch-with-auth");
      const headers = authHeaders({ Accept: "text/event-stream" });
      expect(headers["Accept"]).toBe("text/event-stream");
      expect(headers["Content-Type"]).toBe("application/json");
    });
  });

  describe("appendApiKey", () => {
    it("appends api_key to URL without query params", async () => {
      vi.stubEnv("VIBEDEPLOY_API_KEY", MOCK_API_KEY);
      const { appendApiKey } = await import("../fetch-with-auth");
      const result = appendApiKey("http://example.com/events");
      expect(result).toContain("?api_key=");
      expect(result).toContain(MOCK_API_KEY);
    });

    it("appends with & when URL already has query params", async () => {
      vi.stubEnv("VIBEDEPLOY_API_KEY", MOCK_API_KEY);
      const { appendApiKey } = await import("../fetch-with-auth");
      const result = appendApiKey("http://example.com/events?session_id=abc");
      expect(result).toContain("&api_key=");
    });

    it("returns URL unchanged when no API key", async () => {
      vi.stubEnv("VIBEDEPLOY_API_KEY", "");
      const { appendApiKey } = await import("../fetch-with-auth");
      const url = "http://example.com/events";
      expect(appendApiKey(url)).toBe(url);
    });
  });

  describe("authenticatedFetch", () => {
    it("calls fetch with auth headers", async () => {
      vi.stubEnv("VIBEDEPLOY_API_KEY", MOCK_API_KEY);
      const mockFetch = vi.fn().mockResolvedValue(new Response("ok"));
      vi.stubGlobal("fetch", mockFetch);

      const { authenticatedFetch } = await import("../fetch-with-auth");
      await authenticatedFetch("http://example.com/api/run", {
        method: "POST",
        body: JSON.stringify({ prompt: "test" }),
      });

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url, init] = mockFetch.mock.calls[0];
      expect(url).toBe("http://example.com/api/run");
      expect(init.method).toBe("POST");
      expect(init.headers["Content-Type"]).toBe("application/json");
    });
  });
});
