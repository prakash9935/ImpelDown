"use client";

import { ChatThread } from "@/components/chat/chat-thread";
import { ChatInput } from "@/components/chat/chat-input";
import { useChatMutation } from "@/lib/hooks/use-chat-mutation";

export default function ChatPage() {
  const mutation = useChatMutation();

  return (
    <div className="flex h-full flex-col">
      <ChatThread />
      <ChatInput
        onSend={(query) => mutation.mutate({ query })}
        isLoading={mutation.isPending}
      />
    </div>
  );
}
