import { describe, it, expect, vi, beforeEach } from "vitest";

// Stub env before any module import
vi.stubEnv("VIBEDEPLOY_API_KEY", "test-key-abc");

// Must mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

describe("dashboard-api", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("checkHealth", () => {
    it("returns true when response is ok", async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });

      const { checkHealth } = await import("../dashboard-api");
      const result = await checkHealth();

      expect(result).toBe(true);
    });

    it("returns false when response is not ok", async () => {
      mockFetch.mockResolvedValueOnce({ ok: false });

      const { checkHealth } = await import("../dashboard-api");
      const result = await checkHealth();

      expect(result).toBe(false);
    });

    it("returns false when fetch throws", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      const { checkHealth } = await import("../dashboard-api");
      const result = await checkHealth();

      expect(result).toBe(false);
    });
  });

  describe("getDashboardStats", () => {
    it("returns stats on success", async () => {
      const statsPayload = {
        total_meetings: 10,
        total_brainstorms: 3,
        avg_score: 72,
        go_count: 7,
        nogo_count: 3,
      };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => statsPayload,
      });

      const { getDashboardStats } = await import("../dashboard-api");
      const result = await getDashboardStats();

      expect(result).toEqual(statsPayload);
    });

    it("returns zeroed defaults on failure", async () => {
      mockFetch.mockResolvedValueOnce({ ok: false });

      const { getDashboardStats } = await import("../dashboard-api");
      const result = await getDashboardStats();

      expect(result).toEqual({
        total_meetings: 0,
        total_brainstorms: 0,
        avg_score: 0,
        go_count: 0,
        nogo_count: 0,
      });
    });

    it("returns zeroed defaults on network error", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Connection refused"));

      const { getDashboardStats } = await import("../dashboard-api");
      const result = await getDashboardStats();

      expect(result).toEqual({
        total_meetings: 0,
        total_brainstorms: 0,
        avg_score: 0,
        go_count: 0,
        nogo_count: 0,
      });
    });
  });

  describe("getDashboardResults", () => {
    it("returns results array on success", async () => {
      const resultsPayload = [
        { thread_id: "t1", score: 80, verdict: "GO", created_at: "2026-04-01" },
      ];
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => resultsPayload,
      });

      const { getDashboardResults } = await import("../dashboard-api");
      const result = await getDashboardResults();

      expect(result).toEqual(resultsPayload);
    });

    it("returns empty array on failure", async () => {
      mockFetch.mockResolvedValueOnce({ ok: false });

      const { getDashboardResults } = await import("../dashboard-api");
      const result = await getDashboardResults();

      expect(result).toEqual([]);
    });

    it("returns empty array on network error", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Timeout"));

      const { getDashboardResults } = await import("../dashboard-api");
      const result = await getDashboardResults();

      expect(result).toEqual([]);
    });
  });

  describe("getDashboardDeployments", () => {
    it("returns deployments array on success", async () => {
      const deploymentsPayload = [
        {
          thread_id: "d1",
          score: 90,
          verdict: "GO",
          input_prompt: "test",
          idea_summary: "summary",
          deployment: { repoUrl: "https://github.com/test", liveUrl: "https://test.app" },
          created_at: "2026-04-01",
        },
      ];
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => deploymentsPayload,
      });

      const { getDashboardDeployments } = await import("../dashboard-api");
      const result = await getDashboardDeployments();

      expect(result).toEqual(deploymentsPayload);
    });

    it("returns empty array on failure", async () => {
      mockFetch.mockResolvedValueOnce({ ok: false });

      const { getDashboardDeployments } = await import("../dashboard-api");
      const result = await getDashboardDeployments();

      expect(result).toEqual([]);
    });

    it("returns empty array on network error", async () => {
      mockFetch.mockRejectedValueOnce(new Error("503 Service Unavailable"));

      const { getDashboardDeployments } = await import("../dashboard-api");
      const result = await getDashboardDeployments();

      expect(result).toEqual([]);
    });
  });

  describe("authenticated fetch headers", () => {
    it("all API calls include Content-Type and X-API-Key headers", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({}),
      });

      const { checkHealth } = await import("../dashboard-api");
      await checkHealth();

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [, init] = mockFetch.mock.calls[0];
      expect(init.headers["Content-Type"]).toBe("application/json");
      expect(init.headers["X-API-Key"]).toBe("test-key-abc");
    });
  });
});
