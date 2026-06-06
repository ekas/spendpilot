"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, User, Upload, X } from "lucide-react";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { loadStoredAnalysis } from "@/hooks/useAnalysis";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Application", icon: Upload },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/profile", label: "Profile", icon: User },
];

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "SP";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

interface SidebarProps {
  open?: boolean;
  onClose?: () => void;
  className?: string;
}

export function Sidebar({ open, onClose, className }: SidebarProps) {
  const pathname = usePathname();
  const [applicantName, setApplicantName] = useState("Guest");

  useEffect(() => {
    const analysis = loadStoredAnalysis();
    if (analysis?.applicantName) {
      setApplicantName(analysis.applicantName);
    }
  }, [pathname]);

  const content = (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between">
        <Link
          href="/"
          onClick={onClose}
          className="inline-block hover:opacity-80 transition"
        >
          <img
            src="/screen.png"
            alt="SpendPilot Logo"
            className="h-8 w-auto"
          />
        </Link>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground lg:hidden"
            aria-label="Close menu"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      <nav className="mt-10 flex flex-1 flex-col gap-2">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active =
            href === "/" ? pathname === "/" : pathname.startsWith(href);

          return (
            <Link
              key={href}
              href={href}
              onClick={onClose}
              className={cn(
                "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium transition-colors",
                active
                  ? "border-2 border-accent text-accent"
                  : "border-2 border-transparent text-foreground hover:bg-surface"
              )}
            >
              <Icon
                className={cn(
                  "h-5 w-5 shrink-0",
                  active ? "text-accent" : "text-foreground"
                )}
              />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto space-y-4 border-t border-border pt-4">
        <div className="flex items-center justify-between">
          <Link
            href="/profile"
            onClick={onClose}
            className="flex min-w-0 flex-1 items-center gap-3 rounded-xl p-1 transition-colors hover:bg-surface"
          >
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent-muted text-sm font-semibold text-accent">
              {getInitials(applicantName)}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-foreground">
                {applicantName}
              </p>
              <p className="text-xs text-muted-foreground">Applicant</p>
            </div>
          </Link>
          <ThemeToggle />
        </div>
      </div>
    </div>
  );

  return (
    <>
      <aside
        className={cn(
          "fixed inset-y-4 left-4 z-40 hidden w-60 flex-col rounded-2xl border border-border bg-card p-6 shadow-sm lg:flex",
          className
        )}
      >
        {content}
      </aside>

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-72 border-r border-border bg-card p-6 shadow-xl transition-transform duration-200 lg:hidden",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {content}
      </aside>

      {open && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-foreground/20 backdrop-blur-[1px] lg:hidden"
          onClick={onClose}
          aria-label="Close menu"
        />
      )}
    </>
  );
}
