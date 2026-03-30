"use client";

import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";

interface DashboardShellProps {
  email: string;
  role: string;
  children: React.ReactNode;
}

export function DashboardShell({ email, role, children }: DashboardShellProps) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar role={role} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar email={email} role={role} />
        <main className="flex-1 overflow-auto">{children}</main>
      </div>
    </div>
  );
}
