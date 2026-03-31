"use client";

import { useCallback, useEffect, useState } from "react";

import { DashboardShell } from "@/components/DashboardShell";
import { SectionCard } from "@/components/SectionCard";
import { useAxionEmail } from "@/hooks/useAxionEmail";
import { getSidebarOverview, listOverdueCommitments } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { Commitment } from "@/lib/types";

export default function CommitmentsPage() {
  const { email, saveEmail } = useAxionEmail();
  const [tab, setTab] = useState<"i_owe" | "they_owe">("i_owe");
  const [items, setItems] = useState<Commitment[]>([]);
  const [overdueCount, setOverdueCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadCommitments = useCallback(async () => {
    if (!email) {
      setItems([]);
      setOverdueCount(0);
      return;
    }

    setLoading(true);
    setError("");
    try {
      const [overview, overdue] = await Promise.all([
        getSidebarOverview(email, tab),
        listOverdueCommitments(email),
      ]);
      setItems(overview.commitments.selected_items);
      setOverdueCount(overdue.count);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load commitments");
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [email, tab]);

  useEffect(() => {
    void loadCommitments();
  }, [loadCommitments]);

  return (
    <DashboardShell
      email={email}
      onEmailSave={saveEmail}
      title="Commitments"
      subtitle="Track what you owe and what others owe you"
      actions={
        <button
          type="button"
          onClick={loadCommitments}
          className="rounded-lg border border-axion-border bg-white/5 px-3 py-2 text-sm text-axion-fg hover:bg-white/10"
        >
          Refresh
        </button>
      }
    >
      {error ? <p className="rounded-xl border border-rose-400/40 bg-rose-500/10 p-3 text-sm text-rose-200">{error}</p> : null}
      <div className="grid gap-4 lg:grid-cols-[1fr_280px]">
        <SectionCard title="Commitment Ledger" subtitle={loading ? "Loading..." : `${items.length} items in this tab`}>
          <div className="mb-3 flex gap-2">
            <button
              type="button"
              onClick={() => setTab("i_owe")}
              className={`rounded-md px-2 py-1 text-xs ${tab === "i_owe" ? "bg-axion-accent text-slate-950" : "bg-white/10 text-axion-fg"}`}
            >
              I Owe
            </button>
            <button
              type="button"
              onClick={() => setTab("they_owe")}
              className={`rounded-md px-2 py-1 text-xs ${tab === "they_owe" ? "bg-axion-accent text-slate-950" : "bg-white/10 text-axion-fg"}`}
            >
              They Owe
            </button>
          </div>
          <ul className="space-y-2">
            {items.length === 0 && !loading ? <li className="text-sm text-axion-muted">No commitments in this view.</li> : null}
            {items.map((item) => (
              <li key={item.id} className="rounded-lg border border-axion-border bg-black/20 p-3 text-sm">
                <p className="text-white">{item.text}</p>
                <p className="text-xs text-axion-muted">Due {formatDateTime(item.due_at)} | {item.status}</p>
              </li>
            ))}
          </ul>
        </SectionCard>

        <SectionCard title="Risk Snapshot" subtitle="Auto-overdue count">
          <p className="text-4xl font-semibold text-white">{overdueCount}</p>
          <p className="mt-1 text-sm text-axion-muted">commitments currently overdue</p>
        </SectionCard>
      </div>
    </DashboardShell>
  );
}
