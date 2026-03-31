import { ReactNode } from "react";

type SectionCardProps = {
  title: string;
  subtitle?: string;
  children: ReactNode;
};

export function SectionCard({ title, subtitle, children }: SectionCardProps) {
  return (
    <article className="rounded-2xl border border-axion-border bg-axion-panel/85 p-4 backdrop-blur">
      <header className="mb-3">
        <h2 className="text-base font-semibold text-white">{title}</h2>
        {subtitle ? <p className="mt-1 text-sm text-axion-muted">{subtitle}</p> : null}
      </header>
      {children}
    </article>
  );
}
