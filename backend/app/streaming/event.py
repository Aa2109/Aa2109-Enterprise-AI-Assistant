from enum import Enum


class StreamEvent(str, Enum):
    START = "start"
    TOKEN = "token"
    METADATA = "metadata"
    DONE = "done"
    ERROR = "error"