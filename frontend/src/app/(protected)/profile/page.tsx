"use client";

import { useState } from "react";
import { useUserProfile } from "@/hooks/useUserProfile";
import { useAuth } from "@/components/AuthProvider";
import type { Profile } from "@/lib/types";
import { CountryCombobox } from "@/components/ui/country-combobox";
import { generateOpenQuestions, computeCompletenessScore, applyProfilePatch } from "@/lib/openQuestions";
import { ProfileEditForm } from "@/components/ProfileEditForm";
import { NextStepAction } from "@/components/NextStepAction";
import { AdvisorSummaryModal } from "@/components/AdvisorSummaryModal";
import { downloadAdvisorPdf } from "@/lib/pdf-downloader";

export default function ProfilePage() {
  const { user, accessToken } = useAuth();
  const { userId, profile, loading, error, savePatch, refresh } = useUserProfile({
    userId: user?.userId,
    accessToken: accessToken ?? undefined,
  });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [advisorModalOpen, setAdvisorModalOpen] = useState(false);

  async function patch(p: Partial<Profile>) {
    if (!profile) return;
    setSaving(true);
    setSaveError(null);
    try {
      const merged = applyProfilePatch(profile, p, {
        source: "user_edit",
        timestampIso: new Date().toISOString(),
      });
      const openQs = generateOpenQuestions(merged);
      const score = computeCompletenessScore(merged);
      await savePatch({
        ...p,
        dataQuality: {
          ...merged.dataQuality,
          missingFields: openQs.map((q) => ({
            fieldPath: q.fieldPath,
            question: q.question,
            priority: q.priority,
          })),
          completenessScore: score,
        },
      });
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
      <section className="space-y-3">
        <h2 className="text-xs font-medium tracking-widest uppercase text-muted-foreground">
          Account
        </h2>
        <div className="rounded-xl border border-border/50 bg-card/40 divide-y divide-border/40">
          <div className="flex items-center justify-between px-4 py-3">
            <span className="text-xs text-muted-foreground">Profile complete</span>
            <span className="text-sm text-foreground/85">
              {profile?.dataQuality?.completenessScore
                ? `${profile.dataQuality.completenessScore}%`
                : "—"}
            </span>
          </div>
        </div>
      </section>

      {/* ── Editable profile fields ── */}
      {profile && (
        <ProfileEditForm
          profile={profile}
          saving={saving}
          onChange={patch}
        />
      )}

      {/* ── Advisor summary ── */}
      <NextStepAction onOpen={() => setAdvisorModalOpen(true)} />

      <AdvisorSummaryModal
        open={advisorModalOpen}
        onClose={() => setAdvisorModalOpen(false)}
        profile={profile ?? null}
        threadId=""
        onDownload={(profileSnapshot, summaryText) => {
          downloadAdvisorPdf({
            profile: profileSnapshot,
            summaryText,
            generatedDate: new Date().toISOString().split("T")[0],
          });
          setAdvisorModalOpen(false);
        }}
      />
    </div>
  );
}
