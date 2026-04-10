import { describe, it, expect, vi, beforeEach } from "vitest";

describe("zero-prompt-api", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllEnvs();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ session_id: "test-session", status: "exploring", cards: [] }),
        text: async () => JSON.stringify({ session_id: "test-session", status: "exploring", cards: [] }),
      }),
    );
  });

  it("startSession sends POST with goal", async () => {
    const { startSession } = await import("../zero-prompt-api");
    const session = await startSession(5);
    expect(session.session_id).toBe("test-session");

    const [url, init] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain("/zero-prompt/start");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ goal: 5 });
  });

  it("startSession parses SSE-wrapped response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        text: async () => 'data: {"type":"zp.session.start","session_id":"sse-sess","session_status":"exploring","goal_go_cards":3}\n',
        json: async () => ({}),
      }),
    );
    const { startSession } = await import("../zero-prompt-api");
    const session = await startSession(3);
    expect(session.session_id).toBe("sse-sess");
  });

  it("startSession throws on non-ok response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500 }));
    const { startSession } = await import("../zero-prompt-api");
    await expect(startSession()).rejects.toThrow("Failed to start session");
  });

  it("getDashboard returns session data", async () => {
    const { getDashboard } = await import("../zero-prompt-api");
    const result = await getDashboard();
    expect(result.session_id).toBe("test-session");
  });

  it("queueBuild sends correct action payload", async () => {
    const { queueBuild } = await import("../zero-prompt-api");
    await queueBuild("session-1", "card-abc");

    const [url, init] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain("/zero-prompt/session-1/actions");
    expect(JSON.parse(init.body)).toEqual({ action: "queue_build", card_id: "card-abc" });
  });

  it("passCard sends correct action payload", async () => {
    const { passCard } = await import("../zero-prompt-api");
    await passCard("session-1", "card-xyz");

    const body = JSON.parse((fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].body);
    expect(body).toEqual({ action: "pass_card", card_id: "card-xyz" });
  });

  it("deleteCard sends correct action payload", async () => {
    const { deleteCard } = await import("../zero-prompt-api");
    await deleteCard("session-1", "card-del");

    const body = JSON.parse((fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].body);
    expect(body).toEqual({ action: "delete_card", card_id: "card-del" });
  });

  it("getBuildEventsUrl includes session and card IDs", async () => {
    const { getBuildEventsUrl } = await import("../zero-prompt-api");
    const url = getBuildEventsUrl("sess-1", "card-1");
    expect(url).toContain("/zero-prompt/sess-1/build/card-1/events");
  });
});
