import * as React from "react"
import { Input as InputPrimitive } from "@base-ui/react/input"

import { cn } from "@/lib/utils"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <InputPrimitive
      type={type}
      data-slot="input"
      className={cn(
        /* Base sizing & layout */
        "h-9 w-full min-w-0 rounded-xl px-3 py-1.5 text-base md:text-sm",
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
        /* File inputs */
        "file:inline-flex file:h-6 file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground",
        /* Disabled */
        "disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-40",
        /* Validation */
        "aria-invalid:border-destructive/50 aria-invalid:ring-3 aria-invalid:ring-destructive/20",
        className
      )}
      {...props}
    />
  )
}

export { Input }
