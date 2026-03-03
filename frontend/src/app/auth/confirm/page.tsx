"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { cognitoErrorMessage } from "@/lib/cognito";
import { getPostLoginRoute } from "@/lib/profileGate";

function ConfirmPageContent() {
  const { confirmSignUp, signIn, user, accessToken } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState(searchParams.get("email") ?? "");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [confirmed, setConfirmed] = useState(false);

  // Route after auto sign-in succeeds
  useEffect(() => {
    if (confirmed && user && accessToken) {
      getPostLoginRoute(user.userId, accessToken).then((route) => {
        router.replace(route);
      });
    }
  }, [confirmed, user, accessToken]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await confirmSignUp(email, code);
      if (password) {
        await signIn(email, password);
        setConfirmed(true);
      } else {
        router.replace("/auth/sign-in");
      }
    } catch (err) {
      setError(cognitoErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex-1 flex items-center justify-center px-5">
      <div className="w-full max-w-sm space-y-6">
        <div className="space-y-1 text-center">
          <h1
            className="text-2xl font-normal"
            style={{ fontFamily: "'Cormorant Garamond', serif" }}
          >
            Verify email
          </h1>
          <p className="text-xs text-muted-foreground">
            Enter the code we sent to your email.
          </p>
        </div>

        {error && (
          <div className="px-4 py-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-transparent border border-border/50 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary/50 transition-colors"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground">Verification code</label>
            <input
              type="text"
              required
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="123456"
              className="w-full bg-transparent border border-border/50 rounded-lg px-3 py-2 text-sm font-mono tracking-widest focus:outline-none focus:border-primary/50 transition-colors"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground">
              Password{" "}
              <span className="text-muted-foreground/50">(for auto sign-in)</span>
            </label>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-transparent border border-border/50 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary/50 transition-colors"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-primary text-primary-foreground rounded-xl text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {loading ? "Verifying\u2026" : "Verify and sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function ConfirmPage() {
  return (
    <Suspense
      fallback={
        <div className="flex-1 flex items-center justify-center">
          <div className="size-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
        </div>
      }
    >
      <ConfirmPageContent />
    </Suspense>
  );
}
