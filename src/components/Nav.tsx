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
    <nav className="flex gap-1 overflow-x-auto md:flex-col md:overflow-visible">
      {links.map((l) => {
        const active = pathname === l.href;
        return (
          <Link
            key={l.href}
            href={l.href}
            aria-current={active ? "page" : undefined}
            className={`whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition ${
              active ? "bg-accent/10 text-accent" : "text-muted hover:bg-background hover:text-foreground"
            }`}
          >
            {l.label}
          </Link>
        );
      })}
    </nav>
  );
}
