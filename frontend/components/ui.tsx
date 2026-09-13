import { ReactNode } from "react";
import Link from "next/link";

export function Card({
  children,
  className = "",
  photo = false,
}: {
  children: ReactNode;
  className?: string;
  photo?: boolean;
}) {
  if (photo) {
    return (
      <div className={`relative overflow-hidden rounded-xl border border-white/10 shadow-sm text-white ${className}`}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/images/hero-ocean.jpg"
          alt=""
          aria-hidden="true"
          className="absolute inset-0 w-full h-full object-cover object-bottom"
        />
        <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" />
        <div className="relative z-10 p-5">{children}</div>
      </div>
    );
  }
  return (
    <div
      className={`rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-white/5 p-5 shadow-sm ${className}`}
    >
      {children}
    </div>
  );
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return <h2 className="text-lg font-semibold mb-3">{children}</h2>;
}

export function PageTitle({ children, subtitle }: { children: ReactNode; subtitle?: string }) {
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-bold">{children}</h1>
      {subtitle && <p className="text-sm text-black/50 dark:text-white/50 mt-1">{subtitle}</p>}
    </div>
  );
}

export function Chip({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "good" | "bad" | "warn";
}) {
  const tones: Record<string, string> = {
    neutral: "bg-black/5 text-black/70 dark:bg-white/10 dark:text-white/70",
    good: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
    bad: "bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300",
    warn: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  };
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}

export function ScoreGauge({ label, value }: { label: string; value: number }) {
  const color = value >= 70 ? "#10b981" : value >= 45 ? "#f59e0b" : "#ef4444";
  return (
    <div className="flex flex-col items-center gap-2">
      <div
        className="relative w-28 h-28 rounded-full grid place-items-center"
        style={{
          background: `conic-gradient(${color} ${value * 3.6}deg, rgba(0,0,0,0.08) 0deg)`,
        }}
      >
        <div className="w-[86px] h-[86px] rounded-full bg-white dark:bg-neutral-900 grid place-items-center">
          <span className="text-2xl font-bold">{value}</span>
        </div>
      </div>
      <span className="text-sm text-black/60 dark:text-white/60">{label}</span>
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-black/15 dark:border-white/15 p-8 text-center text-sm text-black/50 dark:text-white/50">
      {children}
    </div>
  );
}

export function NoRunNotice() {
  return (
    <EmptyState>
      No run selected yet.{" "}
      <Link href="/input" className="underline font-medium">
        Start a pipeline run
      </Link>{" "}
      from the Input page first.
    </EmptyState>
  );
}
