from typing import TypedDict


class InputDataDict(TypedDict):
    MessageType: int
    MessageSubTypeName: str
    MessageSource: str
    Data: bytearray
    ChecksumOK: bool
