"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { cognitoErrorMessage } from "@/lib/cognito";
import { getPostLoginRoute } from "@/lib/profileGate";

export default function SignInPage() {
  const { signIn, user, accessToken } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // After signIn() resolves, user+accessToken update in context. Route once both available.
  useEffect(() => {
    if (user && accessToken) {
      getPostLoginRoute(user.userId, accessToken).then((route) => {
        router.replace(route);
      });
    }
  }, [user, accessToken]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await signIn(email, password);
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
            Sign in
          </h1>
          <p className="text-xs text-muted-foreground">Welcome back to Ledger</p>
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
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-transparent border border-border/50 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary/50 transition-colors"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground">Password</label>
            <input
              type="password"
              required
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
            {loading ? "Signing in\u2026" : "Sign in"}
          </button>
        </form>

        <p className="text-center text-xs text-muted-foreground">
          No account?{" "}
          <Link href="/auth/sign-up" className="text-primary hover:underline">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}
