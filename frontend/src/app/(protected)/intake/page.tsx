"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useUserProfile } from "@/hooks/useUserProfile";
import { useAuth } from "@/components/AuthProvider";
import type { IncomeType, VisaType, YesNoUnsure } from "@/lib/types";

type WizardStep = 1 | 2 | 3;

const INCOME_TYPES: IncomeType[] = ["employment", "contractor", "passive", "crypto"];
const VISA_TYPES: { value: VisaType; label: string }[] = [
  { value: "de_rantau", label: "DE Rantau" },
  { value: "tourist", label: "Tourist" },
  { value: "employment_pass", label: "Employment Pass" },
  { value: "other", label: "Other" },
];
const YES_NO_UNSURE: { value: YesNoUnsure; label: string }[] = [
  { value: "yes", label: "Yes" },
  { value: "no", label: "No" },
  { value: "unsure", label: "Unsure" },
];

export default function IntakePage() {
  const router = useRouter();
  const { user, accessToken } = useAuth();
  const { profile, loading, error, savePatch } = useUserProfile({
    userId: user?.userId,
    accessToken: accessToken ?? undefined,
  });
  const [step, setStep] = useState<WizardStep>(1);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  async function handleSave(patch: Parameters<typeof savePatch>[0]) {
    setSaving(true);
    setSaveError(null);
    try {
      await savePatch(patch);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Save failed");
      throw err;
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto px-5 py-12">
        <p className="text-muted-foreground text-sm">Loading…</p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-5 py-12 space-y-8">
      <div>
        <h1
          className="text-3xl font-normal"
          style={{ fontFamily: "'Cormorant Garamond', serif" }}
        >
          Tax intake
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Step {step} of 3
        </p>
      </div>

      {/* Step progress */}
      <div className="flex gap-2">
        {([1, 2, 3] as WizardStep[]).map((s) => (
          <button
            key={s}
            onClick={() => setStep(s)}
            className={[
              "h-1.5 flex-1 rounded-full transition-colors",
              s <= step ? "bg-primary" : "bg-border",
            ].join(" ")}
            aria-label={`Go to step ${s}`}
          />
        ))}
      </div>

      {(error || saveError) && (
        <div className="px-4 py-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm">
          {error || saveError}
        </div>
      )}

      {step === 1 && (
        <Step1
          profile={profile}
          saving={saving}
          onSave={handleSave}
          onNext={() => setStep(2)}
        />
      )}
      {step === 2 && (
        <Step2
          profile={profile}
          saving={saving}
          onSave={handleSave}
          onBack={() => setStep(1)}
          onNext={() => setStep(3)}
        />
      )}
      {step === 3 && (
        <Step3
          profile={profile}
          saving={saving}
          onSave={handleSave}
          onBack={() => setStep(2)}
          onComplete={async () => {
            await handleSave({ dataQuality: { intakeCompleted: true } });
            router.push("/");
          }}
        />
      )}
    </div>
  );
}

// Step 1: Income types
function Step1({
  profile,
  saving,
  onSave,
  onNext,
}: {
  profile: ReturnType<typeof useUserProfile>["profile"];
  saving: boolean;
  onSave: (patch: Parameters<ReturnType<typeof useUserProfile>["savePatch"]>[0]) => Promise<void>;
  onNext: () => void;
}) {
  async function toggle(type: IncomeType) {
    if (!profile) return;
    await onSave({
      incomeTypes: { ...profile.incomeTypes, [type]: !profile.incomeTypes[type] },
    });
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-medium">What types of income do you have?</h2>
        <p className="text-sm text-muted-foreground mt-1">Select all that apply.</p>
      </div>
      <div className="rounded-xl border border-border/50 bg-card/40 divide-y divide-border/40">
        {INCOME_TYPES.map((type) => (
          <label
            key={type}
            className="flex items-center justify-between px-4 py-3.5 cursor-pointer hover:bg-accent/30 transition-colors"
          >
            <span className="text-sm capitalize">{type}</span>
            <input
              type="checkbox"
              checked={profile?.incomeTypes[type] ?? false}
              onChange={() => toggle(type)}
              disabled={saving}
              className="size-4 accent-primary"
            />
          </label>
        ))}
      </div>
      <div className="flex justify-end">
        <button
          onClick={onNext}
          className="px-5 py-2 bg-primary text-primary-foreground rounded-xl text-sm font-medium hover:opacity-90 transition-opacity"
        >
          Next
        </button>
      </div>
    </div>
  );
}

// Step 2: Visa + advisor context
function Step2({
  profile,
  saving,
  onSave,
  onBack,
  onNext,
}: {
  profile: ReturnType<typeof useUserProfile>["profile"];
  saving: boolean;
  onSave: (patch: Parameters<ReturnType<typeof useUserProfile>["savePatch"]>[0]) => Promise<void>;
  onBack: () => void;
  onNext: () => void;
}) {
  async function setVisa(visaType: VisaType) {
    if (!profile) return;
    await onSave({ advisorContext: { ...profile.advisorContext, visaType } });
  }

  async function setTaxResidentElsewhere(value: YesNoUnsure) {
    if (!profile) return;
    await onSave({
      advisorContext: { ...profile.advisorContext, taxResidentElsewhere: value },
    });
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-medium">Your visa and tax residency</h2>
      </div>

      <div className="space-y-2">
        <label className="text-sm text-muted-foreground">Visa type</label>
        <div className="grid grid-cols-2 gap-2">
          {VISA_TYPES.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setVisa(value)}
              disabled={saving}
              className={[
                "px-4 py-2.5 rounded-xl text-sm border transition-colors",
                profile?.advisorContext.visaType === value
                  ? "bg-primary/10 border-primary/40 text-primary"
                  : "border-border/60 text-muted-foreground hover:border-primary/30 hover:text-foreground",
              ].join(" ")}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <label className="text-sm text-muted-foreground">Tax resident elsewhere?</label>
        <div className="flex gap-2">
          {YES_NO_UNSURE.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setTaxResidentElsewhere(value)}
              disabled={saving}
              className={[
                "flex-1 px-4 py-2.5 rounded-xl text-sm border transition-colors",
                profile?.advisorContext.taxResidentElsewhere === value
                  ? "bg-primary/10 border-primary/40 text-primary"
                  : "border-border/60 text-muted-foreground hover:border-primary/30 hover:text-foreground",
              ].join(" ")}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex justify-between">
        <button
          onClick={onBack}
          className="px-5 py-2 rounded-xl text-sm border border-border/60 text-muted-foreground hover:text-foreground transition-colors"
        >
          Back
        </button>
        <button
          onClick={onNext}
          className="px-5 py-2 bg-primary text-primary-foreground rounded-xl text-sm font-medium hover:opacity-90 transition-opacity"
        >
          Next
        </button>
      </div>
    </div>
  );
}

// Step 3: Employment details (shown if employment income selected)
function Step3({
  profile,
  saving,
  onSave,
  onBack,
  onComplete,
}: {
  profile: ReturnType<typeof useUserProfile>["profile"];
  saving: boolean;
  onSave: (patch: Parameters<ReturnType<typeof useUserProfile>["savePatch"]>[0]) => Promise<void>;
  onBack: () => void;
  onComplete: () => Promise<void>;
}) {
  const hasEmployment = profile?.incomeTypes.employment;

  async function setEmploymentField(
    field: "foreignEmployer" | "salaryBorneByLocalEntity" | "workedWhileInJurisdiction",
    value: YesNoUnsure,
  ) {
    if (!profile) return;
    await onSave({
      employment: {
        foreignEmployer: "unsure",
        salaryBorneByLocalEntity: "unsure",
        workedWhileInJurisdiction: "unsure",
        ...profile.employment,
        [field]: value,
      },
    });
  }

  const questions: {
    field: "foreignEmployer" | "salaryBorneByLocalEntity" | "workedWhileInJurisdiction";
    label: string;
  }[] = [
    { field: "foreignEmployer", label: "Foreign employer?" },
    { field: "salaryBorneByLocalEntity", label: "Salary borne by local entity?" },
    { field: "workedWhileInJurisdiction", label: "Worked while in Malaysia?" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-medium">Employment details</h2>
        {!hasEmployment && (
          <p className="text-sm text-muted-foreground mt-1">
            You did not select employment income — you can skip this step.
          </p>
        )}
      </div>

      {hasEmployment && (
        <div className="space-y-4">
          {questions.map(({ field, label }) => (
            <div key={field} className="space-y-2">
              <label className="text-sm text-muted-foreground">{label}</label>
              <div className="flex gap-2">
                {YES_NO_UNSURE.map(({ value, label: optLabel }) => (
                  <button
                    key={value}
                    onClick={() => setEmploymentField(field, value)}
                    disabled={saving}
                    className={[
                      "flex-1 px-4 py-2.5 rounded-xl text-sm border transition-colors",
                      profile?.employment?.[field] === value
                        ? "bg-primary/10 border-primary/40 text-primary"
                        : "border-border/60 text-muted-foreground hover:border-primary/30 hover:text-foreground",
                    ].join(" ")}
                  >
                    {optLabel}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={onBack}
          className="px-5 py-2 rounded-xl text-sm border border-border/60 text-muted-foreground hover:text-foreground transition-colors"
        >
          Back
        </button>
        <button
          type="button"
          onClick={onComplete}
          disabled={saving}
          className="px-5 py-2 bg-primary text-primary-foreground rounded-xl text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          {saving ? "Saving…" : "Complete"}
        </button>
      </div>
    </div>
  );
}
