"use client"

import { Button as ButtonPrimitive } from "@base-ui/react/button"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center border border-transparent bg-clip-padding text-sm font-medium whitespace-nowrap outline-none select-none transition-all duration-150 ease-out focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 active:not-aria-[haspopup]:scale-[0.97] disabled:pointer-events-none disabled:opacity-40 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        /* --- Primary: soft glow teal on glass --- */
        default:
          "rounded-full bg-primary text-primary-foreground shadow-[0_0_16px_var(--glow-primary)] hover:bg-primary/90 hover:shadow-[0_0_24px_var(--glow-primary-strong)] active:bg-primary/80",

        /* --- Outline: glass border button --- */
        outline:
          "rounded-full border-[var(--glass-border-strong)] bg-[var(--glass-bg)] backdrop-blur-xl text-foreground hover:bg-[var(--glass-bg-hover)] hover:border-[oklch(1_0_0/20%)] active:bg-[var(--glass-bg-active)] dark:bg-[var(--glass-bg)] dark:hover:bg-[var(--glass-bg-hover)]",

        /* --- Secondary: frosted glass pill --- */
        secondary:
          "rounded-full bg-secondary text-secondary-foreground backdrop-blur-xl hover:bg-[var(--glass-bg-hover)] active:bg-[var(--glass-bg-active)]",

        /* --- Ghost: invisible until hovered --- */
        ghost:
          "rounded-xl hover:bg-[var(--glass-bg-hover)] hover:text-foreground active:bg-[var(--glass-bg-active)] backdrop-blur-sm",

        /* --- Destructive: muted red on glass --- */
        destructive:
          "rounded-full bg-destructive/10 text-destructive border-destructive/20 hover:bg-destructive/20 focus-visible:border-destructive/40 focus-visible:ring-destructive/20 dark:bg-destructive/15 dark:hover:bg-destructive/25",

        /* --- Link: plain text --- */
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default:
          "h-9 gap-2 px-4 has-data-[icon=inline-end]:pr-3 has-data-[icon=inline-start]:pl-3",
        xs: "h-6 gap-1 px-2.5 text-xs has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 [&_svg:not([class*='size-'])]:size-3",
        sm: "h-7 gap-1.5 px-3 text-[0.8rem] has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2 [&_svg:not([class*='size-'])]:size-3.5",
        lg: "h-10 gap-2 px-5 text-sm has-data-[icon=inline-end]:pr-3.5 has-data-[icon=inline-start]:pl-3.5",
        icon: "size-9 rounded-xl",
        "icon-xs": "size-6 rounded-lg [&_svg:not([class*='size-'])]:size-3",
        "icon-sm": "size-7 rounded-lg",
        "icon-lg": "size-10 rounded-xl",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
