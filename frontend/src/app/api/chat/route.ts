import {
  createUIMessageStream,
  createUIMessageStreamResponse,
  type UIMessage,
} from "ai";

export const maxDuration = 60;

// Local dev: set BACKEND_URL=http://localhost:8000 in frontend/.env.local
// Vercel: set BACKEND_URL to your deployed backend URL
const BACKEND_URL =
  process.env.BACKEND_URL ??
  (process.env.VERCEL_URL
    ? `https://${process.env.VERCEL_URL}`
    : "http://localhost:8000");

type TextPart = { type: "text"; text: string };

export async function POST(req: Request) {
  const body = await req.json();
  const { messages, threadId, profileContext, userId, profile, skippedFieldPaths, todayIso, mode } = body as {
    messages?: UIMessage[];
    threadId?: string;
    profileContext?: string;
    userId?: string;
    profile?: Record<string, unknown>;
    skippedFieldPaths?: string[];
    todayIso?: string;
    mode?: string;
  };

  const lastMsg = messages?.at(-1);
  const input =
    lastMsg?.parts
      ?.filter((p): p is TextPart => p.type === "text")
      .map((p) => p.text)
      .join("") ?? "";

  const backendBody: Record<string, unknown> = { input };
  if (typeof threadId === "string" && threadId.trim()) {
    backendBody.config = { configurable: { thread_id: threadId.trim() } };
  }
  if (profileContext) backendBody.profile_context = profileContext;
  if (profile) backendBody.profile = profile;
  if (skippedFieldPaths) backendBody.skipped_field_paths = skippedFieldPaths;
  if (todayIso) backendBody.today_iso = todayIso;
  if (userId) backendBody.user_id = userId;
  if (mode) backendBody.mode = mode;

  const backendRes = await fetch(`${BACKEND_URL}/app/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(backendBody),
  });

  if (!backendRes.ok || !backendRes.body) {
    throw new Error(`Backend error: ${backendRes.status}`);
  }

  const textId = crypto.randomUUID();

  const uiStream = createUIMessageStream({
    execute: async ({ writer }) => {
      writer.write({ type: "text-start", id: textId });

      const reader = backendRes.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let currentEvent = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith("data: ") && currentEvent === "message") {
            try {
              const [message] = JSON.parse(line.slice(6)) as [
                {
                  type: string;
                  content: string | Array<{ type: string; text: string }>;
                },
                unknown,
              ];
              if (
                message.type === "AIMessageChunk" ||
                message.type === "AIMessage"
              ) {
                const { content } = message;
                if (typeof content === "string" && content) {
                  writer.write({ type: "text-delta", id: textId, delta: content });
                } else if (Array.isArray(content)) {
                  for (const part of content) {
                    if (part.type === "text" && part.text) {
                      writer.write({ type: "text-delta", id: textId, delta: part.text });
                    }
                  }
                }
              }
            } catch {
              // skip malformed SSE chunks
            }
            currentEvent = "";
          } else if (line.startsWith("data: ") && currentEvent === "profile_update") {
            try {
              const patch = JSON.parse(line.slice(6));
              writer.write({ type: "data-profile-update", data: patch });
            } catch {
              // skip malformed profile update
            }
            currentEvent = "";
          } else if (line.startsWith("data: ") && currentEvent === "status") {
            try {
              const payload = JSON.parse(line.slice(6));
              writer.write({ type: "data-status", data: payload });
            } catch {
              // skip malformed status event
            }
            currentEvent = "";
          }
        }
      }

      writer.write({ type: "text-end", id: textId });
    },
  });

  return createUIMessageStreamResponse({ stream: uiStream });
}
