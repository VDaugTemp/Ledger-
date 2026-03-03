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

type Options = {
  /** Pass userId from auth context to skip localStorage bootstrap. */
  userId?: string;
  /** Pass access token from auth context. */
  accessToken?: string;
};

export function useUserProfile(opts: Options = {}): UseUserProfileResult {
  const [userId, setUserId] = useState<string | null>(opts.userId ?? null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const token = opts.accessToken;

  const fetchProfile = useCallback(
    async (uid: string) => {
      const { profile: fetched } = await getUser(uid, token);
      setProfile(fetched);
    },
    [token],
  );

  const bootstrap = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (opts.userId) {
        // Real auth mode: userId provided externally
        setUserId(opts.userId);
        await fetchProfile(opts.userId);
      } else {
        // Mock mode: manage userId via localStorage
        let uid = getStoredUserId();
        if (!uid) {
          const { userId: newId } = await createUser(undefined, token);
          storeUserId(newId);
          uid = newId;
        }
        setUserId(uid);
        await fetchProfile(uid);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load profile");
    } finally {
      setLoading(false);
    }
  }, [opts.userId, token, fetchProfile]); // eslint-disable-line react-hooks/exhaustive-deps

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
      setError(err instanceof Error ? err.message : "Failed to refresh");
    } finally {
      setLoading(false);
    }
  }, [userId, fetchProfile]);

  const savePatch = useCallback(
    async (patch: Partial<Profile>) => {
      if (!userId) return;
      setError(null);
      try {
        const { profile: updated } = await patchProfile(userId, patch, token);
        setProfile(updated);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to save");
        throw err;
      }
    },
    [userId, token],
  );

  return { userId, profile, loading, error, savePatch, refresh };
}
