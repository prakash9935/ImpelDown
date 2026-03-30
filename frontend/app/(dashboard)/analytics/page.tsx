"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useHealth } from "@/lib/hooks/use-health";
import {
  BarChart3,
  Zap,
  MessageSquare,
  ShieldCheck,
  Activity,
} from "lucide-react";

function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
}: {
  title: string;
  value: string;
  subtitle: string;
  icon: React.ElementType;
}) {
  return (
    <Card className="border-border/50">
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-muted-foreground">{title}</p>
            <p className="mt-1 text-2xl font-bold tracking-tight">{value}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>
          </div>
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
            <Icon className="h-5 w-5 text-primary" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function AnalyticsPage() {
  const { data: health } = useHealth();

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight">Analytics</h1>
        <p className="text-sm text-muted-foreground">
          System metrics and usage overview
        </p>
      </div>

      {/* System Status */}
      <Card className="border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Activity className="h-4 w-4" />
            System Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Knowledge Base:</span>
              <Badge
                variant="secondary"
                className={
                  health?.qdrant === "ok" ? "text-emerald-400" : "text-red-400"
                }
              >
                {health?.qdrant === "ok" ? "Online" : "Offline"}
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Cache:</span>
              <Badge
                variant="secondary"
                className={
                  health?.redis === "ok" ? "text-emerald-400" : "text-yellow-400"
                }
              >
                {health?.redis === "ok" ? "Online" : "Degraded"}
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Overall:</span>
              <Badge
                variant="secondary"
                className={
                  health?.status === "ok"
                    ? "text-emerald-400"
                    : "text-yellow-400"
                }
              >
                {health?.status === "ok" ? "Healthy" : "Degraded"}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          title="Queries Today"
          value="—"
          subtitle="Requires metrics endpoint"
          icon={MessageSquare}
        />
        <StatCard
          title="Tokens Used"
          value="—"
          subtitle="Requires metrics endpoint"
          icon={Zap}
        />
        <StatCard
          title="Cache Hit Rate"
          value="—"
          subtitle="Requires metrics endpoint"
          icon={BarChart3}
        />
        <StatCard
          title="Safety Checks"
          value="—"
          subtitle="All queries validated"
          icon={ShieldCheck}
        />
      </div>

      {/* Placeholder for charts */}
      <Card className="border-border/50">
        <CardHeader>
          <CardTitle className="text-sm">Query Volume Over Time</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-border/50 text-sm text-muted-foreground">
            <div className="text-center">
              <BarChart3 className="mx-auto mb-2 h-8 w-8 text-muted-foreground/30" />
              <p>Usage charts coming soon</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
