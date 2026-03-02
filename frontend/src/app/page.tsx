"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight } from "lucide-react";

const capabilities = [
  { title: "Tax planning", detail: "across jurisdictions" },
  { title: "Digital nomad", detail: "income structuring" },
  { title: "Relief & deductions", detail: "optimised for you" },
];

const spring = { type: "spring" as const, stiffness: 320, damping: 28 };
const stagger = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.06 },
  },
};
const fadeUpItem = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: spring },
};
const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.5, delay, ease: [0.22, 1, 0.36, 1] },
} as const);

export default function Home() {
  const reduced = useReducedMotion();
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 relative overflow-hidden min-h-0">
      {/* Ambient glow — primary (teal/cyan) tint */}
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[500px] rounded-full pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse, oklch(0.72 0.10 195 / 0.08) 0%, transparent 70%)",
        }}
        aria-hidden
      />

      <div className="max-w-xl w-full text-center space-y-10 py-20">
        {/* Eyebrow */}
        <motion.div {...fadeUp(0)} className="inline-block">
          <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-border/60 bg-card/40 text-[11px] text-muted-foreground tracking-[0.12em] uppercase">
            <span
              className="size-1.5 rounded-full bg-primary/70 inline-block"
              style={{ boxShadow: "0 0 8px oklch(0.72 0.10 195 / 0.5)" }}
            />
            AI-Powered Accountancy
          </span>
        </motion.div>

        {/* Headline */}
        <motion.h1
          {...fadeUp(0.08)}
          className="text-[64px] md:text-[76px] font-normal leading-[1.05] tracking-[-0.01em]"
          style={{ fontFamily: "'Cormorant Garamond', serif" }}
        >
          Your finances,
          <br />
          <em className="text-primary not-italic">understood.</em>
        </motion.h1>

        {/* Sub */}
        <motion.p
          {...fadeUp(0.16)}
          className="text-sm text-muted-foreground leading-relaxed max-w-sm mx-auto"
        >
          Intelligent tax guidance for digital nomads and remote professionals.
          Ask anything — precise, jurisdiction-aware answers in seconds.
        </motion.p>

        {/* CTA */}
        <motion.div {...fadeUp(0.24)}>
          <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} transition={spring}>
            <Link
              href="/chat"
              className="inline-flex items-center gap-2.5 px-6 py-3 bg-primary text-primary-foreground rounded-xl text-sm font-medium hover:opacity-90 transition-opacity duration-150 group"
            >
              Start a conversation
              <ArrowRight className="size-4 transition-transform duration-200 group-hover:translate-x-0.5" />
            </Link>
          </motion.div>
        </motion.div>

        {/* Capability pills — staggered */}
        <motion.div
          variants={reduced ? undefined : stagger}
          initial="hidden"
          animate="visible"
          className="flex items-start justify-center gap-8 pt-2"
        >
          {capabilities.map((c) => (
            <motion.div
              key={c.title}
              variants={reduced ? undefined : fadeUpItem}
              className="text-center"
            >
              <div className="text-xs font-medium text-foreground/75 tracking-wide">
                {c.title}
              </div>
              <div className="text-[11px] text-muted-foreground mt-0.5">
                {c.detail}
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>

      {/* Bottom decoration: fine hairline */}
      <motion.div
        initial={{ scaleX: 0, opacity: 0 }}
        animate={{ scaleX: 1, opacity: 1 }}
        transition={{ delay: 0.55, duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        className="absolute bottom-0 left-1/2 -translate-x-1/2 w-48 h-px bg-gradient-to-r from-transparent via-primary/40 to-transparent"
        aria-hidden
      />
    </div>
  );
}
