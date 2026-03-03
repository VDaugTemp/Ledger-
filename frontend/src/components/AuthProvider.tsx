// src/components/AuthProvider.tsx
"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  signUp as cognitoSignUp,
  confirmSignUp as cognitoConfirmSignUp,
  signIn as cognitoSignIn,
  refreshSession,
  decodeJwtPayload,
  type CognitoTokens,
} from "@/lib/cognito";

// ── types ────────────────────────────────────────────────────────────────────

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

export type AuthUser = {
  userId: string; // Cognito sub
  email: string;
};

export type AuthContextValue = {
  status: AuthStatus;
  user: AuthUser | null;
  accessToken: string | null; // in memory only — do not display in UI
  signUp: (email: string, password: string) => Promise<void>;
  confirmSignUp: (email: string, code: string) => Promise<void>;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
  refreshAccessToken: () => Promise<string | null>;
};

// ── storage ──────────────────────────────────────────────────────────────────

const REFRESH_TOKEN_KEY = "ns_tax_app:refresh_token";

function storeRefreshToken(token: string) {
  localStorage.setItem(REFRESH_TOKEN_KEY, token);
}

function getStoredRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

function clearStoredRefreshToken() {
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

// ── context ──────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue | null>(null);

const REFRESH_INTERVAL_MS = 10 * 60 * 1000; // 10 minutes

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const refreshTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  function applyTokens(tokens: CognitoTokens) {
    const payload = decodeJwtPayload(tokens.idToken);
    setUser({ userId: payload.sub, email: String(payload.email ?? "") });
    setAccessToken(tokens.accessToken);
    setStatus("authenticated");
    storeRefreshToken(tokens.refreshToken);
  }

  function clearSession() {
    setUser(null);
    setAccessToken(null);
    setStatus("unauthenticated");
    clearStoredRefreshToken();
    if (refreshTimerRef.current) clearInterval(refreshTimerRef.current);
  }

  const refreshAccessToken = useCallback(async (): Promise<string | null> => {
    const storedRefresh = getStoredRefreshToken();
    if (!storedRefresh) {
      clearSession();
      return null;
    }
    try {
      const refreshed = await refreshSession(storedRefresh);
      const payload = decodeJwtPayload(refreshed.idToken);
      setUser({ userId: payload.sub, email: String(payload.email ?? "") });
      setAccessToken(refreshed.accessToken);
      setStatus("authenticated");
      return refreshed.accessToken;
    } catch {
      clearSession();
      return null;
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function startRefreshTimer() {
    if (refreshTimerRef.current) clearInterval(refreshTimerRef.current);
    refreshTimerRef.current = setInterval(() => {
      refreshAccessToken();
    }, REFRESH_INTERVAL_MS);
  }

  // On mount: try to restore session from localStorage refresh token
  useEffect(() => {
    const storedRefresh = getStoredRefreshToken();
    if (!storedRefresh) {
      setStatus("unauthenticated");
      return;
    }
    refreshAccessToken().then((token) => {
      if (token) startRefreshTimer();
    });
    return () => {
      if (refreshTimerRef.current) clearInterval(refreshTimerRef.current);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const signUp = useCallback(async (email: string, password: string) => {
    await cognitoSignUp(email, password);
  }, []);

  const confirmSignUp = useCallback(async (email: string, code: string) => {
    await cognitoConfirmSignUp(email, code);
  }, []);

  const signIn = useCallback(
    async (email: string, password: string) => {
      const tokens = await cognitoSignIn(email, password);
      applyTokens(tokens);
      startRefreshTimer();
    },
    [], // eslint-disable-line react-hooks/exhaustive-deps
  );

  const signOut = useCallback(() => {
    clearSession();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <AuthContext.Provider
      value={{
        status,
        user,
        accessToken,
        signUp,
        confirmSignUp,
        signIn,
        signOut,
        refreshAccessToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
