"use client";

import { motion, useReducedMotion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const CARDS = [
  {
    title: "Stream Text",
    tag: "AI SDK",
    description:
      "Server-sent tokens stream character by character into the chat interface in real time.",
    color: "text-amber-400",
    delay: 0,
  },
  {
    title: "Composable UI",
    tag: "AI Elements",
    description:
      "Conversation, Message, and PromptInput components compose into a full chat experience.",
    color: "text-sky-400",
    delay: 0.1,
  },
  {
    title: "Smooth Motion",
    tag: "Framer Motion",
    description:
      "Spring physics, stagger orchestration, and layout animations bring the interface to life.",
    color: "text-violet-400",
    delay: 0.2,
  },
];

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.12 } },
};

const cardVariants = {
  hidden: { opacity: 0, y: 28 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { type: "spring" as const, stiffness: 260, damping: 20 },
  },
};

export function MotionCardGrid() {
  const reduced = useReducedMotion();

  return (
    <motion.div
      className="grid grid-cols-1 sm:grid-cols-3 gap-4"
      variants={containerVariants}
      initial={reduced ? "visible" : "hidden"}
      whileInView="visible"
      viewport={{ once: true, margin: "-60px" }}
    >
      {CARDS.map((card) => (
        <motion.div
          key={card.title}
          variants={cardVariants}
          whileHover={reduced ? {} : { y: -6, transition: { duration: 0.2 } }}
          className="cursor-default"
        >
          <Card className="h-full border-border/60 bg-card/60 backdrop-blur-sm hover:border-border transition-colors">
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between gap-2">
                <CardTitle className={`text-base font-semibold ${card.color}`}>
                  {card.title}
                </CardTitle>
                <Badge variant="secondary" className="text-xs shrink-0">
                  {card.tag}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {card.description}
              </p>
            </CardContent>
          </Card>
        </motion.div>
      ))}
    </motion.div>
  );
}

const floatVariants = {
  animate: {
    y: [0, -10, 0],
    transition: { duration: 3, repeat: Infinity, ease: "easeInOut" as const },
  },
};

export function FloatingOrb() {
  const reduced = useReducedMotion();
  return (
    <motion.div
      variants={floatVariants}
      animate={reduced ? {} : "animate"}
      className="absolute -top-12 -right-12 size-48 rounded-full bg-primary/10 blur-3xl pointer-events-none"
      aria-hidden
    />
  );
}
