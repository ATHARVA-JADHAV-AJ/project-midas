# Project Midas — Prompt Injection Sanitizer
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------
"""
First-pass sanitizer for ingested document text.

Scans for common prompt injection patterns BEFORE text enters the
vector store. Flagged segments are replaced with a redaction marker
so they never reach the reasoner's context window.

This is a pattern-matching heuristic, not a comprehensive defense.
Stated honestly: it catches the obvious, widely-documented injection
patterns. Novel or obfuscated attacks may bypass it.
"""

import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

REDACTION_MARKER = "[REDACTED: potential prompt injection]"

# Compiled regex patterns — case-insensitive, catch common injection phrases
_INJECTION_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"ignore\s+(all\s+)?previous\s+instructions?",
        r"disregard\s+(all\s+)?prior\s+(instructions?|context|rules)",
        r"reveal\s+(your\s+)?system\s+prompt",
        r"you\s+are\s+now\s+in\s+unrestricted\s+mode",
        r"override\s+(all\s+)?safety\s+(filters?|protocols?|settings?|rules?)",
        r"ignore\s+(your|all)\s+(rules?|guidelines?|constraints?)",
        r"pretend\s+you\s+(are|have)\s+no\s+(restrictions?|rules?|limits?)",
        r"act\s+as\s+(an?\s+)?unrestricted\s+(ai|model|assistant)",
        r"do\s+not\s+follow\s+(your|any)\s+(rules?|guidelines?|instructions?)",
        r"enter\s+(developer|debug|admin|root|sudo)\s+mode",
        r"output\s+(your|the)\s+(system|initial|original)\s+(prompt|instructions?)",
        r"forget\s+(everything|all)\s+(you|that)\s+(were|was)\s+told",
    ]
]


def sanitize_text(text: str, source_name: str = "unknown") -> Tuple[str, List[str]]:
    """Scan text for prompt injection patterns and replace matches.

    Args:
        text: Raw text extracted from a document.
        source_name: Filename or identifier for logging.

    Returns:
        (cleaned_text, flagged_patterns): The sanitized text and a list
        of the matched pattern strings that were redacted.
    """
    flagged: List[str] = []

    def _replace(match: re.Match) -> str:
        matched_text = match.group(0)
        flagged.append(matched_text)
        return REDACTION_MARKER

    cleaned = text
    for pattern in _INJECTION_PATTERNS:
        cleaned = pattern.sub(_replace, cleaned)

    if flagged:
        logger.warning(
            "Sanitizer flagged %d injection pattern(s) in '%s': %s",
            len(flagged), source_name, flagged
        )

    return cleaned, flagged
