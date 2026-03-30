"""
Jailbreak Detection (US-303, Sprint 3)

Gateway-layer classifier to detect prompt injection attempts in user queries.
Reuses sanitizer.flag_adversarial_language() and adds encoding bypass detection.

Implements:
  - classify_jailbreak() — multi-layer detection
  - Base64/ROT13 decoding with re-check
  - Additional gateway-specific patterns
"""

import base64
import codecs
import logging
from typing import Optional, Tuple

from src.secrag.ingestion.sanitizer import flag_adversarial_language

logger = logging.getLogger(__name__)


def classify_jailbreak(query: str) -> Tuple[bool, Optional[str]]:
    """
    Detect jailbreak attempt in user query (US-303).

    Multi-layer detection:
    1. Reuse sanitizer keyword matching (Sprint 1)
    2. Detect base64-encoded jailbreak attempts
    3. Detect ROT13-encoded attempts
    4. Check additional gateway-specific patterns

    Args:
        query: User's input query

    Returns:
        (is_jailbreak: bool, reason: Optional[str])
    """
    # Layer 1: Reuse sanitizer's adversarial language detection
    is_adversarial, reason = flag_adversarial_language(query)
    if is_adversarial:
        logger.warning(f"Jailbreak detected via sanitizer: {reason}")
        return True, reason

    query_lower = query.lower()

    # Layer 2: Additional gateway-specific patterns
    gateway_patterns = [
        "what are your instructions",
        "what is your system prompt",
        "what is your actual purpose",
        "you are actually",
        "forget everything",
        "from now on",
    ]

    for pattern in gateway_patterns:
        if pattern in query_lower:
            logger.warning(f"Jailbreak detected via gateway pattern: '{pattern}'")
            return True, f"Detected jailbreak pattern: '{pattern}'"

    # Layer 3: Detect base64-encoded jailbreak attempts
    try:
        # Try to decode as base64
        if len(query) % 4 == 0:  # Valid base64 must be multiple of 4
            decoded = base64.b64decode(query, validate=True).decode("utf-8", errors="ignore")
            decoded_lower = decoded.lower()

            # Check if decoded text contains jailbreak patterns
            for pattern in gateway_patterns:
                if pattern in decoded_lower:
                    logger.warning(f"Jailbreak detected in base64-decoded query: '{pattern}'")
                    return True, f"Detected base64-encoded jailbreak: '{pattern}'"

            # Also check with sanitizer
            is_adversarial_decoded, reason_decoded = flag_adversarial_language(decoded)
            if is_adversarial_decoded:
                logger.warning(f"Jailbreak detected in base64-decoded query: {reason_decoded}")
                return True, f"Detected base64-encoded jailbreak: {reason_decoded}"

    except Exception:
        pass  # Not valid base64, continue to next layer

    # Layer 4: Detect ROT13-encoded jailbreak attempts
    try:
        rot13_decoded = codecs.decode(query, "rot_13")
        rot13_lower = rot13_decoded.lower()

        # Check if ROT13-decoded text contains jailbreak patterns
        for pattern in gateway_patterns:
            if pattern in rot13_lower:
                logger.warning(f"Jailbreak detected in ROT13-decoded query: '{pattern}'")
                return True, f"Detected ROT13-encoded jailbreak: '{pattern}'"

        # Also check with sanitizer
        is_adversarial_rot13, reason_rot13 = flag_adversarial_language(rot13_decoded)
        if is_adversarial_rot13:
            logger.warning(f"Jailbreak detected in ROT13-decoded query: {reason_rot13}")
            return True, f"Detected ROT13-encoded jailbreak: {reason_rot13}"

    except Exception:
        pass  # ROT13 decode failed, continue

    # Query passed all checks
    logger.debug(f"Query passed jailbreak checks: {query[:50]}...")
    return False, None
