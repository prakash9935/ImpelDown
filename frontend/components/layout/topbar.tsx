"use client";

import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { useHealth } from "@/lib/hooks/use-health";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { LogOut, Settings, User } from "lucide-react";
import { useChatStore } from "@/lib/stores/chat-store";
import { cn } from "@/lib/utils";

interface TopbarProps {
  email: string;
  role: string;
}

function HealthDot() {
  const { data, isError } = useHealth();

  const status = isError ? "down" : data?.status || "unknown";
  const color =
    status === "ok"
      ? "bg-emerald-400/80"
      : status === "degraded"
        ? "bg-amber-400/80"
        : "bg-red-400/80";
  const glowColor =
    status === "ok"
      ? "shadow-[0_0_8px_oklch(0.7_0.15_162/40%)]"
      : status === "degraded"
        ? "shadow-[0_0_8px_oklch(0.7_0.15_80/40%)]"
        : "shadow-[0_0_8px_oklch(0.6_0.2_25/40%)]";
  const label =
    status === "ok"
      ? "All systems healthy"
      : status === "degraded"
        ? "Some services degraded"
        : "Backend unavailable";

  return (
    <div className="flex items-center gap-2" title={label}>
      <div className={cn("h-2 w-2 rounded-full", color, glowColor)} />
      <span className="text-xs text-muted-foreground hidden sm:inline">
        {status === "ok" ? "Healthy" : status === "degraded" ? "Degraded" : "Down"}
      </span>
    </div>
  );
}

const roleColors: Record<string, string> = {
  admin: "bg-primary/12 text-primary border-primary/20",
  finance: "bg-blue-400/10 text-blue-300 border-blue-400/20",
  hr: "bg-purple-400/10 text-purple-300 border-purple-400/20",
  standard: "bg-[var(--glass-bg-elevated)] text-muted-foreground border-[var(--glass-border)]",
};

export function Topbar({ email, role }: TopbarProps) {
  const router = useRouter();

  async function handleSignOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    useChatStore.getState().clearMessages();
    router.push("/login");
    router.refresh();
  }

  const initials = email
    .split("@")[0]
    .slice(0, 2)
    .toUpperCase();

  return (
    <header
      className={cn(
        "flex h-14 items-center justify-between px-4",
        /* Liquid Glass topbar */
        "bg-[var(--glass-bg)] backdrop-blur-2xl",
        "border-b border-[var(--glass-border)]"
      )}
    >
      <div className="flex items-center gap-3">
        <HealthDot />
      </div>

      <div className="flex items-center gap-3">
        <Badge
          variant="outline"
          className={cn("text-xs capitalize backdrop-blur-sm", roleColors[role] || roleColors.standard)}
        >
          {role}
        </Badge>

        <DropdownMenu>
          <DropdownMenuTrigger>
            <div className="flex h-8 w-8 items-center justify-center rounded-full cursor-pointer transition-all duration-150 hover:bg-[var(--glass-bg-hover)]">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="bg-primary/10 text-xs text-primary border border-primary/20">
                  {initials}
                </AvatarFallback>
              </Avatar>
            </div>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align="end"
            className="w-56 glass-elevated rounded-xl"
          >
            <div className="px-2 py-1.5">
              <p className="text-sm font-medium">{email}</p>
              <p className="text-xs text-muted-foreground capitalize">{role} role</p>
            </div>
            <DropdownMenuSeparator className="bg-[var(--glass-border)]" />
            <DropdownMenuItem onClick={() => router.push("/settings")}>
              <Settings className="mr-2 h-4 w-4" />
              Settings
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => router.push("/settings")}>
              <User className="mr-2 h-4 w-4" />
              Profile
            </DropdownMenuItem>
            <DropdownMenuSeparator className="bg-[var(--glass-border)]" />
            <DropdownMenuItem onClick={handleSignOut} className="text-destructive">
              <LogOut className="mr-2 h-4 w-4" />
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
