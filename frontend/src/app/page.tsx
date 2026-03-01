"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";

const capabilities = [
  { title: "Tax planning", detail: "across jurisdictions" },
  { title: "Digital nomad", detail: "income structuring" },
  { title: "Relief & deductions", detail: "optimised for you" },
];

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.55, delay, ease: "easeOut" },
} as const);

export default function Home() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 relative overflow-hidden min-h-0">
      {/* Ambient glow */}
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[500px] rounded-full pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse, oklch(0.80 0.148 75 / 0.06) 0%, transparent 70%)",
        }}
        aria-hidden
      />

      <div className="max-w-xl w-full text-center space-y-10 py-20">
        {/* Eyebrow */}
        <motion.div {...fadeUp(0)} className="inline-block">
          <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-border/60 bg-card/40 text-[11px] text-muted-foreground tracking-[0.12em] uppercase">
            <span
              className="size-1.5 rounded-full bg-primary/70 inline-block"
              style={{ boxShadow: "0 0 6px oklch(0.80 0.148 75 / 0.5)" }}
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
          <Link
            href="/chat"
            className="inline-flex items-center gap-2.5 px-6 py-3 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:opacity-90 active:scale-[0.98] transition-all duration-150 group"
          >
            Start a conversation
            <ArrowRight className="size-4 transition-transform duration-200 group-hover:translate-x-0.5" />
          </Link>
        </motion.div>

        {/* Capability pills */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.45, duration: 0.5 }}
          className="flex items-start justify-center gap-8 pt-2"
        >
          {capabilities.map((c) => (
            <div key={c.title} className="text-center">
              <div className="text-xs font-medium text-foreground/75 tracking-wide">
                {c.title}
              </div>
              <div className="text-[11px] text-muted-foreground mt-0.5">
                {c.detail}
              </div>
            </div>
          ))}
        </motion.div>
      </div>

      {/* Bottom decoration: fine hairline */}
      <motion.div
        initial={{ scaleX: 0, opacity: 0 }}
        animate={{ scaleX: 1, opacity: 1 }}
        transition={{ delay: 0.6, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        className="absolute bottom-0 left-1/2 -translate-x-1/2 w-48 h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent"
        aria-hidden
      />
    </div>
  );
}
