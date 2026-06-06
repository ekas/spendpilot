import { cn } from "@/lib/utils";
import type { AgentStatus } from "@/lib/types";

const statusConfig: Record<
  AgentStatus,
  { color: string; label: string; pulse?: boolean }
> = {
  idle: { color: "bg-muted-foreground/50", label: "Idle" },
  processing: { color: "bg-accent", label: "Processing", pulse: true },
  complete: { color: "bg-emerald-500", label: "Complete" },
  error: { color: "bg-red-500", label: "Error" },
  waiting: { color: "bg-amber-500", label: "Waiting", pulse: true },
};

export function StatusIndicator({
  status,
  showLabel = false,
  size = "sm",
}: {
  status: AgentStatus;
  showLabel?: boolean;
  size?: "sm" | "md";
}) {
  const config = statusConfig[status];

  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="relative flex">
        <span
          className={cn(
            "rounded-full",
            size === "sm" ? "h-2 w-2" : "h-2.5 w-2.5",
            config.color
          )}
        />
        {config.pulse && (
          <span
            className={cn(
              "absolute inline-flex h-full w-full animate-ping rounded-full opacity-75",
              config.color
            )}
          />
        )}
      </span>
      {showLabel && (
        <span className="text-xs text-muted-foreground">{config.label}</span>
      )}
    </span>
  );
}
