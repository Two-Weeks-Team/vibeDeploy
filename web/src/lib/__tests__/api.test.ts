import { describe, it, expect, vi, beforeEach } from "vitest";
import { startMeeting, getMeetingResult, DASHBOARD_API_URL } from "../api";
import { checkHealth } from "../dashboard-api";

describe("api.ts", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe("startMeeting", () => {
    it("returns meetingId and streamUrl on success", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
      });

      const result = await startMeeting("test input");

      expect(result).toHaveProperty("meetingId");
      expect(typeof result.meetingId).toBe("string");
      expect(result.streamUrl).toBe(`${DASHBOARD_API_URL}/run`);
      expect(global.fetch).toHaveBeenCalledWith(`${DASHBOARD_API_URL}/run`, expect.any(Object));
    });

    it("throws an error on non-ok response", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
      });

      await expect(startMeeting("test input")).rejects.toThrow("Agent returned 500");
    });
  });

  describe("checkHealth", () => {
    it("returns true on ok response", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
      });

      const result = await checkHealth();
      expect(result).toBe(true);
      expect(global.fetch).toHaveBeenCalledWith(`${DASHBOARD_API_URL}/health`);
    });

    it("returns false on network error", async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error("Network error"));

      const result = await checkHealth();
      expect(result).toBe(false);
    });
  });

  describe("getMeetingResult", () => {
    it("returns null on 404", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
      });

      const result = await getMeetingResult("test-id");
      expect(result).toBeNull();
      expect(global.fetch).toHaveBeenCalledWith(`${DASHBOARD_API_URL}/result/test-id`);
    });

    it("returns data on success", async () => {
      const mockData = { score: 100, verdict: "GO" };
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockData,
      });

      const result = await getMeetingResult("test-id");
      expect(result).toEqual(mockData);
    });
  });
});
