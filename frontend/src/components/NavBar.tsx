"use client";

import Link from "next/link";
import { useAuth } from "@/components/AuthProvider";
import { ThemeToggle } from "@/components/theme-toggle";

export function NavBar() {
  const { status, user, signOut } = useAuth();
  const isAuthed = status === "authenticated";

  return (
    <header className="sticky top-0 z-50 border-b border-border/40 bg-background/95 backdrop-blur-xl">
      <nav className="max-w-4xl mx-auto px-5 h-14 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5 group" aria-label="Ledger home">
          <div className="size-6 rounded-sm bg-primary/12 border border-primary/25 flex items-center justify-center transition-colors group-hover:bg-primary/20">
            <span
              className="text-primary font-semibold leading-none"
              style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: "14px" }}
            >
              L
            </span>
          </div>
          <span
            className="text-sm font-medium tracking-[0.06em] text-foreground/90 group-hover:text-foreground transition-colors"
            style={{ fontFamily: "'DM Sans', sans-serif" }}
          >
            LEDGER
          </span>
        </Link>

        <div className="flex items-center gap-1">
          {isAuthed ? (
            <>
              <span className="px-3 py-1.5 text-xs text-muted-foreground/70 max-w-[160px] truncate hidden sm:block">
                {user?.email}
              </span>
              <Link
                href="/chat"
                className="px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors rounded-md hover:bg-accent tracking-wide"
              >
                Chat
              </Link>
              <Link
                href="/profile"
                className="px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors rounded-md hover:bg-accent tracking-wide"
              >
                Profile
              </Link>
              <button
                type="button"
                onClick={signOut}
                className="px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors rounded-md hover:bg-accent tracking-wide"
              >
                Sign out
              </button>
            </>
          ) : (
            <Link
              href="/auth/sign-in"
              className="px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors rounded-md hover:bg-accent tracking-wide"
            >
              Sign in
            </Link>
          )}
          <ThemeToggle />
        </div>
      </nav>
    </header>
  );
}
