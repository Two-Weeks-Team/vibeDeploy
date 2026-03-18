import { renderHook } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { usePipelineMonitor } from "../use-pipeline-monitor";

describe("usePipelineMonitor", () => {
  beforeEach(() => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
      body: {
        getReader: () => ({
          read: vi.fn().mockResolvedValue({ done: true }),
        }),
      },
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("has empty initial state", () => {
    const { result } = renderHook(() => usePipelineMonitor());

    expect(result.current.activePipelines).toEqual([]);
    expect(result.current.events).toEqual([]);
    expect(result.current.nodeStatuses).toEqual({});
    expect(result.current.connected).toBe(false);
  });

  it("provides expected interface", () => {
    const { result } = renderHook(() => usePipelineMonitor());

    expect(result.current).toHaveProperty("activePipelines");
    expect(result.current).toHaveProperty("events");
    expect(result.current).toHaveProperty("nodeStatuses");
    expect(result.current).toHaveProperty("connected");
  });

  it("includes nodeMetadata in returned interface", () => {
    const { result } = renderHook(() => usePipelineMonitor());

    expect(result.current).toHaveProperty("nodeMetadata");
    expect(result.current.nodeMetadata).toEqual({});
  });

});

