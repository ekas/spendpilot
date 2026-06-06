import { cn } from "@/lib/utils";
import type { RiskLevel } from "@/lib/types";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "success" | "warning" | "danger" | "info" | "muted";
  size?: "sm" | "md";
  className?: string;
}

const variants = {
  default: "bg-muted text-foreground border-border",
  success:
    "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30",
  warning:
    "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/30",
  danger: "bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/30",
  info: "bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/30",
  muted: "bg-muted/60 text-muted-foreground border-border-subtle",
};

export function Badge({
  children,
  variant = "default",
  size = "sm",
  className,
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border font-medium",
        size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-sm",
        variants[variant],
        className
      )}
    >
      {children}
    </span>
  );
}

export function RiskBadge({ level }: { level: RiskLevel }) {
  const variantMap: Record<RiskLevel, BadgeProps["variant"]> = {
    low: "success",
    medium: "warning",
    high: "danger",
    critical: "danger",
  };
  return (
    <Badge variant={variantMap[level]}>
      {level.charAt(0).toUpperCase() + level.slice(1)} Risk
    </Badge>
  );
}
