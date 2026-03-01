"use client";

import { useChat } from "@ai-sdk/react";
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
import { motion, AnimatePresence } from "framer-motion";
import { SparklesIcon, AlertCircleIcon } from "lucide-react";

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
      transition={{ duration: 0.2 }}
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

export default function ChatPage() {
  const { messages, sendMessage, status, stop } = useChat();

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
      {/* Status bar — only visible when active */}
      <AnimatePresence>
        {(isLoading || status === "error") && (
          <motion.div
            key="status"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
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
              <motion.div
                key="empty"
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.98 }}
                transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
                className="flex flex-col items-center justify-center min-h-[65vh] text-center gap-10"
              >
                {/* Icon + headline */}
                <div className="space-y-4">
                  {/* Animated icon */}
                  <motion.div
                    initial={{ scale: 0.7, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ delay: 0.1, duration: 0.45, ease: "backOut" }}
                    className="relative mx-auto size-14"
                  >
                    {/* Pulsing glow behind the box */}
                    <motion.div
                      animate={{ opacity: [0, 0.35, 0], scale: [0.7, 1.4, 0.7] }}
                      transition={{
                        duration: 3.2,
                        repeat: Infinity,
                        ease: "easeInOut",
                        delay: 0.5,
                      }}
                      className="absolute inset-0 rounded-2xl bg-primary blur-md"
                      aria-hidden
                    />
                    {/* Floating icon box */}
                    <motion.div
                      animate={{ y: [0, -5, 0] }}
                      transition={{
                        duration: 3.6,
                        repeat: Infinity,
                        ease: "easeInOut",
                      }}
                      className="relative size-14 rounded-2xl bg-primary/8 border border-primary/18 flex items-center justify-center"
                    >
                      {/* Breathing sparkle */}
                      <motion.div
                        animate={{ scale: [1, 1.18, 1], opacity: [0.8, 1, 0.8] }}
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
                    <h2
                      className="text-4xl font-normal text-foreground"
                      style={{ fontFamily: "'Cormorant Garamond', serif" }}
                    >
                      How can I help you today?
                    </h2>
                    <p className="text-sm text-muted-foreground max-w-xs mx-auto leading-relaxed">
                      Ask me about taxes, deductions, or financial planning
                      for your location-independent lifestyle.
                    </p>
                  </div>
                </div>

                {/* Suggested questions */}
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.25 }}
                  className="flex flex-wrap gap-2 justify-center max-w-md"
                >
                  {SUGGESTED_QUESTIONS.map((q, i) => (
                    <motion.button
                      key={q}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.3 + i * 0.07 }}
                      onClick={() => handleSuggestion(q)}
                      className="px-3.5 py-2 text-xs rounded-full border border-border/70 bg-card/50 text-muted-foreground hover:text-foreground hover:border-primary/35 hover:bg-primary/5 transition-all duration-200 text-left leading-snug"
                    >
                      {q}
                    </motion.button>
                  ))}
                </motion.div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Messages */}
          <AnimatePresence initial={false}>
            {messages.map((message) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  type: "spring",
                  stiffness: 360,
                  damping: 30,
                }}
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
      <div className="border-t border-border/40 bg-background/95 backdrop-blur-sm p-4 pb-5">
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
