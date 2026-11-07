__author__ = 'henla464'

from multiprocessing import Pool, Queue, Process, current_process
import queue
import hashlib
import logging
import time
import unittest
from battery import Battery

import loraradio
from loraradio.LoraRadioDataHandler import LoraRadioDataHandler
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from loraradio.LoraRadioMessageRS import LoraRadioMessageRS, LoraRadioMessagePunchDoubleSubSecondRS, \
    LoraRadioMessagePunchSubSecondRS, LoraRadioMessageAckRS, LoraRadioMessageStatusRS
from loraradio.RSCoderLora import RSCoderLora

# Run with sudo env/bin/python3 -m unittest loraradio/TestLoraRadioDataHandler_SubSecond.py
# Variant of TestLoraRadioDataHandler_Minimal.py: same cases and same test method names, but the
# message constants are the subsecond SI punch types (single 16 bytes, double 29 bytes) and their
# ECC/CRC are generated for the subsecond payload (they include the TSS byte).
#
# Some tests are expected to fail until the handler supports ReDCoS/erasure decoding for the
# subsecond types.
#
# Run specific case: sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler_SubSecond.TestLoraRadioDataHandler.test_Case6_FindPunchErasuresDoubleMessage
from settings.settings import SettingsClass
from utils.utils import Utils
from functools import wraps

def max_execution_time(max_time):
    def decorator(test_func):
        @wraps(test_func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            result = test_func(*args, **kwargs)
            elapsed = time.perf_counter() - start_time
            assert elapsed <= max_time, f"Test exceeded {max_time:.2f}s (took {elapsed:.2f}s)"
            return result
        return wrapper
    return decorator


def Hex(text: str) -> bytearray:
    return bytearray.fromhex(text)

def _PositionNames(msg_cls, length: int) -> dict[int, str]:
    positionNames = {}
    for cls in reversed(msg_cls.__mro__):
        for name, value in vars(cls).items():
            if type(value) is int and value >= 0 and name[0].isupper() \
                    and not name.startswith(("MessageType", "NoOf")):
                positionNames[value] = name
    missing = set(range(length)) - set(positionNames)
    if missing:
        raise ValueError(f"{msg_cls.__name__}: no field name for byte positions {sorted(missing)}")
    return positionNames


def _FieldNamesInOrder(msg_cls, length: int, air_order: bool = False) -> tuple:
    # Field order (and interleaving) is read from the message class, so a layout change in
    # LoraRadioMessageRS.py carries over to the test data.
    positionNames = _PositionNames(msg_cls, length)
    return tuple(positionNames[position] for position in
                 (msg_cls.InterleavingInAirOrder if air_order else range(length)))


def _NamedMessage(msg_cls, length: int, air_order: bool = False):
    order = _FieldNamesInOrder(msg_cls, length, air_order)

    def NamedMessage(**values):
        unknown = set(values) - set(order)
        if unknown:
            raise TypeError(f"{msg_cls.__name__}: unknown fields {sorted(unknown)}")
        return bytearray(values[name] for name in order)
    return NamedMessage


def Corrupted(base: bytearray, air_order: bool = False, **fields) -> bytearray:
    # Copy of a message with the named fields replaced; shows exactly which bytes are corrupted.
    msg_cls = _MessageClass(base)
    order = _FieldNamesInOrder(msg_cls, len(base), air_order)
    indexes = {name: index for index, name in enumerate(order)}
    unknown = set(fields) - set(indexes)
    if unknown:
        raise TypeError(f"{msg_cls.__name__}: unknown fields {sorted(unknown)}")
    data = bytearray(base)
    for name, value in fields.items():
        data[indexes[name]] = value
    return data


SubSecondMsg = _NamedMessage(LoraRadioMessagePunchSubSecondRS, 16)
SubSecondMsgAirOrder = _NamedMessage(LoraRadioMessagePunchSubSecondRS, 16, air_order=True)
SubSecondDoubleMsg = _NamedMessage(LoraRadioMessagePunchDoubleSubSecondRS, 29)
SubSecondDoubleMsgAirOrder = _NamedMessage(LoraRadioMessagePunchDoubleSubSecondRS, 29, air_order=True)
SubSecondPayload = _NamedMessage(LoraRadioMessagePunchSubSecondRS, 10)          # header + payload, before ECC/CRC
SubSecondDoublePayload = _NamedMessage(LoraRadioMessagePunchDoubleSubSecondRS, 19)
AckMsg = _NamedMessage(LoraRadioMessageAckRS, 7)
StatusMsg = _NamedMessage(LoraRadioMessageStatusRS, 14)


def Feed(handler, data):
    for b in data:
        handler.AddData(b)


def SubSecondFromRaw(raw, double: bool = False):
    batLow = (raw[0] & LoraRadioMessageRS.BatLowBitMask) > 0
    ackRequested = (raw[0] & LoraRadioMessageRS.AckBitMask) > 0
    if double:
        return LoraRadioMessageCreator.GetPunchDoubleSubSecondMessage(batLow, ackRequested, raw[1:])
    return LoraRadioMessageCreator.GetPunchSubSecondMessage(batLow, ackRequested, raw[1:])


def Corrupt(data: bytearray, offsets: dict[int, int]) -> bytearray:
    for offset, value in offsets.items():
        data[offset] = value
    return data


_MESSAGE_CLASSES_BY_TYPE = {
    LoraRadioMessageRS.MessageTypeLoraAck: LoraRadioMessageAckRS,
    LoraRadioMessageRS.MessageTypeStatus: LoraRadioMessageStatusRS,
    LoraRadioMessageRS.MessageTypeSIPunchSubSecond: LoraRadioMessagePunchSubSecondRS,
    LoraRadioMessageRS.MessageTypeSIPunchDoubleSubSecond: LoraRadioMessagePunchDoubleSubSecondRS,
}


def _MessageClass(data):
    return _MESSAGE_CLASSES_BY_TYPE.get(data[0] & LoraRadioMessageRS.MessageTypeBitMask, LoraRadioMessageRS)


def _FieldNames(msg_cls, length: int) -> dict[int, str]:
    names = {}
    for cls in msg_cls.__mro__:
        for name, value in vars(cls).items():
            if name[0].isupper() and isinstance(value, int) and 0 <= value < length \
                    and not name.startswith(("MessageType", "NoOf")):
                names.setdefault(value, name)
    return names


def _HexByte(value) -> str:
    return "??" if value is None else f"0x{value:02x}"


def _BytesHex(data) -> str:
    return " ".join(f"{b:02x}" for b in data)


def DescribeMessage(msg) -> str:
    if msg is None:
        return "no message decoded"
    data = msg.GetByteArray()
    return (f"type={msg.GetMessageType()} header=0x{data[0]:02x} batteryLow={msg.GetBatteryLow()} "
            f"ackRequested={msg.GetAckRequested()} repeater={msg.GetRepeater()} bytes={_BytesHex(data)}")

class TestLoraRadioDataHandler(unittest.TestCase):

    # Message: 8b97bdf2be0a
                                        # stx         31                            37800=>10:30

    SubSecondMsg_Correct_1 = SubSecondMsg(
        H=0x8b, CN0=0x1f, SN3=0x00, SN2=0x00, SN1=0x00, SN0=0xff,
        CN1Plus=0x00, TH=0x93, TL=0xa8, TSS=0x80, ECC0=0xbb, ECC1=0x1e,
        ECC2=0xc3, ECC3=0xb6, CRC0=0x00, CRC1=0x05,
    )
    SubSecondMsg_Corrupted_1 = Corrupted(
        SubSecondMsg_Correct_1, H=0x8c, CN0=0x10, SN1=0x01, CN1Plus=0x01)

    SubSecondDoubleMsg_Correct_1 = SubSecondDoubleMsg(
        H=0x8c, CN0=0xff, SN3=0x00, SN2=0x00, SN1=0x63, SN0=0x67,
        CN1Plus=0x00, TH=0x03, TL=0x86, TSS=0x80, CN0_2=0xff, SN3_2=0x00,
        SN2_2=0x00, SN1_2=0x63, SN0_2=0x67, CN1Plus_2=0x40, TH_2=0x00, TL_2=0x0c,
        TSS_2=0x40, ECC0=0x46, ECC1=0x84, ECC2=0x41, ECC3=0x79, ECC4=0x3c,
        ECC5=0x05, ECC6=0x8d, ECC7=0xcb, CRC0=0x2d, CRC1=0x54,
    )
    SubSecondDoubleMsg_Corrupted_1 = Corrupted(
        SubSecondDoubleMsg_Correct_1, SN3=0x01, SN2=0x01, CN1Plus=0x01, SN3_2=0x01, SN2_2=0x01,
        TH_2=0x01)
                                                                    #             2    3                  6                      10,   11                     15
    SubSecondPayload_Correct_1_WithoutRS_CS = SubSecondPayload(
        H=0x8b, CN0=0x1f, SN3=0x00, SN2=0x00, SN1=0x00, SN0=0xff,
        CN1Plus=0x00, TH=0x93, TL=0xa8, TSS=0x80,
    )
    SubSecondPayload_Correct_2_WithoutRS_CS = SubSecondPayload(
        H=0x8b, CN0=0x1e, SN3=0x01, SN2=0x00, SN1=0x00, SN0=0xff,
        CN1Plus=0x01, TH=0x93, TL=0xb8, TSS=0x80,
    )
    SubSecondDoublePayload_Correct_1_WithoutRS_CS = SubSecondDoublePayload(
        H=0x8c, CN0=0xff, SN3=0x00, SN2=0x00, SN1=0x63, SN0=0x67,
        CN1Plus=0x00, TH=0x03, TL=0x86, TSS=0x80, CN0_2=0xff, SN3_2=0x00,
        SN2_2=0x00, SN1_2=0x63, SN0_2=0x67, CN1Plus_2=0x00, TH_2=0x03, TL_2=0x9d,
        TSS_2=0x40,
    )
    SubSecondDoublePayload_Correct_2_WithoutRS_CS = SubSecondDoublePayload(
        H=0x8c, CN0=0xfe, SN3=0x00, SN2=0x00, SN1=0x63, SN0=0x67,
        CN1Plus=0x00, TH=0x03, TL=0x86, TSS=0x80, CN0_2=0xff, SN3_2=0x0f,
        SN2_2=0x00, SN1_2=0x63, SN0_2=0x67, CN1Plus_2=0x00, TH_2=0x03, TL_2=0x9d,
        TSS_2=0x40,
    )

    # ---
    Case1_SubSecondDoubleMsg_Previous_WithRS = SubSecondDoubleMsg(
        H=0x8c, CN0=0xe7, SN3=0x00, SN2=0x0f, SN1=0x42, SN0=0x3f,
        CN1Plus=0x40, TH=0x8f, TL=0xe1, TSS=0x80, CN0_2=0xe7, SN3_2=0x00,
        SN2_2=0x0f, SN1_2=0x42, SN0_2=0x3f, CN1Plus_2=0x40, TH_2=0x8f, TL_2=0xbe,
        TSS_2=0x40, ECC0=0x7d, ECC1=0xfc, ECC2=0x06, ECC3=0x73, ECC4=0x1f,
        ECC5=0xd6, ECC6=0x87, ECC7=0xa9, CRC0=0x78, CRC1=0x63,
    )
    Case1_SubSecondDoubleMsg_Correct_WithRS = SubSecondDoubleMsg(
        H=0x8c, CN0=0xe7, SN3=0x00, SN2=0x0f, SN1=0x42, SN0=0x3f,
        CN1Plus=0x40, TH=0x8f, TL=0xe2, TSS=0x80, CN0_2=0xe7, SN3_2=0x00,
        SN2_2=0x0f, SN1_2=0x42, SN0_2=0x3f, CN1Plus_2=0x40, TH_2=0x8f, TL_2=0xe3,
        TSS_2=0x40, ECC0=0x0e, ECC1=0xf5, ECC2=0x6c, ECC3=0x51, ECC4=0x81,
        ECC5=0x1f, ECC6=0xde, ECC7=0xcb, CRC0=0xa8, CRC1=0x78,
    )
    Case1_SubSecondDoubleMsg_Corrupted_WithRS = Corrupted(
        Case1_SubSecondDoubleMsg_Correct_WithRS, H=0x0c, CN0=0x6f, SN3=0x08, SN2=0x07, SN0=0x95,
        CN1Plus=0x6a, TH=0x8d, TL=0xa2, SN2_2=0x0b, SN1_2=0x43, ECC0=0x4a, ECC1=0xf8, ECC2=0xa9,
        ECC3=0x53)
    # The correct message for the  (so wrong in positions: 0  1  2  3, 5, 6, 7, 8, 11, 12, 17, 18, 19, 20)
    # ---

    # ---
    Case2_SubSecondDoubleMsg_Previous_WithRS = SubSecondDoubleMsg(
        H=0x8c, CN0=0x10, SN3=0x00, SN2=0x6a, SN1=0xe3, SN0=0xfc,
        CN1Plus=0x0c, TH=0xa2, TL=0xba, TSS=0x80, CN0_2=0x10, SN3_2=0x00,
        SN2_2=0x15, SN1_2=0x66, SN0_2=0x05, CN1Plus_2=0x0c, TH_2=0xa2, TL_2=0xbf,
        TSS_2=0x40, ECC0=0xa5, ECC1=0x6a, ECC2=0x01, ECC3=0x89, ECC4=0x81,
        ECC5=0x07, ECC6=0xeb, ECC7=0x60, CRC0=0xa7, CRC1=0xb8,
    )
    Case2_SubSecondDoubleMsg_Correct_WithRS = SubSecondDoubleMsg(
        H=0x8c, CN0=0x10, SN3=0x00, SN2=0x73, SN1=0xfb, SN0=0x1e,
        CN1Plus=0x0c, TH=0xa2, TL=0xca, TSS=0x80, CN0_2=0x10, SN3_2=0x00,
        SN2_2=0x11, SN1_2=0x1a, SN0_2=0xf0, CN1Plus_2=0x0c, TH_2=0xa2, TL_2=0xd3,
        TSS_2=0x40, ECC0=0x0c, ECC1=0x4b, ECC2=0xe7, ECC3=0x38, ECC4=0x55,
        ECC5=0x72, ECC6=0xa4, ECC7=0x23, CRC0=0x7e, CRC1=0x2e,
    )
    Case2_SubSecondDoubleMsg_Corrupted_WithRS = Corrupted(
        Case2_SubSecondDoubleMsg_Correct_WithRS, CN0=0xd8, SN3=0x08, SN2=0x3f, CN1Plus=0x1d, TH=0xa3,
        TL=0xdb, ECC4=0xde, ECC5=0x5b, ECC6=0x8b, ECC7=0x93)
    # Wrong in positions: [1,  2,  3, 6, 7, 8, 21, 22, 23, 24]
    # ---

    # ---
    Case3_SubSecondDoubleMsg_Previous_WithRS = SubSecondDoubleMsg(
        H=0x8c, CN0=0x10, SN3=0x00, SN2=0x97, SN1=0xae, SN0=0x8a,
        CN1Plus=0x0c, TH=0x02, TL=0x5a, TSS=0x80, CN0_2=0x10, SN3_2=0x00,
        SN2_2=0x1d, SN1_2=0xfa, SN0_2=0xb5, CN1Plus_2=0x0c, TH_2=0x02, TL_2=0x5e,
        TSS_2=0x40, ECC0=0x13, ECC1=0x99, ECC2=0x12, ECC3=0x94, ECC4=0x29,
        ECC5=0x77, ECC6=0x8c, ECC7=0x77, CRC0=0xed, CRC1=0xed,
    )
    Case3_SubSecondDoubleMsg_Correct_WithRS = SubSecondDoubleMsg(
        H=0x8c, CN0=0x10, SN3=0x00, SN2=0x04, SN1=0xca, SN0=0x8e,
        CN1Plus=0x0d, TH=0x02, TL=0xe5, TSS=0x80, CN0_2=0x10, SN3_2=0x00,
        SN2_2=0x10, SN1_2=0xc9, SN0_2=0x4a, CN1Plus_2=0x0d, TH_2=0x02, TL_2=0xe7,
        TSS_2=0x40, ECC0=0x6a, ECC1=0xcc, ECC2=0x57, ECC3=0x85, ECC4=0x14,
        ECC5=0x95, ECC6=0xfb, ECC7=0x93, CRC0=0x7a, CRC1=0x5c,
    )
    Case3_SubSecondDoubleMsg_Corrupted_WithRS = Corrupted(
        Case3_SubSecondDoubleMsg_Correct_WithRS, CN0_2=0x50, SN3_2=0x44, SN2_2=0x50, SN0_2=0x4e)
    # ---  wrong in positions [9, 8, 10, 11, 16]

    # ---
    Case4_SubSecondDoubleMsg_Previous_WithRS = SubSecondMsg(
        H=0x8b, CN0=0x10, SN3=0x00, SN2=0x1c, SN1=0x3e, SN0=0x21,
        CN1Plus=0x0d, TH=0x05, TL=0xbe, TSS=0x80, ECC0=0x30, ECC1=0x30,
        ECC2=0x50, ECC3=0xfe, CRC0=0xef, CRC1=0xcb,
    )
    Case4_SubSecondDoubleMsg_Correct_WithRS = SubSecondDoubleMsg(
        H=0x8c, CN0=0x10, SN3=0x00, SN2=0x1c, SN1=0x3e, SN0=0x21,
        CN1Plus=0x0d, TH=0x05, TL=0xbe, TSS=0x80, CN0_2=0x10, SN3_2=0x00,
        SN2_2=0x0f, SN1_2=0x1a, SN0_2=0xca, CN1Plus_2=0x0d, TH_2=0x05, TL_2=0xc3,
        TSS_2=0x40, ECC0=0xd9, ECC1=0x60, ECC2=0x93, ECC3=0xd4, ECC4=0x60,
        ECC5=0xae, ECC6=0x9a, ECC7=0x47, CRC0=0xcb, CRC1=0xcb,
    )
    Case4_SubSecondDoubleMsg_Corrupted_WithRS = Corrupted(
        Case4_SubSecondDoubleMsg_Correct_WithRS, ECC4=0xf5, ECC5=0xee, ECC6=0xa1, ECC7=0x76)
    # --- wrong in positions [21, 22, 23, 24]

    # ---
    Case5_SubSecondDoubleMsg_Previous_WithRS = SubSecondMsg(
        H=0x8b, CN0=0x10, SN3=0x00, SN2=0x1b, SN1=0xe7, SN0=0xdc,
        CN1Plus=0x0d, TH=0x06, TL=0x1d, TSS=0x80, ECC0=0x96, ECC1=0x31,
        ECC2=0xe8, ECC3=0x62, CRC0=0x8f, CRC1=0x6c,
    )
    Case5_SubSecondDoubleMsg_Correct_WithRS = SubSecondDoubleMsg(
        H=0x8c, CN0=0x10, SN3=0x00, SN2=0x0e, SN1=0x75, SN0=0x77,
        CN1Plus=0x0d, TH=0x06, TL=0x29, TSS=0x80, CN0_2=0x10, SN3_2=0x00,
        SN2_2=0x04, SN1_2=0xca, SN0_2=0xda, CN1Plus_2=0x0d, TH_2=0x06, TL_2=0x2c,
        TSS_2=0x40, ECC0=0xeb, ECC1=0xb7, ECC2=0x16, ECC3=0x83, ECC4=0x72,
        ECC5=0xdd, ECC6=0xa0, ECC7=0x97, CRC0=0xcd, CRC1=0xca,
    )
    Case5_SubSecondDoubleMsg_Corrupted_WithRS = Corrupted(
        Case5_SubSecondDoubleMsg_Correct_WithRS, CN0_2=0x90, SN3_2=0x80, SN2_2=0x84, SN1_2=0x4a,
        SN0_2=0xd2, TL_2=0x1a)
    # --- wrong in positions [9,10,11,12,13,16]

    # ---
    Case6_SubSecondDoubleMsg_Previous_WithRS = SubSecondMsg(
        H=0x8b, CN0=0x10, SN3=0x00, SN2=0x0f, SN1=0xbb, SN0=0x63,
        CN1Plus=0x0d, TH=0x0c, TL=0x67, TSS=0x80, ECC0=0x7d, ECC1=0x18,
        ECC2=0x01, ECC3=0xce, CRC0=0xdc, CRC1=0x1e,
    )
    Case6_SubSecondDoubleMsg_Correct_WithRS = SubSecondDoubleMsg(
        H=0x8c, CN0=0x10, SN3=0x00, SN2=0x80, SN1=0x86, SN0=0x9e,
        CN1Plus=0x0d, TH=0x0c, TL=0xc3, TSS=0x80, CN0_2=0x10, SN3_2=0x00,
        SN2_2=0x0f, SN1_2=0xe0, SN0_2=0xbf, CN1Plus_2=0x0d, TH_2=0x0c, TL_2=0xb0,
        TSS_2=0x40, ECC0=0x3f, ECC1=0x8e, ECC2=0xc2, ECC3=0xba, ECC4=0x90,
        ECC5=0x6d, ECC6=0x16, ECC7=0xd5, CRC0=0x4d, CRC1=0xdc,
    )
    Case6_SubSecondDoubleMsg_Corrupted_WithRS = Corrupted(
        Case6_SubSecondDoubleMsg_Correct_WithRS, ECC1=0xfe, ECC2=0xb3, ECC3=0x6e)
    # ---wrong in positions [18,19,20]

    # ---
    Case7_SubSecondDoubleMsg_Previous_WithRS = SubSecondMsg(
        H=0x8b, CN0=0x10, SN3=0x00, SN2=0x00, SN1=0x77, SN0=0x0e,
        CN1Plus=0x0d, TH=0x0e, TL=0x30, TSS=0x80, ECC0=0x56, ECC1=0xe3,
        ECC2=0x83, ECC3=0x67, CRC0=0x26, CRC1=0xe1,
    )
    Case7_SubSecondDoubleMsg_Correct_WithRS = SubSecondDoubleMsg(
        H=0x8c, CN0=0x10, SN3=0x00, SN2=0x00, SN1=0x6c, SN0=0x42,
        CN1Plus=0x0d, TH=0x0e, TL=0xa3, TSS=0x80, CN0_2=0x10, SN3_2=0x00,
        SN2_2=0x1f, SN1_2=0x7d, SN0_2=0x8d, CN1Plus_2=0x0d, TH_2=0x0e, TL_2=0xb1,
        TSS_2=0x40, ECC0=0xa7, ECC1=0xf0, ECC2=0xd0, ECC3=0x50, ECC4=0x0a,
        ECC5=0xcc, ECC6=0x18, ECC7=0x96, CRC0=0xdc, CRC1=0xc6,
    )
    Case7_SubSecondDoubleMsg_Corrupted_WithRS = Corrupted(
        Case7_SubSecondDoubleMsg_Correct_WithRS, CN0=0x01, SN3=0x01, SN2=0x10, SN1=0x7d, SN0=0x43)
    # ---

    # ---
    Case8_SubSecondDoubleMsg_Previous_AirOrder_WithRS = SubSecondMsgAirOrder(
        H=0x8b, CRC1=0x17, SN2=0x0f, SN1=0x42, CN0=0xff, SN0=0x3f,
        TH=0x06, TL=0xba, SN3=0x00, TSS=0x80, ECC0=0x1c, ECC1=0x9a,
        CN1Plus=0x41, ECC2=0xe9, ECC3=0x14, CRC0=0x82,
    )
    Case8_SubSecondDoubleMsg_Correct_AirOrder_WithRS = SubSecondDoubleMsgAirOrder(
        H=0x8c, CRC0=0x58, SN2=0x0f, SN1=0x42, SN0=0x3f, CN0=0xff,
        TH=0x06, TL=0xba, SN2_2=0x0f, TSS=0x80, SN1_2=0x42, SN3=0x00,
        SN0_2=0x3f, TH_2=0x06, TL_2=0xbb, CN1Plus=0x41, ECC0=0x86, ECC1=0x63,
        TSS_2=0x40, ECC2=0x34, CN0_2=0xff, ECC3=0x42, ECC4=0x1f, ECC5=0x34,
        SN3_2=0x00, ECC6=0xd6, ECC7=0x23, CN1Plus_2=0x41, CRC1=0x6e,
    )
    Case8_SubSecondDoubleMsg_Corrupted_AirOrder_WithRS = Corrupted(
        Case8_SubSecondDoubleMsg_Correct_AirOrder_WithRS, air_order=True, SN2_2=0x8f, SN1_2=0xc2,
        SN3=0x80, SN0_2=0xbf, TH_2=0x0e, ECC4=0x2e, ECC5=0x88, SN3_2=0xcc, ECC6=0x30, ECC7=0xb8,
        CN1Plus_2=0x53, CRC1=0xc8)
    # ---

    # ---
    Case9_SubSecondDoubleMsg_Previous_AirOrder_WithRS = SubSecondDoubleMsgAirOrder(
        H=0x8c, CRC0=0x21, SN2=0x0f, SN1=0x42, SN0=0x3f, CN0=0xff,
        TH=0x07, TL=0x01, SN2_2=0x0f, TSS=0x80, SN1_2=0x42, SN3=0x00,
        SN0_2=0x3f, TH_2=0x07, TL_2=0x02, CN1Plus=0x41, ECC0=0xbc, ECC1=0xb6,
        TSS_2=0x40, ECC2=0x27, CN0_2=0xff, ECC3=0x79, ECC4=0xc4, ECC5=0xab,
        SN3_2=0x00, ECC6=0xa6, ECC7=0xd2, CN1Plus_2=0x41, CRC1=0xd2,
    )
    Case9_SubSecondDoubleMsg_Correct_AirOrder_WithRS = SubSecondDoubleMsgAirOrder(
        H=0x8c, CRC0=0x27, SN2=0x0f, SN1=0x42, SN0=0x3f, CN0=0xff,
        TH=0x07, TL=0x02, SN2_2=0x0f, TSS=0x80, SN1_2=0x42, SN3=0x00,
        SN0_2=0x3f, TH_2=0x07, TL_2=0x03, CN1Plus=0x41, ECC0=0xb9, ECC1=0x9a,
        TSS_2=0x40, ECC2=0x6e, CN0_2=0xff, ECC3=0x39, ECC4=0x37, ECC5=0x41,
        SN3_2=0x00, ECC6=0x0f, ECC7=0x40, CN1Plus_2=0x41, CRC1=0x6f,
    )
    Case9_SubSecondDoubleMsg_Corrupted_AirOrder_WithRS = Corrupted(
        Case9_SubSecondDoubleMsg_Correct_AirOrder_WithRS, air_order=True, SN2=0x4d, SN0=0x39, SN2_2=0x4f,
        SN3=0x04, SN0_2=0x3b, TH_2=0x03, ECC5=0x06, SN3_2=0x88, ECC6=0xc3, ECC7=0xc1, CRC1=0x57)
    # ---

    # ---
    Case10_SubSecondDoubleMsg_Previous_AirOrder_WithRS = SubSecondMsgAirOrder(
        H=0x8b, CRC1=0x8c, SN2=0x0f, SN1=0x42, CN0=0xff, SN0=0x3f,
        TH=0x07, TL=0x03, SN3=0x00, TSS=0x80, ECC0=0x49, ECC1=0xab,
        CN1Plus=0x41, ECC2=0xc5, ECC3=0xe4, CRC0=0xd5,
    )
    Case10_SubSecondDoubleMsg_Correct_AirOrder_WithRS = SubSecondDoubleMsgAirOrder(
        H=0x8c, CRC0=0x86, SN2=0x0f, SN1=0x42, SN0=0x3f, CN0=0xff,
        TH=0x07, TL=0x4d, SN2_2=0x0f, TSS=0x80, SN1_2=0x42, SN3=0x00,
        SN0_2=0x3f, TH_2=0x07, TL_2=0x4d, CN1Plus=0x41, ECC0=0xc5, ECC1=0x3d,
        TSS_2=0x40, ECC2=0xd8, CN0_2=0xff, ECC3=0xbd, ECC4=0xec, ECC5=0x87,
        SN3_2=0x00, ECC6=0x99, ECC7=0x23, CN1Plus_2=0x41, CRC1=0x7c,
    )
    Case10_SubSecondDoubleMsg_Corrupted_AirOrder_WithRS = Corrupted(
        Case10_SubSecondDoubleMsg_Correct_AirOrder_WithRS, air_order=True, H=0x9c, CRC0=0xdd, SN2=0x1e,
        SN1=0x52, SN0=0x3e, SN3_2=0x10, ECC6=0xf3)
    # --

    # ---
    Case11_SubSecondDoubleMsg_Previous_AirOrder_WithRS = SubSecondMsgAirOrder(
        H=0x8b, CRC1=0xd7, SN2=0x0f, SN1=0x42, CN0=0xff, SN0=0x3f,
        TH=0x09, TL=0x0e, SN3=0x00, TSS=0x80, ECC0=0x8b, ECC1=0x15,
        CN1Plus=0x41, ECC2=0x92, ECC3=0xcc, CRC0=0xb0,
    )
    Case11_SubSecondDoubleMsg_Correct_AirOrder_WithRS = SubSecondDoubleMsgAirOrder(
        H=0x8c, CRC0=0xe0, SN2=0x0f, SN1=0x42, SN0=0x3f, CN0=0xff,
        TH=0x09, TL=0x1a, SN2_2=0x0f, TSS=0x80, SN1_2=0x42, SN3=0x00,
        SN0_2=0x3f, TH_2=0x09, TL_2=0x1b, CN1Plus=0x41, ECC0=0x57, ECC1=0xca,
        TSS_2=0x40, ECC2=0x21, CN0_2=0xff, ECC3=0x69, ECC4=0x71, ECC5=0xd2,
        SN3_2=0x00, ECC6=0x8d, ECC7=0xb6, CN1Plus_2=0x41, CRC1=0x61,
    )
    Case11_SubSecondDoubleMsg_Corrupted_AirOrder_WithRS = Corrupted(
        Case11_SubSecondDoubleMsg_Correct_AirOrder_WithRS, air_order=True, H=0xbc, CRC0=0x2d, SN2=0x6b,
        SN1=0x20, SN0=0x18, CN0=0xdf, TH=0x1b, TL=0x2a, SN2_2=0x0e)
    # --

    # ---
    Case12_SubSecondDoubleMsg_Previous_AirOrder_WithRS = SubSecondDoubleMsgAirOrder(
        H=0x8c, CRC0=0x25, SN2=0x0f, SN1=0x42, SN0=0x3f, CN0=0xff,
        TH=0x09, TL=0x42, SN2_2=0x0f, TSS=0x80, SN1_2=0x42, SN3=0x00,
        SN0_2=0x3f, TH_2=0x09, TL_2=0x43, CN1Plus=0x41, ECC0=0x19, ECC1=0x1e,
        TSS_2=0x40, ECC2=0x53, CN0_2=0xff, ECC3=0x64, ECC4=0x15, ECC5=0xb4,
        SN3_2=0x00, ECC6=0xc5, ECC7=0x19, CN1Plus_2=0x41, CRC1=0xf3,
    )
    Case12_SubSecondDoubleMsg_Correct_AirOrder_WithRS = SubSecondDoubleMsgAirOrder(
        H=0x8c, CRC0=0x1d, SN2=0x0f, SN1=0x42, SN0=0x3f, CN0=0xff,
        TH=0x09, TL=0x43, SN2_2=0x0f, TSS=0x80, SN1_2=0x42, SN3=0x00,
        SN0_2=0x3f, TH_2=0x09, TL_2=0x44, CN1Plus=0x41, ECC0=0x13, ECC1=0xd0,
        TSS_2=0x40, ECC2=0x3b, CN0_2=0xff, ECC3=0x9f, ECC4=0xaf, ECC5=0xbd,
        SN3_2=0x00, ECC6=0x93, ECC7=0xad, CN1Plus_2=0x41, CRC1=0xc8,
    )
    Case12_SubSecondDoubleMsg_Corrupted_AirOrder_WithRS = Corrupted(
        Case12_SubSecondDoubleMsg_Correct_AirOrder_WithRS, air_order=True, ECC5=0xd2, SN3_2=0x88,
        ECC6=0xd6, ECC7=0xa4, CN1Plus_2=0x03, CRC1=0xb9)
    # --

    # ---
    Case13_SubSecondDoubleMsg_Previous_AirOrder_WithRS = SubSecondDoubleMsgAirOrder(
        H=0x8c, CRC0=0x59, SN2=0x0f, SN1=0x42, SN0=0x3f, CN0=0xff,
        TH=0x8b, TL=0x14, SN2_2=0x0f, TSS=0x80, SN1_2=0x42, SN3=0x00,
        SN0_2=0x3f, TH_2=0x8b, TL_2=0x15, CN1Plus=0x41, ECC0=0xb1, ECC1=0x79,
        TSS_2=0x40, ECC2=0x87, CN0_2=0xff, ECC3=0xd6, ECC4=0xc3, ECC5=0xe9,
        SN3_2=0x00, ECC6=0x6f, ECC7=0x91, CN1Plus_2=0x41, CRC1=0xcc,
    )
    Case13_SubSecondDoubleMsg_Correct_AirOrder_WithRS = SubSecondDoubleMsgAirOrder(
        H=0x8c, CRC0=0x59, SN2=0x0f, SN1=0x42, SN0=0x3f, CN0=0xff,
        TH=0x8b, TL=0x14, SN2_2=0x0f, TSS=0x80, SN1_2=0x42, SN3=0x00,
        SN0_2=0x3f, TH_2=0x8b, TL_2=0x15, CN1Plus=0x41, ECC0=0xb1, ECC1=0x79,
        TSS_2=0x40, ECC2=0x87, CN0_2=0xff, ECC3=0xd6, ECC4=0xc3, ECC5=0xe9,
        SN3_2=0x00, ECC6=0x6f, ECC7=0x91, CN1Plus_2=0x41, CRC1=0xcc,
    )
    Case13_SubSecondDoubleMsg_Corrupted_AirOrder_WithRS = Corrupted(
        Case13_SubSecondDoubleMsg_Correct_AirOrder_WithRS, air_order=True, H=0x9c, CRC0=0xb7, SN2=0xb6,
        SN1=0x13, SN0=0x33, CN0=0xfe, TL=0x15, SN2_2=0x4f, SN3=0x44, TH_2=0xdf, TL_2=0x51,
        CN1Plus=0x54, ECC0=0x10, ECC1=0xef, ECC2=0x56, CN0_2=0xf7, ECC3=0x3d)
    # --


    # ---
    Case1_SubSecondMsg_Previous_WithRS = SubSecondMsg(
        H=0x8b, CN0=0xe7, SN3=0x00, SN2=0x0f, SN1=0x42, SN0=0x3f,
        CN1Plus=0x40, TH=0x91, TL=0x9e, TSS=0x80, ECC0=0xe1, ECC1=0x98,
        ECC2=0x50, ECC3=0xf8, CRC0=0xe8, CRC1=0xca,
    )
    Case1_SubSecondMsg_Correct_WithRS = SubSecondMsg(
        H=0x8b, CN0=0x10, SN3=0x00, SN2=0x1f, SN1=0x15, SN0=0x8e,
        CN1Plus=0x0c, TH=0x91, TL=0xdf, TSS=0x80, ECC0=0xee, ECC1=0x1f,
        ECC2=0x6c, ECC3=0x40, CRC0=0x51, CRC1=0xa9,
    )
    Case1_SubSecondMsg_Corrupted_WithRS = Corrupted(
        Case1_SubSecondMsg_Correct_WithRS, H=0x9b, CN0=0x11, SN3=0x01, SN2=0x1e, SN1=0x14, TL=0x1f,
        ECC0=0xa8, ECC1=0x55, ECC2=0xad, ECC3=0x1d)
    # -- wrong in positions 0, 1, 2, 3, 4, 8, 9, 10, 11, 12

    # ---
    Case2_SubSecondMsg_Previous_WithRS = SubSecondMsg(
        H=0x8b, CN0=0x10, SN3=0x00, SN2=0x1f, SN1=0x15, SN0=0x8e,
        CN1Plus=0x0c, TH=0x9b, TL=0xe1, TSS=0x80, ECC0=0x66, ECC1=0x6f,
        ECC2=0x68, ECC3=0x88, CRC0=0x6f, CRC1=0x2a,
    )
    Case2_SubSecondMsg_Correct_WithRS = SubSecondMsg(
        H=0x8b, CN0=0x10, SN3=0x00, SN2=0x1f, SN1=0x7d, SN0=0x9e,
        CN1Plus=0x0c, TH=0x9e, TL=0xb1, TSS=0x80, ECC0=0x36, ECC1=0x22,
        ECC2=0x94, ECC3=0x44, CRC0=0xc8, CRC1=0x35,
    )
    Case2_SubSecondMsg_Corrupted_WithRS = Corrupted(
        Case2_SubSecondMsg_Correct_WithRS, CN0=0x36, SN3=0x42, SN2=0x1b, SN1=0x37, SN0=0x60,
        CN1Plus=0xc0, TH=0x01, TL=0x85, ECC0=0xfa, ECC1=0x44)
    # -- wrong in positions 1, 2, 3, 4, 5,6,7, 8, 9, 10

    # ---
    Case3_SubSecondMsg_Previous_WithRS = SubSecondMsg(
        H=0x8b, CN0=0x10, SN3=0x00, SN2=0x04, SN1=0xc8, SN0=0x05,
        CN1Plus=0x0c, TH=0xa2, TL=0x71, TSS=0x80, ECC0=0xed, ECC1=0x74,
        ECC2=0x7a, ECC3=0xee, CRC0=0x1f, CRC1=0x0d,
    )
    Case3_SubSecondMsg_Correct_WithRS = SubSecondMsg(
        H=0x8b, CN0=0x10, SN3=0x00, SN2=0x6a, SN1=0xe3, SN0=0xfc,
        CN1Plus=0x0c, TH=0xa2, TL=0xba, TSS=0x80, ECC0=0x56, ECC1=0xee,
        ECC2=0x6f, ECC3=0xad, CRC0=0xac, CRC1=0xab,
    )
    Case3_SubSecondMsg_Corrupted_WithRS = Corrupted(
        Case3_SubSecondMsg_Correct_WithRS, H=0x9b, CN0=0x00, SN3=0x41, SN2=0x3a, SN1=0xf2, CN1Plus=0x2e,
        TH=0x80, TL=0x8b)
    # -- wrong in positions 1, 2, 3, 4, 6,7, 8

    # ---
    Case4_SubSecondMsg_Previous_WithRS = SubSecondMsg(
        H=0x8b, CN0=0x10, SN3=0x00, SN2=0x1f, SN1=0xb5, SN0=0x6e,
        CN1Plus=0x0c, TH=0xa6, TL=0x65, TSS=0x80, ECC0=0xe8, ECC1=0xc2,
        ECC2=0x9a, ECC3=0xa0, CRC0=0x96, CRC1=0x4f,
    )
    Case4_SubSecondMsg_Correct_WithRS = SubSecondMsg(
        H=0x8b, CN0=0x10, SN3=0x00, SN2=0x00, SN1=0xab, SN0=0x13,
        CN1Plus=0x0c, TH=0xa6, TL=0x80, TSS=0x80, ECC0=0x70, ECC1=0x1f,
        ECC2=0x6e, ECC3=0x88, CRC0=0x75, CRC1=0x5a,
    )
    Case4_SubSecondMsg_Corrupted_WithRS = Corrupted(
        Case4_SubSecondMsg_Correct_WithRS, ECC0=0x69, ECC1=0xef, ECC2=0x5d, ECC3=0xe3, CRC0=0x00,
        CRC1=0x00)
    # -- wrong in positions 9,10,11,12

    # ---
    Case5_SubSecondMsg_Previous_WithRS = SubSecondMsg(
        H=0x8b, CN0=0x10, SN3=0x00, SN2=0x1f, SN1=0x6b, SN0=0xa4,
        CN1Plus=0x0d, TH=0x05, TL=0x6f, TSS=0x80, ECC0=0xce, ECC1=0x9f,
        ECC2=0xfc, ECC3=0x01, CRC0=0x8c, CRC1=0x35,
    )
    Case5_SubSecondMsg_Correct_WithRS = SubSecondMsg(
        H=0x8b, CN0=0x10, SN3=0x00, SN2=0x03, SN1=0xc7, SN0=0x75,
        CN1Plus=0x0d, TH=0x05, TL=0x7c, TSS=0x80, ECC0=0x20, ECC1=0x11,
        ECC2=0x99, ECC3=0x76, CRC0=0xa5, CRC1=0xd8,
    )
    Case5_SubSecondMsg_Corrupted_WithRS = Corrupted(
        Case5_SubSecondMsg_Correct_WithRS, CN0=0x30, SN3=0x22, SN2=0x01, SN1=0xe7, SN0=0x57,
        CN1Plus=0x07, TH=0xcf, TL=0x12, ECC0=0x21, ECC2=0x17, ECC3=0xc3)
    Case5_SubSecondMsg_Corrupted_WithRS2 = Corrupted(
        Case5_SubSecondMsg_Correct_WithRS, CN0=0x29, SN3=0xe8, SN2=0x7c, SN1=0xa9, SN0=0x71)
    # --

    # ---
    Case6_SubSecondMsg_Previous_WithRS = SubSecondMsg(
        H=0x8b, CN0=0x10, SN3=0x00, SN2=0x20, SN1=0x88, SN0=0x97,
        CN1Plus=0x0d, TH=0x05, TL=0xa4, TSS=0x80, ECC0=0x6b, ECC1=0xcb,
        ECC2=0x1f, ECC3=0x37, CRC0=0x8b, CRC1=0x64,
    )
    Case6_SubSecondMsg_Correct_WithRS = SubSecondMsg(
        H=0x8b, CN0=0x10, SN3=0x00, SN2=0x1c, SN1=0x3e, SN0=0x21,
        CN1Plus=0x0d, TH=0x05, TL=0xbe, TSS=0x80, ECC0=0x30, ECC1=0x30,
        ECC2=0x50, ECC3=0xfe, CRC0=0xef, CRC1=0xcb,
    )
    Case6_SubSecondMsg_Corrupted_WithRS = Corrupted(
        Case6_SubSecondMsg_Correct_WithRS, SN0=0x31, CN1Plus=0x50, TH=0xa8, TL=0x22)
    # -- wrong in positions 5,6,7,8

    # ---
    Case7_SubSecondMsg_Previous_WithRS = SubSecondMsg(
        H=0x8b, CN0=0x10, SN3=0x00, SN2=0x1b, SN1=0xe7, SN0=0xdc,
        CN1Plus=0x0d, TH=0x06, TL=0x1d, TSS=0x80, ECC0=0x96, ECC1=0x31,
        ECC2=0xe8, ECC3=0x62, CRC0=0x8f, CRC1=0x6c,
    )
    Case7_SubSecondMsg_Correct_WithRS = SubSecondMsg(
        H=0x8b, CN0=0x10, SN3=0x00, SN2=0x0e, SN1=0x75, SN0=0x77,
        CN1Plus=0x0d, TH=0x06, TL=0x29, TSS=0x80, ECC0=0x08, ECC1=0xcb,
        ECC2=0x96, ECC3=0x60, CRC0=0xcf, CRC1=0x5e,
    )
    Case7_SubSecondMsg_Corrupted_WithRS = Corrupted(
        Case7_SubSecondMsg_Correct_WithRS, ECC0=0x1f, ECC1=0x57, ECC2=0x17, ECC3=0x7e)
    # -- wrong in positions 9, 10,11,12

    # ---
    Case8_SubSecondMsg_Previous_WithRS = SubSecondMsg(
        H=0x8b, CN0=0x10, SN3=0x00, SN2=0x19, SN1=0xf2, SN0=0xf9,
        CN1Plus=0x0d, TH=0x08, TL=0xba, TSS=0x80, ECC0=0x84, ECC1=0xe4,
        ECC2=0xe6, ECC3=0x30, CRC0=0xac, CRC1=0xe4,
    )
    Case8_SubSecondMsg_Correct_WithRS = SubSecondMsg(
        H=0x8b, CN0=0x10, SN3=0x00, SN2=0x00, SN1=0x3c, SN0=0xe9,
        CN1Plus=0x0d, TH=0x08, TL=0xf4, TSS=0x80, ECC0=0x89, ECC1=0x20,
        ECC2=0xf2, ECC3=0x64, CRC0=0x0e, CRC1=0x6e,
    )
    Case8_SubSecondMsg_Corrupted_WithRS = Corrupted(
        Case8_SubSecondMsg_Correct_WithRS, ECC1=0xf4, ECC2=0xc4, ECC3=0xd0)
    # --

    # -- wrong in positions 10,11,12
    Case8_SubSecondMsg_Corrupted_WithRS2 = Corrupted(
        Case8_SubSecondMsg_Correct_WithRS, SN0=0x29, CN1Plus=0x09, TL=0x38, ECC0=0xb4, ECC2=0x18,
        ECC3=0x1d)
    Case8_SubSecondMsg_Corrupted_WithRS_BestCombination = Corrupted(
        Case8_SubSecondMsg_Correct_WithRS, ECC2=0xc4, ECC3=0xd0)
    # -- wrong in positions 9,11,12

    # ---
    Case9_SubSecondMsg_Previous_AirOrder_WithRS = SubSecondDoubleMsgAirOrder(
        H=0x8c, CRC0=0x21, SN2=0x0f, SN1=0x42, SN0=0x3f, CN0=0xff,
        TH=0x07, TL=0x01, SN2_2=0x0f, TSS=0x80, SN1_2=0x42, SN3=0x00,
        SN0_2=0x3f, TH_2=0x07, TL_2=0x02, CN1Plus=0x41, ECC0=0xbc, ECC1=0xb6,
        TSS_2=0x40, ECC2=0x27, CN0_2=0xff, ECC3=0x79, ECC4=0xc4, ECC5=0xab,
        SN3_2=0x00, ECC6=0xa6, ECC7=0xd2, CN1Plus_2=0x41, CRC1=0xd2,
    )
    Case9_SubSecondMsg_Correct_AirOrder_WithRS = SubSecondMsgAirOrder(
        H=0x8b, CRC1=0x58, SN2=0x0f, SN1=0x42, CN0=0xff, SN0=0x3f,
        TH=0x07, TL=0x02, SN3=0x00, TSS=0x80, ECC0=0x2a, ECC1=0xfc,
        CN1Plus=0x41, ECC2=0x17, ECC3=0x03, CRC0=0x02,
    )
    Case9_SubSecondMsg_Corrupted_AirOrder_WithRS = Corrupted(
        Case9_SubSecondMsg_Correct_AirOrder_WithRS, air_order=True, H=0xcb, CRC1=0xc7, SN2=0x0b,
        SN1=0x02, CN0=0xfb)
    # --

    # ---
    Case10_SubSecondMsg_Previous_AirOrder_WithRS = SubSecondMsgAirOrder(
        H=0x8b, CRC1=0x8c, SN2=0x0f, SN1=0x42, CN0=0xff, SN0=0x3f,
        TH=0x07, TL=0x03, SN3=0x00, TSS=0x80, ECC0=0x49, ECC1=0xab,
        CN1Plus=0x41, ECC2=0xc5, ECC3=0xe4, CRC0=0xd5,
    )
    Case10_SubSecondMsg_Correct_AirOrder_WithRS = SubSecondMsgAirOrder(
        H=0x8b, CRC1=0x4d, SN2=0x0f, SN1=0x42, CN0=0xff, SN0=0x3f,
        TH=0x07, TL=0x4b, SN3=0x00, TSS=0x80, ECC0=0x93, ECC1=0x4d,
        CN1Plus=0x41, ECC2=0xa5, ECC3=0xf0, CRC0=0x93,
    )
    Case10_SubSecondMsg_Corrupted_AirOrder_WithRS = Corrupted(
        Case10_SubSecondMsg_Correct_AirOrder_WithRS, air_order=True, H=0xab, SN2=0x2d, CN0=0xfd,
        SN0=0xb7, SN3=0x08, ECC1=0x40, CN1Plus=0x40, ECC2=0x89, ECC3=0x7d)
    # --

    # ---
    Case11_SubSecondMsg_Previous_AirOrder_WithRS = SubSecondMsgAirOrder(
        H=0x8b, CRC1=0xd7, SN2=0x0f, SN1=0x42, CN0=0xff, SN0=0x3f,
        TH=0x09, TL=0x0e, SN3=0x00, TSS=0x80, ECC0=0x8b, ECC1=0x15,
        CN1Plus=0x41, ECC2=0x92, ECC3=0xcc, CRC0=0xb0,
    )
    Case11_SubSecondMsg_Correct_AirOrder_WithRS = SubSecondMsgAirOrder(
        H=0x8b, CRC1=0xba, SN2=0x0f, SN1=0x42, CN0=0xff, SN0=0x3f,
        TH=0x09, TL=0x1a, SN3=0x00, TSS=0x80, ECC0=0x64, ECC1=0x4d,
        CN1Plus=0x41, ECC2=0x5c, ECC3=0xa1, CRC0=0x20,
    )
    Case11_SubSecondMsg_Corrupted_AirOrder_WithRS = Corrupted(
        Case11_SubSecondMsg_Correct_AirOrder_WithRS, air_order=True, CRC1=0xbf, SN1=0x43, CN0=0xde,
        SN0=0x3d, TH=0x29, TL=0x3a, SN3=0x10, ECC0=0xd7, ECC1=0x4c, CN1Plus=0x51)
    # --

    # ---
    Case12_SubSecondMsg_Previous_AirOrder_WithRS = SubSecondMsgAirOrder(
        H=0x8b, CRC1=0xbb, SN2=0x0f, SN1=0x42, CN0=0xff, SN0=0x3f,
        TH=0x09, TL=0x98, SN3=0x00, TSS=0x80, ECC0=0x75, ECC1=0x2b,
        CN1Plus=0x41, ECC2=0x84, ECC3=0x8c, CRC0=0xe5,
    )
    Case12_SubSecondMsg_Correct_AirOrder_WithRS = SubSecondMsgAirOrder(
        H=0x8b, CRC1=0x41, SN2=0x0f, SN1=0x42, CN0=0xff, SN0=0x3f,
        TH=0x09, TL=0xab, SN3=0x00, TSS=0x80, ECC0=0x52, ECC1=0xf9,
        CN1Plus=0x41, ECC2=0x11, ECC3=0xdf, CRC0=0x3f,
    )
    Case12_SubSecondMsg_Corrupted_AirOrder_WithRS = Corrupted(
        Case12_SubSecondMsg_Correct_AirOrder_WithRS, air_order=True, H=0xab, CRC1=0x1b, SN2=0x2f,
        SN1=0x62, CN0=0xfd)
    # --

    # ---
    Case13_SubSecondMsg_Previous_AirOrder_WithRS = SubSecondDoubleMsgAirOrder(
        H=0x8c, CRC0=0x1a, SN2=0x0f, SN1=0x42, SN0=0x3f, CN0=0xff,
        TH=0x8b, TL=0x16, SN2_2=0x0f, TSS=0x80, SN1_2=0x42, SN3=0x00,
        SN0_2=0x3f, TH_2=0x8b, TL_2=0x17, CN1Plus=0x41, ECC0=0x3d, ECC1=0x24,
        TSS_2=0x40, ECC2=0x50, CN0_2=0xff, ECC3=0x45, ECC4=0x9a, ECC5=0xfc,
        SN3_2=0x00, ECC6=0x37, ECC7=0x10, CN1Plus_2=0x41, CRC1=0x2f,
    )
    Case13_SubSecondMsg_Correct_AirOrder_WithRS = SubSecondMsgAirOrder(
        H=0x8b, CRC1=0x79, SN2=0x0f, SN1=0x42, CN0=0xff, SN0=0x3f,
        TH=0x8b, TL=0xb2, SN3=0x00, TSS=0x80, ECC0=0xe9, ECC1=0x9c,
        CN1Plus=0x41, ECC2=0x3a, ECC3=0xb1, CRC0=0xd9,
    )
    Case13_SubSecondMsg_Corrupted_AirOrder_WithRS = Corrupted(
        Case13_SubSecondMsg_Correct_AirOrder_WithRS, air_order=True, H=0xab, SN2=0x2d, CN0=0xfd,
        ECC2=0x92, ECC3=0x73, CRC0=0xe1)
    # --                                                               HEAD   CRC1  SN2   SN1    CN0  SN0    TH    TL   SN3   ECC0  ECC1   W    ECC2  ECC3  CRC0

    # ---
    Case14_AckMsg_Correct_AirOrder_WithRS = AckMsg(
        H=0x85, HASH0=0xff, HASH1=0x39, HASH0_2=0xff, HASH1_2=0x39, HASH0_3=0xff, HASH1_3=0x39)
    Case14_AckMsg_Corrupted_AirOrder_WithRS = Corrupted(
        Case14_AckMsg_Correct_AirOrder_WithRS, H=0x05, HASH1=0x31, HASH0_2=0x77)
    # --

    # ---
    Case15_AckMsg_Correct_AirOrder_WithRS = AckMsg(
        H=0x85, HASH0=0x5d, HASH1=0x04, HASH0_2=0x5d, HASH1_2=0x04, HASH0_3=0x5d, HASH1_3=0x04)
    Case15_AckMsg_Corrupted_AirOrder_WithRS = Corrupted(
        Case15_AckMsg_Correct_AirOrder_WithRS, H=0xc5, HASH1=0x40, HASH0_2=0x59, HASH1_2=0x00)
    # --

    # ---
    Case16_AckMsg_Correct_AirOrder_WithRS = AckMsg(
        H=0x85, HASH0=0x57, HASH1=0xb4, HASH0_2=0x57, HASH1_2=0xb4, HASH0_3=0x57, HASH1_3=0xb4)
    Case16_AckMsg_Corrupted_AirOrder_WithRS = Corrupted(
        Case16_AckMsg_Correct_AirOrder_WithRS, H=0xe5, HASH0=0x51, HASH1=0x92, HASH0_2=0x53,
        HASH1_2=0xb0)
    # --

    # ---
    Case17_StatusMsg_Previous_AirOrder_WithRS = StatusMsg(
        H=0x04, BAT=0x45, CN0=0x00, RELAYPATHNO=0x00, BT0=0xb0, BT1=0x02, BT2=0x47, BT3=0x00,
        BT4=0xd7, BT5=0x6d, ECC0=0x89, ECC1=0xbd, ECC2=0x6a, ECC3=0x50)
    Case17_StatusMsg_Correct_AirOrder_WithRS = StatusMsg(
        H=0x04, BAT=0x45, CN0=0x00, RELAYPATHNO=0x00, BT0=0xb0, BT1=0x02, BT2=0x47, BT3=0x00,
        BT4=0xd7, BT5=0x6d, ECC0=0x89, ECC1=0xbd, ECC2=0x6a, ECC3=0x50)
    Case17_StatusMsg_Corrupted_AirOrder_WithRS = Corrupted(
        Case17_StatusMsg_Correct_AirOrder_WithRS, H=0xc4, BAT=0xcd, CN0=0x40, RELAYPATHNO=0x04,
        BT0=0xd8, BT1=0x20, BT2=0x17, BT3=0x07, BT4=0xd5)
    # --

    # ---
    Case18_SubSecondMsg_Previous_AirOrder_WithRS = SubSecondDoubleMsgAirOrder(
        H=0x8c, CRC0=0x86, SN2=0x0f, SN1=0x42, SN0=0x3f, CN0=0xff,
        TH=0x7d, TL=0x88, SN2_2=0x0f, TSS=0x80, SN1_2=0x42, SN3=0x00,
        SN0_2=0x3f, TH_2=0x7d, TL_2=0x89, CN1Plus=0x41, ECC0=0x22, ECC1=0x04,
        TSS_2=0x40, ECC2=0x8e, CN0_2=0xff, ECC3=0x67, ECC4=0x61, ECC5=0x8a,
        SN3_2=0x00, ECC6=0x54, ECC7=0x3d, CN1Plus_2=0x41, CRC1=0x12,
    )
    Case18_SubSecondMsg_Correct_AirOrder_WithRS = SubSecondMsgAirOrder(
        H=0x8b, CRC1=0x6e, SN2=0x0f, SN1=0x42, CN0=0xff, SN0=0x3f,
        TH=0x7d, TL=0x9f, SN3=0x00, TSS=0x80, ECC0=0x54, ECC1=0xc2,
        CN1Plus=0x41, ECC2=0xfb, ECC3=0x48, CRC0=0x83,
    )
    Case18_SubSecondMsg_Corrupted_AirOrder_WithRS = Corrupted(
        Case18_SubSecondMsg_Correct_AirOrder_WithRS, air_order=True, CRC1=0x36, CN0=0xfe, ECC2=0x7c,
        ECC3=0xba, CRC0=0xe5)
    # --

    # ---
    Case19_SubSecondMsg_Previous_AirOrder_WithRS = SubSecondMsgAirOrder(
        H=0x8b, CRC1=0x7e, SN2=0x0f, SN1=0x42, CN0=0xff, SN0=0x3d,
        TH=0xa0, TL=0x16, SN3=0x02, TSS=0x80, ECC0=0x19, ECC1=0x25,
        CN1Plus=0x41, ECC2=0x27, ECC3=0xd6, CRC0=0xa8,
    )
    Case19_SubSecondMsg_Correct_AirOrder_WithRS = SubSecondMsgAirOrder(
        H=0x8b, CRC1=0x09, SN2=0x0f, SN1=0x42, CN0=0xff, SN0=0x3f,
        TH=0x80, TL=0x16, SN3=0x00, TSS=0x80, ECC0=0x6d, ECC1=0x16,
        CN1Plus=0x41, ECC2=0x26, ECC3=0x0c, CRC0=0x3d,
    )
    Case19_SubSecondMsg_Corrupted_AirOrder_WithRS = Corrupted(
        Case19_SubSecondMsg_Correct_AirOrder_WithRS, air_order=True, H=0xcb, CRC1=0x54, SN2=0x63,
        SN1=0x40, CN0=0xe9, SN0=0x1d, TH=0xa0, TL=0x17, SN3=0x03)
    # --

    # ---
    Case20_AckMsg_Correct_AirOrder_WithRS = AckMsg(
        H=0x85, HASH0=0xf4, HASH1=0x54, HASH0_2=0xf4, HASH1_2=0x54, HASH0_3=0xf4, HASH1_3=0x54)
    Case20_AckMsg_Corrupted_AirOrder_WithRS = Corrupted(
        Case20_AckMsg_Correct_AirOrder_WithRS, HASH0=0xf6, HASH1=0x56, HASH0_2=0xf6, HASH1_2=0xd4,
        HASH0_3=0x0a, HASH1_3=0x3e)
    # --

    # ---
    Case21_AckMsg_Correct_AirOrder_WithRS = AckMsg(
        H=0x85, HASH0=0x8d, HASH1=0xa5, HASH0_2=0x8d, HASH1_2=0xa5, HASH0_3=0x8d, HASH1_3=0xa5)
    Case21_AckMsg_Corrupted_AirOrder_WithRS = Corrupted(
        Case21_AckMsg_Correct_AirOrder_WithRS, H=0xc5, HASH0=0x45, HASH1=0x67, HASH0_2=0x61,
        HASH1_2=0x87, HASH0_3=0x7f, HASH1_3=0x2b)
    # -- many bit error

    # ---
    Case22_AckMsg_Correct_AirOrder_WithRS = AckMsg(
        H=0x85, HASH0=0x3b, HASH1=0xb2, HASH0_2=0x3b, HASH1_2=0xb2, HASH0_3=0x3b, HASH1_3=0xb2)
    Case22_AckMsg_Corrupted_AirOrder_WithRS = Corrupted(
        Case22_AckMsg_Correct_AirOrder_WithRS, HASH0=0xbb, HASH1=0x32, HASH1_2=0xf2, HASH0_3=0x7f,
        HASH1_3=0xf2)
    # --

    # ---
    Case23_AckMsg_Correct_AirOrder_WithRS = AckMsg(
        H=0x85, HASH0=0x29, HASH1=0xc2, HASH0_2=0x29, HASH1_2=0xc2, HASH0_3=0x29, HASH1_3=0xc2)
    Case23_AckMsg_Corrupted_AirOrder_WithRS = Corrupted(
        Case23_AckMsg_Correct_AirOrder_WithRS, HASH0=0x2f, HASH1=0x90, HASH0_2=0x2d, HASH1_2=0x43,
        HASH1_3=0xca)
    # --

    # ---
    Case24_AckMsg_Correct_AirOrder_WithRS = AckMsg(
        H=0x85, HASH0=0xf7, HASH1=0x98, HASH0_2=0xf7, HASH1_2=0x98, HASH0_3=0xf7, HASH1_3=0x98)
    Case24_AckMsg_Corrupted_AirOrder_WithRS = Corrupted(
        Case24_AckMsg_Correct_AirOrder_WithRS, H=0xc5, HASH1=0x9c, HASH0_2=0xfb, HASH1_2=0x84,
        HASH0_3=0xe6, HASH1_3=0x00)
    # --

    # --- Example that generated many message alternatives and took way to much time to decode during o-ringen
    Case25_SubSecondDoubleMsg_Previous_AirOrder_WithRS = SubSecondDoubleMsgAirOrder(
        H=0x8c, CRC0=0x12, SN2=0x21, SN1=0xc9, SN0=0xa3, CN0=0x40,
        TH=0x98, TL=0xa3, SN2_2=0x7a, TSS=0x80, SN1_2=0x3b, SN3=0x00,
        SN0_2=0x70, TH_2=0x98, TL_2=0xa4, CN1Plus=0x02, ECC0=0x44, ECC1=0x28,
        TSS_2=0x40, ECC2=0x62, CN0_2=0x40, ECC3=0x5d, ECC4=0x9e, ECC5=0xb9,
        SN3_2=0x0f, ECC6=0x75, ECC7=0x3f, CN1Plus_2=0x02, CRC1=0xb7,
    )
    Case25_SubSecondDoubleMsg_Correct_AirOrder_WithRS = SubSecondDoubleMsgAirOrder(
        H=0x8c, CRC0=0x60, SN2=0x82, SN1=0x18, SN0=0x79, CN0=0x40,
        TH=0x98, TL=0xa4, SN2_2=0x8a, TSS=0x80, SN1_2=0xb5, SN3=0x0f,
        SN0_2=0x71, TH_2=0x98, TL_2=0xa6, CN1Plus=0x02, ECC0=0x3d, ECC1=0xb8,
        TSS_2=0x40, ECC2=0x7c, CN0_2=0x40, ECC3=0x9e, ECC4=0x3c, ECC5=0xa0,
        SN3_2=0x00, ECC6=0x5f, ECC7=0x48, CN1Plus_2=0x02, CRC1=0x84,
    )
    Case25_SubSecondDoubleMsg_Corrupted_AirOrder_WithRS = Corrupted(
        Case25_SubSecondDoubleMsg_Correct_AirOrder_WithRS, air_order=True, CN1Plus=0x82, ECC0=0xda,
        ECC1=0xc7, ECC2=0x0a, CN0_2=0xd2, ECC3=0xec, ECC4=0x0b, ECC5=0xda, SN3_2=0xfa, ECC6=0x80,
        ECC7=0x4c, CN1Plus_2=0x4e, CRC1=0x3c)
    # ---

    # --- Example that generated many message alternatives and took way to much time to decode during o-ringen
    Case26_SubSecondDoubleMsg_Corrupted_AirOrder_WithRS = SubSecondDoubleMsgAirOrder(
        H=0xcc, CRC0=0xd1, SN2=0x7a, SN1=0x7d, SN0=0xbe, CN0=0x11,
        TH=0x15, TL=0xd9, SN2_2=0x15, TSS=0x80, SN1_2=0xd9, SN3=0x68,
        SN0_2=0xe9, TH_2=0x14, TL_2=0x52, CN1Plus=0xb2, ECC0=0x4c, ECC1=0x4d,
        TSS_2=0x40, ECC2=0x00, CN0_2=0x99, ECC3=0x19, ECC4=0x3c, ECC5=0x0c,
        SN3_2=0x4d, ECC6=0x47, ECC7=0x03, CN1Plus_2=0x2f, CRC1=0x87,
    )
    # ---

    # --- Many errors, don't know correct values. Used to test maximum alternatives
    Case27_SubSecondDoubleMsg_Corrupted_WithRS = SubSecondDoubleMsg(
        H=0xcc, CN0=0x11, SN3=0xff, SN2=0x7a, SN1=0x7d, SN0=0xbe,
        CN1Plus=0xb2, TH=0x92, TL=0x18, TSS=0x80, CN0_2=0x99, SN3_2=0xff,
        SN2_2=0x15, SN1_2=0xd9, SN0_2=0xe9, CN1Plus_2=0x2f, TH_2=0x92, TL_2=0x18,
        TSS_2=0x40, ECC0=0x4c, ECC1=0x4d, ECC2=0x00, ECC3=0x19, ECC4=0x3c,
        ECC5=0x0c, ECC6=0x4d, ECC7=0x47, CRC0=0x03, CRC1=0x2f,
    )
    #                                                                   H     CN0  SN3  SN2    SN1  SN0  CN1Plus  TH   TL    CN0   SN3   SN2   SN1   SN0 CN1Plus TH    TL   ECC0  ECC1  ECC2  ECC3  ECC4  ECC5  ECC6  ECC7  CRC0  CRC1
    Case27_SubSecondMsg_Correct_Previous = SubSecondMsg(
        H=0x8b, CN0=0x1f, SN3=0x00, SN2=0x00, SN1=0x00, SN0=0xff,
        CN1Plus=0x00, TH=0x93, TL=0xa8, TSS=0x80, ECC0=0xbb, ECC1=0x1e,
        ECC2=0xc3, ECC3=0xb6, CRC0=0x00, CRC1=0x05,
    )


# # c8d17a7dbe1115d915d968e91452b24c4d0099193c0c4d47032f87bb

#               IN HEX           HEADER   CRC0     CRC1     ECC0     ECC1     ECC2     ECC3
    # Ack sent:     85f4541ae4974c	10000101 11110100 01010100 00011010 11100100 10010111 01001100
    # Ack received: 85f65618646926	10000101 11110110 01010110 00011000 01100100 01101001 00100110
    # Wrong bits       x x xx xxxx                  x        x        x  x        xxxxxxx   xx x x
    #
    # Total no of bit errors: 15
    # Majority voting would give 2 bit error for the two bytes
    # Best selected bytes: 2 bit error
    # Best selected 4bit groups: 1 bit error
    #
    # Ack sent:     858da51782764e	10000101 10001101 10100101 00010111 10000010 01110110 01001110
    # Ack received: c54567fba084c1	11000101 01000101 01100111 11111011 10100000 10000100 11000001
    # Wrong bits:   x xxxxxxxxxxxx    x       xx  x    xx    x  xxx xx     x   x  xxxx  x  x   xxx
    #                                         33212110 21101130
    #
    # Total no of bit errors: 22 (plus 1 in header)
    # Majority voting would give 6 bit error for the two bytes
    # Best selected bytes: 5 bit error
    # Best selected 4-bit: 5 bit error
    #
    # Ack sent:     853bb2c84b9916	10000101 00111011 10110010 11001000 01001011 10011001 00010110
    # Ack received: 85bb32c80bdd56	10000101 10111011 00110010 11001000 00001011 11011101 01010110
    # Wrong bits:     x x   x xxx             x        x                  x        x   x    x
    #
    # Total no of bit errors: 6
    # Majority voting would give 1 bit error for the two bytes
    # Best selected bytes: 1 bit error
    # Best selected 4-bit: 1 bit error
    #
    #
    # Ack sent:     8529c29a348242	10000101 00101001 11000010 10011010 00110100 10000010 01000010
    # Ack received: 852f909eb5824a	10000101 00101111 10010000 10011110 10110101 10000010 01001010
    # Wrong bits:      xxx xxx   x                 xx   x x  x       x   x      x              x
    #
    # Total no of bit errors: 9
    # Majority voting would give 1 bit error for the two bytes
    # Best selected bytes: 1 bit error
    # Best selected 4-bit: 1 bit error
    #
    #
    # Ack sent:     85f798cf6b5b15	10000101 11110111 10011000 11001111 01101011 01011011 00010101
    # Ack received: c5f79cc3774a8d	11000101 11110111 10011100 11000011 01110111 01001010 10001101
    # Wrong bits:   x    x xxxxxxx    x                     x       xx      xxx      x   x x  xx
    #
    # Total no of

    SubSecondMsg_Correct_HighestTHTL = SubSecondMsg(
        H=0x8b, CN0=0x1f, SN3=0x00, SN2=0x00, SN1=0x00, SN0=0xff,
        CN1Plus=0x00, TH=0xa8, TL=0xc0, TSS=0x80, ECC0=0x45, ECC1=0x6b,
        ECC2=0xf0, ECC3=0x5d, CRC0=0xe7, CRC1=0x4c,
    )
    StatusMsg_Correct_WithRS = StatusMsg(
        H=0x04, BAT=0x60, CN0=0x10, RELAYPATHNO=0x00, BT0=0xd4, BT1=0x12, BT2=0x43, BT3=0x24,
        BT4=0x6a, BT5=0x0c, ECC0=0x47, ECC1=0x32, ECC2=0x63, ECC3=0xa5)

    dataHandler = LoraRadioDataHandler(False)

    def setUp(self):
        #LoraRadioDataHandler.WiRocLogger.setLevel(logging.DEBUG)
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        logging.raiseExceptions = False
        # monkey patch a verbose function
        logging.VERBOSE = 5
        logging.addLevelName(logging.VERBOSE, "VERBOSE")
        logging.Logger.verbose = lambda inst, msg, *args, **kwargs: inst.log(logging.VERBOSE, msg, *args, **kwargs)
        logging.LoggerAdapter.verbose = lambda inst, msg, *args, **kwargs: inst.log(logging.VERBOSE, msg, *args, **kwargs)
        logging.verbose = lambda msg, *args, **kwargs: logging.log(logging.VERBOSE, msg, *args, **kwargs)
        Battery.Setup()
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)
        SettingsClass.SetMessageIDOfLastLoraMessageSent(None)
    def assertBytesEqual(self, actual, expected, label: str = "", compare: str = "exact"):
        msg_cls = _MessageClass(expected)
        offset = 0
        if compare == "skip_header":
            actual, expected, offset = actual[1:], expected[1:], 1
        elif compare == "drop_crc":
            actual, expected = actual[:-2], expected[:-2]
        elif compare == "prefix27":
            actual, expected = actual[:27], expected[:27]
        if actual == expected:
            return
        names = _FieldNames(msg_cls, max(len(actual), len(expected)) + offset)
        report = [f"{label}: message bytes differ"]
        for i in range(max(len(actual), len(expected))):
            got = actual[i] if i < len(actual) else None
            want = expected[i] if i < len(expected) else None
            if got != want:
                report.append(f"  offset {offset + i} ({names.get(offset + i, '?')}): "
                              f"expected {_HexByte(want)} got {_HexByte(got)}")
        report.append("  expected: " + _BytesHex(expected))
        report.append("  actual:   " + _BytesHex(actual))
        self.fail("\n".join(report))

    def tearDown(self):
        self.dataHandler.ReceivedPunchMessageDict = {}
        self.dataHandler.LastPunchMessageTime = None
        self.dataHandler.LastPunchMessage = None
        self.dataHandler.LastDoublePunchMessage = None
        self.dataHandler.DataReceived = bytearray()
        SettingsClass.SetMessageIDOfLastLoraMessageSent(None)

    # A sub second punch received at a finish (1 Nov 2026), in air order, without the RSSI byte. Status2 is
    # also 16 bytes, and when it was tried first Reed-Solomon "corrected" this good punch into a valid Status2.
    # The receiver acked it as a status message, so the sender retried the same bytes 63 times in 10 minutes.
    SubSecondPunch_StatusLookalike_AirOrder = Hex("8b 59 80 62 04 34 0f be 00 49 40 d5 01 17 22 26")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_SubSecondPunchNotTakenForStatus2
    def test_SubSecondPunchNotTakenForStatus2(self):
        print("=== START test_SubSecondPunchNotTakenForStatus2 ===")
        data = TestLoraRadioDataHandler.SubSecondPunch_StatusLookalike_AirOrder
        for i in range(0, len(data)):
            self.dataHandler.AddData(data[i:i + 1])
        self.assertEqual(self.dataHandler._GetLikelyMessageTypes()[0], LoraRadioMessageRS.MessageTypeSIPunchSubSecond)
        msg = self.dataHandler._TryGetMessage()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.GetMessageType(), LoraRadioMessageRS.MessageTypeSIPunchSubSecond)
        print("=== END test_SubSecondPunchNotTakenForStatus2 ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_AddData
    def test_AddData(self):
        print("============================================================================================== START test_AddData ==============================================================================================")
        self.dataHandler.AddData(Hex("02"))
        self.assertEqual(self.dataHandler.DataReceived, Hex("02"), "Adding data failed 1")

        self.dataHandler.AddData(Hex("03 04"))
        self.assertEqual(self.dataHandler.DataReceived, Hex("02 03 04"), "Adding data failed 2")
        print("=== END test_AddData ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_IsLongEnoughToBeMessage
    def test_IsLongEnoughToBeMessage(self):
        print("============================================================================================== START test_IsLongEnoughToBeMessage ==============================================================================================")
        self.dataHandler.AddData(Hex("02 03 04"))
        couldBeMsg = self.dataHandler._IsLongEnoughToBeMessage()
        self.assertFalse(couldBeMsg, "3 bytes should not be a message")
        self.dataHandler.AddData(Hex("02 03 04"))
        couldBeMsg = self.dataHandler._IsLongEnoughToBeMessage()
        self.assertFalse(couldBeMsg, "6 bytes should not be a message")
        self.dataHandler.AddData(Hex("02 03 04"))
        couldBeMsg = self.dataHandler._IsLongEnoughToBeMessage()
        self.assertTrue(couldBeMsg, "9 bytes should be a message")
        print("=== END test_IsLongEnoughToBeMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_CacheMessage
    def test_CacheMessage(self):
        print("============================================================================================== START test_CacheMessage ==============================================================================================")
        rsCodes = RSCoderLora.encode(TestLoraRadioDataHandler.SubSecondMsg_Correct_1)
        loraMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(TestLoraRadioDataHandler.SubSecondMsg_Correct_1 + rsCodes)
        self.dataHandler._CachePunchMessage(loraMsg)
        msgAndMetaData = self.dataHandler.ReceivedPunchMessageDict[loraMsg.GetControlNumber()]
        self.assertEqual(loraMsg, msgAndMetaData.GetLoraRadioMessageRS())
        self.assertIsNotNone(self.dataHandler.LastPunchMessageTime)
        self.assertEqual(self.dataHandler.LastPunchMessage,loraMsg)
        print("=== END test_CacheMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case1_FindPunchErasuresDoubleMessage
    def test_Case1_FindPunchErasuresDoubleMessage(self):
        print("============================================================================================== START test_Case1_FindPunchErasuresDoubleMessage ==============================================================================================")

        correctMsg = LoraRadioMessageCreator.GetPunchDoubleSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case1_SubSecondDoubleMsg_Previous_WithRS)
        loraSubSecondMsg1, loraSubSecondMsg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(correctMsg)
        # Cache individual messages but remove the whole double message from data received
        self.dataHandler._CachePunchMessage(loraSubSecondMsg1)
        self.dataHandler._CachePunchMessage(loraSubSecondMsg2)

        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchDoubleSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case1_SubSecondDoubleMsg_Corrupted_WithRS)
        
        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()
        erasures = self.dataHandler._FindReDCoSPunchDoubleErasures(corruptedLoraMsg, totalRetryDelaySeconds)
        print("test_Case1_FindPunchErasuresDoubleMessage: " + str(erasures))
        corruptPositions = [0, 1, 2, 3, 5, 6, 7, 8, 12, 13, 19, 20, 21, 22]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case2_FindPunchErasuresDoubleMessage
    def test_Case2_FindPunchErasuresDoubleMessage(self):
        print("============================================================================================== START test_Case2_FindPunchErasuresDoubleMessage ==============================================================================================")
        correctMsg = LoraRadioMessageCreator.GetPunchDoubleSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case2_SubSecondDoubleMsg_Previous_WithRS)
        loraSubSecondMsg1, loraSubSecondMsg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(correctMsg)
        # Cache individual messages but remove the whole double message from data received
        self.dataHandler._CachePunchMessage(loraSubSecondMsg1)
        self.dataHandler._CachePunchMessage(loraSubSecondMsg2)

        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchDoubleSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case2_SubSecondDoubleMsg_Corrupted_WithRS)
        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()
        erasures = self.dataHandler._FindReDCoSPunchDoubleErasures(corruptedLoraMsg, totalRetryDelaySeconds)
        corruptPositions = [1, 2, 3, 6, 7, 8, 23, 24, 25, 26]
        print("test_Case2_FindPunchErasuresDoubleMessage erasures: " + str(erasures))
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case3_FindPunchErasuresDoubleMessage
    def test_Case3_FindPunchErasuresDoubleMessage(self):
        print("============================================================================================== START test_Case3_FindPunchErasuresDoubleMessage ==============================================================================================")
        correctMsg = LoraRadioMessageCreator.GetPunchDoubleSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case3_SubSecondDoubleMsg_Previous_WithRS)
        loraSubSecondMsg1, loraSubSecondMsg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(correctMsg)
        # Cache individual messages but remove the whole double message from data received
        self.dataHandler._CachePunchMessage(loraSubSecondMsg1)
        self.dataHandler._CachePunchMessage(loraSubSecondMsg2)

        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchDoubleSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case3_SubSecondDoubleMsg_Corrupted_WithRS)
        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()
        erasures = self.dataHandler._FindReDCoSPunchDoubleErasures(corruptedLoraMsg, totalRetryDelaySeconds)
        print("test_Case3_FindPunchErasuresDoubleMessage: " + str(erasures))
        corruptPositions = [8, 10, 11, 12, 17]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case4_FindPunchErasuresDoubleMessage
    def test_Case4_FindPunchErasuresDoubleMessage(self):
        print("============================================================================================== START test_Case4_FindPunchErasuresDoubleMessage ==============================================================================================")
        correctMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case4_SubSecondDoubleMsg_Previous_WithRS)
        self.dataHandler._CachePunchMessage(correctMsg)

        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchDoubleSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case4_SubSecondDoubleMsg_Corrupted_WithRS)
        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()
        erasures = self.dataHandler._FindReDCoSPunchDoubleErasures(corruptedLoraMsg, totalRetryDelaySeconds)
        print("test_Case4_FindPunchErasuresDoubleMessage: " + str(erasures))
        corruptPositions = [23, 24, 25, 26]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case5_FindPunchErasuresDoubleMessage
    def test_Case5_FindPunchErasuresDoubleMessage(self):
        print("============================================================================================== START test_Case5_FindPunchErasuresDoubleMessage ==============================================================================================")
        correctMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case5_SubSecondDoubleMsg_Previous_WithRS)
        self.dataHandler._CachePunchMessage(correctMsg)

        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchDoubleSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case5_SubSecondDoubleMsg_Corrupted_WithRS)
        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()
        erasures = self.dataHandler._FindReDCoSPunchDoubleErasures(corruptedLoraMsg, totalRetryDelaySeconds)
        print("test_Case5_FindPunchErasuresDoubleMessage: " + str(erasures))
        corruptPositions = [10, 11, 12, 13, 14, 17]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case5_GetPunchDoubleMessage
    def test_Case5_GetPunchDoubleMessage(self):
        print("============================================================================================== START test_Case5_GetPunchDoubleMessage ==============================================================================================")
        correctMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case5_SubSecondDoubleMsg_Previous_WithRS)
        self.dataHandler._CachePunchMessage(correctMsg)

        corruptedInAirOrder = LoraRadioMessagePunchDoubleSubSecondRS.InterleaveToAirOrder(TestLoraRadioDataHandler.Case5_SubSecondDoubleMsg_Corrupted_WithRS)
        Feed(self.dataHandler, corruptedInAirOrder)

        # Can be decoded with ReDCos but has many combinations to try
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(10000)
        punchDoubleMsg = self.dataHandler._GetSubSecondDoublePunchMessage()
        self.assertIsNotNone(punchDoubleMsg)

        print("=== END test_Case5_GetPunchDoubleMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case6_FindPunchErasuresDoubleMessage
    def test_Case6_FindPunchErasuresDoubleMessage(self):
        print("============================================================================================== START test_Case6_FindPunchErasuresDoubleMessage ==============================================================================================")
        correctMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case6_SubSecondDoubleMsg_Previous_WithRS)
        self.dataHandler._CachePunchMessage(correctMsg)

        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchDoubleSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case6_SubSecondDoubleMsg_Corrupted_WithRS)
        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()
        erasures = self.dataHandler._FindReDCoSPunchDoubleErasures(corruptedLoraMsg, totalRetryDelaySeconds)
        print("test_Case6_FindPunchErasuresDoubleMessage: " + str(erasures))
        corruptPositions = [20, 21, 22]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case6_GetPunchDoubleMessage
    def test_Case6_GetPunchDoubleMessage(self):
        print("============================================================================================== START test_Case6_GetPunchDoubleMessage ==============================================================================================")
        correctMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case6_SubSecondDoubleMsg_Previous_WithRS)
        self.dataHandler._CachePunchMessage(correctMsg)

        interleaved = LoraRadioMessagePunchDoubleSubSecondRS.InterleaveToAirOrder(TestLoraRadioDataHandler.Case6_SubSecondDoubleMsg_Corrupted_WithRS)
        Feed(self.dataHandler, interleaved)
        punchDoubleMsg = self.dataHandler._GetSubSecondDoublePunchMessage()
        self.assertIsNotNone(punchDoubleMsg)
        print("=== END test_Case6_GetPunchDoubleMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case7_FindPunchErasuresDoubleMessage
    def test_Case7_FindPunchErasuresDoubleMessage(self):
        print("============================================================================================== START test_Case7_FindPunchErasuresDoubleMessage ==============================================================================================")
        correctMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case7_SubSecondDoubleMsg_Previous_WithRS)
        self.dataHandler._CachePunchMessage(correctMsg)
        self.dataHandler.LastPunchMessageTime = time.monotonic() - 9

        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchDoubleSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case7_SubSecondDoubleMsg_Corrupted_WithRS)
        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()
        erasures = self.dataHandler._FindReDCoSPunchDoubleErasures(corruptedLoraMsg, totalRetryDelaySeconds)
        print("test_Case7_FindPunchErasuresDoubleMessage: " + str(erasures))
        corruptPositions = [1, 2, 3, 4, 5]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case7_GetPunchDoubleMessage
    def test_Case7_GetPunchDoubleMessage(self):
        print("============================================================================================== START test_Case7_GetPunchDoubleMessage ==============================================================================================")
        correctMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case7_SubSecondDoubleMsg_Previous_WithRS)
        self.dataHandler._CachePunchMessage(correctMsg)

        interleaved = LoraRadioMessagePunchDoubleSubSecondRS.InterleaveToAirOrder(TestLoraRadioDataHandler.Case7_SubSecondDoubleMsg_Corrupted_WithRS)
        Feed(self.dataHandler, interleaved)
        punchDoubleMsg = self.dataHandler._GetSubSecondDoublePunchMessage()
        self.assertIsNotNone(punchDoubleMsg)
        print("=== END test_Case7_GetPunchDoubleMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case8_GetPunchDoubleMessage
    def test_Case8_GetPunchDoubleMessage(self):
        print("============================================================================================== START test_Case8_GetPunchDoubleMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(10000)

        deinterleaved = LoraRadioMessagePunchDoubleSubSecondRS.DeInterleaveFromAirOrder(
            TestLoraRadioDataHandler.Case8_SubSecondDoubleMsg_Correct_AirOrder_WithRS[:])
        print("Correct message: " + Utils.GetDataInHex(deinterleaved, logging.DEBUG))

        prevDeinterleaved = LoraRadioMessagePunchSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case8_SubSecondDoubleMsg_Previous_AirOrder_WithRS[:])
        prevCorrectMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(prevDeinterleaved)
        self.dataHandler._CachePunchMessage(prevCorrectMsg)
        seconds = 3.4
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds

        interleaved = TestLoraRadioDataHandler.Case8_SubSecondDoubleMsg_Corrupted_AirOrder_WithRS[:]
        Feed(self.dataHandler, interleaved)
        punchDoubleMsg = self.dataHandler._GetSubSecondDoublePunchMessage()
        self.assertIsNotNone(punchDoubleMsg)
        self.assertBytesEqual(punchDoubleMsg.GetByteArray(), LoraRadioMessagePunchDoubleSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case8_SubSecondDoubleMsg_Correct_AirOrder_WithRS), "test_Case8_GetPunchDoubleMessage")
        print("=== END test_Case8_GetPunchDoubleMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case9_GetPunchDoubleMessage
    def test_Case9_GetPunchDoubleMessage(self):
        print("============================================================================================== START test_Case9_GetPunchDoubleMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(800)

        correctMsg = LoraRadioMessagePunchDoubleSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case9_SubSecondDoubleMsg_Correct_AirOrder_WithRS[:])
        print("The correct msg: " + Utils.GetDataInHex(correctMsg, logging.DEBUG))

        deinterleaved = LoraRadioMessagePunchDoubleSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case9_SubSecondDoubleMsg_Previous_AirOrder_WithRS[:])
        prevMsg = LoraRadioMessageCreator.GetPunchDoubleSubSecondMessageByFullMessageData(deinterleaved)
        loraSubSecondMsg1, loraSubSecondMsg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(prevMsg)
        self.dataHandler._CachePunchMessage(loraSubSecondMsg1)
        self.dataHandler._CachePunchMessage(loraSubSecondMsg2)
        seconds = 2.8
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds

        interleaved = TestLoraRadioDataHandler.Case9_SubSecondDoubleMsg_Corrupted_AirOrder_WithRS[:]
        Feed(self.dataHandler, interleaved)
        punchDoubleMsg = self.dataHandler._GetSubSecondDoublePunchMessage()
        if punchDoubleMsg is not None:
            print("Decoded msg: " + Utils.GetDataInHex(punchDoubleMsg.GetByteArray(), logging.DEBUG))
        print("Correct msg: " + Utils.GetDataInHex(LoraRadioMessagePunchDoubleSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case9_SubSecondDoubleMsg_Correct_AirOrder_WithRS), logging.DEBUG))
        self.assertIsNotNone(punchDoubleMsg)
        self.assertBytesEqual(punchDoubleMsg.GetByteArray(), LoraRadioMessagePunchDoubleSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case9_SubSecondDoubleMsg_Correct_AirOrder_WithRS), "test_Case9_GetPunchDoubleMessage")
        print("=== END test_Case9_GetPunchDoubleMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case10_GetPunchDoubleMessage
    def test_Case10_GetPunchDoubleMessage(self):
        print("============================================================================================== START test_Case10_GetPunchDoubleMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        deinterleaved = LoraRadioMessagePunchSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case10_SubSecondDoubleMsg_Previous_AirOrder_WithRS[:])
        prevMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(deinterleaved)
        self.dataHandler._CachePunchMessage(prevMsg)
        seconds = 2.8
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds

        interleaved = TestLoraRadioDataHandler.Case10_SubSecondDoubleMsg_Corrupted_AirOrder_WithRS[:]
        Feed(self.dataHandler, interleaved)
        punchDoubleMsg = self.dataHandler._GetSubSecondDoublePunchMessage()
        self.assertIsNotNone(punchDoubleMsg)
        print("Decoded msg: " + Utils.GetDataInHex(punchDoubleMsg.GetByteArray(), logging.DEBUG))
        print("Correct msg: " + Utils.GetDataInHex(LoraRadioMessagePunchDoubleSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case10_SubSecondDoubleMsg_Correct_AirOrder_WithRS), logging.DEBUG))
        # One of the CRC bytes is wrong so exclude it when comparing.
        self.assertBytesEqual(punchDoubleMsg.GetByteArray(), LoraRadioMessagePunchDoubleSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case10_SubSecondDoubleMsg_Correct_AirOrder_WithRS), "test_Case10_GetPunchDoubleMessage", "drop_crc")
        print("=== END test_Case10_GetPunchDoubleMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case11_GetPunchDoubleMessage
    def test_Case11_GetPunchDoubleMessage(self):
        print("============================================================================================== START test_Case11_GetPunchDoubleMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        deinterleaved = LoraRadioMessagePunchSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case11_SubSecondDoubleMsg_Previous_AirOrder_WithRS[:])
        prevMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(deinterleaved)
        self.dataHandler._CachePunchMessage(prevMsg)
        seconds = 16
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds

        interleaved = TestLoraRadioDataHandler.Case11_SubSecondDoubleMsg_Corrupted_AirOrder_WithRS[:]
        Feed(self.dataHandler, interleaved)
        punchDoubleMsg = self.dataHandler._GetSubSecondDoublePunchMessage()
        self.assertIsNotNone(punchDoubleMsg)
        print("Decoded msg: " + Utils.GetDataInHex(punchDoubleMsg.GetByteArray(), logging.DEBUG))
        print("Correct msg: " + Utils.GetDataInHex(LoraRadioMessagePunchDoubleSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case11_SubSecondDoubleMsg_Correct_AirOrder_WithRS), logging.DEBUG))
        self.assertBytesEqual(punchDoubleMsg.GetByteArray(), LoraRadioMessagePunchDoubleSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case11_SubSecondDoubleMsg_Correct_AirOrder_WithRS), "test_Case11_GetPunchDoubleMessage")
        print("=== END test_Case11_GetPunchDoubleMessage ===")

    #sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case12_GetPunchDoubleMessage
    def test_Case12_GetPunchDoubleMessage(self):
        print("============================================================================================== START test_Case12_GetPunchDoubleMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        deinterleaved = LoraRadioMessagePunchDoubleSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case12_SubSecondDoubleMsg_Previous_AirOrder_WithRS[:])
        prevMsg = LoraRadioMessageCreator.GetPunchDoubleSubSecondMessageByFullMessageData(deinterleaved)
        loraSubSecondMsg1, loraSubSecondMsg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(prevMsg)
        self.dataHandler._CachePunchMessage(loraSubSecondMsg1)
        self.dataHandler._CachePunchMessage(loraSubSecondMsg2)
        seconds = 3.2
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds

        interleaved = TestLoraRadioDataHandler.Case12_SubSecondDoubleMsg_Corrupted_AirOrder_WithRS[:]
        Feed(self.dataHandler, interleaved)
        punchDoubleMsg = self.dataHandler._GetSubSecondDoublePunchMessage()
        self.assertIsNotNone(punchDoubleMsg)
        print("Decoded msg: " + Utils.GetDataInHex(punchDoubleMsg.GetByteArray(), logging.DEBUG))
        print("Correct msg: " + Utils.GetDataInHex(LoraRadioMessagePunchDoubleSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case12_SubSecondDoubleMsg_Correct_AirOrder_WithRS), logging.DEBUG))
        # One of the CRC bytes is wrong so exclude it when comparing.
        self.assertBytesEqual(punchDoubleMsg.GetByteArray(), LoraRadioMessagePunchDoubleSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case12_SubSecondDoubleMsg_Correct_AirOrder_WithRS), "test_Case12_GetPunchDoubleMessage", "drop_crc")
        print("=== END test_Case12_GetPunchDoubleMessage ===")

    #sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case13_GetPunchDoubleMessage
    def test_Case13_GetPunchDoubleMessage(self):
        print("============================================================================================== START test_Case13_GetPunchDoubleMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        interleaved = TestLoraRadioDataHandler.Case13_SubSecondDoubleMsg_Previous_AirOrder_WithRS[:]
        Feed(self.dataHandler, interleaved)
        prevSubSecondDoubleMsg = self.dataHandler.GetMessage()

        seconds = 17.5
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds

        interleaved = TestLoraRadioDataHandler.Case13_SubSecondDoubleMsg_Corrupted_AirOrder_WithRS[:]
        Feed(self.dataHandler, interleaved)
        punchDoubleMsg = self.dataHandler.GetMessage()
        self.assertIsNotNone(punchDoubleMsg)
        print("Decoded msg: " + Utils.GetDataInHex(punchDoubleMsg.GetByteArray(), logging.DEBUG))
        print("Correct msg: " + Utils.GetDataInHex(LoraRadioMessagePunchDoubleSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case13_SubSecondDoubleMsg_Correct_AirOrder_WithRS), logging.DEBUG))
        print("Corrupt msg: " + Utils.GetDataInHex(LoraRadioMessagePunchDoubleSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case13_SubSecondDoubleMsg_Corrupted_AirOrder_WithRS), logging.DEBUG))
        self.assertBytesEqual(punchDoubleMsg.GetByteArray(), LoraRadioMessagePunchDoubleSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case13_SubSecondDoubleMsg_Correct_AirOrder_WithRS), "test_Case13_GetPunchDoubleMessage")
        self.assertBytesEqual(punchDoubleMsg.GetByteArray(), LoraRadioMessagePunchDoubleSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case13_SubSecondDoubleMsg_Previous_AirOrder_WithRS), "test_Case13_GetPunchDoubleMessage")
        print("=== END test_Case13_GetPunchDoubleMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case1_FindPunchErasuresMessage
    def test_Case1_FindPunchErasuresMessage(self):
        print("============================================================================================== START test_Case1_FindPunchErasuresMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        prevMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case1_SubSecondMsg_Previous_WithRS)
        self.dataHandler._CachePunchMessage(prevMsg)

        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case1_SubSecondMsg_Corrupted_WithRS)
        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsg, totalRetryDelaySeconds)
        print("test_Case1_FindPunchErasuresMessage: " + str(erasures))
        corruptPositions = [0, 1, 2, 3, 4, 8, 10, 11, 12, 13]
        # add 6 since we sent incorrect week information
        corruptPositions.append(6)
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case2_FindPunchErasuresMessage
    def test_Case2_FindPunchErasuresMessage(self):
        print("============================================================================================== START test_Case2_FindPunchErasuresMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        prevMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case2_SubSecondMsg_Previous_WithRS)
        self.dataHandler._CachePunchMessage(prevMsg)


        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case2_SubSecondMsg_Corrupted_WithRS)
        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsg, totalRetryDelaySeconds)
        print("test_Case2_FindPunchErasuresMessage: " + str(erasures))
        corruptPositions = [1, 2, 3, 4, 5, 6, 7, 8, 10, 11]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case3_FindPunchErasuresMessage
    def test_Case3_FindPunchErasuresMessage(self):
        print("============================================================================================== START test_Case3_FindPunchErasuresMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        prevMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case3_SubSecondMsg_Previous_WithRS)
        self.dataHandler._CachePunchMessage(prevMsg)

        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case3_SubSecondMsg_Corrupted_WithRS)
        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsg, totalRetryDelaySeconds)
        print("test_Case3_FindPunchErasuresMessage: " + str(erasures))
        corruptPositions = [1, 2, 3, 4, 6, 7, 8, 10]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case4_FindPunchErasuresMessage
    def test_Case4_FindPunchErasuresMessage(self):
        print("============================================================================================== START test_Case4_FindPunchErasuresMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        prevMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case4_SubSecondMsg_Previous_WithRS)
        self.dataHandler._CachePunchMessage(prevMsg)

        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case4_SubSecondMsg_Corrupted_WithRS)
        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsg, totalRetryDelaySeconds)
        print("test_Case4_FindPunchErasuresMessage: " + str(erasures))
        corruptPositions = [10, 11, 12, 13]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case5_FindPunchErasuresMessage
    def test_Case5_FindPunchErasuresMessage(self):
        print("============================================================================================== START test_Case5_FindPunchErasuresMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        prevMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case5_SubSecondMsg_Previous_WithRS)
        self.dataHandler._CachePunchMessage(prevMsg)

        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case5_SubSecondMsg_Corrupted_WithRS)
        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsg, totalRetryDelaySeconds)
        print("test_Case5_FindPunchErasuresMessage: " + str(erasures))
        corruptPositions = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 13]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

        #self.dataHandler._CacheMessage(prevMsg)

        corruptedLoraMsg2 = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case5_SubSecondMsg_Corrupted_WithRS2)
        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsg2, totalRetryDelaySeconds)
        print("test_Case5_FindPunchErasuresMessage 2: " + str(erasures))
        corruptPositions = [1, 2, 3, 4, 5]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case6_FindPunchErasuresMessage
    def test_Case6_FindPunchErasuresMessage(self):
        print("============================================================================================== START test_Case6_FindPunchErasuresMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        prevMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case6_SubSecondMsg_Previous_WithRS)
        self.dataHandler._CachePunchMessage(prevMsg)
        # Adjust the LastPunchMessageTime
        seconds = 7
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds
        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case6_SubSecondMsg_Corrupted_WithRS)
        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsg, totalRetryDelaySeconds)
        print("test_Case6_FindPunchErasuresMessage: " + str(erasures))
        corruptPositions = [5, 6, 7, 8]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case7_FindPunchErasuresMessage
    def test_Case7_FindPunchErasuresMessage(self):
        print("============================================================================================== START test_Case7_FindPunchErasuresMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        prevMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case7_SubSecondMsg_Previous_WithRS)
        self.dataHandler._CachePunchMessage(prevMsg)
        # Adjust the LastPunchMessageTime
        seconds = 7
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds
        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case7_SubSecondMsg_Corrupted_WithRS)
        SettingsClass.SetSetting("LoraRange", 'L')
        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsg, totalRetryDelaySeconds)
        print("test_Case7_FindPunchErasuresMessage: " + str(erasures))
        corruptPositions = [10, 11, 12, 13]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case8_FindPunchErasuresMessage
    def test_Case8_FindPunchErasuresMessage(self):
        print("============================================================================================== START test_Case8_FindPunchErasuresMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        prevMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case8_SubSecondMsg_Previous_WithRS)
        self.dataHandler._CachePunchMessage(prevMsg)
        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case8_SubSecondMsg_Corrupted_WithRS)
        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsg, totalRetryDelaySeconds)
        print("test_Case8_FindPunchErasuresMessage: " + str(erasures))
        corruptPositions = [11, 12, 13]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case8_FindPunchErasuresMessage2
    def test_Case8_FindPunchErasuresMessage2(self):
        print("============================================================================================== START test_Case8_FindPunchErasuresMessage2 ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        prevMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case8_SubSecondMsg_Previous_WithRS)
        self.dataHandler._CachePunchMessage(prevMsg)
        corruptedLoraMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case8_SubSecondMsg_Corrupted_WithRS2)
        SettingsClass.SetSetting("LoraRange", 'L')
        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsg, totalRetryDelaySeconds)
        print("test_Case8_FindPunchErasuresMessage2: " + str(erasures))
        corruptPositions = [5, 6, 8, 10, 12, 13]
        for pos in erasures:
            self.assertIn(pos, corruptPositions)

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case8_GetPunchMessage_BestCombination
    def test_Case8_GetPunchMessage_BestCombination(self):
        print("============================================================================================== START test_Case8_GetPunchMessage_BestCombination ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        prevMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.Case8_SubSecondMsg_Previous_WithRS)
        self.dataHandler._CachePunchMessage(prevMsg)

        interleaved = LoraRadioMessagePunchSubSecondRS.InterleaveToAirOrder(TestLoraRadioDataHandler.Case8_SubSecondMsg_Corrupted_WithRS_BestCombination)
        Feed(self.dataHandler, interleaved)

        loraMsg = self.dataHandler._GetSubSecondPunchMessage()
        self.assertIsNotNone(loraMsg)
        print(Utils.GetDataInHex(loraMsg.GetByteArray(), logging.DEBUG))
        print("=== END test_Case8_GetPunchMessage_BestCombination ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case9_GetPunchMessage
    def test_Case9_GetPunchMessage(self):
        print("============================================================================================== START test_Case9_GetPunchMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        SettingsClass.SetSetting("LoraRange", 'L')
        deinterleaved = LoraRadioMessagePunchDoubleSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case9_SubSecondMsg_Previous_AirOrder_WithRS[:])
        prevMsg = LoraRadioMessageCreator.GetPunchDoubleSubSecondMessageByFullMessageData(deinterleaved)
        loraSubSecondMsg1, loraSubSecondMsg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(prevMsg)
        self.dataHandler._CachePunchMessage(loraSubSecondMsg1)
        self.dataHandler._CachePunchMessage(loraSubSecondMsg2)
        seconds = 2.8
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds

        interleaved = TestLoraRadioDataHandler.Case9_SubSecondMsg_Corrupted_AirOrder_WithRS[:]
        Feed(self.dataHandler, interleaved)
        punchMsg = self.dataHandler.GetMessage()
        print("Corrupted message: " + Utils.GetDataInHex(LoraRadioMessagePunchSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case9_SubSecondMsg_Corrupted_AirOrder_WithRS[:]), logging.DEBUG))
        print("Correct message:   " + Utils.GetDataInHex(LoraRadioMessagePunchSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case9_SubSecondMsg_Correct_AirOrder_WithRS), logging.DEBUG))
        self.assertIsNotNone(punchMsg)
        # Ignore the CRC since they were sent wrong, and are not corrected
        self.assertBytesEqual(punchMsg.GetByteArray(), LoraRadioMessagePunchSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case9_SubSecondMsg_Correct_AirOrder_WithRS), "test_Case9_GetPunchMessage", "drop_crc")
        print("=== END test_Case9_GetPunchMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case10_GetPunchMessage
    def test_Case10_GetPunchMessage(self):
        print("============================================================================================== START test_Case10_GetPunchMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        deinterleaved = LoraRadioMessagePunchSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case10_SubSecondMsg_Previous_AirOrder_WithRS[:])
        prevMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(deinterleaved)
        self.dataHandler._CachePunchMessage(prevMsg)
        seconds = 9
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds

        interleaved = TestLoraRadioDataHandler.Case10_SubSecondMsg_Corrupted_AirOrder_WithRS[:]
        Feed(self.dataHandler, interleaved)
        punchMsg = self.dataHandler.GetMessage()
        print("Corrupted message: " + Utils.GetDataInHex(LoraRadioMessagePunchSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case10_SubSecondMsg_Corrupted_AirOrder_WithRS[:]), logging.DEBUG))
        print("Correct message:   " + Utils.GetDataInHex(LoraRadioMessagePunchSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case10_SubSecondMsg_Correct_AirOrder_WithRS), logging.DEBUG))
        # 3 SINo bytes wrong and 3 ECC bytes wrong so cannot decode
        self.assertIsNone(punchMsg, "unexpectedly decoded: " + DescribeMessage(punchMsg))
        print("=== END test_Case10_GetPunchMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case11_GetPunchMessage
    def test_Case11_GetPunchMessage(self):
        print("============================================================================================== START test_Case11_GetPunchMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        deinterleaved = LoraRadioMessagePunchSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case11_SubSecondMsg_Previous_AirOrder_WithRS[:])
        prevMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(deinterleaved)
        self.dataHandler._CachePunchMessage(prevMsg)
        seconds = 5
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds

        interleaved = TestLoraRadioDataHandler.Case11_SubSecondMsg_Corrupted_AirOrder_WithRS[:]
        Feed(self.dataHandler, interleaved)
        punchMsg = self.dataHandler.GetMessage()
        print("Corrupted message: " + Utils.GetDataInHex(LoraRadioMessagePunchSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case11_SubSecondMsg_Corrupted_AirOrder_WithRS[:]), logging.DEBUG))
        print("Correct message:   " + Utils.GetDataInHex(LoraRadioMessagePunchSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case11_SubSecondMsg_Correct_AirOrder_WithRS), logging.DEBUG))
        # SN1, SN0, E1 and E2 cannot be guessed.
        # Could TL be guessed. Prev message has TL 0e (14 dec). It was 5 seconds earlier. But TL should be 1a (26 dec). With delays/resends it is difficult to predict a precise TL.
        self.assertIsNone(punchMsg, "unexpectedly decoded: " + DescribeMessage(punchMsg))
        print("=== END test_Case11_GetPunchMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case12_GetPunchMessage
    def test_Case12_GetPunchMessage(self):
        print("============================================================================================== START test_Case12_GetPunchMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        deinterleaved = LoraRadioMessagePunchSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case12_SubSecondMsg_Previous_AirOrder_WithRS[:])
        prevMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(deinterleaved)
        self.dataHandler._CachePunchMessage(prevMsg)
        seconds = 5
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds

        interleaved = TestLoraRadioDataHandler.Case12_SubSecondMsg_Corrupted_AirOrder_WithRS[:]
        Feed(self.dataHandler, interleaved)
        punchMsg = self.dataHandler.GetMessage()
        print("Corrupted message: " + Utils.GetDataInHex(LoraRadioMessagePunchSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case12_SubSecondMsg_Corrupted_AirOrder_WithRS[:]), logging.DEBUG))
        print("Correct message:   " + Utils.GetDataInHex(LoraRadioMessagePunchSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case12_SubSecondMsg_Correct_AirOrder_WithRS), logging.DEBUG))
        self.assertIsNotNone(punchMsg)
        self.assertBytesEqual(punchMsg.GetByteArray(), LoraRadioMessagePunchSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case12_SubSecondMsg_Correct_AirOrder_WithRS), "test_Case12_GetPunchMessage", "drop_crc")
        print("=== END test_Case12_GetPunchMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case13_GetPunchMessage
    def test_Case13_GetPunchMessage(self):
        print("============================================================================================== START test_Case13_GetPunchMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        deinterleaved = LoraRadioMessagePunchDoubleSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case13_SubSecondMsg_Previous_AirOrder_WithRS[:])
        prevMsg = LoraRadioMessageCreator.GetPunchDoubleSubSecondMessageByFullMessageData(deinterleaved)
        loraSubSecondMsg1, loraSubSecondMsg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(prevMsg)
        self.dataHandler._CachePunchMessage(loraSubSecondMsg1)
        self.dataHandler._CachePunchMessage(loraSubSecondMsg2)
        seconds = 9.4
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds

        interleaved = TestLoraRadioDataHandler.Case13_SubSecondMsg_Corrupted_AirOrder_WithRS[:]
        Feed(self.dataHandler, interleaved)
        punchMsg = self.dataHandler.GetMessage()
        print("Corrupted message: " + Utils.GetDataInHex(LoraRadioMessagePunchSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case13_SubSecondMsg_Corrupted_AirOrder_WithRS[:]), logging.DEBUG))
        print("Correct message:   " + Utils.GetDataInHex(LoraRadioMessagePunchSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case13_SubSecondMsg_Correct_AirOrder_WithRS), logging.DEBUG))
        self.assertIsNotNone(punchMsg)
        self.assertBytesEqual(punchMsg.GetByteArray(), LoraRadioMessagePunchSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case13_SubSecondMsg_Correct_AirOrder_WithRS), "test_Case13_GetPunchMessage")
        print("=== END test_Case13_GetPunchMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case14_GetAckMessage
    def test_Case14_GetAckMessage(self):
        print("============================================================================================== START test_Case14_GetAckMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        SettingsClass.SetMessageIDOfLastLoraMessageSent(TestLoraRadioDataHandler.Case14_AckMsg_Correct_AirOrder_WithRS[LoraRadioMessageAckRS.HASH0:LoraRadioMessageAckRS.HASH1+1])
        recAckMsg = TestLoraRadioDataHandler.Case14_AckMsg_Corrupted_AirOrder_WithRS[:]
        Feed(self.dataHandler, recAckMsg)
        ackMsg = self.dataHandler.GetMessage()
        print("Corrupted message: " + Utils.GetDataInHex(TestLoraRadioDataHandler.Case14_AckMsg_Corrupted_AirOrder_WithRS[:], logging.DEBUG))
        print("Correct message:   " + Utils.GetDataInHex(TestLoraRadioDataHandler.Case14_AckMsg_Correct_AirOrder_WithRS, logging.DEBUG))
        self.assertIsNotNone(ackMsg)
        # Header is wrong, ignore that
        self.assertBytesEqual(ackMsg.GetByteArray(), TestLoraRadioDataHandler.Case14_AckMsg_Correct_AirOrder_WithRS, "test_Case14_GetAckMessage", "skip_header")
        print("=== END test_Case14_GetAckMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case15_GetAckMessage
    def test_Case15_GetAckMessage(self):
        print("============================================================================================== START test_Case15_GetAckMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        SettingsClass.SetMessageIDOfLastLoraMessageSent(TestLoraRadioDataHandler.Case15_AckMsg_Correct_AirOrder_WithRS[LoraRadioMessageAckRS.HASH0:LoraRadioMessageAckRS.HASH1+1])
        recAckMsg = TestLoraRadioDataHandler.Case15_AckMsg_Corrupted_AirOrder_WithRS[:]
        Feed(self.dataHandler, recAckMsg)
        ackMsg = self.dataHandler.GetMessage()
        print("Corrupted message: " + Utils.GetDataInHex(TestLoraRadioDataHandler.Case15_AckMsg_Corrupted_AirOrder_WithRS[:], logging.DEBUG))
        print("Correct message:   " + Utils.GetDataInHex(TestLoraRadioDataHandler.Case15_AckMsg_Correct_AirOrder_WithRS, logging.DEBUG))
        self.assertIsNotNone(ackMsg)
        self.assertBytesEqual(ackMsg.GetByteArray(), TestLoraRadioDataHandler.Case15_AckMsg_Correct_AirOrder_WithRS, "test_Case15_GetAckMessage")
        print("=== END test_Case15_GetAckMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case16_GetAckMessage
    def test_Case16_GetAckMessage(self):
        print("============================================================================================== START test_Case16_GetAckMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        SettingsClass.SetMessageIDOfLastLoraMessageSent(TestLoraRadioDataHandler.Case16_AckMsg_Correct_AirOrder_WithRS[LoraRadioMessageAckRS.HASH0:LoraRadioMessageAckRS.HASH1+1])
        recAckMsg = TestLoraRadioDataHandler.Case16_AckMsg_Corrupted_AirOrder_WithRS[:]
        Feed(self.dataHandler, recAckMsg)
        ackMsg = self.dataHandler.GetMessage()
        print("Corrupted message: " + Utils.GetDataInHex(TestLoraRadioDataHandler.Case16_AckMsg_Corrupted_AirOrder_WithRS[:], logging.DEBUG))
        print("Correct message:   " + Utils.GetDataInHex(TestLoraRadioDataHandler.Case16_AckMsg_Correct_AirOrder_WithRS, logging.DEBUG))
        self.assertIsNotNone(ackMsg)
        self.assertBytesEqual(ackMsg.GetByteArray(), TestLoraRadioDataHandler.Case16_AckMsg_Correct_AirOrder_WithRS, "test_Case16_GetAckMessage", "skip_header")
        print("=== END test_Case16_GetAckMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case17_GetStatusMessage
    def test_Case17_GetStatusMessage(self):
        print("============================================================================================== START test_Case17_GetStatusMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        prevStatusMsgArr = TestLoraRadioDataHandler.Case17_StatusMsg_Previous_AirOrder_WithRS[:]
        Feed(self.dataHandler, prevStatusMsgArr)
        prevStatusMsg = self.dataHandler.GetMessage()

        recStatusMsg = TestLoraRadioDataHandler.Case17_StatusMsg_Corrupted_AirOrder_WithRS[:]
        Feed(self.dataHandler, recStatusMsg)
        statusMsg = self.dataHandler.GetMessage()

        print("Corrupted message: " + Utils.GetDataInHex(TestLoraRadioDataHandler.Case17_StatusMsg_Corrupted_AirOrder_WithRS[:], logging.DEBUG))
        print("Correct message:   " + Utils.GetDataInHex(TestLoraRadioDataHandler.Case17_StatusMsg_Correct_AirOrder_WithRS, logging.DEBUG))
        self.assertIsNotNone(statusMsg)
        self.assertBytesEqual(statusMsg.GetByteArray(), TestLoraRadioDataHandler.Case17_StatusMsg_Correct_AirOrder_WithRS, "test_Case17_GetStatusMessage")
        print("=== END test_Case17_GetStatusMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case18_GetPunchMessage
    def test_Case18_GetPunchMessage(self):
        print("============================================================================================== START test_Case18_GetPunchMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        deinterleaved = LoraRadioMessagePunchDoubleSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case18_SubSecondMsg_Previous_AirOrder_WithRS[:])
        prevMsg = LoraRadioMessageCreator.GetPunchDoubleSubSecondMessageByFullMessageData(deinterleaved)
        loraSubSecondMsg1, loraSubSecondMsg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(prevMsg)
        self.dataHandler._CachePunchMessage(loraSubSecondMsg1)
        self.dataHandler._CachePunchMessage(loraSubSecondMsg2)
        seconds = 9.4
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds

        interleaved = TestLoraRadioDataHandler.Case18_SubSecondMsg_Corrupted_AirOrder_WithRS[:]
        Feed(self.dataHandler, interleaved)
        punchMsg = self.dataHandler.GetMessage()
        print("Corrupted message: " + Utils.GetDataInHex(LoraRadioMessagePunchSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case18_SubSecondMsg_Corrupted_AirOrder_WithRS[:]), logging.DEBUG))
        print("Correct message:   " + Utils.GetDataInHex(LoraRadioMessagePunchSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case18_SubSecondMsg_Correct_AirOrder_WithRS), logging.DEBUG))
        self.assertIsNotNone(punchMsg)
        self.assertBytesEqual(punchMsg.GetByteArray(), LoraRadioMessagePunchSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case18_SubSecondMsg_Correct_AirOrder_WithRS), "test_Case18_GetPunchMessage", "drop_crc")
        print("=== END test_Case18_GetPunchMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case19_GetPunchMessage
    def test_Case19_GetPunchMessage(self):
        print("============================================================================================== START test_Case19_GetPunchMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        interleaved1 = TestLoraRadioDataHandler.Case19_SubSecondMsg_Previous_AirOrder_WithRS[:]
        Feed(self.dataHandler, interleaved1)
        punchMsg1 = self.dataHandler.GetMessage()
        self.assertBytesEqual(punchMsg1.GetByteArray(), LoraRadioMessagePunchSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case19_SubSecondMsg_Correct_AirOrder_WithRS), "test_Case19_GetPunchMessage")

        interleaved = TestLoraRadioDataHandler.Case19_SubSecondMsg_Corrupted_AirOrder_WithRS[:]
        Feed(self.dataHandler, interleaved)
        punchMsg2 = self.dataHandler.GetMessage()
        print("Corrupted message: " + Utils.GetDataInHex(LoraRadioMessagePunchSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case19_SubSecondMsg_Corrupted_AirOrder_WithRS[:]), logging.DEBUG))
        print("Correct message:   " + Utils.GetDataInHex(LoraRadioMessagePunchSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case19_SubSecondMsg_Correct_AirOrder_WithRS[:]), logging.DEBUG))
        print("Corrected message: " + Utils.GetDataInHex(punchMsg2.GetByteArray(), logging.DEBUG))
        self.assertIsNotNone(punchMsg2)
        self.assertBytesEqual(punchMsg2.GetByteArray(), LoraRadioMessagePunchSubSecondRS.DeInterleaveFromAirOrder(TestLoraRadioDataHandler.Case19_SubSecondMsg_Correct_AirOrder_WithRS), "test_Case19_GetPunchMessage")
        print("=== END test_Case19_GetPunchMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case20_GetAckMessage
    def test_Case20_GetAckMessage(self):
        print("============================================================================================== START test_Case20_GetAckMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        SettingsClass.SetMessageIDOfLastLoraMessageSent(
            TestLoraRadioDataHandler.Case20_AckMsg_Correct_AirOrder_WithRS[LoraRadioMessageAckRS.HASH0:LoraRadioMessageAckRS.HASH1 + 1])
        recAckMsg = TestLoraRadioDataHandler.Case20_AckMsg_Corrupted_AirOrder_WithRS[:]
        Feed(self.dataHandler, recAckMsg)
        ackMsg = self.dataHandler.GetMessage()
        print("Corrupted message: " + Utils.GetDataInHex(TestLoraRadioDataHandler.Case20_AckMsg_Corrupted_AirOrder_WithRS[:], logging.DEBUG))
        print("Correct message:   " + Utils.GetDataInHex(TestLoraRadioDataHandler.Case20_AckMsg_Correct_AirOrder_WithRS, logging.DEBUG))
        self.assertIsNotNone(ackMsg)
        self.assertBytesEqual(ackMsg.GetByteArray(), TestLoraRadioDataHandler.Case20_AckMsg_Correct_AirOrder_WithRS, "test_Case20_GetAckMessage")
        print("=== END test_Case20_GetAckMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case21_GetAckMessage
    def test_Case21_GetAckMessage(self):
        print("============================================================================================== START test_Case21_GetAckMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        SettingsClass.SetMessageIDOfLastLoraMessageSent(
            TestLoraRadioDataHandler.Case21_AckMsg_Correct_AirOrder_WithRS[LoraRadioMessageAckRS.HASH0:LoraRadioMessageAckRS.HASH1 + 1])
        recAckMsg = TestLoraRadioDataHandler.Case21_AckMsg_Corrupted_AirOrder_WithRS[:]
        Feed(self.dataHandler, recAckMsg)
        ackMsg = self.dataHandler.GetMessage()
        print("Corrupted message: " + Utils.GetDataInHex(TestLoraRadioDataHandler.Case21_AckMsg_Corrupted_AirOrder_WithRS[:], logging.DEBUG))
        print("Correct message:   " + Utils.GetDataInHex(TestLoraRadioDataHandler.Case21_AckMsg_Correct_AirOrder_WithRS, logging.DEBUG))
        # this is too wrong, too many bit errors
        self.assertIsNone(ackMsg, "unexpectedly decoded: " + DescribeMessage(ackMsg))
        print("=== END test_Case21_GetAckMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case22_GetAckMessage
    def test_Case22_GetAckMessage(self):
        print("============================================================================================== START test_Case22_GetAckMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        SettingsClass.SetMessageIDOfLastLoraMessageSent(
            TestLoraRadioDataHandler.Case22_AckMsg_Correct_AirOrder_WithRS[LoraRadioMessageAckRS.HASH0:LoraRadioMessageAckRS.HASH1 + 1])
        recAckMsg = TestLoraRadioDataHandler.Case22_AckMsg_Corrupted_AirOrder_WithRS[:]
        Feed(self.dataHandler, recAckMsg)
        ackMsg = self.dataHandler.GetMessage()
        print("Corrupted message: " + Utils.GetDataInHex(TestLoraRadioDataHandler.Case22_AckMsg_Corrupted_AirOrder_WithRS[:], logging.DEBUG))
        print("Correct message:   " + Utils.GetDataInHex(TestLoraRadioDataHandler.Case22_AckMsg_Correct_AirOrder_WithRS, logging.DEBUG))
        self.assertIsNotNone(ackMsg)
        self.assertBytesEqual(ackMsg.GetByteArray(), TestLoraRadioDataHandler.Case22_AckMsg_Correct_AirOrder_WithRS, "test_Case22_GetAckMessage", "skip_header")
        print("=== END test_Case22_GetAckMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case23_GetAckMessage
    def test_Case23_GetAckMessage(self):
        print("============================================================================================== START test_Case23_GetAckMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        SettingsClass.SetMessageIDOfLastLoraMessageSent(
            TestLoraRadioDataHandler.Case23_AckMsg_Correct_AirOrder_WithRS[LoraRadioMessageAckRS.HASH0:LoraRadioMessageAckRS.HASH1 + 1])
        recAckMsg = TestLoraRadioDataHandler.Case23_AckMsg_Corrupted_AirOrder_WithRS[:]
        Feed(self.dataHandler, recAckMsg)
        ackMsg = self.dataHandler.GetMessage()
        print("Corrupted message: " + Utils.GetDataInHex(TestLoraRadioDataHandler.Case23_AckMsg_Corrupted_AirOrder_WithRS[:], logging.DEBUG))
        print("Correct message:   " + Utils.GetDataInHex(TestLoraRadioDataHandler.Case23_AckMsg_Correct_AirOrder_WithRS, logging.DEBUG))
        self.assertIsNotNone(ackMsg)
        self.assertBytesEqual(ackMsg.GetByteArray(), TestLoraRadioDataHandler.Case23_AckMsg_Correct_AirOrder_WithRS, "test_Case23_GetAckMessage")
        print("=== END test_Case23_GetAckMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case24_GetAckMessage
    def test_Case24_GetAckMessage(self):
        print("============================================================================================== START test_Case24_GetAckMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        SettingsClass.SetMessageIDOfLastLoraMessageSent(
            TestLoraRadioDataHandler.Case24_AckMsg_Correct_AirOrder_WithRS[LoraRadioMessageAckRS.HASH0:LoraRadioMessageAckRS.HASH1 + 1])
        recAckMsg = TestLoraRadioDataHandler.Case24_AckMsg_Corrupted_AirOrder_WithRS[:]
        Feed(self.dataHandler, recAckMsg)
        ackMsg = self.dataHandler.GetMessage()
        print("Corrupted message: " + Utils.GetDataInHex(TestLoraRadioDataHandler.Case24_AckMsg_Corrupted_AirOrder_WithRS[:], logging.DEBUG))
        print("Correct message:   " + Utils.GetDataInHex(TestLoraRadioDataHandler.Case24_AckMsg_Correct_AirOrder_WithRS, logging.DEBUG))
        self.assertIsNotNone(ackMsg)
        self.assertBytesEqual(ackMsg.GetByteArray(), TestLoraRadioDataHandler.Case24_AckMsg_Correct_AirOrder_WithRS, "test_Case24_GetAckMessage")
        print("=== END test_Case24_GetAckMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_FindPunchErasures
    def test_FindPunchErasures(self):
        print("============================================================================================== START test_FindPunchErasures ==============================================================================================")

        loraMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.SubSecondMsg_Correct_1)
        self.dataHandler._CachePunchMessage(loraMsg)

        # TH changed to more than 5 minutes more
        corruptedMessageTH = TestLoraRadioDataHandler.SubSecondMsg_Correct_1[:]
        corruptedMessageTH[7] = corruptedMessageTH[7] | 0x04
        corruptedLoraMsgTH = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            corruptedMessageTH)
        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsgTH, totalRetryDelaySeconds)
        self.assertEqual(erasures, Hex("07"), "TH erasure not correct")

        # TH changed to higher than possible
        corruptedMessageTH2 = TestLoraRadioDataHandler.SubSecondMsg_Correct_1[:]
        corruptedMessageTH2[7] = 0xA9
        corruptedLoraMsgTH2 = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            corruptedMessageTH2)
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsgTH2, totalRetryDelaySeconds)
        self.assertEqual(erasures, Hex("07"), "TH erasure not correct")

        # TH changed to more than 5 minutes more and the combination TH TL too high
        corruptedMessageTL = TestLoraRadioDataHandler.SubSecondMsg_Correct_1[:]
        corruptedMessageTL[7] = 0xA8
        corruptedMessageTL[8] = 0xC1
        corruptedLoraMsgTL = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            corruptedMessageTL)
        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsgTL, totalRetryDelaySeconds)
        self.assertEqual(erasures, Hex("07"), "TH, TL erasure not correct")

        # TL changed to higher than possible (TH already highest)
        loraMsg2 = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.SubSecondMsg_Correct_HighestTHTL)
        self.dataHandler._CachePunchMessage(loraMsg2)
        corruptedMessageTL2 = TestLoraRadioDataHandler.SubSecondMsg_Correct_HighestTHTL[:]
        corruptedMessageTL2[8] = 0xC1
        corruptedLoraMsgTL2 = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            corruptedMessageTL2)
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsgTL2, totalRetryDelaySeconds)
        self.assertEqual(erasures, Hex("08"), "TL erasure not correct")

        # Control number changed
        self.dataHandler._CachePunchMessage(loraMsg)
        corruptedMessageCN0 = TestLoraRadioDataHandler.SubSecondMsg_Correct_1[:]
        corruptedMessageCN0[1] = 0x20
        corruptedLoraMsgCN0 = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            corruptedMessageCN0)
        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()
        erasures = self.dataHandler._FindReDCoSPunchErasures(corruptedLoraMsgCN0, totalRetryDelaySeconds)
        self.assertEqual(erasures, Hex("01"), "CN0 erasure not correct")
        print("=== END test_FindPunchErasures ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_CheckAndRemoveLoraModuleRXError
    def test_CheckAndRemoveLoraModuleRXError(self):
        print("============================================================================================== START test_CheckAndRemoveLoraModuleRXError ==============================================================================================")
        rxerrorMessage = TestLoraRadioDataHandler.SubSecondMsg_Correct_1[:]
        rxerrorMessage = "rx error\r\n".encode('latin-1') + rxerrorMessage
        Feed(self.dataHandler, rxerrorMessage)
        self.assertFalse(self.dataHandler.RxError)
        self.assertEqual(rxerrorMessage, self.dataHandler.DataReceived)
        self.dataHandler._CheckAndRemoveLoraModuleRXError()
        self.assertTrue(self.dataHandler.RxError)
        self.assertEqual(TestLoraRadioDataHandler.SubSecondMsg_Correct_1, self.dataHandler.DataReceived)
        print("=== END test_CheckAndRemoveLoraModuleRXError ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_GetMessageTypeByLength
    def test_GetMessageTypeByLength(self):
        print("============================================================================================== START test_GetMessageTypeByLength ==============================================================================================")
        Feed(self.dataHandler, TestLoraRadioDataHandler.SubSecondMsg_Correct_1)
        msgTypes = self.dataHandler._GetMessageTypesByLength()
        self.assertEqual(msgTypes, [LoraRadioMessageRS.MessageTypeStatus2, LoraRadioMessageRS.MessageTypeSIPunchSubSecond], "Didn't get the expected message type")
        print("=== END test_GetMessageTypeByLength ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_GetLikelyMessageTypes
    def test_GetLikelyMessageTypes(self):
        print("============================================================================================== START test_GetLikelyMessageTypes ==============================================================================================")
        loraMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.SubSecondMsg_Correct_1)
        self.dataHandler._CachePunchMessage(loraMsg)

        # controlnumber bit 8
        messageArr = TestLoraRadioDataHandler.SubSecondMsg_Correct_1[:]
        Feed(self.dataHandler, messageArr)
        messageTypes = self.dataHandler._GetLikelyMessageTypes()
        self.assertEqual(messageTypes, [LoraRadioMessageRS.MessageTypeStatus2, LoraRadioMessageRS.MessageTypeSIPunchSubSecond], "Didn't get the expected message type short punch")

        self.dataHandler.DataReceived = bytearray()
        print("=== END test_GetLikelyMessageTypes ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_GetPunchMessage
    def test_GetPunchMessage(self):
        print("============================================================================================== START test_GetPunchMessage ==============================================================================================")
        interleaved = LoraRadioMessagePunchSubSecondRS.InterleaveToAirOrder(TestLoraRadioDataHandler.SubSecondMsg_Correct_1)
        Feed(self.dataHandler, interleaved)

        # wrong message type
        punchMsg = self.dataHandler._GetAckMessage()
        self.assertIsNone(punchMsg, "unexpectedly decoded: " + DescribeMessage(punchMsg))
        # right message type
        punchMsg = self.dataHandler._GetSubSecondPunchMessage()
        self.assertIsNotNone(punchMsg)
        # Message is only removed from datareceived in TryGetMessage so it should fetch same again
        punchMsg2 = self.dataHandler._GetSubSecondPunchMessage()
        self.assertEqual(punchMsg.GetByteArray(), punchMsg2.GetByteArray())
        print("=== END test_GetPunchMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_GetTwoPunchMessages
    def test_GetTwoPunchMessages(self):
        print("============================================================================================== START test_GetTwoPunchMessages ==============================================================================================")
        # Add two messages at once before trying to fetch the messages
        interleaved = LoraRadioMessagePunchSubSecondRS.InterleaveToAirOrder(TestLoraRadioDataHandler.SubSecondMsg_Correct_1)
        Feed(self.dataHandler, interleaved)
        Feed(self.dataHandler, interleaved)

        punchMsg = self.dataHandler._GetSubSecondPunchMessage()
        self.assertIsNotNone(punchMsg)
        messageLength = LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunchSubSecond]
        self.dataHandler._removeBytesFromDataReceived(messageLength + self.dataHandler.rssiByteCount)
        punchMsg = self.dataHandler.GetMessage()  # Removes the message from data received
        self.assertIsNotNone(punchMsg, "second message not fetched")
        punchMsg = self.dataHandler._GetSubSecondPunchMessage()
        self.assertIsNone(punchMsg, "unexpectedly decoded: " + DescribeMessage(punchMsg))
        print("=== END test_GetTwoPunchMessages ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_GetPunchDoubleMessage
    def test_GetPunchDoubleMessage(self):
        print("============================================================================================== START test_GetPunchDoubleMessage ==============================================================================================")
        # messageTypeToTry, erasures = None):
        interleaved = LoraRadioMessagePunchDoubleSubSecondRS.InterleaveToAirOrder(TestLoraRadioDataHandler.SubSecondDoubleMsg_Correct_1)
        Feed(self.dataHandler, interleaved)

        print("added no of bytes: " + str(len(self.dataHandler.DataReceived)))

        # wrong message type
        punchMsg = self.dataHandler._GetSubSecondPunchMessage()
        self.assertIsNone(punchMsg, "unexpectedly decoded: " + DescribeMessage(punchMsg))
        # right message type
        punchDoubleMsg = self.dataHandler._GetSubSecondDoublePunchMessage()
        self.assertIsNotNone(punchDoubleMsg)
        # returned message so buffer should be empty
        punchDoubleMsg = self.dataHandler._GetSubSecondDoublePunchMessage()
        self.assertIsNotNone(punchDoubleMsg)
        self.assertGreater(len(self.dataHandler.DataReceived), 0)

        punchDoubleMsg = self.dataHandler.GetMessage()
        self.assertIsNotNone(punchDoubleMsg)
        self.assertEqual(len(self.dataHandler.DataReceived), 0)

        print("=== END test_GetPunchDoubleMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_GetTwoPunchDoubleMessages
    def test_GetTwoPunchDoubleMessages(self):
        print("============================================================================================== START test_GetTwoPunchDoubleMessages ==============================================================================================")
        # Add two messages at once before trying to fetch the messages
        interleaved = LoraRadioMessagePunchDoubleSubSecondRS.InterleaveToAirOrder(
            TestLoraRadioDataHandler.SubSecondDoubleMsg_Correct_1)
        Feed(self.dataHandler, interleaved)
        Feed(self.dataHandler, interleaved)

        punchDoubleMsg = self.dataHandler._GetSubSecondDoublePunchMessage()
        self.assertIsNotNone(punchDoubleMsg)
        # remove first message manually since it is only done in TryGetMessage
        messageLength = LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunchDoubleSubSecond]
        self.dataHandler._removeBytesFromDataReceived(messageLength + self.dataHandler.rssiByteCount)
        punchDoubleMsg = self.dataHandler._GetSubSecondDoublePunchMessage()
        self.assertIsNotNone(punchDoubleMsg, "could not get second message")
        punchDoubleMsg = self.dataHandler._GetSubSecondDoublePunchMessage()
        self.assertIsNotNone(punchDoubleMsg)
        print("=== END test_GetTwoPunchDoubleMessages ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_GetMessage_PunchMessage_Correct
    def test_GetMessage_PunchMessage_Correct(self):
        print("============================================================================================== START test_GetMessage_PunchMessage_Correct ==============================================================================================")
        self.dataHandler.AddData(Hex("00 00"))
        msg = self.dataHandler.GetMessage()

        interleaved = LoraRadioMessagePunchSubSecondRS.InterleaveToAirOrder(TestLoraRadioDataHandler.SubSecondMsg_Correct_1)
        Feed(self.dataHandler, interleaved)

        msg = self.dataHandler.GetMessage()
        self.assertIsNotNone(msg, "expected to receive the message back")
        self.assertBytesEqual(msg.GetByteArray(), TestLoraRadioDataHandler.SubSecondMsg_Correct_1, "test_GetMessage_PunchMessage_Correct: Didn't receive the same bytes back")
        self.assertEqual(len(self.dataHandler.DataReceived), 0,
                         "DataReceived not empty")
        print("=== END test_GetMessage_PunchMessage_Correct ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_GetMessage_PunchMessage_WithPrefixGarbage
    def test_GetMessage_PunchMessage_WithPrefixGarbage(self):
        print("============================================================================================== START test_GetMessage_PunchMessage_WithPrefixGarbage ==============================================================================================")
        self.dataHandler.AddData(Hex("00 00"))
        msg = self.dataHandler.GetMessage() # will clear datarecieve

        interleaved = LoraRadioMessagePunchSubSecondRS.InterleaveToAirOrder(TestLoraRadioDataHandler.SubSecondMsg_Correct_1)
        Feed(self.dataHandler, interleaved)

        msg = self.dataHandler.GetMessage()
        self.assertIsNotNone(msg, "expected to receive the message back")
        self.assertBytesEqual(msg.GetByteArray(), TestLoraRadioDataHandler.SubSecondMsg_Correct_1, "test_GetMessage_PunchMessage_WithPrefixGarbage: Didn't receive the same bytes back")
        self.assertEqual(len(self.dataHandler.DataReceived), 0,
                         "DataReceived not empty")
        print("=== END test_GetMessage_PunchMessage_WithPrefixGarbage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_GetMessage_CorruptedPunchMessage
    def test_GetMessage_CorruptedPunchMessage(self):
        print("============================================================================================== START test_GetMessage_CorruptedPunchMessage ==============================================================================================")
        interleaved = LoraRadioMessagePunchSubSecondRS.InterleaveToAirOrder(TestLoraRadioDataHandler.SubSecondMsg_Corrupted_1)
        Feed(self.dataHandler, interleaved)

        # Not decodable because we have no lastmessage so we incorrecly will assume wrong
        # Controlnumber CN0 and CN1Plus
        msg2 = self.dataHandler.GetMessage()
        self.assertIsNone(msg2, "Received a message but it shouldn't be decodable")

        loraMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.SubSecondMsg_Correct_1)
        self.dataHandler._CachePunchMessage(loraMsg)

        # correct one byte, then it should be decodable without RedCos
        corrupt = TestLoraRadioDataHandler.SubSecondMsg_Corrupted_1[:]
        corrupt[4] = 0x00
        interleaved2  = LoraRadioMessagePunchSubSecondRS.InterleaveToAirOrder(corrupt)
        Feed(self.dataHandler, interleaved2)

        msg3 = self.dataHandler.GetMessage()
        self.assertIsNotNone(msg3, "Didn't receive a message, it should be decodable")
        print("=== END test_GetMessage_CorruptedPunchMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_GetMessage_PunchDoubleMessage
    def test_GetMessage_PunchDoubleMessage(self):
        # messageTypeToTry, erasures = None):
        print("============================================================================================== START test_GetMessage_PunchDoubleMessage ==============================================================================================")
        interleaved = LoraRadioMessagePunchDoubleSubSecondRS.InterleaveToAirOrder(TestLoraRadioDataHandler.SubSecondDoubleMsg_Correct_1)
        Feed(self.dataHandler, interleaved)

        msg = self.dataHandler.GetMessage()
        self.assertIsNotNone(msg, "Expected to receive the message back")
        self.assertBytesEqual(msg.GetByteArray(), TestLoraRadioDataHandler.SubSecondDoubleMsg_Correct_1, "test_GetMessage_PunchDoubleMessage: Didn't receive the same bytes back")

        interleaved2 = LoraRadioMessagePunchDoubleSubSecondRS.InterleaveToAirOrder(TestLoraRadioDataHandler.SubSecondDoubleMsg_Corrupted_1[:])
        Feed(self.dataHandler, interleaved2)

        msg2 = self.dataHandler.GetMessage()
        self.assertIsNotNone(msg2, "Message should be decodable with alternatives")

        print("=== END test_GetMessage_PunchDoubleMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_GetMessage_Status
    def test_GetMessage_Status(self):
        print("============================================================================================== START test_GetMessage_Status ==============================================================================================")
        Feed(self.dataHandler, TestLoraRadioDataHandler.StatusMsg_Correct_WithRS)

        msg = self.dataHandler.GetMessage()
        self.assertIsNotNone(msg, "Expected to receive the message back")
        self.assertBytesEqual(msg.GetByteArray(), TestLoraRadioDataHandler.StatusMsg_Correct_WithRS, "test_GetMessage_Status: Didn't receive the same bytes back")
        self.assertEqual(msg.GetMessageCategory(), "DATA")
        self.assertTrue(isinstance(msg, LoraRadioMessageRS))
        print("=== END test_GetMessage_Status ===")
        # self.assertEqual(TestLoraRadioDataHandler.SubSecondMsg_Correct_1 + rsCodes, msg2.GetByteArray(), "Didn't receive a corrected message")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_GetAlternatives
    def test_GetAlternatives(self):
        print("============================================================================================== START test_GetAlternatives ==============================================================================================")
        msg = SubSecondFromRaw(TestLoraRadioDataHandler.SubSecondPayload_Correct_1_WithoutRS_CS)

        self.dataHandler._CachePunchMessage(msg)

        msg2 = SubSecondFromRaw(TestLoraRadioDataHandler.SubSecondPayload_Correct_2_WithoutRS_CS)

        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()
        alts, fixedValues, fixedErasures = self.dataHandler._GetPunchMessageAlternatives(msg2, totalRetryDelaySeconds)

        self.assertEqual(len(alts), 4)

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_GetAlternativesDouble
    def test_GetAlternativesDouble(self):
        print("============================================================================================== START test_GetAlternativesDouble ==============================================================================================")
        msg = SubSecondFromRaw(TestLoraRadioDataHandler.SubSecondDoublePayload_Correct_1_WithoutRS_CS, True)

        msg1, msg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(msg)
        self.dataHandler._CachePunchMessage(msg1)
        self.dataHandler._CachePunchMessage(msg2)

        msg3 = SubSecondFromRaw(TestLoraRadioDataHandler.SubSecondDoublePayload_Correct_2_WithoutRS_CS, True)

        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()
        alts, fixedValues, fixedErasures = self.dataHandler._GetPunchDoubleMessageAlternatives(msg3, totalRetryDelaySeconds)

        for i in range(len(alts)):
            print(alts[i])

        self.assertEqual(len(alts), 8)

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_GetReDCoSErasures
    def test_GetReDCoSErasures(self):
        print("============================================================================================== START test_GetReDCoSErasures ==============================================================================================")

        msg = SubSecondFromRaw(TestLoraRadioDataHandler.SubSecondDoublePayload_Correct_1_WithoutRS_CS, True)

        msg1, msg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(msg)
        self.dataHandler._CachePunchMessage(msg1)
        self.dataHandler._CachePunchMessage(msg2)

        msg3 = SubSecondFromRaw(TestLoraRadioDataHandler.SubSecondDoublePayload_Correct_2_WithoutRS_CS, True)

        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()
        alts, fixedValues, fixedErasures = self.dataHandler._GetPunchDoubleMessageAlternatives(msg3, totalRetryDelaySeconds)
        erasuresCombinations = self.dataHandler._GetReDCoSErasureCombinations(msg3, fixedValues, fixedErasures, 0)

        self.assertEqual(len(alts), 8, "No of alternatives wrong")
        self.assertEqual(fixedValues, [0, 1, 2, 6, 7, 10, 11, 15, 16], "fixedValues unexpected")
        self.assertEqual(fixedErasures, bytearray(), "fixedErasures unexpected")
        self.assertEqual(len(list(erasuresCombinations)), 43758, "No of erasure combinations unexpected")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_SevenPlusOneCRCWrong_DecodeReDCos
    def test_SevenPlusOneCRCWrong_DecodeReDCos(self):
        print("============================================================================================== START test_SevenPlusOneCRCWrong_DecodeReDCos ==============================================================================================")

        msg = SubSecondFromRaw(TestLoraRadioDataHandler.SubSecondDoublePayload_Correct_1_WithoutRS_CS, True)

        msg1, msg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(msg)
        # print("tw: "+  str(msg2.GetTwelveHourTimer()))
        self.dataHandler._CachePunchMessage(msg1)
        self.dataHandler._CachePunchMessage(msg2)

        msg3 = SubSecondFromRaw(TestLoraRadioDataHandler.SubSecondDoublePayload_Correct_2_WithoutRS_CS, True)

        corruptedMessageData = msg3.GetByteArray()[:]
        print("Correct message  : " + Utils.GetDataInHex(corruptedMessageData, logging.DEBUG))
        corruptedMessageData = Corrupt(corruptedMessageData, {LoraRadioMessagePunchDoubleSubSecondRS.TL: 0x00, LoraRadioMessagePunchDoubleSubSecondRS.TL_2: 0x00, LoraRadioMessagePunchDoubleSubSecondRS.SN0: 0x01, LoraRadioMessagePunchDoubleSubSecondRS.SN1: 0x01, LoraRadioMessagePunchDoubleSubSecondRS.SN2: 0x01, LoraRadioMessagePunchDoubleSubSecondRS.SN0_2: 0x01, LoraRadioMessagePunchDoubleSubSecondRS.SN1_2: 0x01, LoraRadioMessagePunchDoubleSubSecondRS.CRC0: 0x00})
        #msg4Corrupted = LoraRadioMessageCreator.GetPunchDoubleSubSecondMessageByFullMessageData(corruptedMessageData)

        interleaved2 = LoraRadioMessagePunchDoubleSubSecondRS.InterleaveToAirOrder(corruptedMessageData[:])
        Feed(self.dataHandler, interleaved2)

        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(10000)
        msg = self.dataHandler.GetMessage()
        self.assertIsNotNone(msg)

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_SevenPlusOneCRCWrong_FewerCombinations_DecodeReDCos
    def test_SevenPlusOneCRCWrong_FewerCombinations_DecodeReDCos(self):
        print("============================================================================================== START test_SevenPlusOneCRCWrong_FewerCombinations_DecodeReDCos ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')

        msg = SubSecondFromRaw(TestLoraRadioDataHandler.SubSecondDoublePayload_Correct_1_WithoutRS_CS, True)

        msg1, msg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(msg)
        # print("tw: "+  str(msg2.GetTwelveHourTimer()))
        self.dataHandler._CachePunchMessage(msg1)
        self.dataHandler._CachePunchMessage(msg2)

        msg3 = SubSecondFromRaw(TestLoraRadioDataHandler.SubSecondDoublePayload_Correct_2_WithoutRS_CS, True)

        corruptedMessageData = msg3.GetByteArray()[:]
        print("Correct message  : " + Utils.GetDataInHex(corruptedMessageData, logging.DEBUG))
        corruptedMessageData = Corrupt(corruptedMessageData, {LoraRadioMessagePunchDoubleSubSecondRS.TL: 0x00, LoraRadioMessagePunchDoubleSubSecondRS.TL_2: 0x00, LoraRadioMessagePunchDoubleSubSecondRS.SN0: 0x01, LoraRadioMessagePunchDoubleSubSecondRS.SN1: 0x01, LoraRadioMessagePunchDoubleSubSecondRS.SN2: 0x01, LoraRadioMessagePunchDoubleSubSecondRS.SN0_2: 0x01, LoraRadioMessagePunchDoubleSubSecondRS.SN1_2: 0x01, LoraRadioMessagePunchDoubleSubSecondRS.CRC0: 0x00})

        interleaved2 = LoraRadioMessagePunchDoubleSubSecondRS.InterleaveToAirOrder(corruptedMessageData[:])
        Feed(self.dataHandler, interleaved2)

        # We don't expect it to work with this few combinations (this force it to reduce combinations to inlcude only for erasures)
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)
        msg = self.dataHandler.GetMessage()
        self.assertIsNone(msg)

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_SevenPlusOneCRCWrong_MoreCombinations_DecodeReDCos
    def test_SevenPlusOneCRCWrong_MoreCombinations_DecodeReDCos(self):
        print("============================================================================================== START test_SevenPlusOneCRCWrong_MoreCombinations_DecodeReDCos ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')

        msg = SubSecondFromRaw(TestLoraRadioDataHandler.SubSecondDoublePayload_Correct_1_WithoutRS_CS, True)


        msg1, msg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(msg)
        self.dataHandler._CachePunchMessage(msg1)
        self.dataHandler._CachePunchMessage(msg2)

        msg3 = SubSecondFromRaw(TestLoraRadioDataHandler.SubSecondDoublePayload_Correct_2_WithoutRS_CS, True)
        correct = msg3.GetByteArray()[:]

        corruptedMessageData = msg3.GetByteArray()[:]
        corruptedMessageData = Corrupt(corruptedMessageData, {LoraRadioMessagePunchDoubleSubSecondRS.TL: 0x00, LoraRadioMessagePunchDoubleSubSecondRS.TL_2: 0x00, LoraRadioMessagePunchDoubleSubSecondRS.SN0: 0x01, LoraRadioMessagePunchDoubleSubSecondRS.SN1: 0x01, LoraRadioMessagePunchDoubleSubSecondRS.SN2: 0x01, LoraRadioMessagePunchDoubleSubSecondRS.SN0_2: 0x01, LoraRadioMessagePunchDoubleSubSecondRS.SN1_2: 0x01, LoraRadioMessagePunchDoubleSubSecondRS.CRC0: 0x00})
        # msg4Corrupted = LoraRadioMessageCreator.GetPunchDoubleSubSecondMessageByFullMessageData(corruptedMessageData)

        interleaved2 = LoraRadioMessagePunchDoubleSubSecondRS.InterleaveToAirOrder(corruptedMessageData[:])
        Feed(self.dataHandler, interleaved2)

        # This should reduce the combinations to include 6 erasures. Plus the two extra ECC bytes can correct one error. So should work.
        # Important that the redcos tests the alternative with the correct controlnumber first, otherwise it finds a false message.
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(200)
        msg4 = self.dataHandler.GetMessage()

        print("Correct message  : " + Utils.GetDataInHex(correct, logging.DEBUG))
        print("Decoded message  : " + Utils.GetDataInHex(msg4.GetByteArray(), logging.DEBUG))

        self.assertIsNotNone(msg4)
        self.assertBytesEqual(msg4.GetByteArray(), correct, "test_SevenPlusOneCRCWrong_MoreCombinations_DecodeReDCos")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_FivePlusOneCRCWrong_FewerCombinations_DecodeReDCos
    def test_FivePlusOneCRCWrong_FewerCombinations_DecodeReDCos(self):
        print("============================================================================================== START test_FivePlusOneCRCWrong_FewerCombinations_DecodeReDCos ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')

        msg = SubSecondFromRaw(TestLoraRadioDataHandler.SubSecondDoublePayload_Correct_1_WithoutRS_CS, True)


        msg1, msg2 = self.dataHandler._GetPunchReDCoSTupleFromPunchDouble(msg)
        self.dataHandler._CachePunchMessage(msg1)
        self.dataHandler._CachePunchMessage(msg2)

        msg3 = SubSecondFromRaw(TestLoraRadioDataHandler.SubSecondDoublePayload_Correct_2_WithoutRS_CS, True)
        correct = msg3.GetByteArray()[:]

        corruptedMessageData = msg3.GetByteArray()[:]
        corruptedMessageData = Corrupt(corruptedMessageData, {LoraRadioMessagePunchDoubleSubSecondRS.TL: 0x00, LoraRadioMessagePunchDoubleSubSecondRS.TL_2: 0x00, LoraRadioMessagePunchDoubleSubSecondRS.SN0: 0x01, LoraRadioMessagePunchDoubleSubSecondRS.SN1: 0x01, LoraRadioMessagePunchDoubleSubSecondRS.SN2: 0x01})
        #corruptedMessageData[LoraRadioMessagePunchDoubleSubSecondRS.SN0_2] = 0x01
        #corruptedMessageData[LoraRadioMessagePunchDoubleSubSecondRS.SN1_2] = 0x01
        corruptedMessageData = Corrupt(corruptedMessageData, {LoraRadioMessagePunchDoubleSubSecondRS.CRC0: 0x00})
        # msg4Corrupted = LoraRadioMessageCreator.GetPunchDoubleSubSecondMessageByFullMessageData(corruptedMessageData)

        interleaved2 = LoraRadioMessagePunchDoubleSubSecondRS.InterleaveToAirOrder(corruptedMessageData[:])
        Feed(self.dataHandler, interleaved2)

        # We don't expect it to work with this few combinations
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)
        msg4 = self.dataHandler.GetMessage()

        print("Correct message  : " + Utils.GetDataInHex(correct, logging.DEBUG))
        print("Decoded message  : " + Utils.GetDataInHex(msg4.GetByteArray(), logging.DEBUG))

        self.assertIsNotNone(msg4)
        self.assertBytesEqual(msg4.GetByteArray(), correct, "test_FivePlusOneCRCWrong_FewerCombinations_DecodeReDCos")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case25_GetPunchDoubleMessage
    @max_execution_time(4)
    def test_Case25_GetPunchDoubleMessage(self):
        print("============================================================================================== START test_Case25_GetPunchDoubleMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'MF')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        # Add all the old control numbers that was added previously. This is needed to recreate the many alternatives
        # that was created. With new changes to how many differenct control numbers that should be used it should no longer happen though.
        prevMsgs = [TestLoraRadioDataHandler.SubSecondMsg_Correct_1.copy() for _ in range(9)]
        prevMsgs[0][1] = 107
        prevMsgs[1][1] = 118
        prevMsgs[2][1] = 235
        prevMsgs[3][1] = 135
        prevMsgs[4][1] = 255
        prevMsgs[4][6] = prevMsgs[4][6] | 0x40
        prevMsgs[5][1] = 180
        prevMsgs[6][1] = 115
        prevMsgs[7][1] = 180
        prevMsgs[7][6] = prevMsgs[7][6] | 0x40
        prevMsgs[8][1] = 184



        for prevMsg in prevMsgs:
            rsCodes = RSCoderLora.encode(prevMsg)
            loraMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(prevMsg + rsCodes)
            self.dataHandler._CachePunchMessage(loraMsg)

        interleaved = TestLoraRadioDataHandler.Case25_SubSecondDoubleMsg_Previous_AirOrder_WithRS[:]
        Feed(self.dataHandler, interleaved)
        prevSubSecondDoubleMsg = self.dataHandler.GetMessage()

        seconds = 2
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds

        interleaved = TestLoraRadioDataHandler.Case25_SubSecondDoubleMsg_Corrupted_AirOrder_WithRS[:]
        Feed(self.dataHandler, interleaved)
        punchDoubleMsg = self.dataHandler.GetMessage()
        self.assertIsNone(punchDoubleMsg, "unexpectedly decoded: " + DescribeMessage(punchDoubleMsg))
        # This test takes arount a minute but we should never spend that much time, especially not when MS is selected
        print("=== END test_Case25_GetPunchDoubleMessage ===")

    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_Case26_GetPunchDoubleMessage
    @max_execution_time(2)
    def test_Case26_GetPunchDoubleMessage(self):
        print(
            "============================================================================================== START test_Case26_GetPunchDoubleMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'MF')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100)

        # Add all the old control numbers that was added previously. This is needed to recreate the many alternatives
        # that was created. With new changes to how many different control numbers that should be used it should no longer happen though.
        prevMsgs = [TestLoraRadioDataHandler.SubSecondMsg_Correct_1.copy() for _ in range(14)]
        prevMsgs[0][1] = 31
        prevMsgs[1][1] = 164
        prevMsgs[2][1] = 157
        prevMsgs[3][1] = 128
        prevMsgs[4][1] = 255
        prevMsgs[4][6] = prevMsgs[4][6] | 0x40
        prevMsgs[5][1] = 105
        prevMsgs[6][1] = 71
        prevMsgs[7][1] = 158
        prevMsgs[8][1] = 255
        prevMsgs[9][1] = 250
        prevMsgs[10][1] = 106
        prevMsgs[10][6] = prevMsgs[4][6] | 0x40
        prevMsgs[11][1] = 182
        prevMsgs[12][1] = 159
        prevMsgs[13][1] = 124

        for prevMsg in prevMsgs:
            rsCodes = RSCoderLora.encode(prevMsg)
            loraMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(prevMsg + rsCodes)
            self.dataHandler._CachePunchMessage(loraMsg)

        #interleaved = TestLoraRadioDataHandler.Case26_SubSecondDoubleMsg_Previous_AirOrder_WithRS[:]
        #for i in range(0, len(interleaved)):
        #    self.dataHandler.AddData(interleaved[i:i + 1])
        #prevSubSecondDoubleMsg = self.dataHandler.GetMessage()

        seconds = 2
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds

        interleaved = TestLoraRadioDataHandler.Case26_SubSecondDoubleMsg_Corrupted_AirOrder_WithRS[:]
        Feed(self.dataHandler, interleaved)
        punchDoubleMsg = self.dataHandler.GetMessage()
        self.assertIsNone(punchDoubleMsg, "unexpectedly decoded: " + DescribeMessage(punchDoubleMsg))
        print("=== END test_Case26_GetPunchDoubleMessage ===")


    # sudo env/bin/python3 -m unittest loraradio.TestLoraRadioDataHandler.TestLoraRadioDataHandler.test_DoubleMessage
    def test_DoubleMessage(self):
        print("============================================================================================== START test_DoubleMessage ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'L')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(10000)

        # Six corrupted fields; the two TSS bytes are inside the payload so the message cannot be
        # compared as a 27-byte punch prefix anymore, the whole 29-byte subsecond message is.
        Correct_DoubleMsg_WithRS = TestLoraRadioDataHandler.SubSecondDoubleMsg_Correct_1
        DoubleMsg_WithRS = TestLoraRadioDataHandler.SubSecondDoubleMsg_Corrupted_1
        print("len: " + str(len(DoubleMsg_WithRS)))

        interleaved = LoraRadioMessagePunchDoubleSubSecondRS.InterleaveToAirOrder(DoubleMsg_WithRS[:])
        Feed(self.dataHandler, interleaved)
        punchDoubleMsg = self.dataHandler._GetSubSecondDoublePunchMessage()
        self.assertIsNotNone(punchDoubleMsg)
        print(Utils.GetDataInHex(punchDoubleMsg.GetByteArray(), logging.DEBUG))
        self.assertBytesEqual(punchDoubleMsg.GetByteArray(), Correct_DoubleMsg_WithRS, "test_DoubleMessage: Didn't receive the same bytes back")
        print("control1: "  +str(punchDoubleMsg.GetControlNumber()))
        print("cardno 1: " + str(punchDoubleMsg.GetSICardNo()))
        print("hour 1: " + str(punchDoubleMsg.GetHour()))
        print("control2: " + str(punchDoubleMsg.GetControlNumber_2()))
        print("cardno 2: " + str(punchDoubleMsg.GetSICardNo_2()))
        print("hour 2: " + str(punchDoubleMsg.GetHour_2()))
        print("=== END test_DoubleMessage ===")


    @max_execution_time(2)
    def test_Case27_GetPunchDoubleMessage_UL_WorstCase(self):
        print(
            "============================================================================================== START test_Case27_GetPunchDoubleMessage_UL_WorstCase ==============================================================================================")
        SettingsClass.SetSetting("LoraRange", 'UL')
        SettingsClass.SetReDCoSCombinationThresholdPerSecondTotalRetryTime(100) # standard setting

        # Add all the old control numbers that was added previously. This is needed to recreate the many alternatives
        # that was created. With new changes to how many different control numbers that should be used it should no longer happen though.
        prevMsgs = [TestLoraRadioDataHandler.Case27_SubSecondMsg_Correct_Previous.copy() for _ in range(14)]
        prevMsgs[0][1] = 31
        prevMsgs[1][1] = 164
        prevMsgs[2][1] = 157
        prevMsgs[3][1] = 128
        prevMsgs[4][1] = 255
        prevMsgs[4][6] = prevMsgs[4][6] | 0x40
        prevMsgs[5][1] = 105
        prevMsgs[6][1] = 71
        prevMsgs[7][1] = 158
        prevMsgs[8][1] = 255
        prevMsgs[9][1] = 250
        prevMsgs[10][1] = 106
        prevMsgs[10][6] = prevMsgs[4][6] | 0x40
        prevMsgs[11][1] = 182
        prevMsgs[12][1] = 159
        prevMsgs[13][1] = 124

        for prevMsg in prevMsgs:
            rsCodes = RSCoderLora.encode(prevMsg)
            loraMsg = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(prevMsg + rsCodes)
            self.dataHandler._CachePunchMessage(loraMsg)
            # Case27_SubSecondMsg_Correct_Previous [0x87, 0x1F, 0x00, 0x00, 0x00, 0xFF, 0x00, 0X93, 0xA8, 0x13, 0x95, 0xfe, 0x24, 0xba, 0xb2]
            #                       H   CN0    SN3  SN2    SN1  SN0  CN1Plus TH    TL    ECC  ECC   ECC   ECC    CRC  CRC

        #prevSubSecondDoubleMsg = self.dataHandler.GetMessage()

        seconds = 2
        self.dataHandler.LastPunchMessageTime = time.monotonic() - seconds

        # Case27 has different header, TH/TL 400 seconds back in time compared to previous message. SN3 is not 0. This should be worst case.
        deinterleaved = TestLoraRadioDataHandler.Case27_SubSecondDoubleMsg_Corrupted_WithRS[:]
        interleaved = LoraRadioMessagePunchDoubleSubSecondRS.InterleaveToAirOrder(deinterleaved)
        print("Deinterleaved: " + Utils.GetDataInHex(deinterleaved, logging.DEBUG))
        print("Interleaved: " + Utils.GetDataInHex(interleaved, logging.DEBUG))
        
        Feed(self.dataHandler, interleaved)
        punchDoubleMsg = self.dataHandler.GetMessage()
        self.assertIsNone(punchDoubleMsg, "unexpectedly decoded: " + DescribeMessage(punchDoubleMsg))
        # This test takes arount a minute but we should never spend that much time, especially not when MS is selected
        print("=== END test_Case27_GetPunchDoubleMessage_UL_WorstCase ===")

    # The three tests below are subsecond specific; they do not depend on the handler's
    # ReDCoS/erasure support and are expected to pass today.

    def test_SubSecondLayout(self):
        print("============================================================================================== START test_SubSecondLayout ==============================================================================================")
        single = LoraRadioMessagePunchSubSecondRS
        double = LoraRadioMessagePunchDoubleSubSecondRS
        self.assertEqual((single.TSS, single.NoOfECCBytes, single.NoOfCRCBytes), (9, 4, 2))
        self.assertEqual((double.TSS, double.TSS_2, double.NoOfECCBytes, double.NoOfCRCBytes), (9, 18, 8, 2))
        # single leads with CRC1 in air order, double with CRC0
        self.assertEqual(single.InterleavingInAirOrder[:2], [single.H, single.CRC1])
        self.assertEqual(double.InterleavingInAirOrder[:2], [double.H, double.CRC0])

        correctSingle = TestLoraRadioDataHandler.SubSecondMsg_Correct_1
        self.assertEqual(correctSingle[single.TSS], 0x80)
        self.assertEqual(single.DeInterleaveFromAirOrder(single.InterleaveToAirOrder(correctSingle)), correctSingle)

        correctDouble = TestLoraRadioDataHandler.SubSecondDoubleMsg_Correct_1
        self.assertEqual((correctDouble[double.TSS], correctDouble[double.TSS_2]), (0x80, 0x40))
        self.assertEqual(double.DeInterleaveFromAirOrder(double.InterleaveToAirOrder(correctDouble)), correctDouble)
        print("=== END test_SubSecondLayout ===")

    def test_SubSecondCodes(self):
        print("============================================================================================== START test_SubSecondCodes ==============================================================================================")
        checked = 0
        for name, data in vars(TestLoraRadioDataHandler).items():
            if not isinstance(data, (bytes, bytearray)) or len(data) not in (16, 29):
                continue
            if 'Corrupted' in name or 'AckMsg' in name or 'StatusMsg' in name:
                continue
            msg_cls = LoraRadioMessagePunchDoubleSubSecondRS if len(data) == 29 else LoraRadioMessagePunchSubSecondRS
            if 'AirOrder' in name:
                data = msg_cls.DeInterleaveFromAirOrder(data[:])
            msg = msg_cls()
            msg.SetHeader(data[0:1])
            msg.AddPayload(data[1:len(data) - msg_cls.NoOfECCBytes - msg_cls.NoOfCRCBytes])
            msg.GenerateAndAddRSCode()
            msg.GenerateAndAddCRC()
            if msg.GetByteArray() != data:
                # The Case19 previous capture is a recorded frame, not a canonical encoding
                self.assertEqual(name, 'Case19_SubSecondMsg_Previous_AirOrder_WithRS')
                continue
            checked += 1
        self.assertEqual(checked, 61)

        # Changing only TSS leaves the punched fields untouched but changes both ECC and CRC
        tss = LoraRadioMessagePunchSubSecondRS.TSS
        changed = TestLoraRadioDataHandler.SubSecondMsg_Correct_1[:]
        changed[tss] ^= 0x01
        msg = LoraRadioMessagePunchSubSecondRS()
        msg.SetHeader(changed[0:1])
        msg.AddPayload(changed[1:len(changed) - 6])
        msg.GenerateAndAddRSCode()
        msg.GenerateAndAddCRC()
        recoded = msg.GetByteArray()
        correct = TestLoraRadioDataHandler.SubSecondMsg_Correct_1
        self.assertEqual(recoded[1:tss], correct[1:tss])
        self.assertNotEqual(recoded[10:14], correct[10:14], "ECC should change with TSS")
        self.assertNotEqual(recoded[14:16], correct[14:16], "CRC should change with TSS")
        print("=== END test_SubSecondCodes ===")

    def test_SubSecondTimeConversions(self):
        print("============================================================================================== START test_SubSecondTimeConversions ==============================================================================================")
        single = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.SubSecondMsg_Correct_1)
        self.assertEqual(single.GetSubSecondRaw(), 0x80)
        self.assertEqual(single.GetSubSecondAsTenthOfSeconds(), int(0x80 // 25.6))
        self.assertEqual(single.GetSubSecondAsMilliSeconds(), int(0x80 * 1000 / 256))

        double = LoraRadioMessageCreator.GetPunchDoubleSubSecondMessageByFullMessageData(
            TestLoraRadioDataHandler.SubSecondDoubleMsg_Correct_1)
        self.assertEqual(double.GetSubSecondRaw(), 0x80)
        self.assertEqual(double.GetSubSecondRaw_2(), 0x40)
        self.assertEqual(double.GetSubSecondAsTenthOfSeconds(), int(0x80 // 25.6))
        self.assertEqual(double.GetSubSecondAsTenthOfSeconds_2(), int(0x40 // 25.6))
        print("=== END test_SubSecondTimeConversions ===")
