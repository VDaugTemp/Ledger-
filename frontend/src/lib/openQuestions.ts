import type {
  Profile,
  OpenQuestion,
  OpenQuestionCategory,
  PatchMeta,
} from "./types";

// ─── Constants ────────────────────────────────────────────────────────────────

const JURISDICTION_LABEL = "Malaysia";

// ─── isMissing ────────────────────────────────────────────────────────────────

/**
 * Deterministic missing-field checker.
 *
 * Rules:
 * - undefined or null => missing
 * - YesNoUnsure === "unsure" => missing
 * - Empty array => missing
 * - boolean false is a VALID answer (not missing)
 */
export function isMissing(fieldValue: unknown): boolean {
  if (fieldValue === undefined || fieldValue === null) return true;
  if (fieldValue === "unsure") return true;
  if (Array.isArray(fieldValue)) {
    if (fieldValue.length === 0) return true;
    return false;
  }
  return false;
}

// ─── Question Catalogue ───────────────────────────────────────────────────────

type CatalogueEntry = Omit<OpenQuestion, "status"> & {
  condition?: (profile: Profile) => boolean;
  whyNeeded: string;
};

function buildCatalogue(year: number): CatalogueEntry[] {
  const y = String(year);

  return [
    // ── Tier 1: Always required ────────────────────────────────────────────
    {
      id: "presence.trips",
      fieldPath: "presence.trips",
      priority: 100,
      category: "mrd" as OpenQuestionCategory,
      blocking: true,
      question: `What were your entry and exit dates for each trip to ${JURISDICTION_LABEL} in ${y}? Add all trips.`,
      whyNeeded: "Mandatory Residence Determination requires exact or estimated travel dates.",
      skipAllowed: true,
    },
    {
      id: "incomeTypes",
      fieldPath: "incomeTypes",
      priority: 95,
      category: "mrd" as OpenQuestionCategory,
      blocking: true,
      question: `Which income types did you have in ${y}? (Employment / Contractor / Passive / Crypto)`,
      whyNeeded: "Income type drives which gating questions apply.",
      skipAllowed: true,
    },

    // ── Conditional on employment income ──────────────────────────────────
    {
      id: "employment.workedWhileInJurisdiction",
      fieldPath: "employment.workedWhileInJurisdiction",
      priority: 92,
      category: "mrd" as OpenQuestionCategory,
      blocking: true,
      question: `Did you physically perform any employment work while you were in ${JURISDICTION_LABEL}?`,
      whyNeeded: "Physical work in-country triggers local employment source income rules.",
      skipAllowed: true,
      condition: (p) => p.incomeTypes.employment === true,
    },
    {
      id: "employment.foreignEmployer",
      fieldPath: "employment.foreignEmployer",
      priority: 88,
      category: "gate" as OpenQuestionCategory,
      blocking: true,
      question: `Was your employer foreign (not a ${JURISDICTION_LABEL} employer)?`,
      whyNeeded: "Foreign employer status affects local source income determination.",
      skipAllowed: true,
      condition: (p) => p.incomeTypes.employment === true,
    },
    {
      id: "employment.salaryBorneByLocalEntity",
      fieldPath: "employment.salaryBorneByLocalEntity",
      priority: 86,
      category: "gate" as OpenQuestionCategory,
      blocking: true,
      question: `Was your salary paid by, recharged to, or borne by a ${JURISDICTION_LABEL} entity?`,
      whyNeeded: "Salary borne by a local entity creates a local source income issue.",
      skipAllowed: true,
      condition: (p) => p.incomeTypes.employment === true,
    },

    // ── Conditional on passive income ─────────────────────────────────────
    {
      id: "passive.types",
      fieldPath: "passive.types",
      priority: 82,
      category: "mrd" as OpenQuestionCategory,
      blocking: true,
      question: `What passive income did you have? (Dividends / Interest / Rental / Other)`,
      whyNeeded: "Type of passive income determines remittance and source rules.",
      skipAllowed: true,
      condition: (p) => p.incomeTypes.passive === true,
    },
    {
      id: "passive.remittedOrReceivedInJurisdiction",
      fieldPath: "passive.remittedOrReceivedInJurisdiction",
      priority: 80,
      category: "gate" as OpenQuestionCategory,
      blocking: true,
      question: `Was any of that passive income received or remitted into ${JURISDICTION_LABEL}?`,
      whyNeeded: "Remittance into jurisdiction may trigger taxable event.",
      skipAllowed: true,
      condition: (p) => p.incomeTypes.passive === true,
    },

    // ── Conditional on contractor income ──────────────────────────────────
    {
      id: "contractor.performedServicesInJurisdiction",
      fieldPath: "contractor.performedServicesInJurisdiction",
      priority: 92,
      category: "mrd" as OpenQuestionCategory,
      blocking: true,
      question: `Did you physically perform any contractor/freelance services while you were in ${JURISDICTION_LABEL}?`,
      whyNeeded: "Physical service delivery in-country creates a local source income issue.",
      skipAllowed: true,
      condition: (p) => p.incomeTypes.contractor === true,
    },
    {
      id: "contractor.invoicedLocalEntity",
      fieldPath: "contractor.invoicedLocalEntity",
      priority: 78,
      category: "advisor" as OpenQuestionCategory,
      blocking: false,
      question: `Were any invoices issued to a ${JURISDICTION_LABEL} entity?`,
      whyNeeded: "Invoicing local entities can indicate a local source of income.",
      skipAllowed: true,
      condition: (p) => p.incomeTypes.contractor === true,
    },

    // ── Tier 3: Advisor context — always in catalogue ──────────────────────
    {
      id: "advisorContext.visaType",
      fieldPath: "advisorContext.visaType",
      priority: 70,
      category: "advisor" as OpenQuestionCategory,
      blocking: false,
      question: `What visa/permit type were you on in ${JURISDICTION_LABEL}?`,
      whyNeeded: "Visa type affects De Rantau eligibility and residency analysis.",
      skipAllowed: true,
    },
    {
      id: "advisorContext.visaDeclaredIncome",
      fieldPath: "advisorContext.visaDeclaredIncome",
      priority: 68,
      category: "advisor" as OpenQuestionCategory,
      blocking: false,
      question: `If applicable: did you declare an annual income on your visa application? If yes, what amount and currency?`,
      whyNeeded: "Visa-declared income may be relevant for De Rantau holders.",
      skipAllowed: true,
    },
    {
      id: "advisorContext.filesTaxElsewhere",
      fieldPath: "advisorContext.filesTaxElsewhere",
      priority: 60,
      category: "advisor" as OpenQuestionCategory,
      blocking: false,
      question: `Do you currently file or pay tax in another country?`,
      whyNeeded: "Filing elsewhere affects tax treaty analysis and dual residency.",
      skipAllowed: true,
    },
    {
      id: "advisorContext.otherTaxCountry",
      fieldPath: "advisorContext.otherTaxCountry",
      priority: 58,
      category: "advisor" as OpenQuestionCategory,
      blocking: false,
      question: `Which country is that?`,
      whyNeeded: "Other tax country identifies applicable double tax treaties.",
      skipAllowed: true,
    },
    {
      id: "advisorContext.taxResidentElsewhere",
      fieldPath: "advisorContext.taxResidentElsewhere",
      priority: 56,
      category: "advisor" as OpenQuestionCategory,
      blocking: false,
      question: `Are you considered tax-resident there (to the best of your knowledge)?`,
      whyNeeded: "Dual tax residency triggers tie-breaker rules under tax treaties.",
      skipAllowed: true,
    },
    {
      id: "advisorContext.isCompanyDirector",
      fieldPath: "advisorContext.isCompanyDirector",
      priority: 55,
      category: "advisor" as OpenQuestionCategory,
      blocking: false,
      question: `Are you a director of any company?`,
      whyNeeded: "Director fees sourced in-country may be taxable regardless of residency.",
      skipAllowed: true,
    },

    // ── Tier 4: Nice-to-have ───────────────────────────────────────────────
    {
      id: "advisorContext.permanentHomeInJurisdiction",
      fieldPath: "advisorContext.permanentHomeInJurisdiction",
      priority: 45,
      category: "nice" as OpenQuestionCategory,
      blocking: false,
      question: `Did you maintain a home in ${JURISDICTION_LABEL} (rent/own/none)?`,
      whyNeeded: "Permanent home is a residency tie-breaker factor under tax treaties.",
      skipAllowed: true,
    },
    {
      id: "advisorContext.citizenships",
      fieldPath: "advisorContext.citizenships",
      priority: 40,
      category: "nice" as OpenQuestionCategory,
      blocking: false,
      question: `What citizenship(s) do you hold?`,
      whyNeeded: "Citizenship can affect treaty eligibility and reporting obligations.",
      skipAllowed: true,
    },
  ];
}

// ─── Field value resolver ─────────────────────────────────────────────────────

/**
 * Retrieves the raw value for a given fieldPath from the profile.
 * Returns undefined if the path doesn't exist.
 */
function getFieldValue(profile: Profile, fieldPath: string): unknown {
  switch (fieldPath) {
    case "presence.trips":
      return profile.presence?.trips;
    case "incomeTypes":
      return profile.incomeTypes;
    case "employment.workedWhileInJurisdiction":
      return profile.employment?.workedWhileInJurisdiction;
    case "employment.foreignEmployer":
      return profile.employment?.foreignEmployer;
    case "employment.salaryBorneByLocalEntity":
      return profile.employment?.salaryBorneByLocalEntity;
    case "passive.types":
      return profile.passive?.types;
    case "passive.remittedOrReceivedInJurisdiction":
      return profile.passive?.remittedOrReceivedInJurisdiction;
    case "contractor.performedServicesInJurisdiction":
      return profile.contractor?.performedServicesInJurisdiction;
    case "contractor.invoicedLocalEntity":
      return profile.contractor?.invoicedLocalEntity;
    case "advisorContext.visaType":
      return profile.advisorContext?.visaType;
    case "advisorContext.visaDeclaredIncome":
      return profile.advisorContext?.visaDeclaredIncome;
    case "advisorContext.filesTaxElsewhere":
      // boolean false is valid, only undefined is missing
      return profile.advisorContext?.filesTaxElsewhere;
    case "advisorContext.otherTaxCountry":
      return profile.advisorContext?.otherTaxCountry;
    case "advisorContext.taxResidentElsewhere":
      return profile.advisorContext?.taxResidentElsewhere;
    case "advisorContext.isCompanyDirector":
      // boolean false is valid, only undefined is missing
      return profile.advisorContext?.isCompanyDirector;
    case "advisorContext.permanentHomeInJurisdiction":
      return profile.advisorContext?.permanentHomeInJurisdiction;
    case "advisorContext.citizenships":
      return profile.advisorContext?.citizenships;
    default:
      return undefined;
  }
}

/**
 * Special missing check for incomeTypes:
 * - Missing if all income types are false (none selected)
 * - Answered if at least one is true
 */
function isIncomeTypesMissing(profile: Profile): boolean {
  const { incomeTypes } = profile;
  return !Object.values(incomeTypes).some(Boolean);
}

/**
 * Special missing check for advisorContext.filesTaxElsewhere:
 * Only missing if undefined (boolean false is valid).
 */
function isFilesTaxElsewhereMissing(profile: Profile): boolean {
  return profile.advisorContext?.filesTaxElsewhere === undefined;
}

/**
 * Special missing check for advisorContext.isCompanyDirector:
 * Only missing if undefined (boolean false is valid).
 */
function isCompanyDirectorMissing(profile: Profile): boolean {
  return profile.advisorContext?.isCompanyDirector === undefined;
}

/**
 * Special missing check for advisorContext.visaDeclaredIncome:
 * Missing if undefined. If provided: only missing if `provided` field is not set.
 */
function isVisaDeclaredIncomeMissing(profile: Profile): boolean {
  const v = profile.advisorContext?.visaDeclaredIncome;
  if (v === undefined) return true;
  // If the object exists but `provided` is not a boolean, treat as missing
  return typeof v.provided !== "boolean";
}

/**
 * Returns true if the field at `fieldPath` is considered missing for the given profile.
 */
function isFieldMissing(profile: Profile, fieldPath: string): boolean {
  switch (fieldPath) {
    case "presence.trips": {
      const trips = profile.presence?.trips;
      if (trips.length === 0) return true;
      return trips.some((t) => !t.entryDate || !t.exitDate);
    }
    case "incomeTypes":
      return isIncomeTypesMissing(profile);
    case "advisorContext.filesTaxElsewhere":
      return isFilesTaxElsewhereMissing(profile);
    case "advisorContext.isCompanyDirector":
      return isCompanyDirectorMissing(profile);
    case "advisorContext.visaDeclaredIncome":
      return isVisaDeclaredIncomeMissing(profile);
    default:
      return isMissing(getFieldValue(profile, fieldPath));
  }
}

// ─── generateOpenQuestions ────────────────────────────────────────────────────

/**
 * Builds the sorted open-question list from the 17-question catalogue.
 *
 * Logic:
 * 1. Build candidate list from catalogue (conditional ones only if relevant income type selected)
 * 2. Filter out questions where field is NOT missing (already answered)
 * 3. Also exclude fieldPaths in skippedFieldPaths
 * 4. De-dupe by fieldPath (use a Set)
 * 5. Sort descending by priority
 * 6. Return array of OpenQuestion objects with status: "open"
 */
export function generateOpenQuestions(
  profile: Profile,
  skippedFieldPaths: string[] = [],
): OpenQuestion[] {
  const catalogue = buildCatalogue(profile.assessmentYear);
  const skippedSet = new Set(skippedFieldPaths);
  const seenPaths = new Set<string>();
  const result: OpenQuestion[] = [];

  for (const entry of catalogue) {
    // Skip if already seen (de-dupe)
    if (seenPaths.has(entry.fieldPath)) continue;

    // Skip if condition not met (conditional questions)
    if (entry.condition && !entry.condition(profile)) continue;

    // Skip if in skippedFieldPaths
    if (skippedSet.has(entry.fieldPath)) continue;

    // Skip if field is already answered (not missing)
    if (!isFieldMissing(profile, entry.fieldPath)) continue;

    seenPaths.add(entry.fieldPath);

    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { condition: _condition, ...rest } = entry;
    result.push({
      ...rest,
      status: "open",
    });
  }

  // Sort descending by priority
  result.sort((a, b) => b.priority - a.priority);

  return result;
}

// ─── computeCompletenessScore ─────────────────────────────────────────────────

/**
 * Rough 0–100 completeness score weighted by priority.
 *
 * Weight = blocking ? priority * 2 : priority
 * Score = Math.round(answeredWeight / totalWeight * 100)
 *
 * Only counts questions from the catalogue that are relevant
 * (conditional ones only if income type selected).
 * Skipped fields are treated as not answered (not counted in answeredWeight).
 */
export function computeCompletenessScore(
  profile: Profile,
  skippedFieldPaths: string[] = [],
): number {
  const catalogue = buildCatalogue(profile.assessmentYear);
  const skippedSet = new Set(skippedFieldPaths);

  let totalWeight = 0;
  let answeredWeight = 0;

  for (const entry of catalogue) {
    // Skip conditional questions that don't apply
    if (entry.condition && !entry.condition(profile)) continue;

    const weight = entry.blocking ? entry.priority * 2 : entry.priority;
    totalWeight += weight;

    // Skipped fields are not counted as answered
    if (skippedSet.has(entry.fieldPath)) continue;

    // If field is not missing, it's answered
    if (!isFieldMissing(profile, entry.fieldPath)) {
      answeredWeight += weight;
    }
  }

  if (totalWeight === 0) return 0;

  return Math.round((answeredWeight / totalWeight) * 100);
}

// ─── applyProfilePatch ────────────────────────────────────────────────────────

/**
 * Single entry point for all profile mutations.
 * Deep-merges known nested sub-objects; increments profileVersion; updates updatedAt.
 * Accepts PatchMeta for future audit-trail support (not yet persisted).
 *
 * Note: optional sub-objects (employment, contractor, passive) are merged if provided,
 * but cannot be cleared to undefined via this function. Pass the full updated sub-object
 * to replace all fields within them.
 */
export function applyProfilePatch(
  profile: Profile,
  patch: Partial<Profile>,
  meta: PatchMeta,
): Profile {
  const merged: Profile = {
    ...profile,
    ...patch,
    presence: patch.presence
      ? { ...profile.presence, ...patch.presence }
      : profile.presence,
    incomeTypes: patch.incomeTypes
      ? { ...profile.incomeTypes, ...patch.incomeTypes }
      : profile.incomeTypes,
    advisorContext: patch.advisorContext
      ? { ...profile.advisorContext, ...patch.advisorContext }
      : profile.advisorContext,
    dataQuality: patch.dataQuality
      ? { ...profile.dataQuality, ...patch.dataQuality }
      : profile.dataQuality,
    employment: patch.employment != null
      ? { ...profile.employment, ...patch.employment }
      : profile.employment,
    contractor: patch.contractor != null
      ? { ...profile.contractor, ...patch.contractor }
      : profile.contractor,
    passive: patch.passive != null
      ? { ...profile.passive, ...patch.passive }
      : profile.passive,
    profileVersion: profile.profileVersion + 1,
    updatedAt: new Date().toISOString(),
  };

  if (process.env.NODE_ENV === "development") {
    console.debug("[applyProfilePatch]", meta);
  }

  return merged;
}
