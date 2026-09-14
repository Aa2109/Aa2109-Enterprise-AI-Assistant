import re

from app.security.audit import audit_security_event


INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(the\s+)?system\s+prompt",
    r"reveal\s+(the\s+)?system\s+prompt",
    r"show\s+me\s+your\s+instructions",
    r"disregard\s+previous\s+rules",
    r"you\s+are\s+now\s+the\s+system",
    # PR-30 — additional system-boundary probes.
    r"show\s+(your|the)\s+system\s+prompt",
    r"(repeat|copy|echo|print)\s+(your|the)\s+(system\s+prompt|instructions|rules|developer\s+message)",
    r"what\s+are\s+your\s+(system|developer|initial)\s+(prompt|instructions|rules)",
]


def detect_prompt_injection(text: str) -> bool:
    normalized = text.lower()
    return any(
        re.search(pattern, normalized)
        for pattern in INJECTION_PATTERNS
    )


def validate_user_prompt(text: str) -> None:
    if not text.strip():
        raise ValueError("Prompt cannot be empty")

    if len(text) > 10_000:
        raise ValueError("Prompt exceeds maximum length")

    if detect_prompt_injection(text):
        audit_security_event(
            event="prompt_injection_detected",
            user_id=None,
            resource="user_input",
            action="validate",
            allowed=False,
        )
        raise ValueError(
            "Potential prompt injection detected"
        )
