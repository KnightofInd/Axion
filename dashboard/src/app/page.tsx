export default function Home() {
  return (
    <main className="min-h-screen px-6 py-10 md:px-10">
      <div className="mx-auto max-w-5xl space-y-8">
        <section className="rounded-2xl border border-slate-800 bg-slate-950/80 p-6 md:p-8">
          <p className="text-xs uppercase tracking-[0.2em] text-sky-300">Phase 1</p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-100 md:text-4xl">
            AXION Foundation Is Ready
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-6 text-slate-300 md:text-base">
            Backend and dashboard scaffolds are in place. Next step is wiring Google OAuth and
            Supabase credentials to run live Gmail and Calendar integration checks.
          </p>
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5">
            <p className="text-xs uppercase tracking-wider text-slate-400">Backend</p>
            <p className="mt-2 text-lg font-semibold text-slate-100">FastAPI</p>
            <p className="mt-2 text-sm text-slate-300">Health endpoints + integration stubs created.</p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5">
            <p className="text-xs uppercase tracking-wider text-slate-400">Database</p>
            <p className="mt-2 text-lg font-semibold text-slate-100">Supabase + pgvector</p>
            <p className="mt-2 text-sm text-slate-300">users, tasks, commitments, briefings schema ready.</p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5">
            <p className="text-xs uppercase tracking-wider text-slate-400">Frontend</p>
            <p className="mt-2 text-lg font-semibold text-slate-100">Next.js 14</p>
            <p className="mt-2 text-sm text-slate-300">Tailwind + key libraries installed for next phases.</p>
          </div>
        </section>

        <section className="rounded-2xl border border-sky-800/60 bg-sky-950/30 p-6">
          <h2 className="text-lg font-semibold text-sky-100">Quick Check URLs</h2>
          <ul className="mt-3 space-y-2 text-sm text-sky-50/90">
            <li>FastAPI health: http://localhost:8000/health</li>
            <li>API health: http://localhost:8000/api/v1/system/health</li>
            <li>OAuth URL: http://localhost:8000/api/v1/auth/google/url</li>
          </ul>
        </section>
      </div>
    </main>
  );
}
