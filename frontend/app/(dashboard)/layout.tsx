import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { DashboardShell } from "./dashboard-shell";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  const email = user.email || "unknown";
  const role =
    (user.user_metadata?.role as string) ||
    "standard";

  return (
    <DashboardShell email={email} role={role}>
      {children}
    </DashboardShell>
  );
}
