import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/components/theme-provider";
import { ThemeToggle } from "@/components/theme-toggle";

export const metadata: Metadata = {
  title: "Ledger — AI Tax Advisor",
  description:
    "Intelligent tax and accounting guidance for digital nomads and remote professionals.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <head>
        {/* Prevent flash of wrong theme */}
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('theme');if(t==='light')document.documentElement.classList.remove('dark');else if(!t&&!matchMedia('(prefers-color-scheme: dark)').matches)document.documentElement.classList.remove('dark');else document.documentElement.classList.add('dark');}catch(e){}})()`,
          }}
        />
      </head>
      <body className="antialiased min-h-screen flex flex-col">
        <ThemeProvider>
          <TooltipProvider>
            <header className="sticky top-0 z-50 border-b border-border/40 bg-background/95 backdrop-blur-xl">
              <nav className="max-w-4xl mx-auto px-5 h-14 flex items-center justify-between">
                <Link
                  href="/"
                  className="flex items-center gap-2.5 group"
                  aria-label="Ledger home"
                >
                  {/* Diamond mark */}
                  <div className="size-6 rounded-sm bg-primary/12 border border-primary/25 flex items-center justify-center transition-colors group-hover:bg-primary/20">
                    <span
                      className="text-primary font-semibold leading-none"
                      style={{
                        fontFamily: "'Cormorant Garamond', serif",
                        fontSize: "14px",
                      }}
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
                  <Link
                    href="/chat"
                    className="px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors rounded-md hover:bg-accent tracking-wide"
                  >
                    Chat
                  </Link>
                  <Link
                    href="/intake"
                    className="px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors rounded-md hover:bg-accent tracking-wide"
                  >
                    Intake
                  </Link>
                  <Link
                    href="/profile"
                    className="px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors rounded-md hover:bg-accent tracking-wide"
                  >
                    Profile
                  </Link>
                  <ThemeToggle />
                </div>
              </nav>
            </header>
            <main className="flex-1 flex flex-col">{children}</main>
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
