import type { ReactNode } from "react";

interface PlaceholderPageProps {
  title: string;
  children?: ReactNode;
}

export function PlaceholderPage({ title, children }: PlaceholderPageProps) {
  return (
    <section className="placeholder-page">
      <span className="eyebrow">ПРИЗМА Desktop</span>
      <h1>{title}</h1>
      {children ?? <p>Локальная конфигурация приложения.</p>}
    </section>
  );
}
