import * as React from "react"

import { cn } from "@/lib/utils"

function Textarea({ className, ...props }: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        /* Base sizing & layout */
        "flex field-sizing-content min-h-16 w-full rounded-xl px-3 py-2.5 text-base md:text-sm",
        /* Liquid Glass surface */
        "bg-[var(--glass-bg)] backdrop-blur-xl",
        "border border-[var(--glass-border)]",
        /* Typography */
        "text-foreground placeholder:text-muted-foreground",
        /* Transitions */
        "transition-all duration-150 ease-out outline-none",
        /* Focus: soft glow ring */
        "focus-visible:border-[oklch(1_0_0/18%)] focus-visible:bg-[var(--glass-bg-hover)]",
        "focus-visible:ring-3 focus-visible:ring-ring/50",
        "focus-visible:shadow-[0_0_16px_var(--glow-primary)]",
        /* Disabled */
        "disabled:cursor-not-allowed disabled:opacity-40",
        /* Validation */
        "aria-invalid:border-destructive/50 aria-invalid:ring-3 aria-invalid:ring-destructive/20",
        className
      )}
      {...props}
    />
  )
}

export { Textarea }
