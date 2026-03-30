"use client";

import { useQuery } from "@tanstack/react-query";
import type { HealthResponse } from "@/lib/api/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL!;

export function useHealth() {
  return useQuery<HealthResponse>({
    queryKey: ["health"],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/api/v1/health`);
      if (!res.ok) throw new Error("Health check failed");
      return res.json();
    },
    refetchInterval: 30_000,
    retry: 1,
  });
}
