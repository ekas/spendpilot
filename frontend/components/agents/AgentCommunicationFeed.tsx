import { MessageSquare, AlertTriangle, HelpCircle, CheckCircle2 } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { cn, formatDate, getAgentColor, getAgentLabel } from "@/lib/utils";
import type { AgentMessage } from "@/lib/types";

const typeConfig = {
  analysis: { icon: MessageSquare, variant: "info" as const, label: "Analysis" },
  question: { icon: HelpCircle, variant: "warning" as const, label: "Question" },
  response: { icon: MessageSquare, variant: "success" as const, label: "Response" },
  conflict: { icon: AlertTriangle, variant: "danger" as const, label: "Conflict" },
  resolution: { icon: CheckCircle2, variant: "success" as const, label: "Resolution" },
};

interface AgentCommunicationFeedProps {
  messages: AgentMessage[];
}

export function AgentCommunicationFeed({ messages }: AgentCommunicationFeedProps) {
  return (
    <Card>
      <CardHeader
        title="Agent Communication Layer"
        subtitle="Inter-agent messages and conflict resolution"
      />

      <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
        {messages.map((msg) => {
          const config = typeConfig[msg.type];
          const Icon = config.icon;

          return (
            <div
              key={msg.id}
              className="rounded-lg border border-border bg-surface p-3"
            >
              <div className="flex items-center gap-2 mb-2 flex-wrap">
                <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                <span className={cn("text-xs font-semibold", getAgentColor(msg.from))}>
                  {getAgentLabel(msg.from)}
                </span>
                <span className="text-muted-foreground/50 text-xs">→</span>
                <span className="text-xs text-muted-foreground">
                  {msg.to === "broadcast"
                    ? "All Agents"
                    : getAgentLabel(msg.to)}
                </span>
                <Badge variant={config.variant} className="ml-auto">
                  {config.label}
                </Badge>
              </div>
              <p className="text-sm text-foreground/90 leading-relaxed">{msg.content}</p>
              <p className="text-[10px] text-muted-foreground/80 mt-2 font-mono">
                {formatDate(msg.timestamp)}
              </p>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
