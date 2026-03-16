import type { Profile, OpenQuestion } from "@/lib/types";

/**
 * Serialise the user's profile and next open question into a compact string
 * injected into every chat request as agent context.
 */
export function formatProfileContext(
  profile: Profile | null,
  nextQuestion?: OpenQuestion | null,
): string {
  if (!profile) return "";

  const lines: string[] = [
    `User Tax Profile (${profile.jurisdiction}, assessment year ${profile.assessmentYear}):`,
  ];

  // Income types
  const active = Object.entries(profile.incomeTypes ?? {})
    .filter(([, v]) => v)
    .map(([k]) => k);
  lines.push(`• Income: ${active.length ? active.join(", ") : "none declared"}`);

  // Presence
  lines.push(`• Trips logged: ${profile.presence.trips.length}`);

  // Advisor context
  const ctx = profile.advisorContext;
  if (ctx.citizenships?.length) lines.push(`• Citizenships: ${ctx.citizenships.join(", ")}`);
  if (ctx.visaType) lines.push(`• Visa: ${ctx.visaType}`);
  if (ctx.filesTaxElsewhere) lines.push(`• Files tax elsewhere: yes`);
  if (ctx.isCompanyDirector) lines.push(`• Company director: yes`);
  if (ctx.taxResidentElsewhere) lines.push(`• Tax resident elsewhere: ${ctx.taxResidentElsewhere}`);

  // Data quality
  const score = profile.dataQuality?.completenessScore;
  if (score !== undefined) lines.push(`• Profile completeness: ${score}%`);

  // Next open question for the agent to drive
  if (nextQuestion) {
    lines.push(
      `\nNext unanswered question the agent should ask (after answering any user question):`,
      `  Field: ${nextQuestion.fieldPath}`,
      `  Q: "${nextQuestion.question}"`,
    );
  }

  return lines.join("\n");
}
