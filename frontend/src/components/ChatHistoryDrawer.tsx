"use client";

import { useEffect, useState } from "react";
import type { UIMessage } from "ai";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { HistoryIcon, MessageSquareIcon } from "lucide-react";

interface ThreadMeta {
  threadId: string;
  title: string;
  createdAt: string;
}

interface ChatHistoryDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  userId: string | undefined;
  onSelectThread: (threadId: string, messages: UIMessage[]) => void;
}

function toUIMessage(m: { role: "user" | "assistant"; content: string }): UIMessage {
  return {
    id: crypto.randomUUID(),
    role: m.role,
    parts: [{ type: "text", text: m.content }],
  };
}

function relativeDate(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diff / 86_400_000);
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;
  return new Date(iso).toLocaleDateString();
}

export function ChatHistoryDrawer({
  open,
  onOpenChange,
  userId,
  onSelectThread,
}: ChatHistoryDrawerProps) {
  const [threads, setThreads] = useState<ThreadMeta[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingThread, setLoadingThread] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !userId) return;
    setLoading(true);
    fetch(`/api/chat/threads?userId=${encodeURIComponent(userId)}`)
      .then((r) => r.json())
      .then((data) => setThreads(data.threads ?? []))
      .catch(() => setThreads([]))
      .finally(() => setLoading(false));
  }, [open, userId]);

  async function handleSelectThread(thread: ThreadMeta) {
    setLoadingThread(thread.threadId);
    try {
      const res = await fetch(`/api/chat/threads/${thread.threadId}/messages`);
      if (!res.ok) return;
      const data = await res.json();
      const messages: UIMessage[] = (data.messages ?? []).map(toUIMessage);
      onSelectThread(thread.threadId, messages);
    } finally {
      setLoadingThread(null);
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-80 sm:w-96 flex flex-col p-0">
        <SheetHeader className="px-4 py-3 border-b border-border/40">
          <SheetTitle className="flex items-center gap-2 text-sm font-medium">
            <HistoryIcon className="size-4 text-muted-foreground" />
            Chat History
          </SheetTitle>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto">
          {loading && (
            <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
              Loading…
            </div>
          )}

          {!loading && threads.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 gap-2 text-sm text-muted-foreground">
              <MessageSquareIcon className="size-8 opacity-30" />
              <p>No conversations yet</p>
            </div>
          )}

          {!loading &&
            threads.map((thread) => (
              <button
                key={thread.threadId}
                onClick={() => handleSelectThread(thread)}
                disabled={loadingThread === thread.threadId}
                className="w-full text-left px-4 py-3 border-b border-border/20 hover:bg-accent/50 transition-colors disabled:opacity-50"
              >
                <p className="text-sm text-foreground truncate">{thread.title}</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {relativeDate(thread.createdAt)}
                </p>
              </button>
            ))}
        </div>
      </SheetContent>
    </Sheet>
  );
}
