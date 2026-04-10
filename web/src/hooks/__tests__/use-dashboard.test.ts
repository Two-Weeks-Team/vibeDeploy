import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { MeetingResultFull, VerdictType } from "@/types/dashboard";

// Mock the dashboard-api module at the top level
vi.mock("@/lib/dashboard-api", () => ({
  checkHealth: vi.fn(),
  getDashboardStats: vi.fn(),
  getDashboardResults: vi.fn(),
  getDashboardBrainstorms: vi.fn(),
  getDashboardDeployments: vi.fn(),
}));

// Import after mock registration
import {
  checkHealth,
  getDashboardStats,
  getDashboardResults,
  getDashboardBrainstorms,
  getDashboardDeployments,
} from "@/lib/dashboard-api";
import { useDashboard } from "../use-dashboard";

const mockCheckHealth = vi.mocked(checkHealth);
const mockGetStats = vi.mocked(getDashboardStats);
const mockGetResults = vi.mocked(getDashboardResults);
const mockGetBrainstorms = vi.mocked(getDashboardBrainstorms);
const mockGetDeployments = vi.mocked(getDashboardDeployments);

function setupHealthyMocks(results: MeetingResultFull[] = []) {
  mockCheckHealth.mockResolvedValue(true);
  mockGetStats.mockResolvedValue({
    total_meetings: 5,
    total_brainstorms: 2,
    avg_score: 65,
    go_count: 3,
    nogo_count: 2,
  });
  mockGetResults.mockResolvedValue(results as never);
  mockGetBrainstorms.mockResolvedValue([]);
  mockGetDeployments.mockResolvedValue([]);
}

function makeMeetingResult(
  overrides: Partial<MeetingResultFull> & { score: number; verdict: VerdictType },
): MeetingResultFull {
  return {
    thread_id: `thread-${Math.random().toString(36).slice(2, 8)}`,
    analyses: [],
    scoring: {
      final_score: overrides.score,
      decision: overrides.verdict === "NO-GO" ? "NO_GO" : overrides.verdict,
    },
    debates: [],
    documents: [],
    created_at: new Date().toISOString(),
    ...overrides,
  } as MeetingResultFull;
}

/** Flush all microtasks and pending timers in the right order */
async function flushTimersAndMicrotasks() {
  // Flush the setTimeout(refresh, 0) and let promise resolutions settle
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1);
  });
}

describe("useDashboard", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns zeroed stats on initial load failure", async () => {
    mockCheckHealth.mockResolvedValue(false);

    const { result } = renderHook(() => useDashboard());

    await flushTimersAndMicrotasks();

    expect(result.current.loading).toBe(false);
    expect(result.current.healthy).toBe(false);
    expect(result.current.stats.total_meetings).toBe(0);
    expect(result.current.stats.avg_score).toBe(0);
    expect(result.current.stats.go_count).toBe(0);
    expect(result.current.stats.nogo_count).toBe(0);
  });

  it("polls on POLL_MS interval (5000ms)", async () => {
    setupHealthyMocks();

    const { result } = renderHook(() => useDashboard());

    // Initial immediate refresh
    await flushTimersAndMicrotasks();

    expect(result.current.loading).toBe(false);

    const initialCallCount = mockCheckHealth.mock.calls.length;

    // Advance by one poll interval
    await act(async () => {
      vi.advanceTimersByTime(5000);
      await vi.advanceTimersByTimeAsync(0);
    });

    expect(mockCheckHealth.mock.calls.length).toBeGreaterThan(initialCallCount);

    // Advance by another poll interval
    await act(async () => {
      vi.advanceTimersByTime(5000);
      await vi.advanceTimersByTimeAsync(0);
    });

    expect(mockCheckHealth.mock.calls.length).toBeGreaterThan(
      initialCallCount + 1,
    );
  });

  it("computeScoreDistribution bins correctly (0-25, 26-50, 51-75, 76-100)", async () => {
    const results: MeetingResultFull[] = [
      makeMeetingResult({ score: 10, verdict: "NO-GO" }),
      makeMeetingResult({ score: 25, verdict: "NO-GO" }),
      makeMeetingResult({ score: 30, verdict: "CONDITIONAL" }),
      makeMeetingResult({ score: 50, verdict: "CONDITIONAL" }),
      makeMeetingResult({ score: 60, verdict: "CONDITIONAL" }),
      makeMeetingResult({ score: 75, verdict: "GO" }),
      makeMeetingResult({ score: 80, verdict: "GO" }),
      makeMeetingResult({ score: 95, verdict: "GO" }),
      makeMeetingResult({ score: 100, verdict: "GO" }),
    ];

    setupHealthyMocks(results);

    const { result } = renderHook(() => useDashboard());

    await flushTimersAndMicrotasks();

    expect(result.current.loading).toBe(false);

    const dist = result.current.scoreDistribution;
    expect(dist).toHaveLength(4);
    // 0-25: scores 10, 25
    expect(dist[0].range).toBe("0\u201325");
    expect(dist[0].count).toBe(2);
    // 26-50: scores 30, 50
    expect(dist[1].range).toBe("26\u201350");
    expect(dist[1].count).toBe(2);
    // 51-75: scores 60, 75
    expect(dist[2].range).toBe("51\u201375");
    expect(dist[2].count).toBe(2);
    // 76-100: scores 80, 95, 100
    expect(dist[3].range).toBe("76\u2013100");
    expect(dist[3].count).toBe(3);
  });

  it("computeVerdictBreakdown counts GO/CONDITIONAL/NO-GO", async () => {
    const results: MeetingResultFull[] = [
      makeMeetingResult({ score: 80, verdict: "GO" }),
      makeMeetingResult({ score: 85, verdict: "GO" }),
      makeMeetingResult({ score: 55, verdict: "CONDITIONAL" }),
      makeMeetingResult({ score: 20, verdict: "NO-GO" }),
      makeMeetingResult({ score: 15, verdict: "NO-GO" }),
      makeMeetingResult({ score: 10, verdict: "NO-GO" }),
    ];

    setupHealthyMocks(results);

    const { result } = renderHook(() => useDashboard());

    await flushTimersAndMicrotasks();

    expect(result.current.loading).toBe(false);

    const breakdown = result.current.verdictBreakdown;
    expect(breakdown.GO).toBe(2);
    expect(breakdown.CONDITIONAL).toBe(1);
    expect(breakdown["NO-GO"]).toBe(3);
  });

  it("cleanup stops polling on unmount", async () => {
    setupHealthyMocks();

    const { result, unmount } = renderHook(() => useDashboard());

    await flushTimersAndMicrotasks();

    expect(result.current.loading).toBe(false);

    const callsBeforeUnmount = mockCheckHealth.mock.calls.length;

    unmount();

    // Advance past several poll cycles after unmount
    await act(async () => {
      vi.advanceTimersByTime(20000);
      await vi.advanceTimersByTimeAsync(0);
    });

    // No more calls should have been made
    expect(mockCheckHealth.mock.calls.length).toBe(callsBeforeUnmount);
  });

  it("returns healthy=true and populated stats when API is healthy", async () => {
    setupHealthyMocks();

    const { result } = renderHook(() => useDashboard());

    await flushTimersAndMicrotasks();

    expect(result.current.loading).toBe(false);
    expect(result.current.healthy).toBe(true);
    expect(result.current.stats.total_meetings).toBe(5);
    expect(result.current.stats.avg_score).toBe(65);
    expect(result.current.lastUpdated).not.toBeNull();
  });
});
