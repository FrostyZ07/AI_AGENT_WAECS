"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/brief", label: "Daily Brief" },
  { href: "/approvals", label: "Approvals" },
  { href: "/calendar", label: "Calendar & Requests" },
  { href: "/settings", label: "Settings" },
];

export default function Nav() {
  const pathname = usePathname();
  return (
    <nav className="flex gap-1 md:flex-col">
      {links.map((l) => (
        <Link
          key={l.href}
          href={l.href}
          className={`rounded px-3 py-2 text-sm ${
            pathname === l.href ? "bg-foreground text-background" : "hover:bg-black/5 dark:hover:bg-white/10"
          }`}
        >
          {l.label}
        </Link>
      ))}
    </nav>
  );
}
