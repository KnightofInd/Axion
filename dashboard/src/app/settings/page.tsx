"use client";

import { useState } from "react";

import { DashboardShell } from "@/components/DashboardShell";
import { SectionCard } from "@/components/SectionCard";
import { useAxionEmail } from "@/hooks/useAxionEmail";
import { getLatestRun, getOAuthUrl, triggerOrchestrator } from "@/lib/api";

export default function SettingsPage() {
  const { email, saveEmail } = useAxionEmail();
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  const runPipeline = async () => {
    if (!email) {
      setError("Set an email first.");
      return;
    }

    setError("");
    try {
      const response = await triggerOrchestrator(email, true, 2);
      setStatus(`Pipeline run ${response.run_id} is ${response.status}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to trigger orchestrator");
    }
  };

  const checkLatest = async () => {
    if (!email) {
      setError("Set an email first.");
      return;
    }

    setError("");
    try {
      const response = await getLatestRun(email);
      if (!response.exists) {
        setStatus("No run found for this user yet.");
        return;
      }
      setStatus(`Latest run status: ${String(response.run?.status || "unknown")}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to check run");
    }
  };

  const openOAuth = async () => {
    setError("");
    try {
      const response = await getOAuthUrl();
      window.open(response.authorization_url, "_blank", "noopener,noreferrer");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to open OAuth URL");
    }
  };

  return (
    <DashboardShell
      email={email}
      onEmailSave={saveEmail}
      title="Settings"
      subtitle="Connection, pipeline, and environment controls"
    >
      {error ? <p className="rounded-xl border border-rose-400/40 bg-rose-500/10 p-3 text-sm text-rose-200">{error}</p> : null}
      {status ? <p className="rounded-xl border border-emerald-400/40 bg-emerald-500/10 p-3 text-sm text-emerald-200">{status}</p> : null}

      <div className="grid gap-4 lg:grid-cols-3">
        <SectionCard title="Backend Base URL">
          <p className="text-sm text-axion-fg/90">{process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}</p>
        </SectionCard>

        <SectionCard title="Google OAuth">
          <button
            type="button"
            onClick={openOAuth}
            className="rounded-lg bg-axion-accent px-3 py-2 text-sm font-semibold text-slate-950 hover:brightness-105"
          >
            Open OAuth Flow
          </button>
        </SectionCard>

        <SectionCard title="Orchestrator">
          <div className="space-y-2">
            <button
              type="button"
              onClick={runPipeline}
              className="w-full rounded-lg border border-axion-border bg-white/5 px-3 py-2 text-sm text-axion-fg hover:bg-white/10"
            >
              Trigger Pipeline
            </button>
            <button
              type="button"
              onClick={checkLatest}
              className="w-full rounded-lg border border-axion-border bg-white/5 px-3 py-2 text-sm text-axion-fg hover:bg-white/10"
            >
              Check Latest Run
            </button>
          </div>
        </SectionCard>
      </div>
    </DashboardShell>
  );
}
