"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/input", label: "Input" },
  { href: "/add-resume", label: "Add Resume" },
  { href: "/evaluation", label: "Evaluation" },
  { href: "/report", label: "Final Report" },
  { href: "/history", label: "History" },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <nav className="relative overflow-hidden border-b border-white/10 sticky top-0 z-10">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src="/images/hero-ocean.jpg"
        alt=""
        aria-hidden="true"
        className="absolute inset-0 w-full h-full object-cover"
      />
      <div className="absolute inset-0 bg-slate-950/75 backdrop-blur-sm" />
      <div className="relative z-10 max-w-6xl mx-auto px-4 py-3 flex items-center gap-1 overflow-x-auto">
        {LINKS.map((link) => {
          const active = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`text-sm px-2.5 py-1 rounded-md whitespace-nowrap transition-colors ${
                active
                  ? "bg-white text-black"
                  : "text-white/70 hover:bg-white/10"
              }`}
            >
              {link.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
