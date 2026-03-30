"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  MessageSquare,
  Upload,
  BarChart3,
  Settings,
  PlusCircle,
  PanelLeftClose,
  PanelLeft,
  Shield,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useChatStore } from "@/lib/stores/chat-store";
import { cn } from "@/lib/utils";

interface SidebarProps {
  role: string;
}

export function Sidebar({ role }: SidebarProps) {
  const pathname = usePathname();
  const { sidebarOpen, toggleSidebar, clearMessages } = useChatStore();

  const isAdmin = role === "admin";

  const navItems = [
    { href: "/chat", label: "Chat", icon: MessageSquare, show: true },
    { href: "/ingest", label: "Ingest", icon: Upload, show: isAdmin },
    { href: "/analytics", label: "Analytics", icon: BarChart3, show: isAdmin },
    { href: "/settings", label: "Settings", icon: Settings, show: true },
  ].filter((item) => item.show);

  /* ---- Collapsed state --------------------------------------------------- */
  if (!sidebarOpen) {
    return (
      <div
        className={cn(
          "flex h-full w-14 flex-col items-center py-4",
          /* Liquid Glass sidebar */
          "bg-[var(--glass-bg)] backdrop-blur-2xl",
          "border-r border-[var(--glass-border)]"
        )}
      >
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleSidebar}
          className="mb-4 text-muted-foreground hover:text-foreground"
        >
          <PanelLeft className="h-4 w-4" />
        </Button>
        <div className="flex flex-col items-center gap-1.5">
          {navItems.map((item) => (
            <Link key={item.href} href={item.href}>
              <Button
                variant="ghost"
                size="icon"
                className={cn(
                  "text-muted-foreground hover:text-foreground",
                  pathname === item.href &&
                    "bg-primary/10 text-primary shadow-[0_0_12px_var(--glow-primary)]"
                )}
              >
                <item.icon className="h-4 w-4" />
              </Button>
            </Link>
          ))}
        </div>
      </div>
    );
  }

  /* ---- Expanded state ---------------------------------------------------- */
  return (
    <div
      className={cn(
        "flex h-full w-60 flex-col",
        /* Liquid Glass sidebar */
        "bg-[var(--glass-bg)] backdrop-blur-2xl",
        "border-r border-[var(--glass-border)]"
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-4">
        <Link href="/chat" className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/15 shadow-[0_0_12px_var(--glow-primary)]">
            <Shield className="h-4 w-4 text-primary" />
          </div>
          <span className="text-sm font-semibold tracking-tight">Hina</span>
        </Link>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={toggleSidebar}
          className="text-muted-foreground hover:text-foreground"
        >
          <PanelLeftClose className="h-4 w-4" />
        </Button>
      </div>

      <div className="px-3">
        <Button
          variant="outline"
          className="w-full justify-start gap-2 text-sm"
          onClick={() => {
            clearMessages();
            window.location.href = "/chat";
          }}
        >
          <PlusCircle className="h-4 w-4" />
          New Chat
        </Button>
      </div>

      <Separator className="my-3 opacity-30" />

      {/* Navigation */}
      <nav className="flex-1 space-y-0.5 px-3">
        {navItems.map((item) => (
          <Link key={item.href} href={item.href}>
            <div
              className={cn(
                "flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition-all duration-150 ease-out",
                pathname === item.href
                  ? "bg-primary/10 text-primary font-medium shadow-[0_0_12px_var(--glow-primary)]"
                  : "text-muted-foreground hover:bg-[var(--glass-bg-hover)] hover:text-foreground"
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </div>
          </Link>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-[var(--glass-border)] p-3">
        <p className="text-[11px] text-muted-foreground/40 text-center tracking-wide">
          Hina
        </p>
      </div>
    </div>
  );
}
