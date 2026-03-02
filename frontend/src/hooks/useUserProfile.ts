"use client";

import { useState, useEffect, useCallback } from "react";
import { createUser, getUser, patchProfile } from "@/lib/userApi";
import type { Profile } from "@/lib/types";

const USER_ID_KEY = "ns_tax_app:user_id";

function getStoredUserId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(USER_ID_KEY);
}

function storeUserId(userId: string) {
  localStorage.setItem(USER_ID_KEY, userId);
}

export type UseUserProfileResult = {
  userId: string | null;
  profile: Profile | null;
  loading: boolean;
  error: string | null;
  savePatch: (patch: Partial<Profile>) => Promise<void>;
  refresh: () => Promise<void>;
};

export function useUserProfile(): UseUserProfileResult {
  const [userId, setUserId] = useState<string | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProfile = useCallback(async (uid: string) => {
    const { profile: fetched } = await getUser(uid);
    setProfile(fetched);
  }, []);

  const bootstrap = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      let uid = getStoredUserId();
      if (!uid) {
        const { userId: newId } = await createUser();
        storeUserId(newId);
        uid = newId;
      }
      setUserId(uid);
      await fetchProfile(uid);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load profile");
    } finally {
      setLoading(false);
    }
  }, [fetchProfile]);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  const refresh = useCallback(async () => {
    if (!userId) return;
    setLoading(true);
    setError(null);
    try {
      await fetchProfile(userId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh profile");
    } finally {
      setLoading(false);
    }
  }, [userId, fetchProfile]);

  const savePatch = useCallback(
    async (patch: Partial<Profile>) => {
      if (!userId) return;
      setError(null);
      try {
        const { profile: updated } = await patchProfile(userId, patch);
        setProfile(updated);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to save profile");
        throw err;
      }
    },
    [userId],
  );

  return { userId, profile, loading, error, savePatch, refresh };
}
