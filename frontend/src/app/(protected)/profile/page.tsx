"use client";

import { useState } from "react";
import { useUserProfile } from "@/hooks/useUserProfile";
import { useAuth } from "@/components/AuthProvider";
import type { IncomeType, VisaType, HomeType, YesNoUnsure, Profile } from "@/lib/types";
import { CountryCombobox } from "@/components/ui/country-combobox";
import { CountryMultiSelect } from "@/components/ui/country-multi-select";

const INCOME_TYPES: { value: IncomeType; label: string }[] = [
  { value: "employment", label: "Employment" },
  { value: "contractor", label: "Contractor" },
  { value: "passive", label: "Passive" },
  { value: "crypto", label: "Crypto" },
];

const VISA_OPTIONS: { value: VisaType; label: string }[] = [
  { value: "de_rantau", label: "DE Rantau" },
  { value: "tourist", label: "Tourist" },
  { value: "employment_pass", label: "Employment Pass" },
  { value: "other", label: "Other" },
];

const HOME_OPTIONS: { value: HomeType; label: string }[] = [
  { value: "rent", label: "Rent" },
  { value: "own", label: "Own" },
  { value: "none", label: "None" },
];

const YNU_OPTIONS: { value: YesNoUnsure; label: string }[] = [
  { value: "yes", label: "Yes" },
  { value: "no", label: "No" },
  { value: "unsure", label: "Unsure" },
];

const ASSESSMENT_YEARS = [2023, 2024, 2025, 2026];

export default function ProfilePage() {
  const { user, accessToken } = useAuth();
  const { userId, profile, loading, error, savePatch, refresh } = useUserProfile({
    userId: user?.userId,
    accessToken: accessToken ?? undefined,
  });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  async function patch(p: Partial<Profile>) {
    if (!profile) return;
    setSaving(true);
    setSaveError(null);
    try {
      await savePatch(p);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleRefresh() {
    setRefreshing(true);
    setSaveError(null);
    try {
      await refresh();
    } finally {
      setRefreshing(false);
    }
  }

  if (loading && !profile) {
    return (
      <div className="max-w-2xl mx-auto px-5 py-12">
        <p className="text-muted-foreground text-sm">Loading profile…</p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-5 py-12 space-y-10">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1
            className="text-3xl font-normal"
            style={{ fontFamily: "'Cormorant Garamond', serif" }}
          >
            Your Profile
          </h1>
          {profile && (
            <p className="text-xs text-muted-foreground mt-1">
              v{profile.profileVersion} · updated {new Date(profile.updatedAt).toLocaleString()}
            </p>
          )}
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="px-3 py-1.5 text-xs rounded-lg border border-border/60 text-muted-foreground hover:text-foreground hover:border-border transition-colors disabled:opacity-50"
        >
          {refreshing ? "Refreshing…" : "Refresh from server"}
        </button>
      </div>

      {/* Error banner */}
      {(error || saveError) && (
        <div className="px-4 py-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm">
          {saveError || error}
        </div>
      )}

      {/* Saving indicator */}
      {saving && (
        <p className="text-xs text-muted-foreground -mt-6">Saving…</p>
      )}

      {/* ── Account ── */}
      <Section title="Account">
        <ReadRow label="User ID" value={userId ?? "—"} mono />
        <div className="px-4 py-3 space-y-1.5">
          <span className="text-xs text-muted-foreground">Jurisdiction</span>
          <CountryCombobox
            value={profile?.jurisdiction}
            disabled={saving}
            onChange={(code) => patch({ jurisdiction: code })}
          />
        </div>
        <ReadRow
          label="Profile complete"
          value={profile?.dataQuality.mrdComplete ? "Yes" : "No"}
        />
        <ReadRow
          label="Completeness score"
          value={profile ? `${profile.dataQuality.completenessScore}%` : "—"}
        />
      </Section>

      {/* ── Assessment year ── */}
      <Section title="Assessment year">
        <div className="px-4 py-3 flex items-center justify-between">
          <span className="text-xs text-muted-foreground">Year</span>
          <div className="flex gap-1.5">
            {ASSESSMENT_YEARS.map((yr) => (
              <button
                key={yr}
                onClick={() => patch({ assessmentYear: yr })}
                disabled={saving}
                className={[
                  "px-3 py-1 rounded-lg text-xs border transition-colors",
                  profile?.assessmentYear === yr
                    ? "bg-primary/10 border-primary/40 text-primary font-medium"
                    : "border-border/50 text-muted-foreground hover:border-primary/30 hover:text-foreground",
                ].join(" ")}
              >
                {yr}
              </button>
            ))}
          </div>
        </div>
      </Section>

      {/* ── Income types ── */}
      <Section title="Income types">
        {INCOME_TYPES.map(({ value, label }) => (
          <Toggle
            key={value}
            label={label}
            checked={profile?.incomeTypes[value] ?? false}
            disabled={saving}
            onChange={() =>
              patch({
                incomeTypes: {
                  ...profile!.incomeTypes,
                  [value]: !profile!.incomeTypes[value],
                },
              })
            }
          />
        ))}
      </Section>

      {/* ── Advisor context ── */}
      <Section title="Advisor context">
        {/* Files tax elsewhere */}
        <Toggle
          label="Files tax elsewhere"
          checked={profile?.advisorContext.filesTaxElsewhere ?? false}
          disabled={saving}
          onChange={() =>
            patch({
              advisorContext: {
                ...profile!.advisorContext,
                filesTaxElsewhere: !profile!.advisorContext.filesTaxElsewhere,
              },
            })
          }
        />

        {/* Company director */}
        <Toggle
          label="Company director"
          checked={profile?.advisorContext.isCompanyDirector ?? false}
          disabled={saving}
          onChange={() =>
            patch({
              advisorContext: {
                ...profile!.advisorContext,
                isCompanyDirector: !profile!.advisorContext.isCompanyDirector,
              },
            })
          }
        />

        {/* Tax resident elsewhere */}
        <div className="px-4 py-3 space-y-2">
          <span className="text-xs text-muted-foreground">Tax resident elsewhere?</span>
          <ChipGroup
            options={YNU_OPTIONS}
            value={profile?.advisorContext.taxResidentElsewhere}
            disabled={saving}
            onChange={(v) =>
              patch({
                advisorContext: {
                  ...profile!.advisorContext,
                  taxResidentElsewhere: v as YesNoUnsure,
                },
              })
            }
          />
        </div>

        {/* Visa type */}
        <div className="px-4 py-3 space-y-2">
          <span className="text-xs text-muted-foreground">Visa type</span>
          <ChipGroup
            options={VISA_OPTIONS}
            value={profile?.advisorContext.visaType}
            disabled={saving}
            onChange={(v) =>
              patch({
                advisorContext: {
                  ...profile!.advisorContext,
                  visaType: v as VisaType,
                },
              })
            }
          />
        </div>

        {/* Permanent home */}
        <div className="px-4 py-3 space-y-2">
          <span className="text-xs text-muted-foreground">Permanent home in jurisdiction</span>
          <ChipGroup
            options={HOME_OPTIONS}
            value={profile?.advisorContext.permanentHomeInJurisdiction}
            disabled={saving}
            onChange={(v) =>
              patch({
                advisorContext: {
                  ...profile!.advisorContext,
                  permanentHomeInJurisdiction: v as HomeType,
                },
              })
            }
          />
        </div>

        {/* Citizenships */}
        <div className="px-4 py-3 space-y-1.5">
          <span className="text-xs text-muted-foreground">Citizenships</span>
          <CountryMultiSelect
            value={profile?.advisorContext.citizenships ?? []}
            disabled={saving}
            onChange={(citizenships) =>
              patch({
                advisorContext: { ...profile!.advisorContext, citizenships },
              })
            }
          />
        </div>
      </Section>
    </div>
  );
}

// ─── sub-components ─────────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="text-xs font-medium tracking-widest uppercase text-muted-foreground">
        {title}
      </h2>
      <div className="rounded-xl border border-border/50 bg-card/40 divide-y divide-border/40">
        {children}
      </div>
    </section>
  );
}

function ReadRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between px-4 py-3">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className={["text-sm text-foreground/85", mono ? "font-mono text-xs" : ""].join(" ")}>
        {value}
      </span>
    </div>
  );
}

function Toggle({
  label,
  checked,
  disabled,
  onChange,
}: {
  label: string;
  checked: boolean;
  disabled: boolean;
  onChange: () => void;
}) {
  return (
    <div className="flex items-center justify-between px-4 py-3">
      <span className="text-sm text-foreground/80">{label}</span>
      <button
        onClick={onChange}
        disabled={disabled}
        aria-pressed={checked}
        className={[
          "relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none disabled:opacity-50",
          checked ? "bg-primary" : "bg-border",
        ].join(" ")}
      >
        <span
          className={[
            "inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform",
            checked ? "translate-x-4" : "translate-x-1",
          ].join(" ")}
        />
      </button>
    </div>
  );
}

function ChipGroup({
  options,
  value,
  disabled,
  onChange,
}: {
  options: { value: string; label: string }[];
  value: string | undefined;
  disabled: boolean;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          disabled={disabled}
          className={[
            "px-3 py-1 rounded-lg text-xs border transition-colors disabled:opacity-50",
            value === opt.value
              ? "bg-primary/10 border-primary/40 text-primary font-medium"
              : "border-border/50 text-muted-foreground hover:border-primary/30 hover:text-foreground",
          ].join(" ")}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
