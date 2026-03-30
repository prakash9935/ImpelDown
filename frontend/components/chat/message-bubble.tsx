"use client";

import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import { Badge } from "@/components/ui/badge";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Clock,
  Zap,
  ShieldCheck,
  ShieldAlert,
  Lock,
  FileText,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import type { ChatMessage } from "@/lib/stores/chat-store";
import { cn } from "@/lib/utils";

interface MessageBubbleProps {
  message: ChatMessage;
}

function MetadataStrip({ message }: { message: ChatMessage }) {
  const m = message.metadata;
  if (!m) return null;

  return (
    <div className="mt-2.5 flex flex-wrap items-center gap-1.5 text-xs">
      <Badge variant="secondary" className="gap-1 font-mono">
        <Clock className="h-3 w-3" />
        {m.latency_ms.toFixed(0)}ms
      </Badge>

      {m.cache_hit && (
        <Badge variant="secondary" className="gap-1">
          <Zap className="h-3 w-3 text-amber-300/80" />
          Cached
        </Badge>
      )}

      <Badge
        variant="secondary"
        className={cn(
          "gap-1",
          m.is_safe ? "text-emerald-300/80" : "text-red-300/80"
        )}
      >
        {m.is_safe ? (
          <ShieldCheck className="h-3 w-3" />
        ) : (
          <ShieldAlert className="h-3 w-3" />
        )}
        {m.is_safe ? "Safe" : "Unsafe"}
      </Badge>

      {m.pii_redacted && (
        <Badge variant="secondary" className="gap-1 text-amber-300/80">
          <Lock className="h-3 w-3" />
          PII Redacted
        </Badge>
      )}

      <Badge variant="secondary" className="gap-1 font-mono">
        {m.tokens_used} tokens
      </Badge>
    </div>
  );
}

function ChunkAccordion({ chunks }: { chunks: string[] }) {
  // Hide if no chunks, or all chunks are just "unknown" placeholder IDs
  const meaningful = chunks?.filter((c) => c && c !== "unknown") ?? [];
  if (meaningful.length === 0) return null;

  return (
    <Accordion className="mt-3">
      <AccordionItem value="sources" className="border-[var(--glass-border)]">
        <AccordionTrigger className="py-2 text-xs text-muted-foreground hover:no-underline">
          <span className="flex items-center gap-1.5">
            <FileText className="h-3 w-3" />
            {meaningful.length} source{meaningful.length > 1 ? "s" : ""} used
          </span>
        </AccordionTrigger>
        <AccordionContent>
          <div className="space-y-2">
            {meaningful.map((chunk, i) => (
              <div
                key={i}
                className="rounded-lg border border-[var(--glass-border)] bg-[var(--glass-bg)] backdrop-blur-xl p-2.5 text-xs font-mono text-muted-foreground"
              >
                {chunk}
              </div>
            ))}
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  /* ---- Loading state ----------------------------------------------------- */
  if (message.isLoading) {
    return (
      <div className="flex justify-start animate-glass-in">
        <div
          className={cn(
            "max-w-[80%] rounded-2xl rounded-bl-md px-4 py-3",
            "bg-[var(--glass-bg)] backdrop-blur-2xl",
            "border border-[var(--glass-border)]"
          )}
        >
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-sm">Thinking...</span>
          </div>
        </div>
      </div>
    );
  }

  /* ---- Error state ------------------------------------------------------- */
  if (message.error) {
    return (
      <div className="flex justify-start animate-glass-in">
        <div
          className={cn(
            "max-w-[80%] rounded-2xl rounded-bl-md px-4 py-3",
            "bg-destructive/8 backdrop-blur-2xl",
            "border border-destructive/20"
          )}
        >
          <div className="flex items-start gap-2 text-destructive">
            <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <p className="text-sm">{message.error}</p>
          </div>
        </div>
      </div>
    );
  }

  /* ---- Normal message ---------------------------------------------------- */
  return (
    <div
      className={cn(
        "flex animate-glass-in",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <div
        className={cn(
          "max-w-[80%] rounded-2xl px-4 py-3",
          isUser
            ? [
                /* User bubble: primary teal with soft glow */
                "rounded-br-md",
                "bg-primary/15 backdrop-blur-2xl",
                "border border-primary/20",
                "shadow-[0_0_20px_var(--glow-primary)]",
                "text-foreground",
              ]
            : [
                /* Assistant bubble: neutral glass panel */
                "rounded-bl-md",
                "bg-[var(--glass-bg)] backdrop-blur-2xl",
                "border border-[var(--glass-border)]",
                "glass-inner-shadow",
              ]
        )}
      >
        {isUser ? (
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="prose prose-sm prose-invert max-w-none text-foreground prose-p:text-foreground/90 prose-strong:text-foreground prose-code:text-primary/90 prose-code:bg-[var(--glass-bg)] prose-code:rounded-md prose-code:px-1.5 prose-code:py-0.5 prose-code:border prose-code:border-[var(--glass-border)]">
            <ReactMarkdown
              rehypePlugins={[rehypeSanitize]}
              remarkPlugins={[remarkGfm]}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {/* Security: no technical metadata exposed to end users */}
      </div>
    </div>
  );
}
