"use client";

import { useState } from "react";
import type { Profile, IncomeType, VisaType, HomeType, YesNoUnsure, Trip } from "@/lib/types";
import { CountryCombobox } from "@/components/ui/country-combobox";
import { CountryMultiSelect } from "@/components/ui/country-multi-select";

// ─── constants ───────────────────────────────────────────────────────────────

const ASSESSMENT_YEARS = [2023, 2024, 2025, 2026];

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

const PASSIVE_TYPE_OPTIONS: { value: "dividends" | "interest" | "rental" | "other"; label: string }[] = [
  { value: "dividends", label: "Dividends" },
  { value: "interest", label: "Interest" },
  { value: "rental", label: "Rental" },
  { value: "other", label: "Other" },
];

// ─── main component ───────────────────────────────────────────────────────────

type Props = {
  profile: Profile;
  onChange: (patch: Partial<Profile>) => void;
  saving?: boolean;
};

export function ProfileEditForm({ profile, onChange, saving = false }: Props) {
  const hasEmp = !!profile.incomeTypes?.employment;
  const hasCon = !!profile.incomeTypes?.contractor;
  const hasPas = !!profile.incomeTypes?.passive;
  const filesTaxElsewhere = !!profile.advisorContext?.filesTaxElsewhere;
  const visaDeclaredIncome = profile.advisorContext?.visaDeclaredIncome;

  return (
    <div className="space-y-6">
      {/* Jurisdiction */}
      <Section title="Jurisdiction">
        <div className="px-4 py-3 space-y-1.5">
          <span className="text-xs text-muted-foreground">Country</span>
          <CountryCombobox
            value={profile.jurisdiction}
            disabled={saving}
            onChange={(code) => onChange({ jurisdiction: code })}
          />
        </div>
      </Section>

      {/* Assessment year */}
      <Section title="Assessment year">
        <div className="px-4 py-3 flex items-center justify-between">
          <span className="text-xs text-muted-foreground">Year</span>
          <div className="flex gap-1.5">
            {ASSESSMENT_YEARS.map((yr) => (
              <button
                key={yr}
                onClick={() => onChange({ assessmentYear: yr })}
                disabled={saving}
                className={[
                  "px-3 py-1 rounded-lg text-xs border transition-colors",
                  profile.assessmentYear === yr
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

      {/* Income types */}
      <Section title="Income types">
        {INCOME_TYPES.map(({ value, label }) => (
          <Toggle
            key={value}
            label={label}
            checked={(profile.incomeTypes || {})[value] ?? false}
            disabled={saving}
            onChange={() =>
              onChange({
                incomeTypes: {
                  ...profile.incomeTypes,
                  [value]: !profile.incomeTypes[value],
                },
              })
            }
          />
        ))}
      </Section>

      {/* Employment details — shown only when employment is selected */}
      {hasEmp && (
        <Section title="Employment details">
          <div className="px-4 py-3 space-y-2">
            <span className="text-xs text-muted-foreground">
              Did you physically work while in Malaysia?
            </span>
            <ChipGroup
              options={YNU_OPTIONS}
              value={profile.employment?.workedWhileInJurisdiction}
              disabled={saving}
              onChange={(v) =>
                onChange({
                  employment: {
                    ...profile.employment,
                    workedWhileInJurisdiction: v as YesNoUnsure,
                  } as NonNullable<Profile["employment"]>,
                })
              }
            />
          </div>
          <div className="px-4 py-3 space-y-2">
            <span className="text-xs text-muted-foreground">
              Was your employer foreign (not Malaysian)?
            </span>
            <ChipGroup
              options={YNU_OPTIONS}
              value={profile.employment?.foreignEmployer}
              disabled={saving}
              onChange={(v) =>
                onChange({
                  employment: {
                    ...profile.employment,
                    foreignEmployer: v as YesNoUnsure,
                  } as NonNullable<Profile["employment"]>,
                })
              }
            />
          </div>
          <div className="px-4 py-3 space-y-2">
            <span className="text-xs text-muted-foreground">
              Was your salary borne by a Malaysian entity?
            </span>
            <ChipGroup
              options={YNU_OPTIONS}
              value={profile.employment?.salaryBorneByLocalEntity}
              disabled={saving}
              onChange={(v) =>
                onChange({
                  employment: {
                    ...profile.employment,
                    salaryBorneByLocalEntity: v as YesNoUnsure,
                  } as NonNullable<Profile["employment"]>,
                })
              }
            />
          </div>
        </Section>
      )}

      {/* Contractor details — shown only when contractor is selected */}
      {hasCon && (
        <Section title="Contractor details">
          <div className="px-4 py-3 space-y-2">
            <span className="text-xs text-muted-foreground">
              Did you perform contractor/freelance services while in Malaysia?
            </span>
            <ChipGroup
              options={YNU_OPTIONS}
              value={profile.contractor?.performedServicesInJurisdiction}
              disabled={saving}
              onChange={(v) =>
                onChange({
                  contractor: {
                    ...profile.contractor,
                    performedServicesInJurisdiction: v as YesNoUnsure,
                  } as NonNullable<Profile["contractor"]>,
                })
              }
            />
          </div>
          <div className="px-4 py-3 space-y-2">
            <span className="text-xs text-muted-foreground">
              Did you invoice any Malaysian entities?
            </span>
            <ChipGroup
              options={YNU_OPTIONS}
              value={profile.contractor?.invoicedLocalEntity}
              disabled={saving}
              onChange={(v) =>
                onChange({
                  contractor: {
                    ...profile.contractor,
                    invoicedLocalEntity: v as YesNoUnsure,
                  } as NonNullable<Profile["contractor"]>,
                })
              }
            />
          </div>
        </Section>
      )}

      {/* Passive income details — shown only when passive is selected */}
      {hasPas && (
        <Section title="Passive income details">
          <div className="px-4 py-3 space-y-2">
            <span className="text-xs text-muted-foreground">Passive income types</span>
            <MultiChipGroup
              options={PASSIVE_TYPE_OPTIONS}
              value={profile.passive?.types ?? []}
              disabled={saving}
              onChange={(types) =>
                onChange({
                  passive: {
                    ...profile.passive,
                    types: types as NonNullable<Profile["passive"]>["types"],
                  } as NonNullable<Profile["passive"]>,
                })
              }
            />
          </div>
          <div className="px-4 py-3 space-y-2">
            <span className="text-xs text-muted-foreground">
              Was any passive income received or remitted into Malaysia?
            </span>
            <ChipGroup
              options={YNU_OPTIONS}
              value={profile.passive?.remittedOrReceivedInJurisdiction}
              disabled={saving}
              onChange={(v) =>
                onChange({
                  passive: {
                    ...profile.passive,
                    remittedOrReceivedInJurisdiction: v as YesNoUnsure,
                  } as NonNullable<Profile["passive"]>,
                })
              }
            />
          </div>
        </Section>
      )}

      {/* Advisor context */}
      <Section title="Advisor context">
        <Toggle
          label="Files tax elsewhere"
          checked={profile.advisorContext?.filesTaxElsewhere ?? false}
          disabled={saving}
          onChange={() =>
            onChange({
              advisorContext: {
                ...profile.advisorContext,
                filesTaxElsewhere: !profile.advisorContext?.filesTaxElsewhere,
              },
            })
          }
        />

        {/* Other tax country — shown when filesTaxElsewhere is true */}
        {filesTaxElsewhere && (
          <div className="px-4 py-3 space-y-1.5">
            <span className="text-xs text-muted-foreground">Which country?</span>
            <CountryCombobox
              value={profile.advisorContext?.otherTaxCountry}
              disabled={saving}
              onChange={(code) =>
                onChange({
                  advisorContext: {
                    ...profile.advisorContext,
                    otherTaxCountry: code,
                  },
                })
              }
            />
          </div>
        )}

        <Toggle
          label="Company director"
          checked={profile.advisorContext?.isCompanyDirector ?? false}
          disabled={saving}
          onChange={() =>
            onChange({
              advisorContext: {
                ...profile.advisorContext,
                isCompanyDirector: !profile.advisorContext?.isCompanyDirector,
              },
            })
          }
        />

        <div className="px-4 py-3 space-y-2">
          <span className="text-xs text-muted-foreground">Tax resident elsewhere?</span>
          <ChipGroup
            options={YNU_OPTIONS}
            value={profile.advisorContext?.taxResidentElsewhere}
            disabled={saving}
            onChange={(v) =>
              onChange({
                advisorContext: {
                  ...profile.advisorContext,
                  taxResidentElsewhere: v as YesNoUnsure,
                },
              })
            }
          />
        </div>

        <div className="px-4 py-3 space-y-2">
          <span className="text-xs text-muted-foreground">Visa type</span>
          <ChipGroup
            options={VISA_OPTIONS}
            value={profile.advisorContext?.visaType}
            disabled={saving}
            onChange={(v) =>
              onChange({
                advisorContext: {
                  ...profile.advisorContext,
                  visaType: v as VisaType,
                },
              })
            }
          />
        </div>

        {/* Visa declared income */}
        <Toggle
          label="Declared income on visa application"
          checked={visaDeclaredIncome?.provided ?? false}
          disabled={saving}
          onChange={() => {
            const nowProvided = !(visaDeclaredIncome?.provided ?? false);
            onChange({
              advisorContext: {
                ...profile.advisorContext,
                visaDeclaredIncome: { provided: nowProvided },
              },
            });
          }}
        />
        {visaDeclaredIncome?.provided && (
          <div className="px-4 py-3 grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <span className="text-xs text-muted-foreground">Amount</span>
              <input
                type="number"
                min={0}
                value={visaDeclaredIncome.amount ?? ""}
                onChange={(e) =>
                  onChange({
                    advisorContext: {
                      ...profile.advisorContext,
                      visaDeclaredIncome: {
                        ...visaDeclaredIncome,
                        amount: e.target.value ? Number(e.target.value) : undefined,
                      },
                    },
                  })
                }
                disabled={saving}
                placeholder="e.g. 24000"
                className="w-full px-3 py-2 rounded-lg border border-border/60 bg-background text-sm focus:outline-none focus:ring-1 focus:ring-primary/40 disabled:opacity-50"
              />
            </div>
            <div className="space-y-1.5">
              <span className="text-xs text-muted-foreground">Currency</span>
              <input
                type="text"
                maxLength={3}
                value={visaDeclaredIncome.currency ?? ""}
                onChange={(e) =>
                  onChange({
                    advisorContext: {
                      ...profile.advisorContext,
                      visaDeclaredIncome: {
                        ...visaDeclaredIncome,
                        currency: e.target.value.toUpperCase() || undefined,
                      },
                    },
                  })
                }
                disabled={saving}
                placeholder="USD"
                className="w-full px-3 py-2 rounded-lg border border-border/60 bg-background text-sm uppercase placeholder:normal-case focus:outline-none focus:ring-1 focus:ring-primary/40 disabled:opacity-50"
              />
            </div>
          </div>
        )}

        <div className="px-4 py-3 space-y-2">
          <span className="text-xs text-muted-foreground">Permanent home in jurisdiction</span>
          <ChipGroup
            options={HOME_OPTIONS}
            value={profile.advisorContext?.permanentHomeInJurisdiction}
            disabled={saving}
            onChange={(v) =>
              onChange({
                advisorContext: {
                  ...profile.advisorContext,
                  permanentHomeInJurisdiction: v as HomeType,
                },
              })
            }
          />
        </div>

        <div className="px-4 py-3 space-y-1.5">
          <span className="text-xs text-muted-foreground">Citizenships</span>
          <CountryMultiSelect
            value={profile.advisorContext?.citizenships ?? []}
            disabled={saving}
            onChange={(citizenships) =>
              onChange({
                advisorContext: { ...profile.advisorContext, citizenships },
              })
            }
          />
        </div>
      </Section>

      {/* Trip log */}
      <TripLogSection
        trips={profile.presence?.trips ?? []}
        saving={saving}
        onTripsChange={(trips) => onChange({ presence: { trips } })}
      />
    </div>
  );
}

// ─── TripLogSection ───────────────────────────────────────────────────────────

type TripForm = {
  country: string;
  entryDate: string;
  exitDate: string;
  dateConfidence: "exact" | "estimated";
  notes: string;
};

const BLANK_FORM: TripForm = {
  country: "",
  entryDate: "",
  exitDate: "",
  dateConfidence: "exact",
  notes: "",
};

function TripLogSection({
  trips,
  saving,
  onTripsChange,
}: {
  trips: Trip[];
  saving: boolean;
  onTripsChange: (trips: Trip[]) => void;
}) {
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState<TripForm>(BLANK_FORM);
  const [formError, setFormError] = useState<string | null>(null);

  function set<K extends keyof TripForm>(key: K, value: TripForm[K]) {
    setForm((f) => ({ ...f, [key]: value }));
    setFormError(null);
  }

  function handleAdd() {
    if (!form.country) return setFormError("Country is required.");
    if (!form.entryDate) return setFormError("Entry date is required.");
    if (!form.exitDate) return setFormError("Exit date is required.");
    if (form.entryDate > form.exitDate) return setFormError("Entry must be before exit.");

    const newTrip: Trip = {
      tripId: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      country: form.country,
      entryDate: form.entryDate,
      exitDate: form.exitDate,
      dateConfidence: form.dateConfidence,
      notes: form.notes || undefined,
    };
    onTripsChange([...trips, newTrip]);
    setForm(BLANK_FORM);
    setAdding(false);
  }

  function handleDelete(tripId: string) {
    onTripsChange(trips.filter((t) => t.tripId !== tripId));
  }

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-medium tracking-widest uppercase text-muted-foreground">
          Trip log
        </h2>
        <span className="text-xs text-muted-foreground">
          {trips.length} {trips.length === 1 ? "trip" : "trips"}
        </span>
      </div>

      <div className="rounded-xl border border-border/50 bg-card/40 divide-y divide-border/40">
        {trips.length === 0 && !adding && (
          <p className="px-4 py-4 text-sm text-muted-foreground">No trips logged yet.</p>
        )}

        {trips
          .slice()
          .sort((a, b) => b.entryDate.localeCompare(a.entryDate))
          .map((trip) => (
            <div key={trip.tripId} className="flex items-start justify-between px-4 py-3 gap-3">
              <div className="space-y-0.5 min-w-0">
                <p className="text-sm font-medium">{trip.country}</p>
                <p className="text-xs text-muted-foreground">
                  {trip.entryDate} → {trip.exitDate}
                </p>
                {trip.notes && (
                  <p className="text-xs text-muted-foreground/70 truncate">{trip.notes}</p>
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span
                  className={[
                    "px-2 py-0.5 rounded text-[10px] font-medium",
                    trip.dateConfidence === "exact"
                      ? "bg-primary/10 text-primary"
                      : "bg-amber-500/10 text-amber-600 dark:text-amber-400",
                  ].join(" ")}
                >
                  {trip.dateConfidence}
                </span>
                <button
                  onClick={() => handleDelete(trip.tripId)}
                  disabled={saving}
                  className="text-muted-foreground/50 hover:text-destructive transition-colors disabled:opacity-30 text-xs"
                  aria-label="Delete trip"
                >
                  ✕
                </button>
              </div>
            </div>
          ))}

        {adding && (
          <div className="px-4 py-4 space-y-3">
            <div className="space-y-1.5">
              <span className="text-xs text-muted-foreground">Country</span>
              <CountryCombobox
                value={form.country || undefined}
                onChange={(code) => set("country", code)}
                disabled={saving}
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <span className="text-xs text-muted-foreground">Entry date</span>
                <input
                  type="date"
                  value={form.entryDate}
                  onChange={(e) => set("entryDate", e.target.value)}
                  disabled={saving}
                  className="w-full px-3 py-2 rounded-lg border border-border/60 bg-background text-sm focus:outline-none focus:ring-1 focus:ring-primary/40 disabled:opacity-50"
                />
              </div>
              <div className="space-y-1.5">
                <span className="text-xs text-muted-foreground">Exit date</span>
                <input
                  type="date"
                  value={form.exitDate}
                  onChange={(e) => set("exitDate", e.target.value)}
                  disabled={saving}
                  className="w-full px-3 py-2 rounded-lg border border-border/60 bg-background text-sm focus:outline-none focus:ring-1 focus:ring-primary/40 disabled:opacity-50"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <span className="text-xs text-muted-foreground">Date confidence</span>
              <div className="flex gap-1.5">
                {(["exact", "estimated"] as const).map((opt) => (
                  <button
                    key={opt}
                    type="button"
                    onClick={() => set("dateConfidence", opt)}
                    disabled={saving}
                    className={[
                      "px-3 py-1 rounded-lg text-xs border transition-colors",
                      form.dateConfidence === opt
                        ? "bg-primary/10 border-primary/40 text-primary font-medium"
                        : "border-border/50 text-muted-foreground hover:border-primary/30 hover:text-foreground",
                    ].join(" ")}
                  >
                    {opt}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-1.5">
              <span className="text-xs text-muted-foreground">Notes (optional)</span>
              <input
                type="text"
                value={form.notes}
                onChange={(e) => set("notes", e.target.value)}
                placeholder="e.g. business trip"
                disabled={saving}
                className="w-full px-3 py-2 rounded-lg border border-border/60 bg-background text-sm placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/40 disabled:opacity-50"
              />
            </div>

            {formError && (
              <p className="text-xs text-destructive">{formError}</p>
            )}

            <div className="flex gap-2 pt-1">
              <button
                type="button"
                onClick={handleAdd}
                disabled={saving}
                className="px-4 py-1.5 bg-primary text-primary-foreground rounded-lg text-xs font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                Add trip
              </button>
              <button
                type="button"
                onClick={() => { setAdding(false); setForm(BLANK_FORM); setFormError(null); }}
                className="px-4 py-1.5 rounded-lg text-xs border border-border/60 text-muted-foreground hover:text-foreground transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      {!adding && (
        <button
          type="button"
          onClick={() => setAdding(true)}
          disabled={saving}
          className="w-full px-4 py-2.5 rounded-xl text-sm border border-dashed border-border/60 text-muted-foreground hover:border-primary/40 hover:text-foreground transition-colors disabled:opacity-50"
        >
          + Add trip
        </button>
      )}
    </section>
  );
}

// ─── shared primitives ────────────────────────────────────────────────────────

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

function MultiChipGroup({
  options,
  value,
  disabled,
  onChange,
}: {
  options: { value: string; label: string }[];
  value: string[];
  disabled: boolean;
  onChange: (v: string[]) => void;
}) {
  function toggle(v: string) {
    if (value.includes(v)) {
      onChange(value.filter((x) => x !== v));
    } else {
      onChange([...value, v]);
    }
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((opt) => {
        const selected = value.includes(opt.value);
        return (
          <button
            key={opt.value}
            onClick={() => toggle(opt.value)}
            disabled={disabled}
            className={[
              "px-3 py-1 rounded-lg text-xs border transition-colors disabled:opacity-50",
              selected
                ? "bg-primary/10 border-primary/40 text-primary font-medium"
                : "border-border/50 text-muted-foreground hover:border-primary/30 hover:text-foreground",
            ].join(" ")}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
