"use client";

import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import type { Profile } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ProfileEditForm } from "@/components/ProfileEditForm";

type Props = {
  open: boolean;
  onClose: () => void;
  profile: Profile | null;
  threadId: string;
  onDownload: (profileSnapshot: Partial<Profile>, summaryText: string) => void;
};

export function AdvisorSummaryModal({
  open,
  onClose,
  profile,
  threadId,
  onDownload,
}: Props) {
  const [localProfile, setLocalProfile] = useState<Profile | null>(profile);
  const [summaryText, setSummaryText] = useState("");
  const [summaryLoading, setSummaryLoading] = useState(false);

  // Re-initialise local state and fetch summary whenever the modal opens
  useEffect(() => {
    if (!open) return;
    setLocalProfile(profile);
    setSummaryText("");
    setSummaryLoading(true);

    fetch("/api/chat/summary", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ threadId }),
    })
      .then((r) => r.json())
      .then((data: { summary?: string; error?: string }) => {
        if (!data.error) setSummaryText(data.summary ?? "");
      })
      .catch(() => {/* fail silently — user can type their own notes */})
      .finally(() => setSummaryLoading(false));
  }, [open, profile, threadId]);

  function handleChange(patch: Partial<Profile>) {
    setLocalProfile((prev) => prev ? { ...prev, ...patch } : prev);
  }

  function handleDownload() {
    if (!localProfile) return;
    onDownload(localProfile, summaryText);
  }

  return (
    <Dialog open={open} onOpenChange={(isOpen) => { if (!isOpen) onClose(); }}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-xl [font-family:'Cormorant_Garamond',serif]">
            Prepare Summary for Advisor
          </DialogTitle>
          <DialogDescription>
            This summary contains the key details of your situation based on
            your profile and the discussion with the AI assistant. You can
            review and edit the information below before downloading it as a PDF
            to share with your accountant.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-6 mt-2">
          {/* Section 1 — editable profile fields */}
          {localProfile && (
            <ProfileEditForm
              profile={localProfile}
              onChange={handleChange}
            />
          )}

          {/* Section 2 — AI Summary */}
          <div className="rounded-xl border border-border/50 bg-card/40 px-5 py-4 flex flex-col gap-3">
            <label
              htmlFor="advisor-summary-textarea"
              className="text-xs font-medium tracking-widest uppercase text-muted-foreground"
            >
              Situation Summary
            </label>
            <Textarea
              id="advisor-summary-textarea"
              value={summaryText}
              onChange={(e) => setSummaryText(e.target.value)}
              placeholder={summaryLoading ? "Generating summary…" : "Add notes for your accountant…"}
              disabled={summaryLoading}
              rows={10}
              className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-sm text-foreground resize-y focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>
        </div>

        <DialogFooter className="mt-2">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="default"
            onClick={handleDownload}
            disabled={!localProfile}
            title={!localProfile ? "Profile required to download" : undefined}
          >
            Download PDF
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
