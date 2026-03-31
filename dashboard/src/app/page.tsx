"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { DashboardShell } from "@/components/DashboardShell";
import { SectionCard } from "@/components/SectionCard";
import { useAxionEmail } from "@/hooks/useAxionEmail";
import { formatDateTime } from "@/lib/format";
import { getSidebarOverview, runSidebarSync } from "@/lib/api";
import type { SidebarOverview } from "@/lib/types";

export default function Home() {
  const { email, saveEmail } = useAxionEmail();
  const [tab, setTab] = useState<"i_owe" | "they_owe">("i_owe");
  const [overview, setOverview] = useState<SidebarOverview | null>(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState("");

  const loadOverview = useCallback(async () => {
    if (!email) {
      setOverview(null);
      return;
    }

    setLoading(true);
    setError("");
    try {
      const data = await getSidebarOverview(email, tab);
      setOverview(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load overview");
      setOverview(null);
    } finally {
      setLoading(false);
    }
  }, [email, tab]);

  useEffect(() => {
    void loadOverview();
  }, [loadOverview]);

  const onSync = async () => {
    if (!email) {
      setError("Set an email first.");
      return;
    }

    setSyncing(true);
    setError("");
    try {
      const result = await runSidebarSync(email, true);
      setOverview(result.overview);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  const selectedCommitments = useMemo(() => {
    return overview?.commitments.selected_items ?? [];
  }, [overview]);

  return (
    <DashboardShell
      email={email}
      onEmailSave={saveEmail}
      title="Overview"
      subtitle="Live command center for your priorities, commitments, and focus blocks"
      actions={
        <>
          <button
            type="button"
            onClick={loadOverview}
            className="rounded-lg border border-axion-border bg-white/5 px-3 py-2 text-sm text-axion-fg hover:bg-white/10"
          >
            Refresh
          </button>
          <button
            type="button"
            onClick={onSync}
            disabled={syncing}
            className="rounded-lg bg-axion-accent px-3 py-2 text-sm font-semibold text-slate-950 hover:brightness-105 disabled:opacity-60"
          >
            {syncing ? "Syncing..." : "Run Full Sync"}
          </button>
        </>
      }
    >
      {error ? <p className="rounded-xl border border-rose-400/40 bg-rose-500/10 p-3 text-sm text-rose-200">{error}</p> : null}

      {!email ? <p className="rounded-xl border border-amber-400/30 bg-amber-500/10 p-3 text-sm text-amber-100">Set your connected email to load dashboard data.</p> : null}

      {loading ? <p className="text-sm text-axion-muted">Loading dashboard data...</p> : null}

      {overview ? (
        <div className="grid gap-4 lg:grid-cols-3">
          <SectionCard title="Briefing" subtitle={`Updated ${formatDateTime(overview.generated_at)}`}>
            <p className="text-sm leading-6 text-axion-fg/90">{overview.briefing?.text || "No briefing yet."}</p>
          </SectionCard>

          <SectionCard title="Mission Stats" subtitle="Current active workload">
            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="rounded-lg border border-axion-border bg-black/20 p-2">
                <p className="text-xs text-axion-muted">Tasks</p>
                <p className="text-xl font-semibold text-white">{overview.stats.tasks}</p>
              </div>
              <div className="rounded-lg border border-axion-border bg-black/20 p-2">
                <p className="text-xs text-axion-muted">Focus</p>
                <p className="text-xl font-semibold text-white">{overview.stats.focus_blocks}</p>
              </div>
              <div className="rounded-lg border border-axion-border bg-black/20 p-2">
                <p className="text-xs text-axion-muted">Commitments</p>
                <p className="text-xl font-semibold text-white">{overview.stats.commitments}</p>
              </div>
            </div>
          </SectionCard>

          <SectionCard title="Next Slot" subtitle="Best next free time from latest run">
            <p className="text-sm text-axion-fg/90">{formatDateTime(overview.calendar.next_free_slot)}</p>
            <p className="mt-2 text-xs text-axion-muted">Latest run: {overview.latest_run?.status || "none"}</p>
          </SectionCard>

          <SectionCard title="Priority Tasks" subtitle="Top pending tasks by score">
            <ul className="space-y-2">
              {overview.priority_tasks.length === 0 ? <li className="text-sm text-axion-muted">No pending priorities.</li> : null}
              {overview.priority_tasks.map((task) => (
                <li key={task.id} className="rounded-lg border border-axion-border bg-black/20 p-2 text-sm">
                  <p className="font-medium text-white">{task.title}</p>
                  <p className="text-xs text-axion-muted">P{task.priority} | {task.status} | Score {task.computed_score ?? "-"}</p>
                </li>
              ))}
            </ul>
          </SectionCard>

          <SectionCard title="Commitments" subtitle="Switch between what you owe and what they owe">
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
              {selectedCommitments.length === 0 ? <li className="text-sm text-axion-muted">No tracked items.</li> : null}
              {selectedCommitments.map((item) => (
                <li key={item.id} className="rounded-lg border border-axion-border bg-black/20 p-2 text-sm">
                  <p className="text-white">{item.text}</p>
                  <p className="text-xs text-axion-muted">Due {formatDateTime(item.due_at)} | {item.status}</p>
                </li>
              ))}
            </ul>
          </SectionCard>

          <SectionCard title="Focus Blocks" subtitle="Blocks proposed or scheduled by orchestrator">
            <ul className="space-y-2">
              {overview.calendar.focus_blocks.length === 0 ? <li className="text-sm text-axion-muted">No focus blocks yet.</li> : null}
              {overview.calendar.focus_blocks.map((block, index) => (
                <li key={`${index}-${String(block.start || "slot")}`} className="rounded-lg border border-axion-border bg-black/20 p-2 text-sm">
                  <p className="text-white">{String(block.summary || "Focus Block")}</p>
                  <p className="text-xs text-axion-muted">
                    {formatDateTime(String(block.start || ""))} to {formatDateTime(String(block.end || ""))}
                  </p>
                </li>
              ))}
            </ul>
          </SectionCard>
        </div>
      ) : null}
    </DashboardShell>
  );
}
