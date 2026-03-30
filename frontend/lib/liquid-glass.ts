/**
 * LIQUID GLASS DESIGN SYSTEM — Reference & Utility Constants
 *
 * This file documents every token, utility class, and component pattern
 * in the SecRAG Liquid Glass design system. Import the `cn()` helper
 * from "@/lib/utils" and compose these strings as needed.
 *
 * Apple "Liquid Glass" characteristics translated to dark-mode web:
 *   - Translucent frosted panels with heavy backdrop-blur
 *   - Subtle light-refraction highlight on top edges
 *   - Soft, rounded corners (radius scale starts at 0.75rem)
 *   - Layered depth via translucent panels floating over content
 *   - Muted, desaturated palette — no bright saturated colors
 *   - Thin borders at low-opacity white
 *   - Soft glowing accents, not harsh
 *   - Deep dark background with subtle noise/grain texture
 */

// ---------------------------------------------------------------------------
// 1. COLOR PALETTE (CSS custom properties defined in globals.css)
// ---------------------------------------------------------------------------
// Copy these directly into any design token documentation.
//
// Background & surface
//   --background:           oklch(0.11 0.008 285)    Deep dark, cool-violet
//   --card:                 oklch(1 0 0 / 5%)        5% white glass
//   --popover:              oklch(0.16 0.01 285)     Slightly denser glass
//   --sidebar:              oklch(1 0 0 / 3%)        Near-invisible glass
//
// Text
//   --foreground:           oklch(0.93 0.005 285)    Soft white (not pure)
//   --muted-foreground:     oklch(0.60 0.005 285)    Low-contrast metadata
//   --secondary-foreground: oklch(0.88 0.005 285)
//
// Primary accent (desaturated teal)
//   --primary:              oklch(0.72 0.12 192)
//   --primary-foreground:   oklch(0.11 0.008 285)
//
// Borders
//   --border:               oklch(1 0 0 / 8%)
//   --glass-border:         oklch(1 0 0 / 10%)
//   --glass-border-strong:  oklch(1 0 0 / 15%)
//
// Glass fills
//   --glass-bg:             oklch(1 0 0 / 4%)
//   --glass-bg-hover:       oklch(1 0 0 / 7%)
//   --glass-bg-active:      oklch(1 0 0 / 10%)
//   --glass-bg-elevated:    oklch(1 0 0 / 6%)
//
// Glow effects
//   --glow-primary:         oklch(0.72 0.12 192 / 15%)
//   --glow-primary-strong:  oklch(0.72 0.12 192 / 25%)
//   --glow-user:            oklch(0.65 0.10 260 / 15%)
//
// Destructive
//   --destructive:          oklch(0.62 0.18 25)
//
// Ring (focus glow)
//   --ring:                 oklch(0.72 0.12 192 / 50%)

// ---------------------------------------------------------------------------
// 2. KEY UTILITY CLASSES
// ---------------------------------------------------------------------------
// These are defined in globals.css @layer utilities. Use them directly on
// elements or compose them with cn().

export const GLASS_CLASSES = {
  /** Standard glass surface (24px blur, 1px border, soft shadow) */
  surface: "glass",

  /** Elevated glass (40px blur, stronger presence) */
  elevated: "glass-elevated",

  /** Strongest glass (48px blur, stronger border) */
  strong: "glass-strong",

  /** Adds refraction highlight pseudo-element on top edge */
  refraction: "glass-refraction",

  /** Inner shadow for additional depth */
  innerShadow: "glass-inner-shadow",

  /** Interactive hover/active transitions */
  interactive: "glass-interactive",

  /** Primary accent glow */
  glowPrimary: "glow-primary",

  /** Primary glow as a ring */
  glowPrimaryRing: "glow-primary-ring",

  /** Fade-in animation for glass panels */
  animateIn: "animate-glass-in",

  /** Shimmer loading effect on glass */
  shimmer: "animate-glass-shimmer",

  /** Soft pulse animation */
  pulse: "animate-soft-pulse",
} as const;

// ---------------------------------------------------------------------------
// 3. COMMON TAILWIND CLASS COMBINATIONS
// ---------------------------------------------------------------------------
// Use these as building blocks. They pair Tailwind utilities with the custom
// CSS variables defined in our theme.

export const PATTERNS = {
  /** Thin glass border */
  border: "border border-[var(--glass-border)]",

  /** Strong glass border */
  borderStrong: "border border-[var(--glass-border-strong)]",

  /** Glass background */
  bg: "bg-[var(--glass-bg)]",

  /** Glass background on hover */
  bgHover: "hover:bg-[var(--glass-bg-hover)]",

  /** Heavy backdrop blur (sidebar, topbar, input area) */
  blurHeavy: "backdrop-blur-2xl",

  /** Standard backdrop blur (cards, panels) */
  blurStandard: "backdrop-blur-xl",

  /** Focus ring with glow */
  focusGlow:
    "focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:shadow-[0_0_16px_var(--glow-primary)]",

  /** Primary text with glow container */
  primaryGlow:
    "text-primary shadow-[0_0_12px_var(--glow-primary)]",

  /** Muted text */
  muted: "text-muted-foreground",

  /** Very muted text (for timestamps, version info) */
  mutedDeep: "text-muted-foreground/40",
} as const;

// ---------------------------------------------------------------------------
// 4. COMPONENT PATTERN STRINGS
// ---------------------------------------------------------------------------
// Ready-to-use class strings for each component type. Apply with cn().

export const COMPONENT = {
  // --- Glass Card --------------------------------------------------------
  card: "glass glass-refraction glass-inner-shadow rounded-2xl",

  // --- Glass Sidebar -----------------------------------------------------
  sidebar:
    "bg-[var(--glass-bg)] backdrop-blur-2xl border-r border-[var(--glass-border)]",

  // --- Glass Topbar ------------------------------------------------------
  topbar:
    "bg-[var(--glass-bg)] backdrop-blur-2xl border-b border-[var(--glass-border)]",

  // --- Glass Input Area (chat footer) ------------------------------------
  inputArea:
    "bg-[var(--glass-bg)] backdrop-blur-2xl border-t border-[var(--glass-border)]",

  // --- Glass Input / Textarea --------------------------------------------
  input: [
    "bg-[var(--glass-bg)] backdrop-blur-xl",
    "border border-[var(--glass-border)]",
    "focus-visible:border-[oklch(1_0_0/18%)] focus-visible:bg-[var(--glass-bg-hover)]",
    "focus-visible:ring-3 focus-visible:ring-ring/50",
    "focus-visible:shadow-[0_0_16px_var(--glow-primary)]",
    "rounded-xl",
  ].join(" "),

  // --- User Message Bubble -----------------------------------------------
  bubbleUser: [
    "rounded-2xl rounded-br-md",
    "bg-primary/15 backdrop-blur-2xl",
    "border border-primary/20",
    "shadow-[0_0_20px_var(--glow-primary)]",
  ].join(" "),

  // --- Assistant Message Bubble ------------------------------------------
  bubbleAssistant: [
    "rounded-2xl rounded-bl-md",
    "bg-[var(--glass-bg)] backdrop-blur-2xl",
    "border border-[var(--glass-border)]",
    "glass-inner-shadow",
  ].join(" "),

  // --- Button: Primary (pill + glow) -------------------------------------
  btnPrimary:
    "rounded-full bg-primary text-primary-foreground shadow-[0_0_16px_var(--glow-primary)] hover:shadow-[0_0_24px_var(--glow-primary-strong)]",

  // --- Button: Secondary (glass pill) ------------------------------------
  btnSecondary:
    "rounded-full bg-secondary text-secondary-foreground backdrop-blur-xl",

  // --- Button: Ghost (invisible until hover) -----------------------------
  btnGhost:
    "rounded-xl hover:bg-[var(--glass-bg-hover)] backdrop-blur-sm",

  // --- Button: Outline (glass border pill) -------------------------------
  btnOutline:
    "rounded-full border-[var(--glass-border-strong)] bg-[var(--glass-bg)] backdrop-blur-xl",

  // --- Badge: Default (primary tint) -------------------------------------
  badgeDefault:
    "rounded-full bg-primary/15 text-primary border-primary/20 backdrop-blur-sm",

  // --- Badge: Secondary (glass) ------------------------------------------
  badgeSecondary:
    "rounded-full bg-[var(--glass-bg-elevated)] text-secondary-foreground border-[var(--glass-border)] backdrop-blur-xl",

  // --- Nav item (active) -------------------------------------------------
  navActive:
    "bg-primary/10 text-primary font-medium shadow-[0_0_12px_var(--glow-primary)] rounded-xl",

  // --- Nav item (inactive) -----------------------------------------------
  navInactive:
    "text-muted-foreground hover:bg-[var(--glass-bg-hover)] hover:text-foreground rounded-xl transition-all duration-150 ease-out",
} as const;

// ---------------------------------------------------------------------------
// 5. SPACING SCALE (4px base, matches --space-* tokens)
// ---------------------------------------------------------------------------
export const SPACING = {
  1: "4px",
  2: "8px",
  3: "12px",
  4: "16px",
  5: "20px",
  6: "24px",
  8: "32px",
  10: "40px",
  12: "48px",
  16: "64px",
} as const;

// ---------------------------------------------------------------------------
// 6. ANIMATION DURATIONS
// ---------------------------------------------------------------------------
export const DURATION = {
  /** Micro-interactions (hover, focus) */
  fast: "150ms",
  /** Standard transitions (panel open, tab switch) */
  normal: "250ms",
  /** Slower entrances (page-level) — still under 300ms */
  slow: "300ms",
} as const;

// ---------------------------------------------------------------------------
// 7. EASING CURVES
// ---------------------------------------------------------------------------
export const EASING = {
  /** Entrances — element arriving on screen */
  entrance: "ease-out",
  /** Exits — element leaving screen */
  exit: "ease-in",
  /** State changes — morphing between states */
  stateChange: "ease-in-out",
} as const;
