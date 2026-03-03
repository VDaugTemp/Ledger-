export type YesNoUnsure = "yes" | "no" | "unsure";
export type Jurisdiction = string; // ISO 3166-1 alpha-2 country code
export type WizardStep = 1 | 2 | 3;
export type Phase = "intake" | "assessment" | "elevated_risk";
export type IncomeType = "employment" | "contractor" | "passive" | "crypto";
export type VisaType = "de_rantau" | "tourist" | "employment_pass" | "other";
export type HomeType = "rent" | "own" | "none";

export type Trip = {
  tripId: string;
  country: string;
  entryDate: string;
  exitDate: string;
  dateConfidence: "exact" | "estimated";
  notes?: string;
};

export type Profile = {
  profileVersion: number;
  updatedAt: string;
  jurisdiction: Jurisdiction;
  assessmentYear: number;
  presence: { trips: Trip[] };
  incomeTypes: Record<IncomeType, boolean>;
  employment?: {
    foreignEmployer: YesNoUnsure;
    salaryBorneByLocalEntity: YesNoUnsure;
    workedWhileInJurisdiction: YesNoUnsure;
  };
  contractor?: {
    performedServicesInJurisdiction: YesNoUnsure;
    invoicedLocalEntity: YesNoUnsure;
  };
  passive?: {
    types: Array<"dividends" | "interest" | "rental" | "other">;
    remittedOrReceivedInJurisdiction: YesNoUnsure;
  };
  advisorContext: {
    filesTaxElsewhere: boolean;
    otherTaxCountry?: string;
    taxResidentElsewhere?: YesNoUnsure;
    citizenships: string[];
    visaType?: VisaType;
    visaDeclaredIncome?: { provided: boolean; amount?: number; currency?: string };
    isCompanyDirector?: boolean;
    permanentHomeInJurisdiction?: HomeType;
  };
  dataQuality: {
    mrdComplete?: boolean;
    intakeCompleted?: boolean;
    missingFields?: Array<{ fieldPath: string; question: string; priority: number }>;
    completenessScore?: number;
  };
};

// ─── Conversation-loop types ─────────────────────────────────────────────────

export type OpenQuestionCategory = "mrd" | "gate" | "advisor" | "nice";
export type OpenQuestionStatus = "open" | "answered" | "skipped";

export type OpenQuestion = {
  id: string;                    // stable, derived from fieldPath
  fieldPath: string;             // e.g. "presence.trips" or "employment.foreignEmployer"
  priority: number;              // higher = earlier
  category: OpenQuestionCategory;
  blocking: boolean;             // if missing => blocks certain outputs
  question: string;              // user-facing question text
  whyNeeded: string;             // short internal justification
  status: OpenQuestionStatus;    // runtime only; not persisted in Profile
  skipAllowed: boolean;
};

export type ConfidenceTier = "high" | "medium" | "low";

export type PatchMeta = {
  source: "wizard" | "chat" | "user_edit";
  questionId?: string;
  fieldPath?: string;
  confidenceTier?: ConfidenceTier;
  rawUserText?: string;
  timestampIso: string;
};

export type ExtractResult = {
  answeredFieldPaths: string[];
  profilePatch: Partial<Profile>;
  confidenceTier: ConfidenceTier;
  notes?: string;
};
