"use client";

import { useMutation } from "@tanstack/react-query";
import { apiPost, type QueryResponse, ApiError } from "@/lib/api/client";
import { useChatStore } from "@/lib/stores/chat-store";

interface ChatInput {
  query: string;
  top_k?: number;
}

export function useChatMutation() {
  const { addMessage, updateMessage } = useChatStore();

  return useMutation<QueryResponse, ApiError, ChatInput>({
    mutationFn: async (input) => {
      // Add user message
      addMessage({ role: "user", content: input.query });

      // Add placeholder assistant message
      const assistantId = addMessage({
        role: "assistant",
        content: "",
        isLoading: true,
      });

      try {
        const response = await apiPost<QueryResponse>("/api/v1/query", {
          query: input.query,
          top_k: input.top_k ?? 5,
        });

        updateMessage(assistantId, {
          content: response.response,
          metadata: response,
          isLoading: false,
        });

        return response;
      } catch (err) {
        const error = err as ApiError;
        updateMessage(assistantId, {
          content: "",
          isLoading: false,
          error:
            error.status === 403
              ? "Your query could not be processed. Please rephrase and try again."
              : error.status === 429
                ? "You're sending too many requests. Please wait a moment."
                : "Something went wrong. Please try again.",
        });
        throw error;
      }
    },
  });
}
