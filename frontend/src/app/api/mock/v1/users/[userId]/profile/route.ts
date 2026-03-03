import { NextResponse } from "next/server";
import { users, profiles, makeDefaultProfile, persistStore } from "../../../../_store";
import type { Profile } from "@/lib/types";

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ userId: string }> },
) {
  const { userId } = await params;

  const body = await request.json().catch(() => ({}));
  const profilePatch: Partial<Profile> = body.profilePatch ?? {};

  // Ensure user exists
  if (!users.has(userId)) {
    users.set(userId, { userId, createdAt: new Date().toISOString() });
  }

  const existing = profiles.get(userId) ?? makeDefaultProfile();

  // Shallow merge top-level; deep merge known sub-objects
  const updated: Profile = {
    ...existing,
    ...profilePatch,
    // Always increment version and timestamp
    profileVersion: existing.profileVersion + 1,
    updatedAt: new Date().toISOString(),
    // Deep merge nested objects
    presence: profilePatch.presence
      ? { ...existing.presence, ...profilePatch.presence }
      : existing.presence,
    incomeTypes: profilePatch.incomeTypes
      ? { ...existing.incomeTypes, ...profilePatch.incomeTypes }
      : existing.incomeTypes,
    advisorContext: profilePatch.advisorContext
      ? { ...existing.advisorContext, ...profilePatch.advisorContext }
      : existing.advisorContext,
    dataQuality: profilePatch.dataQuality
      ? { ...existing.dataQuality, ...profilePatch.dataQuality }
      : existing.dataQuality,
  };

  profiles.set(userId, updated);
  persistStore();

  return NextResponse.json({ profile: updated });
}
