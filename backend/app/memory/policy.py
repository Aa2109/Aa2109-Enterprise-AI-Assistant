import re

from app.schemas.memory import ExtractedMemory


class MemoryPolicy:

    # Patterns for information that must never be stored.
    SECRET_PATTERNS = [
        # Existing
        re.compile(
            r"\b(password|passwd|pwd)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(api[_\s-]?key|apikey)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(access[_\s-]?token|auth[_\s-]?token|bearer[_\s-]?token)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(secret|client[_\s-]?secret)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(credit[_\s-]?card|card[_\s-]?number|cvv)\b",
            re.IGNORECASE,
        ),

        # Secret-value patterns
        re.compile(
            r"\bsk-[A-Za-z0-9_\-]+\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bbearer\s+[A-Za-z0-9._~+/=-]+\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b",
            re.IGNORECASE,
        ),
    ]

    # Memory must never become an authorization mechanism.
    AUTHORIZATION_PATTERNS = [
        re.compile(
            r"\b(user|i)\s+(am|is)\s+(an?\s+)?admin(istrator)?\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(user|i)\s+(have|has)\s+(admin|administrator|root)\s+(access|permissions?)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(always|automatically)\s+(allow|approve|execute)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(skip|bypass|ignore)\s+(approval|authorization|permissions?)\b",
            re.IGNORECASE,
        ),
    ]

    # Instruction-like content should not become persistent memory.
    INSTRUCTION_PATTERNS = [
        re.compile(
            r"\bignore\s+(all\s+)?(previous|system|developer)\s+instructions\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bforget\s+(all\s+)?previous\s+instructions\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bdo\s+not\s+follow\s+(the\s+)?system\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\byou\s+must\s+(always|never)\b",
            re.IGNORECASE,
        ),
    ]

    def should_store(
        self,
        memory: ExtractedMemory,
    ) -> bool:

        content = memory.content.strip()

        if not content:
            return False

        # Ignore very low-value memories.
        if memory.importance <= 0.0:
            return False

        # Never persist secrets or credentials.
        if self._matches_any(
            content,
            self.SECRET_PATTERNS,
        ):
            return False

        # Never persist authorization claims.
        if self._matches_any(
            content,
            self.AUTHORIZATION_PATTERNS,
        ):
            return False

        # Never persist instruction-like content.
        if self._matches_any(
            content,
            self.INSTRUCTION_PATTERNS,
        ):
            return False

        return True

    @staticmethod
    def _matches_any(
        content: str,
        patterns: list[re.Pattern],
    ) -> bool:

        return any(
            pattern.search(content)
            for pattern in patterns
        )