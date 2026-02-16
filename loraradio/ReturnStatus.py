from enum import Enum


class ReturnStatus(Enum):
    SENT = 1
    BUSY = 2
    NOREPLY = 3
    OTHER = 4