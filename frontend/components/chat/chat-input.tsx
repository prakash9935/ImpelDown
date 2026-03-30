"use client";

import { useState, useRef, useCallback } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Send, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  onSend: (query: string) => void;
  isLoading: boolean;
  disabled?: boolean;
}

export function ChatInput({ onSend, isLoading, disabled }: ChatInputProps) {
  const [query, setQuery] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = useCallback(() => {
    const trimmed = query.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed);
    setQuery("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [query, isLoading, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div
      className={cn(
        "p-4",
        "bg-[var(--glass-bg)] backdrop-blur-2xl",
        "border-t border-[var(--glass-border)]"
      )}
    >
      <div className="flex items-end gap-2">
        <Textarea
          ref={textareaRef}
          placeholder="Ask Hina a question..."
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            e.target.style.height = "auto";
            e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`;
          }}
          onKeyDown={handleKeyDown}
          rows={1}
          className="min-h-[44px] max-h-[200px] resize-none"
          disabled={disabled}
        />

        <Button
          size="icon"
          className={cn(
            "h-9 w-9 flex-shrink-0",
            !query.trim() && "opacity-40"
          )}
          onClick={handleSend}
          disabled={!query.trim() || isLoading || disabled}
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </Button>
      </div>

      <p className="mt-1.5 text-center text-[10px] text-muted-foreground/40">
        {typeof navigator !== "undefined" && navigator.platform?.includes("Mac")
          ? "\u2318"
          : "Ctrl"}
        +Enter to send
      </p>
    </div>
  );
}
