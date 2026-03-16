"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import type { UIMessage } from "ai";
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
import { SparklesIcon, AlertCircleIcon, PlusIcon, HistoryIcon, ZapIcon, LockIcon } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/components/AuthProvider";
import { useUserProfile } from "@/hooks/useUserProfile";
import { generateOpenQuestions } from "@/lib/openQuestions";
import type { Profile, OpenQuestion } from "@/lib/types";
import { NextStepAction } from "@/components/NextStepAction";
import { AdvisorSummaryModal } from "@/components/AdvisorSummaryModal";
import { downloadAdvisorPdf } from "@/lib/pdf-downloader";
import { ChatHistoryDrawer } from "@/components/ChatHistoryDrawer";

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

const SKIP_PHRASES = ["prefer not to answer", "rather not say", "skip this", "skip"];

const SUGGESTED_QUESTIONS = [
  "What are my tax obligations as a digital nomad?",
  "How do I declare foreign-sourced income?",
  "What deductions can I claim as a freelancer?",
  "Am I eligible for any personal tax reliefs?",
  "How does residency status affect my tax rate?",
];

function AssistantAvatar({ streaming = false }: { streaming?: boolean }) {
  const reduced = useReducedMotion();
  const active = streaming && !reduced;
  return (
    <div className="relative flex-shrink-0 mt-0.5 size-6">
      {/* Glow ring */}
      {active && (
        <motion.div
          className="absolute inset-0 rounded-md bg-primary blur-[6px]"
          animate={{ opacity: [0, 0.45, 0], scale: [0.6, 1.5, 0.6] }}
          transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
          aria-hidden
        />
      )}
      <div className="relative size-6 rounded-md bg-primary/10 border border-primary/20 flex items-center justify-center">
        <motion.div
          animate={active ? { scale: [1, 1.2, 1], opacity: [0.75, 1, 0.75] } : {}}
          transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
        >
          <SparklesIcon className="size-3 text-primary" />
        </motion.div>
      </div>
    </div>
  );
}

function ThinkingIndicator({ label }: { label: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      transition={springSoft}
      className="flex items-center gap-2.5 w-full max-w-3xl mx-auto px-4 py-1"
    >
      <AssistantAvatar streaming />
      <span className="text-xs text-muted-foreground/70">{label}</span>
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

function ChatContent({
  onNewChat,
  threadId,
  initialMessages,
  onHistoryOpen,
}: {
  onNewChat: () => void;
  threadId: string;
  initialMessages: UIMessage[];
  onHistoryOpen: () => void;
}) {
  const { user, accessToken } = useAuth();
  const { profile, userId, savePatch } = useUserProfile({
    userId: user?.userId,
    accessToken: accessToken ?? undefined,
  });

  // Session-only list of skipped field paths
  const [skippedFieldPaths, setSkippedFieldPaths] = useState<string[]>([]);
  const [advisorModalOpen, setAdvisorModalOpen] = useState(false);
  const [mode, setMode] = useState<"fast" | "private">("fast");
  const [thinkingLabel, setThinkingLabel] = useState("Thinking...");

  // Compute next open question reactively from profile + skipped list
  const openQuestions = useMemo(
    () => (profile ? generateOpenQuestions(profile, skippedFieldPaths) : []),
    [profile, skippedFieldPaths],
  );
  const nextQuestion: OpenQuestion | null = openQuestions[0] ?? null;

  // Mutable body ref — DefaultChatTransport stores this object reference;
  // mutations here are visible at send time without recreating the transport.
  const chatBodyRef = useRef<Record<string, unknown>>({ threadId });
  chatBodyRef.current.threadId = threadId;
  chatBodyRef.current.profile = profile ?? undefined;
  chatBodyRef.current.skippedFieldPaths = skippedFieldPaths;
  chatBodyRef.current.todayIso = new Date().toISOString().split("T")[0];
  chatBodyRef.current.userId = userId || undefined;
  chatBodyRef.current.mode = mode;

  const transport = useMemo(
    () => new DefaultChatTransport({ body: chatBodyRef.current }),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- transport created once; body is mutated via ref
    [],
  );

  const { messages, sendMessage, status, stop } = useChat({ transport, messages: initialMessages });

  // Apply profile updates delivered as data-profile-update stream parts
  const lastProcessedRef = useRef(0);
  useEffect(() => {
    const newMessages = messages.slice(lastProcessedRef.current);
    if (newMessages.length === 0) return;

    for (const msg of newMessages) {
      if (msg.role !== "assistant") continue;
      for (const part of msg.parts) {
        if ((part as { type: string }).type === "data-status") {
          const s = (part as { type: string; data: { status: string } }).data.status;
          if (s === "retrieving") setThinkingLabel("Searching knowledge base...");
          else if (s === "answering") setThinkingLabel("Composing answer...");
        }
        if ((part as { type: string }).type === "data-profile-update" && profile && userId) {
          const patch = (part as { type: string; data: unknown }).data as Partial<Profile>;
          // Merge trips additively: append new trips from the patch to existing ones
          // (patch.presence.trips only contains the newly extracted trip, not the full list)
          const patchTrips = patch.presence?.trips;
          const effectivePatch: Partial<Profile> = patchTrips
            ? {
                ...patch,
                presence: {
                  ...patch.presence,
                  trips: [
                    ...(profile.presence?.trips ?? []).filter(
                      (et) => !patchTrips.some((nt) => nt.tripId === et.tripId),
                    ),
                    ...patchTrips,
                  ],
                },
              }
            : patch;
          savePatch(effectivePatch).catch(console.error);
        }
      }
    }
    lastProcessedRef.current = messages.length;
  }, [messages, profile, userId, savePatch]);

  const isLoading = status === "submitted" || status === "streaming";
  const isThinking = status === "submitted";
  const isEmpty = messages.length === 0;

  // Reset thinking label when loading finishes
  useEffect(() => {
    if (!isLoading) setThinkingLabel("Thinking...");
  }, [isLoading]);

  const completeness = profile?.dataQuality?.completenessScore ?? 0;
  const hasAssistantMessage = messages.some((m) => m.role === "assistant");
  const showAdvisorCta = completeness >= 80 && hasAssistantMessage;

  function isSkipMessage(text: string): boolean {
    const lower = text.toLowerCase().trim();
    return SKIP_PHRASES.some((p) => lower.includes(p));
  }

  function handleSkipQuestion() {
    if (!nextQuestion) return;
    setSkippedFieldPaths((prev) => [...prev, nextQuestion.fieldPath]);
  }

  function handleSubmit(msg: PromptInputMessage) {
    const text = msg.text.trim();
    if (!text) return;
    if (nextQuestion && isSkipMessage(text)) {
      setSkippedFieldPaths((prev) => [...prev, nextQuestion.fieldPath]);
      return;
    }
    sendMessage({ text, files: msg.files });
  }

  function handleSuggestion(text: string) {
    sendMessage({ text });
  }

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)]">
      {/* Top bar */}
      <div className="flex-shrink-0 border-b border-border/30 flex items-center justify-between px-4 py-2">
        <motion.button
          type="button"
          onClick={onHistoryOpen}
          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-muted-foreground hover:text-foreground rounded-lg hover:bg-accent transition-colors"
          aria-label="Open chat history"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          transition={springSoft}
        >
          <HistoryIcon className="size-3.5" />
          History
        </motion.button>

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

      {/* Conversation */}
      <Conversation className="flex-1">
        <ConversationContent className="max-w-3xl mx-auto w-full">
          <AnimatePresence>
            {isEmpty && !isLoading && (
              <ChatEmptyState onSuggestionClick={handleSuggestion} />
            )}
          </AnimatePresence>

          <AnimatePresence initial={false}>
            {messages.map((message, idx) => (
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
                      <AssistantAvatar streaming={status === "streaming" && idx === messages.length - 1} />
                      <MessageContent className="flex-1 prose-chat">
                        {message.parts.map((part, i) => {
                          if (part.type === "text") {
                            return (
                              <MessageResponse key={i}>{part.text}</MessageResponse>
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
                            <MessageResponse key={i}>{part.text}</MessageResponse>
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

          <AnimatePresence>
            {showAdvisorCta && !isLoading && (
              <motion.div
                key="advisor-cta"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={springSoft}
                className="max-w-3xl mx-auto w-full px-4 pb-4"
              >
                <NextStepAction onOpen={() => setAdvisorModalOpen(true)} />
              </motion.div>
            )}
          </AnimatePresence>
        </ConversationContent>

        <ConversationScrollButton />
      </Conversation>

      {/* Input area */}
      <div className="border-t border-border/40 bg-background/95 backdrop-blur-xl p-4 pb-5">
        <div className="max-w-3xl mx-auto">
          <PromptInput onSubmit={handleSubmit}>
            <PromptInputTextarea
              placeholder={
                nextQuestion
                  ? nextQuestion.question
                  : "Ask about taxes, deductions, or financial planning…"
              }
              disabled={isLoading}
            />
            <PromptInputFooter>
              <div className="flex items-center gap-3">
                <ModeSelector mode={mode} onChange={setMode} disabled={isLoading} />
                <p className="text-[11px] text-muted-foreground/70 tracking-wide">
                  Shift + Enter for new line
                </p>
              </div>
              <PromptInputSubmit status={status} onStop={stop} />
            </PromptInputFooter>
          </PromptInput>
        </div>
      </div>

      <AdvisorSummaryModal
        open={advisorModalOpen}
        onClose={() => setAdvisorModalOpen(false)}
        profile={profile ?? null}
        threadId={threadId}
        onDownload={(profileSnapshot, summaryText) => {
          downloadAdvisorPdf({
            profile: profileSnapshot,
            summaryText,
            generatedDate: new Date().toISOString().split("T")[0],
          });
          setAdvisorModalOpen(false);
        }}
      />
    </div>
  );
}

// ─── ModeSelector ─────────────────────────────────────────────────────────────

type ChatMode = "fast" | "private";

const MODE_OPTIONS: { value: ChatMode; label: string; icon: React.ReactNode; description: string }[] = [
  {
    value: "fast",
    label: "Fast",
    icon: <ZapIcon className="size-3" />,
    description: "Anthropic Claude",
  },
  {
    value: "private",
    label: "Private mode",
    icon: <LockIcon className="size-3" />,
    description: "Self-hosted model",
  },
];

function ModeSelector({
  mode,
  onChange,
  disabled,
}: {
  mode: ChatMode;
  onChange: (m: ChatMode) => void;
  disabled: boolean;
}) {
  const current = MODE_OPTIONS.find((o) => o.value === mode) ?? MODE_OPTIONS[0];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          disabled={disabled}
          className="inline-flex items-center gap-1.5 px-2 py-1 rounded-lg text-[11px] text-muted-foreground hover:text-foreground hover:bg-accent border border-transparent hover:border-border/40 transition-colors disabled:opacity-40"
          aria-label="Select chat mode"
        >
          {current.icon}
          <span>{current.label}</span>
          <span className="text-muted-foreground/50">▾</span>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" side="top" className="w-48">
        {MODE_OPTIONS.map((opt) => (
          <DropdownMenuItem
            key={opt.value}
            onClick={() => onChange(opt.value)}
            className={[
              "flex items-start gap-2.5 px-3 py-2.5 text-xs cursor-pointer",
              opt.value === mode ? "text-primary" : "",
            ].join(" ")}
          >
            <span className="mt-0.5 shrink-0">{opt.icon}</span>
            <div>
              <p className="font-medium leading-tight">{opt.label}</p>
              <p className="text-muted-foreground text-[10px] mt-0.5">{opt.description}</p>
            </div>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default function ChatPage() {
  const { user } = useAuth();
  const [threadId, setThreadId] = useState(() => crypto.randomUUID());
  const [initialMessages, setInitialMessages] = useState<UIMessage[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);

  const handleNewChat = useCallback(() => {
    setThreadId(crypto.randomUUID());
    setInitialMessages([]);
  }, []);

  const handleSelectThread = useCallback(
    (selectedThreadId: string, messages: UIMessage[]) => {
      setThreadId(selectedThreadId);
      setInitialMessages(messages);
      setHistoryOpen(false);
    },
    [],
  );

  return (
    <>
      <ChatContent
        key={threadId}
        onNewChat={handleNewChat}
        threadId={threadId}
        initialMessages={initialMessages}
        onHistoryOpen={() => setHistoryOpen(true)}
      />
      <ChatHistoryDrawer
        open={historyOpen}
        onOpenChange={setHistoryOpen}
        userId={user?.userId}
        onSelectThread={handleSelectThread}
      />
    </>
  );
}
