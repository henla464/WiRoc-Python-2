from enum import Enum


class ReturnStatus(Enum):
    SENT = 1
    BUSY = 2
    NOREPLY = 3
    OTHER = 4
    NOT_ATTACHED = 5  # mesh node has an address but no parent right now (mid-reattach) - transient, not a hard failure
    NOT_JOINED = 6  # mesh node has no address at all / never joined