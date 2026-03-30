import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export default async function IngestLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const role = (user?.user_metadata?.role as string) || "standard";

  if (role !== "admin") redirect("/chat");

  return <>{children}</>;
}
