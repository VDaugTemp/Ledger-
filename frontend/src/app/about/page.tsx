"use client";

import { motion, useReducedMotion } from "framer-motion";
import Link from "next/link";
import { ArrowRight, BookOpen, Shield, AlertTriangle, Eye, FileText, Users } from "lucide-react";

const ease = [0.22, 1, 0.36, 1] as const;

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 22 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.55, delay, ease },
});

const stagger = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.07, delayChildren: 0.05 },
  },
};

const staggerItem = {
  hidden: { opacity: 0, y: 16 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.45, ease },
  },
};

const sources = [
  {
    title: "Malaysia Master Tax Guide 2025 (42nd Edition)",
    publisher: "Wolters Kluwer",
  },
  {
    title: "Income Tax Act 1967 (Act 53)",
    detail: "Sections 4, 7, 12, 13, Schedule 6, Schedule 7 and Section 153",
  },
  {
    title: "PR 11/2017 – Residence Status of Individuals",
    publisher: "LHDN Public Ruling",
  },
  {
    title: "PR 8/2011 – Employment Income (60-Day Exemption)",
    publisher: "LHDN Public Ruling",
  },
  {
    title: "PR 2/2012 – Tax Treaty Relief for Foreign Nationals Working in Malaysia",
    publisher: "LHDN Public Ruling",
  },
  {
    title: "PR 11/2021 – Bilateral and Unilateral Credit Relief",
    publisher: "LHDN Public Ruling",
  },
  {
    title: "Guidelines on Tax Treatment in Relation to Income Received from Abroad (June 2024)",
    publisher: "LHDN",
  },
  {
    title: "Official resources from the Malaysian Inland Revenue Board (LHDN)",
  },
];

const sections = [
  {
    index: "01",
    icon: BookOpen,
    heading: "What this tool is",
    body: "This tool is designed to help you research your Malaysian tax position and prepare for a conversation with a licensed tax adviser. It provides general information based on curated tax materials and official guidance. It is intended for research and preparation only and does not replace personal tax advice.\n\nThe goal is to help you understand the main factors that may affect your position — such as tax residency, where your work was physically performed, possible exemptions, treaty relief, filing obligations, and the records you may need to keep.",
  },
  {
    index: "02",
    icon: Shield,
    heading: "What this system is based on",
    body: "This system aggregates information curated from accountant-reviewed materials, Malaysian tax legislation, public rulings, treaty guidance, and official tax authority resources. The aim is to organise high-quality reference material in one place so you can explore the rules in a structured way and better understand how they may apply to your situation.\n\nTax treatment can change over time and always depends on your exact facts. You should confirm your personal position with a qualified adviser and check for any recent legislative or administrative updates.",
  },
];

export default function AboutPage() {
  const reduced = useReducedMotion();

  return (
    <div className="relative flex-1 overflow-hidden">
      {/* Ambient background */}
      <div
        className="pointer-events-none fixed inset-0 -z-10"
        aria-hidden
        style={{
          background:
            "radial-gradient(ellipse 60% 50% at 70% 20%, oklch(0.72 0.10 195 / 0.05) 0%, transparent 70%), radial-gradient(ellipse 40% 40% at 20% 80%, oklch(0.52 0.12 230 / 0.04) 0%, transparent 65%)",
        }}
      />

      <div className="max-w-2xl mx-auto px-6 py-16 pb-28">
        {/* ── Page header ── */}
        <motion.div
          {...(reduced ? {} : fadeUp(0))}
          className="mb-16"
        >
          <div className="inline-flex items-center gap-2 mb-6 px-3 py-1.5 rounded-full border border-border/50 bg-card/40 text-[10px] text-muted-foreground tracking-[0.14em] uppercase">
            <span
              className="size-1.5 rounded-full bg-primary/70 inline-block"
              style={{ boxShadow: "0 0 8px oklch(0.72 0.10 195 / 0.5)" }}
            />
            Documentation
          </div>
          <h1
            className="text-[56px] md:text-[68px] font-normal leading-[1.04] tracking-[-0.01em] text-foreground"
            style={{ fontFamily: "'Cormorant Garamond', serif" }}
          >
            About
            <br />
            <em className="text-primary not-italic">this tool.</em>
          </h1>
          <div className="mt-6 h-px w-16 bg-gradient-to-r from-primary/50 to-transparent" />
        </motion.div>

        {/* ── Main sections 01 + 02 ── */}
        <div className="space-y-14">
          {sections.map((s, i) => {
            const Icon = s.icon;
            return (
              <motion.section
                key={s.index}
                {...(reduced ? {} : fadeUp(0.1 + i * 0.08))}
                aria-labelledby={`section-${s.index}`}
              >
                <div className="flex items-start gap-4 mb-4">
                  <span
                    className="text-[11px] font-medium text-primary/50 tracking-[0.12em] mt-1 tabular-nums select-none"
                    style={{ fontFamily: "'IBM Plex Mono', monospace" }}
                  >
                    {s.index}
                  </span>
                  <div className="flex items-center gap-2.5">
                    <div className="size-7 rounded-md bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
                      <Icon className="size-3.5 text-primary" />
                    </div>
                    <h2
                      id={`section-${s.index}`}
                      className="text-2xl font-normal text-foreground"
                      style={{ fontFamily: "'Cormorant Garamond', serif" }}
                    >
                      {s.heading}
                    </h2>
                  </div>
                </div>
                <div className="ml-[calc(theme(spacing.4)+11px+theme(spacing.4))] space-y-3">
                  {s.body.split("\n\n").map((para, j) => (
                    <p key={j} className="text-sm text-muted-foreground leading-relaxed">
                      {para}
                    </p>
                  ))}
                </div>
                <div className="mt-8 h-px bg-border/40" />
              </motion.section>
            );
          })}

          {/* ── 03 What to pay attention to — accented ── */}
          <motion.section
            {...(reduced ? {} : fadeUp(0.26))}
            aria-labelledby="section-03"
          >
            <div className="flex items-start gap-4 mb-4">
              <span
                className="text-[11px] font-medium text-primary/50 tracking-[0.12em] mt-1 tabular-nums select-none"
                style={{ fontFamily: "'IBM Plex Mono', monospace" }}
              >
                03
              </span>
              <div className="flex items-center gap-2.5">
                <div className="size-7 rounded-md bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
                  <AlertTriangle className="size-3.5 text-primary" />
                </div>
                <h2
                  id="section-03"
                  className="text-2xl font-normal text-foreground"
                  style={{ fontFamily: "'Cormorant Garamond', serif" }}
                >
                  What to pay attention to
                </h2>
              </div>
            </div>
            <div className="ml-[calc(theme(spacing.4)+11px+theme(spacing.4))]">
              <div className="pl-4 border-l-2 border-primary/35 space-y-3">
                <p className="text-sm text-muted-foreground leading-relaxed">
                  In many cases, the key questions are not simply where you are paid or where your
                  company is based. Malaysian tax treatment often depends on where the work was
                  physically performed, how long you stayed in Malaysia, what type of income you
                  earned, and whether exemptions or treaty protections may apply.
                </p>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  Keeping accurate records is important. Useful documentation may include:
                </p>
                <motion.ul
                  variants={reduced ? undefined : stagger}
                  initial="hidden"
                  animate="visible"
                  className="space-y-1.5 text-sm text-muted-foreground"
                >
                  {[
                    "Passport stamps or travel logs",
                    "Contracts, invoices, and payslips",
                    "Tax returns and tax residence certificates",
                    "Proof of foreign tax paid",
                  ].map((item) => (
                    <motion.li
                      key={item}
                      variants={reduced ? undefined : staggerItem}
                      className="flex items-start gap-2.5"
                    >
                      <span className="mt-[7px] size-1 rounded-full bg-primary/50 flex-shrink-0" />
                      {item}
                    </motion.li>
                  ))}
                </motion.ul>
                <p className="text-sm text-muted-foreground leading-relaxed pt-1">
                  The clearer your records are, the easier it becomes to understand your situation
                  and prepare for filing or adviser review.
                </p>
              </div>
            </div>
            <div className="mt-8 h-px bg-border/40" />
          </motion.section>

          {/* ── 04 Privacy ── */}
          <motion.section
            {...(reduced ? {} : fadeUp(0.32))}
            aria-labelledby="section-04"
          >
            <div className="flex items-start gap-4 mb-4">
              <span
                className="text-[11px] font-medium text-primary/50 tracking-[0.12em] mt-1 tabular-nums select-none"
                style={{ fontFamily: "'IBM Plex Mono', monospace" }}
              >
                04
              </span>
              <div className="flex items-center gap-2.5">
                <div className="size-7 rounded-md bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
                  <Eye className="size-3.5 text-primary" />
                </div>
                <h2
                  id="section-04"
                  className="text-2xl font-normal text-foreground"
                  style={{ fontFamily: "'Cormorant Garamond', serif" }}
                >
                  Privacy and AI models
                </h2>
              </div>
            </div>
            <div className="ml-[calc(theme(spacing.4)+11px+theme(spacing.4))] space-y-3">
              <p className="text-sm text-muted-foreground leading-relaxed">
                You can use this tool without providing your name or personal identifying details.
                The system focuses on facts relevant to tax analysis — such as travel days, where
                work was performed, and the type of income you earn — rather than personal identity.
              </p>
              <p className="text-sm text-muted-foreground leading-relaxed">
                AI responses are generated using either a fast large language model provided via the
                Anthropic API or a private self-hosted model, depending on the mode you select in
                the chat interface. Both modes operate within the same research framework built on
                curated tax materials and official guidance.
              </p>
            </div>
            <div className="mt-8 h-px bg-border/40" />
          </motion.section>

          {/* ── 05 Sources ── */}
          <motion.section
            {...(reduced ? {} : fadeUp(0.38))}
            aria-labelledby="section-05"
          >
            <div className="flex items-start gap-4 mb-4">
              <span
                className="text-[11px] font-medium text-primary/50 tracking-[0.12em] mt-1 tabular-nums select-none"
                style={{ fontFamily: "'IBM Plex Mono', monospace" }}
              >
                05
              </span>
              <div className="flex items-center gap-2.5">
                <div className="size-7 rounded-md bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
                  <FileText className="size-3.5 text-primary" />
                </div>
                <h2
                  id="section-05"
                  className="text-2xl font-normal text-foreground"
                  style={{ fontFamily: "'Cormorant Garamond', serif" }}
                >
                  Sources used in this system
                </h2>
              </div>
            </div>
            <div className="ml-[calc(theme(spacing.4)+11px+theme(spacing.4))]">
              <p className="text-sm text-muted-foreground leading-relaxed mb-5">
                This tool is built using guidance and reference material including:
              </p>
              <motion.div
                variants={reduced ? undefined : stagger}
                initial="hidden"
                animate="visible"
                className="space-y-2"
              >
                {sources.map((src, i) => (
                  <motion.div
                    key={i}
                    variants={reduced ? undefined : staggerItem}
                    className="flex items-start gap-3 group"
                  >
                    <span
                      className="mt-[6px] text-[10px] text-primary/40 tabular-nums select-none flex-shrink-0 w-4 text-right"
                      style={{ fontFamily: "'IBM Plex Mono', monospace" }}
                    >
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <div className="flex-1 py-2.5 px-3.5 rounded-lg border border-border/40 bg-card/30 hover:border-primary/25 hover:bg-primary/5 transition-colors duration-200">
                      <p className="text-sm text-foreground/85 leading-snug font-medium">
                        {src.title}
                      </p>
                      {(src.publisher || src.detail) && (
                        <p className="text-[11px] text-muted-foreground mt-0.5">
                          {src.publisher ?? src.detail}
                        </p>
                      )}
                    </div>
                  </motion.div>
                ))}
              </motion.div>
              <p className="mt-4 text-[11px] text-muted-foreground/60 leading-relaxed">
                Where relevant, explanations may reference underlying legislation or rulings so that
                users can review the original guidance.
              </p>
            </div>
            <div className="mt-8 h-px bg-border/40" />
          </motion.section>

          {/* ── 06 When to seek advice ── */}
          <motion.section
            {...(reduced ? {} : fadeUp(0.44))}
            aria-labelledby="section-06"
          >
            <div className="flex items-start gap-4 mb-4">
              <span
                className="text-[11px] font-medium text-primary/50 tracking-[0.12em] mt-1 tabular-nums select-none"
                style={{ fontFamily: "'IBM Plex Mono', monospace" }}
              >
                06
              </span>
              <div className="flex items-center gap-2.5">
                <div className="size-7 rounded-md bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
                  <Users className="size-3.5 text-primary" />
                </div>
                <h2
                  id="section-06"
                  className="text-2xl font-normal text-foreground"
                  style={{ fontFamily: "'Cormorant Garamond', serif" }}
                >
                  When to seek professional advice
                </h2>
              </div>
            </div>
            <div className="ml-[calc(theme(spacing.4)+11px+theme(spacing.4))] space-y-5">
              <p className="text-sm text-muted-foreground leading-relaxed">
                Once you have explored your situation, you can generate a structured summary of your
                profile and the key points discussed with the AI assistant. This summary can be
                downloaded and shared with a licensed Malaysian tax adviser to help them quickly
                understand your circumstances and provide professional guidance.
              </p>
              <motion.div
                whileHover={reduced ? {} : { scale: 1.01 }}
                whileTap={reduced ? {} : { scale: 0.99 }}
                transition={{ type: "spring", stiffness: 380, damping: 28 }}
              >
                <Link
                  href="/chat"
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary/10 border border-primary/25 text-sm text-primary hover:bg-primary/15 hover:border-primary/40 transition-colors duration-200 group"
                >
                  Start your research
                  <ArrowRight className="size-3.5 transition-transform duration-200 group-hover:translate-x-0.5" />
                </Link>
              </motion.div>
            </div>
          </motion.section>
        </div>

        {/* ── Bottom hairline ── */}
        <motion.div
          initial={{ scaleX: 0, opacity: 0 }}
          animate={{ scaleX: 1, opacity: 1 }}
          transition={{ delay: 0.7, duration: 0.8, ease }}
          className="mt-20 h-px w-24 mx-auto bg-gradient-to-r from-transparent via-primary/30 to-transparent"
          aria-hidden
        />
      </div>
    </div>
  );
}
