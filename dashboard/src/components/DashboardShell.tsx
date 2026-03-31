"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FormEvent, ReactNode, useMemo, useState } from "react";

import { getOAuthUrl } from "@/lib/api";

type ShellProps = {
  email: string;
  onEmailSave: (email: string) => void;
  title: string;
  subtitle: string;
  actions?: ReactNode;
  children: ReactNode;
};

const navItems = [
  { href: "/", label: "Overview" },
  { href: "/tasks", label: "Tasks" },
  { href: "/calendar", label: "Calendar" },
  { href: "/commitments", label: "Commitments" },
  { href: "/ask", label: "Ask AXION" },
  { href: "/settings", label: "Settings" },
];

export function DashboardShell({ email, onEmailSave, title, subtitle, actions, children }: ShellProps) {
  const pathname = usePathname();
  const [pendingEmail, setPendingEmail] = useState(email);
  const [oauthPending, setOauthPending] = useState(false);

  const activePath = useMemo(() => pathname || "/", [pathname]);

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onEmailSave(pendingEmail);
  };

  const connectGoogle = async () => {
    setOauthPending(true);
    try {
      const response = await getOAuthUrl();
      window.open(response.authorization_url, "_blank", "noopener,noreferrer");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to get OAuth URL";
      window.alert(message);
    } finally {
      setOauthPending(false);
    }
  };

  return (
    <div className="min-h-screen bg-axion-bg text-axion-fg">
      <div className="pointer-events-none fixed inset-0 bg-axion-atmosphere opacity-70" />
      <div className="relative mx-auto grid min-h-screen max-w-7xl gap-6 px-4 py-6 md:grid-cols-[250px_1fr] md:px-6">
        <aside className="rounded-2xl border border-axion-border bg-axion-panel/85 p-4 backdrop-blur">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-axion-muted">AXION Control</p>
          <nav className="mt-4 space-y-2">
            {navItems.map((item) => {
              const active = activePath === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`block rounded-xl px-3 py-2 text-sm transition ${
                    active
                      ? "bg-axion-accent text-slate-950"
                      : "bg-white/0 text-axion-fg/90 hover:bg-white/10 hover:text-white"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <form onSubmit={onSubmit} className="mt-6 space-y-2 rounded-xl border border-axion-border bg-black/20 p-3">
            <label htmlFor="axion-email" className="text-xs uppercase tracking-[0.14em] text-axion-muted">
              Connected Email
            </label>
            <input
              id="axion-email"
              value={pendingEmail}
              onChange={(event) => setPendingEmail(event.target.value)}
              placeholder="you@company.com"
              className="w-full rounded-lg border border-axion-border bg-slate-950/80 px-3 py-2 text-sm outline-none ring-0 focus:border-axion-accent"
            />
            <button
              type="submit"
              className="w-full rounded-lg bg-axion-accent px-3 py-2 text-sm font-semibold text-slate-950 transition hover:brightness-105"
            >
              Save Email
            </button>
            <button
              type="button"
              onClick={connectGoogle}
              disabled={oauthPending}
              className="w-full rounded-lg border border-axion-border bg-white/5 px-3 py-2 text-sm text-axion-fg transition hover:bg-white/10 disabled:opacity-60"
            >
              {oauthPending ? "Opening OAuth..." : "Connect Google"}
            </button>
          </form>
        </aside>

        <main className="space-y-4">
          <header className="rounded-2xl border border-axion-border bg-axion-panel/85 p-5 backdrop-blur">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h1 className="text-2xl font-semibold text-white">{title}</h1>
                <p className="mt-1 text-sm text-axion-muted">{subtitle}</p>
              </div>
              {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
            </div>
          </header>
          <section>{children}</section>
        </main>
      </div>
    </div>
  );
}
