__author__ = 'henla464'

from typing import TypedDict

from loraradio.LoraRadioMessageRS import LoraRadioMessageAckRS
from loraradio.LoraRadioMessageRS import LoraRadioMessageStatusRS
from loraradio.LoraRadioMessageRS import LoraRadioMessagePunchReDCoSRS
from loraradio.LoraRadioMessageRS import LoraRadioMessagePunchDoubleReDCoSRS


class InputDataDict(TypedDict):
    MessageType: str
    MessageSubTypeName: str
    MessageSource: str
    Data: bytearray
    ChecksumOK: bool
    MessageID: bytearray | None
    SIStationSerialNumber: str | None
    LoraRadioMessage: LoraRadioMessageAckRS | LoraRadioMessageStatusRS | LoraRadioMessagePunchReDCoSRS | LoraRadioMessagePunchDoubleReDCoSRS | None

