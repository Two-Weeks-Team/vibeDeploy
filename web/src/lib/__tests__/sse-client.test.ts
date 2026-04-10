import { describe, it, expect, vi, beforeEach } from "vitest";
import { createSSEClient } from "../sse-client";

function mockReadableStream(chunks: string[]) {
  let index = 0;
  return {
    getReader: () => ({
      read: async () => {
        if (index >= chunks.length) return { done: true, value: undefined };
        const value = new TextEncoder().encode(chunks[index++]);
        return { done: false, value };
      },
    }),
  };
}

describe("sse-client", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllEnvs();
  });

  it("parses JSON SSE data lines and calls onEvent", async () => {
    const events: Array<{ type: string; data: Record<string, unknown> }> = [];

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        body: mockReadableStream([
          'data: {"type":"phase","step":"council"}\n\n',
          'data: {"type":"score","value":85}\n\n',
        ]),
      }),
    );

    const abort = createSSEClient({
      url: "http://test/run",
      body: { prompt: "test" },
      onEvent: (event) => events.push(event),
      onComplete: () => {},
    });

    // Wait for async stream processing
    await new Promise((r) => setTimeout(r, 50));

    expect(events.length).toBe(2);
    expect(events[0].type).toBe("phase");
    expect(events[1].data).toEqual({ type: "score", value: 85 });

    abort();
  });

  it("handles plain text SSE data gracefully", async () => {
    const events: Array<{ type: string; data: Record<string, unknown> }> = [];

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        body: mockReadableStream(["data: not-json-content\n\n"]),
      }),
    );

    createSSEClient({
      url: "http://test/run",
      body: { prompt: "test" },
      onEvent: (event) => events.push(event),
    });

    await new Promise((r) => setTimeout(r, 50));

    expect(events.length).toBe(1);
    expect(events[0].type).toBe("message");
    expect(events[0].data).toEqual({ text: "not-json-content" });
  });

  it("calls onError on non-ok response", async () => {
    const errors: Error[] = [];

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
      }),
    );

    createSSEClient({
      url: "http://test/run",
      body: { prompt: "test" },
      onEvent: () => {},
      onError: (err) => errors.push(err),
    });

    await new Promise((r) => setTimeout(r, 50));

    expect(errors.length).toBe(1);
    expect(errors[0].message).toContain("500");
  });

  it("calls onComplete when stream ends", async () => {
    let completed = false;

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        body: mockReadableStream([]),
      }),
    );

    createSSEClient({
      url: "http://test/run",
      body: { prompt: "test" },
      onEvent: () => {},
      onComplete: () => {
        completed = true;
      },
    });

    await new Promise((r) => setTimeout(r, 50));

    expect(completed).toBe(true);
  });

  it("abort returns a function", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        body: mockReadableStream([]),
      }),
    );

    const abort = createSSEClient({
      url: "http://test/run",
      body: { prompt: "test" },
      onEvent: () => {},
    });

    expect(typeof abort).toBe("function");
    abort(); // Should not throw
  });

  it("ignores SSE comment lines starting with colon", async () => {
    const events: Array<{ type: string }> = [];

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        body: mockReadableStream([
          ": this is a comment\n",
          'data: {"type":"real"}\n\n',
        ]),
      }),
    );

    createSSEClient({
      url: "http://test/run",
      body: { prompt: "test" },
      onEvent: (event) => events.push(event),
    });

    await new Promise((r) => setTimeout(r, 50));

    expect(events.length).toBe(1);
    expect(events[0].type).toBe("real");
  });
});
