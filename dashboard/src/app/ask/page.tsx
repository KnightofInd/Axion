"use client";

import { FormEvent, useState } from "react";

import { DashboardShell } from "@/components/DashboardShell";
import { SectionCard } from "@/components/SectionCard";
import { useAxionEmail } from "@/hooks/useAxionEmail";
import { askSidebar } from "@/lib/api";

export default function AskPage() {
  const { email, saveEmail } = useAxionEmail();
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [mode, setMode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!email) {
      setError("Set an email first.");
      return;
    }

    if (!question.trim()) {
      setError("Enter a question.");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const response = await askSidebar(email, question.trim());
      setAnswer(response.answer);
      setMode(response.mode);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to ask AXION");
    } finally {
      setLoading(false);
    }
  };

  return (
    <DashboardShell
      email={email}
      onEmailSave={saveEmail}
      title="Ask AXION"
      subtitle="Query your current tasks, calendar slots, and commitments"
    >
      {error ? <p className="rounded-xl border border-rose-400/40 bg-rose-500/10 p-3 text-sm text-rose-200">{error}</p> : null}
      <div className="grid gap-4 lg:grid-cols-2">
        <SectionCard title="Question" subtitle="Ask in natural language">
          <form className="space-y-2" onSubmit={onSubmit}>
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              rows={5}
              placeholder="What are my top commitments this week?"
              className="w-full rounded-lg border border-axion-border bg-slate-950/80 px-3 py-2 text-sm"
            />
            <button
              type="submit"
              disabled={loading}
              className="rounded-lg bg-axion-accent px-3 py-2 text-sm font-semibold text-slate-950 hover:brightness-105 disabled:opacity-60"
            >
              {loading ? "Thinking..." : "Ask"}
            </button>
          </form>
        </SectionCard>

        <SectionCard title="Answer" subtitle={mode ? `Mode: ${mode}` : "No answer yet"}>
          <p className="text-sm leading-6 text-axion-fg/90">{answer || "AXION answer will appear here."}</p>
        </SectionCard>
      </div>
    </DashboardShell>
  );
}
