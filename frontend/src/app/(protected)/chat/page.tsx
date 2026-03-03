"use client";

import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { useCallback, useMemo, useState } from "react";
import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import {
  Message,
  MessageContent,
  MessageResponse,
} from "@/components/ai-elements/message";
import {
  PromptInput,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
  type PromptInputMessage,
} from "@/components/ai-elements/prompt-input";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { SparklesIcon, AlertCircleIcon, PlusIcon } from "lucide-react";

const springTransition = { type: "spring" as const, stiffness: 380, damping: 30 };
const springSoft = { type: "spring" as const, stiffness: 260, damping: 24 };
const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.06, delayChildren: 0.08 },
  },
  exit: { opacity: 0, transition: { staggerChildren: 0.03, staggerDirection: -1 } },
};
const staggerItem = {
  hidden: { opacity: 0, y: 14 },
  visible: { opacity: 1, y: 0, transition: springTransition },
};
const staggerItemSubtle = {
  hidden: { opacity: 0, y: 8 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.35, ease: [0.22, 1, 0.36, 1] as const },
  },
};

const SESSION_KEY = "chatThreadId";

const SUGGESTED_QUESTIONS = [
  "What are my tax obligations as a digital nomad?",
  "How do I declare foreign-sourced income?",
  "What deductions can I claim as a freelancer?",
  "Am I eligible for any personal tax reliefs?",
  "How does residency status affect my tax rate?",
];

function AssistantAvatar() {
  return (
    <div className="size-6 rounded-md bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0 mt-0.5">
      <SparklesIcon className="size-3 text-primary" />
    </div>
  );
}

function ThinkingIndicator() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      transition={springSoft}
      className="flex items-start gap-3 w-full max-w-3xl mx-auto px-4"
    >
      <AssistantAvatar />
      <div className="flex items-center gap-1.5 pt-1.5 text-muted-foreground">
        <span className="loading-dot" />
        <span className="loading-dot" />
        <span className="loading-dot" />
      </div>
    </motion.div>
  );
}

function StatusPill({ status }: { status: string }) {
  const isStreaming = status === "streaming";
  const isSubmitted = status === "submitted";
  const isError = status === "error";

  if (!isStreaming && !isSubmitted && !isError) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      transition={springSoft}
      className={[
        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-medium tracking-wide",
        isError
          ? "bg-destructive/10 text-destructive border border-destructive/20"
          : "bg-primary/8 text-primary/80 border border-primary/15",
      ].join(" ")}
    >
      {isError ? (
        <>
          <AlertCircleIcon className="size-2.5" />
          Error
        </>
      ) : isSubmitted ? (
        <>
          <span className="loading-dot size-1.5" />
          Thinking
        </>
      ) : (
        <>
          <motion.span
            className="size-1.5 rounded-full bg-primary/70 inline-block"
            animate={{ opacity: [0.4, 1, 0.4] }}
            transition={{ duration: 1.2, repeat: Infinity }}
          />
          Responding
        </>
      )}
    </motion.div>
  );
}

function ChatEmptyState({ onSuggestionClick }: { onSuggestionClick: (text: string) => void }) {
  const reduced = useReducedMotion();
  return (
    <motion.div
      key="empty"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, scale: 0.98 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      className="flex flex-col items-center justify-center min-h-[65vh] text-center gap-10"
    >
      <motion.div
        className="flex flex-col items-center gap-10"
        variants={reduced ? undefined : staggerContainer}
        initial="hidden"
        animate="visible"
      >
        {/* Icon + headline */}
        <div className="space-y-4">
          <motion.div variants={reduced ? undefined : staggerItem} className="relative mx-auto size-14">
            <motion.div
              animate={
                reduced
                  ? {}
                  : {
                      opacity: [0, 0.35, 0],
                      scale: [0.7, 1.4, 0.7],
                    }
              }
              transition={{
                duration: 3.2,
                repeat: Infinity,
                ease: "easeInOut",
                delay: 0.5,
              }}
              className="absolute inset-0 rounded-2xl bg-primary blur-md"
              aria-hidden
            />
            <motion.div
              animate={reduced ? {} : { y: [0, -5, 0] }}
              transition={{
                duration: 3.6,
                repeat: Infinity,
                ease: "easeInOut",
              }}
              className="relative size-14 rounded-2xl bg-primary/8 border border-primary/20 flex items-center justify-center"
            >
              <motion.div
                animate={
                  reduced
                    ? {}
                    : { scale: [1, 1.18, 1], opacity: [0.8, 1, 0.8] }
                }
                transition={{
                  duration: 3.6,
                  repeat: Infinity,
                  ease: "easeInOut",
                  delay: 0.25,
                }}
              >
                <SparklesIcon className="size-6 text-primary" />
              </motion.div>
            </motion.div>
          </motion.div>

          <div className="space-y-2">
            <motion.h2
              variants={reduced ? undefined : staggerItemSubtle}
              className="text-4xl font-normal text-foreground"
              style={{ fontFamily: "'Cormorant Garamond', serif" }}
            >
              How can I help you today?
            </motion.h2>
            <motion.p
              variants={reduced ? undefined : staggerItemSubtle}
              className="text-sm text-muted-foreground max-w-xs mx-auto leading-relaxed"
            >
              Ask me about taxes, deductions, or financial planning for your
              location-independent lifestyle.
            </motion.p>
          </div>
        </div>

        <motion.div
          variants={reduced ? undefined : staggerContainer}
          className="flex flex-wrap gap-2 justify-center max-w-md"
        >
          {SUGGESTED_QUESTIONS.map((q) => (
            <motion.button
              key={q}
              variants={reduced ? undefined : staggerItem}
              onClick={() => onSuggestionClick(q)}
              className="px-3.5 py-2 text-xs rounded-xl border border-border/70 bg-card/50 text-muted-foreground hover:text-foreground hover:border-primary/35 hover:bg-primary/5 transition-colors duration-200 text-left leading-snug"
              whileHover={{ scale: 1.02, y: -1 }}
              whileTap={{ scale: 0.98 }}
              transition={springSoft}
            >
              {q}
            </motion.button>
          ))}
        </motion.div>
      </motion.div>
    </motion.div>
  );
}

function getOrCreateThreadId(): string {
  if (typeof window === "undefined") return crypto.randomUUID();
  let id = sessionStorage.getItem(SESSION_KEY);
  if (!id) {
    id = crypto.randomUUID();
    sessionStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

/** Call when user explicitly starts a new chat. Clears session and returns new thread id. */
function resetThreadId(): string {
  if (typeof window !== "undefined") {
    sessionStorage.removeItem(SESSION_KEY);
  }
  const newId = crypto.randomUUID();
  if (typeof window !== "undefined") {
    sessionStorage.setItem(SESSION_KEY, newId);
  }
  return newId;
}

function ChatContent({ onNewChat }: { onNewChat: () => void }) {
  const threadId = useMemo(() => getOrCreateThreadId(), []);
  const transport = useMemo(
    () => new DefaultChatTransport({ body: { threadId } }),
    [threadId],
  );
  const { messages, sendMessage, status, stop } = useChat({ transport });

  const isLoading = status === "submitted" || status === "streaming";
  const isThinking = status === "submitted";
  const isEmpty = messages.length === 0;

  function handleSubmit(msg: PromptInputMessage) {
    if (!msg.text.trim()) return;
    sendMessage({ text: msg.text, files: msg.files });
  }

  function handleSuggestion(text: string) {
    sendMessage({ text });
  }

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)]">
      {/* Top bar: New chat (right) — resets thread and clears conversation */}
      <div className="flex-shrink-0 border-b border-border/30 flex items-center justify-end px-4 py-2">
        <motion.button
          type="button"
          onClick={onNewChat}
          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-muted-foreground hover:text-foreground rounded-lg hover:bg-accent transition-colors"
          aria-label="Start new chat"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          transition={springSoft}
        >
          <PlusIcon className="size-3.5" />
          New chat
        </motion.button>
      </div>
      {/* Status bar — only visible when active */}
      <AnimatePresence>
        {(isLoading || status === "error") && (
          <motion.div
            key="status"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={springSoft}
            className="border-b border-border/30 overflow-hidden"
          >
            <div className="max-w-4xl mx-auto px-5 py-2 flex items-center gap-2">
              <StatusPill status={status} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Conversation */}
      <Conversation className="flex-1">
        <ConversationContent className="max-w-3xl mx-auto w-full">
          <AnimatePresence>
            {/* Empty state */}
            {isEmpty && !isLoading && (
              <ChatEmptyState onSuggestionClick={handleSuggestion} />
            )}
          </AnimatePresence>

          {/* Messages */}
          <AnimatePresence initial={false}>
            {messages.map((message) => (
              <motion.div
                key={message.id}
                layout
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -8 }}
                transition={springTransition}
              >
                <Message from={message.role}>
                  {message.role === "assistant" ? (
                    <div className="flex items-start gap-3 w-full">
                      <AssistantAvatar />
                      <MessageContent className="flex-1 prose-chat">
                        {message.parts.map((part, i) => {
                          if (part.type === "text") {
                            return (
                              <MessageResponse key={i}>
                                {part.text}
                              </MessageResponse>
                            );
                          }
                          return null;
                        })}
                      </MessageContent>
                    </div>
                  ) : (
                    <MessageContent>
                      {message.parts.map((part, i) => {
                        if (part.type === "text") {
                          return (
                            <MessageResponse key={i}>
                              {part.text}
                            </MessageResponse>
                          );
                        }
                        return null;
                      })}
                    </MessageContent>
                  )}
                </Message>
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Thinking dots */}
          <AnimatePresence>
            {isThinking && <ThinkingIndicator key="thinking" />}
          </AnimatePresence>
        </ConversationContent>

        <ConversationScrollButton />
      </Conversation>

      {/* Input area */}
      <div className="border-t border-border/40 bg-background/95 backdrop-blur-xl p-4 pb-5">
        <div className="max-w-3xl mx-auto">
          <PromptInput onSubmit={handleSubmit}>
            <PromptInputTextarea
              placeholder="Ask about taxes, deductions, or financial planning…"
              disabled={isLoading}
            />
            <PromptInputFooter>
              <p className="text-[11px] text-muted-foreground/70 tracking-wide">
                Shift + Enter for new line
              </p>
              <PromptInputSubmit status={status} onStop={stop} />
            </PromptInputFooter>
          </PromptInput>
        </div>
      </div>
    </div>
  );
}

export default function ChatPage() {
  const [threadId, setThreadId] = useState(() =>
    typeof window !== "undefined" ? getOrCreateThreadId() : crypto.randomUUID(),
  );
  const handleNewChat = useCallback(() => {
    setThreadId(resetThreadId());
  }, []);
  return <ChatContent key={threadId} onNewChat={handleNewChat} />;
}
