from enum import Enum


class MemoryType(str, Enum):
    SEMANTIC = "semantic"
    EPISODIC = "episodic"