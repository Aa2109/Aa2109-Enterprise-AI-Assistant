from enum import Enum


class DocumentStatus(str, Enum):
    """
    Represents the current processing state of a document.
    """

    UPLOADED = "UPLOADED"

    EXTRACTING = "EXTRACTING"

    EXTRACTED = "EXTRACTED"

    CHUNKING = "CHUNKING"

    READY = "READY"

    FAILED = "FAILED"
