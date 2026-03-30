"use client";

import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { LogOut, User } from "lucide-react";
import { useEffect, useState } from "react";

export default function SettingsPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("standard");

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (user) {
        setEmail(user.email || "");
        setRole((user.user_metadata?.role as string) || "standard");
      }
    });
  }, []);

  async function handleSignOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">
          Account and application settings
        </p>
      </div>

      <Card className="border-border/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <User className="h-4 w-4" />
            Profile
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">{email}</p>
              <p className="text-xs text-muted-foreground">Email address</p>
            </div>
          </div>
          <Separator />
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium capitalize">{role}</p>
              <p className="text-xs text-muted-foreground">Access role</p>
            </div>
            <Badge variant="outline" className="capitalize">
              {role}
            </Badge>
          </div>
        </CardContent>
      </Card>

      <Button
        variant="destructive"
        onClick={handleSignOut}
        className="w-full"
      >
        <LogOut className="mr-2 h-4 w-4" />
        Sign Out
      </Button>

      <p className="text-center text-xs text-muted-foreground/50">
        Hina
      </p>
    </div>
  );
}
