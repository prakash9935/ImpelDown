"use client";

import { useEffect, useRef } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageBubble } from "./message-bubble";
import { useChatStore } from "@/lib/stores/chat-store";
import { Shield, MessageSquare } from "lucide-react";

export function ChatThread() {
  const { messages } = useChatStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="text-center space-y-5 max-w-md px-4 animate-glass-in">
          {/* Hero icon in glass container */}
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 border border-primary/15 shadow-[0_0_32px_var(--glow-primary)] backdrop-blur-xl">
            <Shield className="h-8 w-8 text-primary" />
          </div>

          <h2 className="text-xl font-semibold tracking-tight text-foreground">
            Hina
          </h2>

          <p className="text-sm text-muted-foreground leading-relaxed">
            Ask questions about your organization&apos;s documents.
          </p>

          <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground/50">
            <MessageSquare className="h-3 w-3" />
            <span>Type a question below to get started</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <ScrollArea className="flex-1">
      <div className="mx-auto max-w-3xl space-y-4 px-4 py-6">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
