"use client";

import { useMutation } from "@tanstack/react-query";
import { apiUpload, type IngestResponse, ApiError } from "@/lib/api/client";

interface IngestInput {
  file: File;
  dept: string;
  visibility: string;
  base_tier: number;
}

export function useIngestMutation() {
  return useMutation<IngestResponse, ApiError, IngestInput>({
    mutationFn: async (input) => {
      const formData = new FormData();
      formData.append("file", input.file);
      formData.append("dept", input.dept);
      formData.append("visibility", input.visibility);
      formData.append("base_tier", String(input.base_tier));
      return apiUpload<IngestResponse>("/api/v1/ingest", formData);
    },
  });
}
