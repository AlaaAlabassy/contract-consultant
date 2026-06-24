"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS: { href: string; label: string }[] = [
  { href: "/", label: "المحادثة" },
  { href: "/risk", label: "فحص المخاطر" },
];

export default function NavBar() {
  const pathname = usePathname();

  return (
    <nav className="flex items-center gap-1 border-b border-gray-200 bg-white px-4 py-2">
      <span className="ml-4 font-bold text-gray-900">مستشار العقود</span>
      {LINKS.map((link) => {
        const active = pathname === link.href;
        return (
          <Link
            key={link.href}
            href={link.href}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
              active ? "bg-blue-600 text-white" : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
