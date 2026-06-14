"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export interface NavItem {
  label: string;
  href: string;
}

export const NAV_ITEMS: NavItem[] = [
  { label: "研究入口", href: "/" },
  { label: "ETF 明細", href: "/etf" },
  { label: "ETF 比較", href: "/compare" },
  { label: "配息排行", href: "/dividends" },
  { label: "組合建構", href: "/portfolio" },
  { label: "回測", href: "/backtest" },
  { label: "財務推算", href: "/projection" },
  { label: "資料來源", href: "/data-sources" },
  { label: "AI 助理", href: "/ai" },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export default function SideNav() {
  const pathname = usePathname();

  return (
    <nav className="flex h-full w-16 flex-col gap-space-1 border-r border-border-subtle bg-bg-surface px-space-2 py-space-4 lg:w-[220px] lg:px-space-3">
      {NAV_ITEMS.map((item) => {
        const active = isActive(pathname, item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            title={item.label}
            className={`flex items-center gap-space-2 truncate rounded-sm px-space-2 py-space-2 text-body transition-colors ${
              active
                ? "bg-accent-primary/10 text-accent-primary"
                : "text-text-secondary hover:bg-bg-surface-raised hover:text-text-primary"
            }`}
          >
            <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-sm border border-current text-small">
              {item.label.slice(0, 1)}
            </span>
            <span className="hidden truncate lg:inline">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
