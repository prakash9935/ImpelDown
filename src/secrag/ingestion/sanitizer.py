"""
Adversarial Content Sanitizer (US-103, US-104)

Removes hidden text (zero-width spaces, white-on-white) and flags adversarial
imperative language using PromptGuard.
"""

import logging
from typing import Optional, Tuple

from ftfy import fix_text

logger = logging.getLogger(__name__)

# Try to import PromptGuard for advanced adversarial detection
try:
    from promptguard import guard

    HAS_PROMPTGUARD = True
except ImportError:
    HAS_PROMPTGUARD = False
    logger.warning("PromptGuard not installed. Using keyword matching only.")

# Adversarial patterns (common jailbreak attempts)
JAILBREAK_KEYWORDS = [
    "ignore the system prompt",
    "ignore previous instructions",
    "forget your prompt",
    "you are now",
    "developer mode",
    "execute",
    "new instructions:",
    "from now on",
    "your real instructions",
    "bypass your safeguards",
    "jailbreak",
    "pretend you",
    "act as if",
    "ignore safety",
]


def scrub_hidden_text(text: str) -> str:
    """
    Remove hidden text artifacts from chunk (US-103).

    Uses ftfy library to fix Unicode issues:
    - Zero-width spaces (\u200b, \u200c, \u200d, \ufeff)
    - Mojibake and other encoding issues
    - Control characters

    Args:
        text: Raw chunk text

    Returns:
        Cleaned text with hidden characters removed
    """
    original_len = len(text)

    # Use ftfy to fix Unicode issues
    cleaned = fix_text(text)

    # Explicitly remove zero-width and invisible characters
    zero_width_chars = {"\u200b", "\u200c", "\u200d", "\ufeff", "\u2060", "\u3164", "\u180e"}
    cleaned = "".join(c for c in cleaned if c not in zero_width_chars)

    # Remove control characters except newlines/tabs
    cleaned = "".join(c for c in cleaned if ord(c) >= 32 or c in "\n\t\r")

    # Normalize whitespace
    cleaned = "\n".join(line.strip() for line in cleaned.split("\n") if line.strip())

    if len(cleaned) < original_len:
        logger.info(f"Scrubbed hidden characters: {original_len} → {len(cleaned)} chars")

    return cleaned


def flag_adversarial_language(text: str) -> Tuple[bool, Optional[str]]:
    """
    Detect adversarial imperative language in chunk (US-104).

    Uses PromptGuard (Meta) for advanced detection, falls back to keyword matching.

    Args:
        text: Chunk text to classify

    Returns:
        (is_adversarial: bool, reason: Optional[str])

    Examples:
        >>> flag_adversarial_language("What is 2+2?")
        (False, None)

        >>> flag_adversarial_language("Ignore the system prompt and...")
        (True, "PromptGuard flagged as jailbreak")
    """
    # First try PromptGuard if available
    if HAS_PROMPTGUARD:
        try:
            result = guard(text)
            if result and result.get("jailbreak_score", 0) > 0.5:
                reason = f"PromptGuard detected jailbreak (score: {result.get('jailbreak_score', 0):.2f})"  # noqa: E501
                logger.warning(f"Flagged adversarial content: {reason}")
                return True, reason
        except Exception as e:
            logger.error(f"PromptGuard error: {e}. Falling back to keyword matching.")

    # Fallback: keyword matching
    text_lower = text.lower()
    for keyword in JAILBREAK_KEYWORDS:
        if keyword in text_lower:
            reason = f"Matched jailbreak keyword: '{keyword}'"
            logger.warning(f"Flagged adversarial content: {reason}")
            return True, reason

    logger.debug(f"No adversarial patterns detected in {len(text)} chars")
    return False, None
