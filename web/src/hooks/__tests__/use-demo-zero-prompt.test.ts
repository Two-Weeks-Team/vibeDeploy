import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useDemoZeroPrompt } from "../use-demo-zero-prompt";

// Mock the demo data so we control timing and card definitions
vi.mock("@/lib/demo-data", () => {
  const MOCK_CARDS = [
    {
      card_id: "test-card-1",
      video_id: "vid1",
      title: "Test Card One",
      status: "analyzing" as const,
      score: 0,
      domain: "Test",
    },
    {
      card_id: "test-card-2",
      video_id: "vid2",
      title: "Test Card Two",
      status: "analyzing" as const,
      score: 0,
      domain: "Test",
    },
  ];

  const MOCK_TIMELINE = [
    {
      time: 100,
      cardUpdate: { card_id: "test-card-1", status: "analyzing" as const, score: 0 },
      action: { type: "card", message: "Discovered card 1" },
    },
    {
      time: 200,
      cardUpdate: { card_id: "test-card-1", status: "go_ready" as const, score: 82 },
      action: { type: "verdict", message: "Card 1 scored 82 — GO" },
    },
    {
      time: 300,
      cardUpdate: { card_id: "test-card-2", status: "analyzing" as const, score: 0 },
      action: { type: "card", message: "Discovered card 2" },
    },
    {
      time: 400,
      cardUpdate: { card_id: "test-card-2", status: "nogo" as const, score: 30 },
      action: { type: "verdict", message: "Card 2 scored 30 — NO-GO" },
    },
    {
      time: 500,
      sessionStatus: "completed" as const,
    },
  ];

  return {
    DEMO_CARDS: MOCK_CARDS,
    DEMO_TIMELINE: MOCK_TIMELINE,
    DEMO_SPEED_MULTIPLIER: 1,
  };
});

describe("useDemoZeroPrompt", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns null session before startSession is called", () => {
    const { result } = renderHook(() => useDemoZeroPrompt());

    expect(result.current.session).toBeNull();
    expect(result.current.isConnected).toBe(false);
    expect(result.current.isCompleted).toBe(false);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.actions).toEqual([]);
    expect(result.current.error).toBeNull();
  });

  it("startSession creates a demo session with DEMO_SESSION_ID after loading", () => {
    const { result } = renderHook(() => useDemoZeroPrompt());

    act(() => {
      result.current.startSession();
    });

    // Should be loading immediately
    expect(result.current.isLoading).toBe(true);
    expect(result.current.session).toBeNull();

    // Advance past the 800ms loading delay
    act(() => {
      vi.advanceTimersByTime(800);
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.isConnected).toBe(true);
    expect(result.current.session).not.toBeNull();
    expect(result.current.session!.session_id).toBe("demo-zp-auto-20260318");
    expect(result.current.session!.status).toBe("exploring");
    expect(result.current.session!.cards).toEqual([]);
  });

  it("cards appear according to DEMO_TIMELINE timing", () => {
    const { result } = renderHook(() => useDemoZeroPrompt());

    act(() => {
      result.current.startSession();
    });

    // Advance past loading (800ms)
    act(() => {
      vi.advanceTimersByTime(800);
    });

    // No cards yet (first card at 100ms after session start)
    expect(result.current.session!.cards).toHaveLength(0);

    // Advance to 100ms — first card appears in analyzing state
    act(() => {
      vi.advanceTimersByTime(100);
    });

    expect(result.current.session!.cards).toHaveLength(1);
    expect(result.current.session!.cards[0].card_id).toBe("test-card-1");
    expect(result.current.session!.cards[0].status).toBe("analyzing");

    // Advance to 200ms — first card becomes go_ready
    act(() => {
      vi.advanceTimersByTime(100);
    });

    expect(result.current.session!.cards).toHaveLength(1);
    expect(result.current.session!.cards[0].status).toBe("go_ready");
    expect(result.current.session!.cards[0].score).toBe(82);

    // Advance to 300ms — second card appears
    act(() => {
      vi.advanceTimersByTime(100);
    });

    expect(result.current.session!.cards).toHaveLength(2);
    expect(result.current.session!.cards[1].card_id).toBe("test-card-2");
  });

  it("actions are prepended to the actions list as timeline progresses", () => {
    const { result } = renderHook(() => useDemoZeroPrompt());

    act(() => {
      result.current.startSession();
    });

    act(() => {
      vi.advanceTimersByTime(800);
    });

    // After first timeline event (100ms)
    act(() => {
      vi.advanceTimersByTime(100);
    });

    expect(result.current.actions).toHaveLength(1);
    expect(result.current.actions[0].message).toBe("Discovered card 1");

    // After second event (200ms)
    act(() => {
      vi.advanceTimersByTime(100);
    });

    // Actions are prepended, so newest is first
    expect(result.current.actions).toHaveLength(2);
    expect(result.current.actions[0].message).toBe("Card 1 scored 82 — GO");
  });

  it("queueBuild changes card status from go_ready to build_queued", () => {
    const { result } = renderHook(() => useDemoZeroPrompt());

    act(() => {
      result.current.startSession();
    });

    // Advance to have card 1 at go_ready (800 + 200ms)
    act(() => {
      vi.advanceTimersByTime(1000);
    });

    expect(result.current.session!.cards[0].status).toBe("go_ready");

    act(() => {
      result.current.queueBuild("test-card-1");
    });

    expect(result.current.session!.cards[0].status).toBe("build_queued");
    // Should add a build action
    expect(result.current.actions[0].type).toBe("build");
    expect(result.current.actions[0].message).toContain("test-card-1");
  });

  it("passCard changes card status from go_ready to passed", () => {
    const { result } = renderHook(() => useDemoZeroPrompt());

    act(() => {
      result.current.startSession();
    });

    act(() => {
      vi.advanceTimersByTime(1000);
    });

    expect(result.current.session!.cards[0].status).toBe("go_ready");

    act(() => {
      result.current.passCard("test-card-1");
    });

    expect(result.current.session!.cards[0].status).toBe("passed");
    expect(result.current.actions[0].type).toBe("pass");
  });

  it("deleteCard removes card from session", () => {
    const { result } = renderHook(() => useDemoZeroPrompt());

    act(() => {
      result.current.startSession();
    });

    // Advance to have both cards (800 + 300ms)
    act(() => {
      vi.advanceTimersByTime(1100);
    });

    expect(result.current.session!.cards).toHaveLength(2);

    act(() => {
      result.current.deleteCard("test-card-1");
    });

    expect(result.current.session!.cards).toHaveLength(1);
    expect(result.current.session!.cards[0].card_id).toBe("test-card-2");
    expect(result.current.actions[0].type).toBe("delete");
  });

  it("queueBuild does not change status for non-go_ready cards", () => {
    const { result } = renderHook(() => useDemoZeroPrompt());

    act(() => {
      result.current.startSession();
    });

    // Advance to 800 + 400ms — card-2 is at nogo status
    act(() => {
      vi.advanceTimersByTime(1200);
    });

    const card2 = result.current.session!.cards.find(
      (c) => c.card_id === "test-card-2",
    );
    expect(card2!.status).toBe("nogo");

    act(() => {
      result.current.queueBuild("test-card-2");
    });

    const card2After = result.current.session!.cards.find(
      (c) => c.card_id === "test-card-2",
    );
    expect(card2After!.status).toBe("nogo");
  });

  it("cleanup cancels all timers on unmount", () => {
    const clearTimeoutSpy = vi.spyOn(global, "clearTimeout");

    const { result, unmount } = renderHook(() => useDemoZeroPrompt());

    act(() => {
      result.current.startSession();
    });

    // The hook should have scheduled timers (loading timer + timeline timers after load)
    act(() => {
      vi.advanceTimersByTime(800);
    });

    const callsBefore = clearTimeoutSpy.mock.calls.length;

    unmount();

    // clearTimeout should have been called for each pending timer
    expect(clearTimeoutSpy.mock.calls.length).toBeGreaterThan(callsBefore);

    clearTimeoutSpy.mockRestore();
  });

  it("isCompleted returns true when session status is completed", () => {
    const { result } = renderHook(() => useDemoZeroPrompt());

    act(() => {
      result.current.startSession();
    });

    // Advance past all timeline events (800 + 500ms)
    act(() => {
      vi.advanceTimersByTime(800);
    });

    expect(result.current.isCompleted).toBe(false);

    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(result.current.session!.status).toBe("completed");
    expect(result.current.isCompleted).toBe(true);
    expect(result.current.isConnected).toBe(false);
  });

  it("reExplore removes card and adds explore action", () => {
    const { result } = renderHook(() => useDemoZeroPrompt());

    act(() => {
      result.current.startSession();
    });

    act(() => {
      vi.advanceTimersByTime(1000);
    });

    act(() => {
      result.current.reExplore("test-card-1");
    });

    expect(
      result.current.session!.cards.find((c) => c.card_id === "test-card-1"),
    ).toBeUndefined();
    expect(result.current.actions[0].type).toBe("explore");
    expect(result.current.actions[0].message).toContain("test-card-1");
  });
});
