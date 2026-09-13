"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Input" },
  { href: "/add-resume", label: "Add Resume" },
  { href: "/evaluation", label: "Evaluation" },
  { href: "/report", label: "Final Report" },
  { href: "/history", label: "History" },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <nav className="border-b border-black/10 dark:border-white/10 bg-white/80 dark:bg-black/40 backdrop-blur sticky top-0 z-10">
      <div className="max-w-6xl mx-auto px-4 py-2.5 flex items-center gap-1 overflow-x-auto">
        <span className="font-semibold text-sm mr-3 whitespace-nowrap">Resume Agent</span>
        {LINKS.map((link) => {
          const active = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`text-sm px-2.5 py-1 rounded-md whitespace-nowrap transition-colors ${
                active
                  ? "bg-black text-white dark:bg-white dark:text-black"
                  : "text-black/60 dark:text-white/60 hover:bg-black/5 dark:hover:bg-white/10"
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
