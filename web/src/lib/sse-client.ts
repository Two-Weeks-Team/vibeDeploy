/**
 * SSE Client — Connects to the Gradient ADK agent's streaming endpoint.
 *
 * The agent uses @entrypoint which creates a POST /run endpoint that
 * streams text/event-stream responses. This client manages the connection,
 * parses SSE events, and dispatches them to callbacks.
 *
 * TODO (Wave 5): Implement full SSE parsing with event types,
 * reconnection logic, and error handling.
 */

export interface SSEEvent {
  /** Event type from the agent (e.g., "phase", "speech", "score", "verdict") */
  type: string;
  /** JSON-parsed data payload */
  data: Record<string, unknown>;
}

export interface SSEClientOptions {
  /** Agent endpoint URL */
  url: string;
  /** Request body (the user's idea input) */
  body: Record<string, unknown>;
  /** Called for each SSE event */
  onEvent: (event: SSEEvent) => void;
  /** Called when the stream ends */
  onComplete?: () => void;
  /** Called on error */
  onError?: (error: Error) => void;
}

/**
 * Creates an SSE connection to the agent endpoint.
 * Returns an abort function to cancel the stream.
 */
export function createSSEClient(options: SSEClientOptions): () => void {
  const controller = new AbortController();

  async function connect() {
    try {
      const response = await fetch(options.url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(options.body),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`Agent returned ${response.status}: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("No response body");
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || trimmed.startsWith(":")) continue;

          // Parse SSE data lines
          if (trimmed.startsWith("data: ")) {
            const rawData = trimmed.slice(6);
            try {
              const parsed = JSON.parse(rawData);
              options.onEvent({
                type: parsed.type ?? "message",
                data: parsed,
              });
            } catch {
              // Plain text event
              options.onEvent({
                type: "message",
                data: { text: rawData },
              });
            }
          }
        }
      }

      options.onComplete?.();
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        return; // Expected cancellation
      }
      options.onError?.(error instanceof Error ? error : new Error(String(error)));
    }
  }

  connect();

  return () => controller.abort();
}
