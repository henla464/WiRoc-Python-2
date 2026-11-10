__author__ = 'henla464'

import itertools
import logging
import time
from multiprocessing import Pool

from loraradio.LoraRadioMessageAndMetadata import LoraRadioMessageAndMetadata
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from loraradio.LoraRadioMessageRS import LoraRadioMessageRS, LoraRadioMessageReDCoSRS, LoraRadioMessageAckRS, LoraRadioMessageStatus2RS
from loraradio.LoraRadioMessageRS import LoraRadioMessagePunchReDCoSRS, LoraRadioMessagePunchDoubleReDCoSRS
from loraradio.LoraRadioMessageRS import LoraRadioMessagePunchSubSecondRS, LoraRadioMessagePunchDoubleSubSecondRS
from loraradio.RSCoderLora import RSCoderLora
from settings.settings import SettingsClass
from utils.utils import Utils
from collections.abc import Iterable
import hashlib
from typing import Tuple, List

"""
Upstream — Who creates and calls LoraRadioDataHandler

LoraRadioDRF1268DS_RS.__init__()          LoraRadioRAK3172.__init__()
        │                                          │
        ├── new LoraRadioDataHandler(1,0,0)        ├── new LoraRadioDataHandler(2,1,1)
        │                                          │
        ▼                                          ▼
LoraRadioDRF1268DS_RS.GetRadioData()      LoraRadioRAK3172.GetRadioData()
        │                                          │
        ├── .AddData(bytes)                        ├── .HasData() → .GetMessage()
        │   (per byte from serial)                 ├── .AddData(receivedMsgData)
        │                                          │   (per radio message)
        ├── .GetMessage()                          └── .GetMessage()
        │                                          │
        └──────────────────┬───────────────────────┘
                           │
                           ▼
              ReceiveLoraAdapter (line 144)
                           │
                           ▼
              DecodeLoraMessage.py
                           │
                           ▼
              Start.py (main loop)


Internal callgraph of LoraRadioDataHandler

Naming: ReDCoS is the decoding algorithm used by all four punch message types;
it is not a family marker. Shared helpers are named after the message shape
(Single/Double) with no family word; family-specific helpers carry the exact
type name (PunchReDCoS, PunchSubSecond, PunchDoubleReDCoS,
PunchDoubleSubSecond).

GetMessage()                         ◄── public entry point
  ├── _CheckAndRemoveLoraModuleRXError()
  ├── _removeBytesFromDataReceived()
  ├── ClearDataReceived()
  └── _TryGetMessage()
        ├── _GetLikelyMessageTypes()
        │     ├── _GetMessageTypesByLength()
        │     └── GetHeaderMessageType() [static]
        ├── _GetPunchReDCoSMessage()          ←─── single punch decode
        ├── _GetPunchSubSecondMessage()       ←─── single subsecond decode
        │     ├── _GetPunchMessageAlternatives() / _GetPunchSubSecondMessageAlternatives()
        │     │     ├── _GenerateMessageAlternatives()              [shared: both singles]
        │     │     ├── _FindReDCoSPunchErasures() / _FindReDCoSPunchSubSecondErasures()
        │     │     └── GetHeaderMessageType()
        │     ├── _GetSingleMessageWithErasures()                   [shared: both singles]
        │     │     ├── _FindSingleMessageErasures()                [shared: both singles]
        │     │     │     (positions from loraMsg.__class__; last-message state
        │     │     │      passed in by the family getter)
        │     │     └── RSCoderLora.decode()
        │     ├── _GetSingleMessageUsingReDCoS()                    [shared: both singles]
        │     │     ├── _GetReDCoSErasureCombinations()             [shared]
        │     │     ├── _GetNoOfCombinations() / _GetNoOfHalfMatchesRequired() [shared]
        │     │     ├── _decode_single_redcos() Pool workers
        │     │     └── LoraRadioMessageCreator.GetPunchMessageByFullMessageData()
        │     └── _IsSameSingleMessage() + _CachePunch[SubSecond]Message()
        ├── _GetPunchDoubleReDCoSMessage()    ←─── double punch decode
        ├── _GetPunchDoubleSubSecondMessage() ←─── double subsecond decode
        │     ├── _GetPunchDoubleMessageAlternatives() /
        │     │   _GetPunchDoubleSubSecondMessageAlternatives()
        │     │     ├── _GenerateMessageAlternatives()              [shared: both doubles]
        │     │     ├── _AddFixedErasursToCombinationIterator()     [shared]
        │     │     ├── _GetReDCoSErasureCombinations()             [shared]
        │     │     └── _FindReDCoSPunchDoubleErasures() /
        │     │         _FindReDCoSPunchDoubleSubSecondErasures()   (two singles of same family)
        │     ├── _GetDoubleMessageUsingReDCoS()                    [shared: both doubles]
        │     │     ├── _GetNoOfCombinations() / _GetNoOfHalfMatchesRequired()
        │     │     ├── _decode_double_redcos() Pool workers
        │     │     └── LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData()
        │     ├── _try_decode_double_alt() Pool workers
        │     │     └── _get_double_message_with_erasures()         [shared: both doubles]
        │     └── _IsSameDoubleMessage() + _CacheDoublePunch[SubSecond]Message()
        ├── _GetAckMessage()
        │     ├── SettingsClass.GetMessageIDOfLastLoraMessageSent()
        │     └── LoraRadioMessageAckRS [constructor]
        ├── _GetStatus2Message()
              ├── RSCoderLora.check()
              ├── RSCoderLora.decode()
              └── LoraRadioMessageCreator.GetStatus2MessageByFullMessageData()
"""


_decode_pool = None


def _get_decode_pool():
    global _decode_pool
    if _decode_pool is None:
        _decode_pool = Pool(4)
    return _decode_pool


def _decode_single_redcos(args):
    """Worker for persistent Pool: RS decode a single message (shared by punch and punch subsecond)."""
    corruptedMessageData, erasuresCombination = args
    try:
        return RSCoderLora.decode(corruptedMessageData, erasuresCombination)
    except Exception:
        return None


def _decode_double_redcos(args):
    """Worker for persistent Pool: RS decode a double message (shared by punch and punch subsecond)."""
    corruptedMessageData, erasuresCombination = args
    try:
        return RSCoderLora.decodeLong(corruptedMessageData, erasuresCombination)
    except Exception:
        return None


def _try_decode_double_alt(packed):
    """Worker for Pool: try RS-decode then erasure-decode one double alternative (shared by both doubles).

    packed: (messageAlt, rssiValue, snrValue, statusValue, allErasures)
    Returns (messageAlt, loraPunchMsg_or_None)
    """
    messageAlt, rssiValue, snrValue, statusValue, allErasures = packed

    # First try plain RS decode
    try:
        correctedData = RSCoderLora.decodeLong(
            bytearray(messageAlt[:-LoraRadioMessagePunchDoubleReDCoSRS.NoOfCRCBytes])
        )
        if correctedData is not None and RSCoderLora.checkLong(correctedData):
            # RS decoding an alternative (built from guessed field values) can land on any valid
            # codeword, so only accept it when its CRC confirms it is the received message.
            theCRCHash = hashlib.shake_128(correctedData[1:]).digest(2)
            if theCRCHash == bytes(messageAlt[-LoraRadioMessagePunchDoubleReDCoSRS.NoOfCRCBytes:]):
                msg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(
                    correctedData + messageAlt[-LoraRadioMessagePunchDoubleReDCoSRS.NoOfCRCBytes:],
                    rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
                return (messageAlt, msg)
    except Exception:
        pass

    # Then try with erasures
    if allErasures:
        msg = _get_double_message_with_erasures(
            bytearray(messageAlt), rssiValue, snrValue, statusValue, erasures=list(allErasures))
        if msg is not None:
            return (messageAlt, msg)

    return (messageAlt, None)

def _get_double_message_with_erasures(messageDataToConsider: bytearray, rssiValue: int, snrValue: int, statusValue: int, erasures: bytearray = None) -> LoraRadioMessageReDCoSRS | None:
        """Shared: punch double and punch subsecond double decode with erasures."""
        if len(erasures) > 0:
            try:
                erasuresToUse = list(set(erasures))
                if len(erasuresToUse) >= LoraRadioMessagePunchDoubleReDCoSRS.NoOfECCBytes:
                    erasuresToUse = erasuresToUse[0:LoraRadioMessagePunchReDCoSRS.NoOfECCBytes]
                elif len(erasuresToUse) % 2 != 0:
                    # Odd number
                    numberOfErasuresToUse = len(erasuresToUse) - 1
                    erasuresToUse = erasuresToUse[0:numberOfErasuresToUse]
                messageDataToConsiderWithoutCRC = messageDataToConsider[:-LoraRadioMessagePunchDoubleReDCoSRS.NoOfCRCBytes]

                LoraRadioDataHandler.WiRocLogger.verbose("LoraRadioDataHandler::_get_double_message_with_erasures ErasuresToUse: " + str(erasuresToUse))
                correctedData2 = RSCoderLora.decodeLong(messageDataToConsiderWithoutCRC, bytearray(erasuresToUse))

                if not RSCoderLora.checkLong(correctedData2):
                    # for some reason sometimes decode just returns the corrupted message with no change
                    # and no exception thrown. So check the decoded message to make sure we don't return
                    # a message that is clearly wrong
                    LoraRadioDataHandler.WiRocLogger.debug("LoraRadioDataHandler::_get_double_message_with_erasures Could not decode with erasures")
                    return None
                # Decoding with guessed erasures can land on any valid codeword; require the CRC to confirm it.
                theCRCHash = hashlib.shake_128(correctedData2[1:]).digest(2)
                if theCRCHash != bytes(messageDataToConsider[-LoraRadioMessagePunchDoubleReDCoSRS.NoOfCRCBytes:]):
                    LoraRadioDataHandler.WiRocLogger.debug("LoraRadioDataHandler::_get_double_message_with_erasures Decoded message does not match the received CRC")
                    return None
                loraMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(correctedData2 + messageDataToConsider[-LoraRadioMessagePunchDoubleReDCoSRS.NoOfCRCBytes:],
                                                                                   rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
                return loraMsg
            except Exception as err2:
                LoraRadioDataHandler.WiRocLogger.error(
                    "LoraRadioDataHandler::_get_double_message_with_erasures RS decoding failed also with erasures with exception: " + str(err2))
                return None
        else:
            LoraRadioDataHandler.WiRocLogger.error(
                "LoraRadioDataHandler::_get_double_message_with_erasures No erasures found so could not decode")
            return None


class LoraRadioDataHandler(object):
    WiRocLogger = logging.getLogger('WiRoc')
    MessageTypesExpected: list[int] = [LoraRadioMessageRS.MessageTypeSIPunchReDCoS, LoraRadioMessageRS.MessageTypeLoraAck, LoraRadioMessageRS.MessageTypeSIPunchDoubleReDCoS, LoraRadioMessageRS.MessageTypeStatus2, LoraRadioMessageRS.MessageTypeSIPunchSubSecond, LoraRadioMessageRS.MessageTypeSIPunchDoubleSubSecond]
    rssiValueCount: int = 0

    def __init__(self, noOfRSSIBytesExpected: int, noOfSNRBytesExpected: int = 0, noOfStatusBytesExpected: int = 0):
        self.DataReceived: bytearray = bytearray()
        # Dictionary of correctly received Punch message by control number
        self.ReceivedPunchMessageDict = {}
        self.LastPunchMessage: LoraRadioMessagePunchReDCoSRS | None = None
        self.LastPunchMessageTime: float | None = None
        self.LastPunchSubSecondMessage: LoraRadioMessagePunchSubSecondRS | None = None
        self.LastPunchSubSecondMessageTime: float | None = None
        self.LastPunchDoubleMessage: LoraRadioMessagePunchDoubleReDCoSRS | None = None
        self.LastPunchDoubleSubSecondMessage: LoraRadioMessagePunchDoubleSubSecondRS | None = None
        self.RxError = False
        self.rssiByteCount = noOfRSSIBytesExpected
        self.SNRByteCount = noOfSNRBytesExpected
        self.StatusByteCount = noOfStatusBytesExpected

    def AddData(self, dataByteOrArray):
        if isinstance(dataByteOrArray, Iterable):
            self.DataReceived.extend(dataByteOrArray)
        else:
            self.DataReceived.append(dataByteOrArray)

    def HasData(self) -> bool:
       return len(self.DataReceived) > 0

    def _IsLongEnoughToBeMessage(self):
        return len(self.DataReceived) >= (min(LoraRadioMessageRS.MessageLengths) + self.rssiByteCount + self.SNRByteCount + self.StatusByteCount)

    def _CachePunchMessage(self, loraMsg: LoraRadioMessagePunchReDCoSRS):
        controlNumber = loraMsg.GetControlNumber()
        msgAndMetadata = LoraRadioMessageAndMetadata(loraMsg)
        self.ReceivedPunchMessageDict[controlNumber] = msgAndMetadata
        self.LastPunchMessageTime = msgAndMetadata.GetTimeCreated()
        self.LastPunchMessage = loraMsg
        self.RxError = False

    def _CachePunchSubSecondMessage(self, loraMsg: LoraRadioMessagePunchSubSecondRS):
        controlNumber = loraMsg.GetControlNumber()
        msgAndMetadata = LoraRadioMessageAndMetadata(loraMsg)
        self.ReceivedPunchMessageDict[controlNumber] = msgAndMetadata
        self.LastPunchSubSecondMessageTime = msgAndMetadata.GetTimeCreated()
        self.LastPunchSubSecondMessage = loraMsg
        self.RxError = False

    def _CacheDoublePunchMessage(self, loraDoubleMsg: LoraRadioMessagePunchDoubleReDCoSRS):
        self.LastPunchDoubleMessage = loraDoubleMsg
        loraPunchMsg1, loraPunchMsg2 = self._GetPunchReDCoSTupleFromPunchDouble(loraDoubleMsg)
        self._CachePunchMessage(loraPunchMsg1)
        self._CachePunchMessage(loraPunchMsg2)

    def _CacheDoublePunchSubSecondMessage(self, loraDoubleMsg: LoraRadioMessagePunchDoubleSubSecondRS):
        self.LastPunchDoubleSubSecondMessage = loraDoubleMsg
        loraPunchMsg1, loraPunchMsg2 = self._GetPunchReDCoSTupleFromPunchDoubleSubSecond(loraDoubleMsg)
        self._CachePunchSubSecondMessage(loraPunchMsg1)
        self._CachePunchSubSecondMessage(loraPunchMsg2)

    def ClearDataReceived(self):
        LoraRadioDataHandler.WiRocLogger.debug("LoraRadioDataHandler::ClearDataReceived Data: " + Utils.GetDataInHex(self.DataReceived, logging.DEBUG))
        self.DataReceived = bytearray([])

    def _removeBytesFromDataReceived(self, noOfBytesToRemove):
        self.DataReceived = self.DataReceived[noOfBytesToRemove:]

    def _IsSameSingleMessage(self, loraMsg1: LoraRadioMessageReDCoSRS | None, loraMsg2: LoraRadioMessageReDCoSRS | None) -> bool:
        """Shared: called by both single-message getters (punch and punch subsecond)."""
        if loraMsg1 is None or loraMsg2 is None:
            return False

        msgCls = loraMsg1.__class__
        firstPunchConfidencePercentage = 0
        msg1ByteArray = loraMsg1.GetByteArray()
        msg2ByteArray = loraMsg2.GetByteArray()
        if msg1ByteArray[msgCls.CRC0] == msg2ByteArray[msgCls.CRC0]:
            firstPunchConfidencePercentage += 50
        if msg1ByteArray[msgCls.CRC1] == msg2ByteArray[msgCls.CRC1]:
            firstPunchConfidencePercentage += 50
        if msg1ByteArray[msgCls.TL] == msg2ByteArray[msgCls.TL]:
            firstPunchConfidencePercentage += 40
        if msg1ByteArray[msgCls.TH] == msg2ByteArray[msgCls.TH]:
            firstPunchConfidencePercentage += 10
        if msg1ByteArray[msgCls.SN0] == msg2ByteArray[msgCls.SN0]:
            firstPunchConfidencePercentage += 20
        if msg1ByteArray[msgCls.SN1] == msg2ByteArray[msgCls.SN1]:
            firstPunchConfidencePercentage += 20
        if msg1ByteArray[msgCls.SN2] == msg2ByteArray[msgCls.SN2]:
            firstPunchConfidencePercentage += 20
        if msg1ByteArray[msgCls.ECC0] == msg2ByteArray[msgCls.ECC0]:
            firstPunchConfidencePercentage += 20
        if msg1ByteArray[msgCls.ECC1] == msg2ByteArray[msgCls.ECC1]:
            firstPunchConfidencePercentage += 20
        if msg1ByteArray[msgCls.ECC2] == msg2ByteArray[msgCls.ECC2]:
            firstPunchConfidencePercentage += 20
        if msg1ByteArray[msgCls.ECC3] == msg2ByteArray[msgCls.ECC3]:
            firstPunchConfidencePercentage += 20
        #print("percentage1; " + str(firstPunchConfidencePercentage))
        return firstPunchConfidencePercentage >= 100

    def _IsSameDoubleMessage(self, loraMsg1: LoraRadioMessageReDCoSRS | None, loraMsg2: LoraRadioMessageReDCoSRS | None) -> bool:
        """Shared: called by both double-message getters (punch and punch subsecond)."""
        if loraMsg1 is None or loraMsg2 is None:
            return False

        msgCls = loraMsg1.__class__
        firstPunchConfidencePercentage = 0
        secondPunchConfidencePercentage = 0
        msg1ByteArray = loraMsg1.GetByteArray()
        msg2ByteArray = loraMsg2.GetByteArray()
        if msg1ByteArray[msgCls.CRC0] == msg2ByteArray[msgCls.CRC0]:
            firstPunchConfidencePercentage += 50
            secondPunchConfidencePercentage += 50
        if msg1ByteArray[msgCls.CRC1] == msg2ByteArray[msgCls.CRC1]:
            firstPunchConfidencePercentage += 50
            secondPunchConfidencePercentage += 50
        if msg1ByteArray[msgCls.TL] == msg2ByteArray[msgCls.TL]:
            firstPunchConfidencePercentage += 40
        if msg1ByteArray[msgCls.TL_2] == msg2ByteArray[msgCls.TL_2]:
            secondPunchConfidencePercentage += 40
        if msg1ByteArray[msgCls.TH] == msg2ByteArray[msgCls.TH]:
            firstPunchConfidencePercentage += 10
        if msg1ByteArray[msgCls.TH_2] == msg2ByteArray[msgCls.TH_2]:
            secondPunchConfidencePercentage += 10
        if msg1ByteArray[msgCls.SN0] == msg2ByteArray[msgCls.SN0]:
            firstPunchConfidencePercentage += 20
        if msg1ByteArray[msgCls.SN1] == msg2ByteArray[msgCls.SN1]:
            firstPunchConfidencePercentage += 20
        if msg1ByteArray[msgCls.SN2] == msg2ByteArray[msgCls.SN2]:
            firstPunchConfidencePercentage += 20
        if msg1ByteArray[msgCls.SN0_2] == msg2ByteArray[msgCls.SN0_2]:
            secondPunchConfidencePercentage += 20
        if msg1ByteArray[msgCls.SN1_2] == msg2ByteArray[msgCls.SN1_2]:
            secondPunchConfidencePercentage += 20
        if msg1ByteArray[msgCls.SN2_2] == msg2ByteArray[msgCls.SN2_2]:
            secondPunchConfidencePercentage += 20
        if msg1ByteArray[msgCls.ECC0] == msg2ByteArray[msgCls.ECC0]:
            firstPunchConfidencePercentage += 15
            secondPunchConfidencePercentage += 15
        if msg1ByteArray[msgCls.ECC1] == msg2ByteArray[msgCls.ECC1]:
            firstPunchConfidencePercentage += 15
            secondPunchConfidencePercentage += 15
        if msg1ByteArray[msgCls.ECC2] == msg2ByteArray[msgCls.ECC2]:
            firstPunchConfidencePercentage += 15
            secondPunchConfidencePercentage += 15
        if msg1ByteArray[msgCls.ECC3] == msg2ByteArray[msgCls.ECC3]:
            firstPunchConfidencePercentage += 15
            secondPunchConfidencePercentage += 15
        if msg1ByteArray[msgCls.ECC4] == msg2ByteArray[msgCls.ECC4]:
            firstPunchConfidencePercentage += 15
            secondPunchConfidencePercentage += 15
        if msg1ByteArray[msgCls.ECC5] == msg2ByteArray[msgCls.ECC5]:
            firstPunchConfidencePercentage += 15
            secondPunchConfidencePercentage += 15
        if msg1ByteArray[msgCls.ECC6] == msg2ByteArray[msgCls.ECC6]:
            firstPunchConfidencePercentage += 15
            secondPunchConfidencePercentage += 15
        if msg1ByteArray[msgCls.ECC7] == msg2ByteArray[msgCls.ECC7]:
            firstPunchConfidencePercentage += 15
            secondPunchConfidencePercentage += 15
        #print("percentage1; " + str(firstPunchConfidencePercentage) + " percentage2: " + str(secondPunchConfidencePercentage))
        return firstPunchConfidencePercentage >= 100 and secondPunchConfidencePercentage >= 100

    def _GetPunchDoubleMessageAlternatives(self, loraMsg: LoraRadioMessagePunchDoubleReDCoSRS, totalRetryDelaySeconds: float = None) -> Tuple[List[bytearray], list, bytearray]:
        possibilities: list[list[int] | None] = [None] * LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunchDoubleReDCoS]

        headers = None
        if self.LastPunchMessage is not None:

            headers = [(self.LastPunchMessage.GetHeaderData()[0] & ~LoraRadioMessageRS.MessageTypeBitMask) | LoraRadioMessageRS.MessageTypeSIPunchDoubleReDCoS]
            if (self.LastPunchMessage.GetHeaderData()[0] & ~LoraRadioMessageRS.MessageTypeBitMask) != \
                    (loraMsg.GetHeaderData()[0] & ~LoraRadioMessageRS.MessageTypeBitMask):
                headers += [(loraMsg.GetHeaderData()[0] & ~LoraRadioMessageRS.MessageTypeBitMask) | LoraRadioMessageRS.MessageTypeSIPunchDoubleReDCoS]

        # Only use a maximum of 4 control numbers, use the latest 4
        maximumNoOfControlNumbersToTest = 1
        loraRange = SettingsClass.GetLoraRange()
        if loraRange == 'UL':
            maximumNoOfControlNumbersToTest = 4
        elif loraRange == 'XL':
            maximumNoOfControlNumbersToTest = 3
        elif loraRange == 'L':
            maximumNoOfControlNumbersToTest = 3
        elif loraRange == 'ML':
            maximumNoOfControlNumbersToTest = 2
        elif loraRange == 'MF' or loraRange == 'MS':
            maximumNoOfControlNumbersToTest = 1
        elif loraRange == 'F' or loraRange == 'S':
            maximumNoOfControlNumbersToTest = 1
        elif loraRange == 'XF':
            maximumNoOfControlNumbersToTest = 1
        elif loraRange == 'UF':
            maximumNoOfControlNumbersToTest = 1

        controlNumbers = [(controlNumber & 0xFF) for controlNumber in sorted(self.ReceivedPunchMessageDict.keys(), key=lambda k: self.ReceivedPunchMessageDict[k].timeCreated, reverse=True)]
        controlNumber8bit = (loraMsg.GetControlNumber() & 0xFF)
        # prepend the message's own control number if it is not in the list, or move it to the front if it is already in the list
        if controlNumber8bit not in controlNumbers:
            controlNumbers.insert(0, controlNumber8bit)
        else:
            controlNumbers.insert(0, controlNumbers.pop(controlNumbers.index(controlNumber8bit)))
        controlNumbers = controlNumbers[:maximumNoOfControlNumbersToTest]

        # Assume cn1Plus is the same as the last punch message. Unlikely to be different so dont create alternative with received message value
        cn1Plus = None
        if self.LastPunchMessage is not None:
            cn1Plus = [self.LastPunchMessage.GetByteArray()[LoraRadioMessagePunchDoubleReDCoSRS.CN1Plus]]
        
        TH: None | list[int] = None
        if self.LastPunchMessageTime is not None:
            retryDelay = totalRetryDelaySeconds if totalRetryDelaySeconds is not None else SettingsClass.GetTotalRetryDelaySeconds()
            noOfSecondsSinceLastMessage = int(time.monotonic() - self.LastPunchMessageTime)
            lowestTimeWeAssumeCanBeCorrect = max(self.LastPunchMessage.GetTwelveHourTimerAsInt() \
                                                + noOfSecondsSinceLastMessage - retryDelay,
                                                 self.LastPunchMessage.GetTwelveHourTimerAsInt())
            # Assuming a delay of delivery of a message of max 5 minutes
            highestTimeWeAssumeCanBeCorrect = self.LastPunchMessage.GetTwelveHourTimerAsInt() \
                                          + noOfSecondsSinceLastMessage + 2 * retryDelay
            if (lowestTimeWeAssumeCanBeCorrect & 0xFF00) <= loraMsg.GetTwelveHourTimer()[0] <= (highestTimeWeAssumeCanBeCorrect & 0xFF00):
                # the TH is very reasonable so assume it is correct
                TH = [loraMsg.GetTwelveHourTimer()[0]]
            else:
                TH = list(range((lowestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8, ((highestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8)+1))


        # Message 2
        # Only use a maximum of 4 control numbers, use the latest 4
        # prepend the message's own control number if it is not in the list, or move it to the front if it is already in the list
        controlNumbers_2 = controlNumbers[:]
        controlNumber8bit_2 = (loraMsg.GetControlNumber_2() & 0xFF)
        if controlNumber8bit_2 not in controlNumbers_2:
            controlNumbers_2.insert(0, controlNumber8bit_2)
        else:
            controlNumbers_2.insert(0, controlNumbers_2.pop(controlNumbers_2.index(controlNumber8bit_2)))
        controlNumbers_2 = controlNumbers_2[:maximumNoOfControlNumbersToTest]   

        cn1Plus_2: list[int] | None = None
        if self.LastPunchMessage is not None:
            cn1Plus_2 = [self.LastPunchMessage.GetPayloadByteArray()[LoraRadioMessagePunchReDCoSRS.CN1Plus - 1]]
        TH2 = None
        if self.LastPunchMessageTime is not None:
            noOfSecondsSinceLastMessage = int(time.monotonic() - self.LastPunchMessageTime)
            lowestTimeWeAssumeCanBeCorrect = max(self.LastPunchMessage.GetTwelveHourTimerAsInt() \
                                                 + noOfSecondsSinceLastMessage - retryDelay,
                                                 self.LastPunchMessage.GetTwelveHourTimerAsInt())
            highestTimeWeAssumeCanBeCorrect = self.LastPunchMessage.GetTwelveHourTimerAsInt() \
                + noOfSecondsSinceLastMessage + 2 * retryDelay
            if ((lowestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8) <= loraMsg.GetTwelveHourTimer_2()[0] \
                    <= ((highestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8):
                # the TH is very reasonable so assume it is correct
                TH2 = [loraMsg.GetTwelveHourTimer_2()[0]]
            else:
                TH2 = list(range((lowestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8, ((highestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8)+1))

        fixedValues =  []
        if headers is not None:
            possibilities[LoraRadioMessagePunchDoubleReDCoSRS.H] = headers
            fixedValues += [LoraRadioMessagePunchDoubleReDCoSRS.H]
        possibilities[LoraRadioMessagePunchDoubleReDCoSRS.CN0] = controlNumbers
        fixedValues += [LoraRadioMessagePunchDoubleReDCoSRS.CN0]
        if cn1Plus is not None:
            possibilities[LoraRadioMessagePunchDoubleReDCoSRS.CN1Plus] = cn1Plus
            fixedValues += [LoraRadioMessagePunchDoubleReDCoSRS.CN1Plus]
        if TH is not None:
            possibilities[LoraRadioMessagePunchDoubleReDCoSRS.TH] = TH
            fixedValues += [LoraRadioMessagePunchDoubleReDCoSRS.TH]
        possibilities[LoraRadioMessagePunchDoubleReDCoSRS.CN0_2] = controlNumbers_2
        fixedValues += [LoraRadioMessagePunchDoubleReDCoSRS.CN0_2]
        if cn1Plus_2 is not None:
            possibilities[LoraRadioMessagePunchDoubleReDCoSRS.CN1Plus_2] = cn1Plus_2
            fixedValues += [LoraRadioMessagePunchDoubleReDCoSRS.CN1Plus_2]
        if TH2 is not None:
            possibilities[LoraRadioMessagePunchDoubleReDCoSRS.TH_2] = TH2
            fixedValues += [LoraRadioMessagePunchDoubleReDCoSRS.TH_2]

        messageData = loraMsg.GetByteArray()
        LoraRadioDataHandler.WiRocLogger.verbose("possibilities: " + str(possibilities))
        generatedMessages = self._GenerateMessageAlternatives(bytearray(), possibilities, messageData)
        fixedErasures = self._FindReDCoSPunchDoubleErasures(loraMsg, totalRetryDelaySeconds)
        fixedErasures = bytearray(set(fixedErasures) - set(fixedValues))
        return generatedMessages, fixedValues, fixedErasures

    def _GetPunchDoubleSubSecondMessageAlternatives(self, loraMsg: LoraRadioMessagePunchDoubleSubSecondRS, totalRetryDelaySeconds: float = None) -> Tuple[List[bytearray], list, bytearray]:
        possibilities: list[list[int] | None] = [None] * LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunchDoubleSubSecond]

        headers = None
        if self.LastPunchSubSecondMessage is not None:

            headers = [(self.LastPunchSubSecondMessage.GetHeaderData()[0] & ~LoraRadioMessageRS.MessageTypeBitMask) | LoraRadioMessageRS.MessageTypeSIPunchDoubleSubSecond]
            if (self.LastPunchSubSecondMessage.GetHeaderData()[0] & ~LoraRadioMessageRS.MessageTypeBitMask) != \
                    (loraMsg.GetHeaderData()[0] & ~LoraRadioMessageRS.MessageTypeBitMask):
                headers += [(loraMsg.GetHeaderData()[0] & ~LoraRadioMessageRS.MessageTypeBitMask) | LoraRadioMessageRS.MessageTypeSIPunchDoubleSubSecond]

        # Only use a maximum of 4 control numbers, use the latest 4
        maximumNoOfControlNumbersToTest = 1
        loraRange = SettingsClass.GetLoraRange()
        if loraRange == 'UL':
            maximumNoOfControlNumbersToTest = 4
        elif loraRange == 'XL':
            maximumNoOfControlNumbersToTest = 3
        elif loraRange == 'L':
            maximumNoOfControlNumbersToTest = 3
        elif loraRange == 'ML':
            maximumNoOfControlNumbersToTest = 2
        elif loraRange == 'MF' or loraRange == 'MS':
            maximumNoOfControlNumbersToTest = 1
        elif loraRange == 'F' or loraRange == 'S':
            maximumNoOfControlNumbersToTest = 1
        elif loraRange == 'XF':
            maximumNoOfControlNumbersToTest = 1
        elif loraRange == 'UF':
            maximumNoOfControlNumbersToTest = 1

        controlNumbers = [(controlNumber & 0xFF) for controlNumber in sorted(self.ReceivedPunchMessageDict.keys(), key=lambda k: self.ReceivedPunchMessageDict[k].timeCreated, reverse=True)]
        controlNumber8bit = (loraMsg.GetControlNumber() & 0xFF)
        # prepend the message's own control number if it is not in the list, or move it to the front if it is already in the list
        if controlNumber8bit not in controlNumbers:
            controlNumbers.insert(0, controlNumber8bit)
        else:
            controlNumbers.insert(0, controlNumbers.pop(controlNumbers.index(controlNumber8bit)))
        controlNumbers = controlNumbers[:maximumNoOfControlNumbersToTest]

        # Assume cn1Plus is the same as the last punch message. Unlikely to be different so dont create alternative with received message value
        cn1Plus: None | list[int] = None
        if self.LastPunchSubSecondMessage is not None:
            cn1Plus = [self.LastPunchSubSecondMessage.GetByteArray()[LoraRadioMessagePunchDoubleSubSecondRS.CN1Plus]]

        TH: None | list[int] = None
        if self.LastPunchSubSecondMessageTime is not None:
            retryDelay = totalRetryDelaySeconds if totalRetryDelaySeconds is not None else SettingsClass.GetTotalRetryDelaySeconds()
            noOfSecondsSinceLastMessage = int(time.monotonic() - self.LastPunchSubSecondMessageTime)
            lowestTimeWeAssumeCanBeCorrect = max(self.LastPunchSubSecondMessage.GetTwelveHourTimerAsInt() \
                                                + noOfSecondsSinceLastMessage - retryDelay,
                                                 self.LastPunchSubSecondMessage.GetTwelveHourTimerAsInt())
            # Assuming a delay of delivery of a message of max 5 minutes
            highestTimeWeAssumeCanBeCorrect = self.LastPunchSubSecondMessage.GetTwelveHourTimerAsInt() \
                                          + noOfSecondsSinceLastMessage + 2 * retryDelay
            if (lowestTimeWeAssumeCanBeCorrect & 0xFF00) <= loraMsg.GetTwelveHourTimer()[0] <= (highestTimeWeAssumeCanBeCorrect & 0xFF00):
                # the TH is very reasonable so assume it is correct
                TH = [loraMsg.GetTwelveHourTimer()[0]]
            else:
                TH = list(range((lowestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8, ((highestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8)+1))


        # Message 2
        # Only use a maximum of 4 control numbers, use the latest 4
        # prepend the message's own control number if it is not in the list, or move it to the front if it is already in the list
        controlNumbers_2 = controlNumbers[:]
        controlNumber8bit_2 = (loraMsg.GetControlNumber_2() & 0xFF)
        if controlNumber8bit_2 not in controlNumbers_2:
            controlNumbers_2.insert(0, controlNumber8bit_2)
        else:
            controlNumbers_2.insert(0, controlNumbers_2.pop(controlNumbers_2.index(controlNumber8bit_2)))
        controlNumbers_2 = controlNumbers_2[:maximumNoOfControlNumbersToTest]

        cn1Plus_2: list[int] | None = None
        if self.LastPunchSubSecondMessage is not None:
            cn1Plus_2 = [self.LastPunchSubSecondMessage.GetPayloadByteArray()[LoraRadioMessagePunchSubSecondRS.CN1Plus - 1]]
        TH2 = None
        if self.LastPunchSubSecondMessageTime is not None:
            noOfSecondsSinceLastMessage = int(time.monotonic() - self.LastPunchSubSecondMessageTime)
            lowestTimeWeAssumeCanBeCorrect = max(self.LastPunchSubSecondMessage.GetTwelveHourTimerAsInt() \
                                                 + noOfSecondsSinceLastMessage - retryDelay,
                                                 self.LastPunchSubSecondMessage.GetTwelveHourTimerAsInt())
            highestTimeWeAssumeCanBeCorrect = self.LastPunchSubSecondMessage.GetTwelveHourTimerAsInt() \
                + noOfSecondsSinceLastMessage + 2 * retryDelay
            if ((lowestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8) <= loraMsg.GetTwelveHourTimer_2()[0] \
                    <= ((highestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8):
                # the TH is very reasonable so assume it is correct
                TH2 = [loraMsg.GetTwelveHourTimer_2()[0]]
            else:
                TH2 = list(range((lowestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8, ((highestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8)+1))

        fixedValues =  []
        if headers is not None:
            possibilities[LoraRadioMessagePunchDoubleSubSecondRS.H] = headers
            fixedValues += [LoraRadioMessagePunchDoubleSubSecondRS.H]
        possibilities[LoraRadioMessagePunchDoubleSubSecondRS.CN0] = controlNumbers
        fixedValues += [LoraRadioMessagePunchDoubleSubSecondRS.CN0]
        if cn1Plus is not None:
            possibilities[LoraRadioMessagePunchDoubleSubSecondRS.CN1Plus] = cn1Plus
            fixedValues += [LoraRadioMessagePunchDoubleSubSecondRS.CN1Plus]
        if TH is not None:
            possibilities[LoraRadioMessagePunchDoubleSubSecondRS.TH] = TH
            fixedValues += [LoraRadioMessagePunchDoubleSubSecondRS.TH]
        possibilities[LoraRadioMessagePunchDoubleSubSecondRS.CN0_2] = controlNumbers_2
        fixedValues += [LoraRadioMessagePunchDoubleSubSecondRS.CN0_2]
        if cn1Plus_2 is not None:
            possibilities[LoraRadioMessagePunchDoubleSubSecondRS.CN1Plus_2] = cn1Plus_2
            fixedValues += [LoraRadioMessagePunchDoubleSubSecondRS.CN1Plus_2]
        if TH2 is not None:
            possibilities[LoraRadioMessagePunchDoubleSubSecondRS.TH_2] = TH2
            fixedValues += [LoraRadioMessagePunchDoubleSubSecondRS.TH_2]

        messageData = loraMsg.GetByteArray()
        LoraRadioDataHandler.WiRocLogger.verbose("possibilities: " + str(possibilities))
        generatedMessages = self._GenerateMessageAlternatives(bytearray(), possibilities, messageData)
        fixedErasures = self._FindReDCoSPunchDoubleSubSecondErasures(loraMsg, totalRetryDelaySeconds)
        fixedErasures = bytearray(set(fixedErasures) - set(fixedValues))
        return generatedMessages, fixedValues, fixedErasures

    def _GetPunchMessageAlternatives(self, loraMsg: LoraRadioMessagePunchReDCoSRS, totalRetryDelaySeconds: float = None) -> Tuple[List[bytearray], list, bytearray]:
        headers = [(loraMsg.GetHeaderData()[0] & ~LoraRadioMessageRS.MessageTypeBitMask) | LoraRadioMessageRS.MessageTypeSIPunchReDCoS]
        if self.LastPunchMessage is not None:
            if (self.LastPunchMessage.GetHeaderData()[0] & ~LoraRadioMessageRS.MessageTypeBitMask) != \
                    (loraMsg.GetHeaderData()[0] & ~LoraRadioMessageRS.MessageTypeBitMask):
                headers += [(self.LastPunchMessage.GetHeaderData()[0] & ~LoraRadioMessageRS.MessageTypeBitMask) | LoraRadioMessageRS.MessageTypeSIPunchReDCoS]

        # Only use a maximum of 8 control numbers, use the latest
        maximumNoOfControlNumbersToTest = 2
        loraRange = SettingsClass.GetLoraRange()
        if loraRange == 'UL':
            maximumNoOfControlNumbersToTest = 8
        elif loraRange == 'XL':
            maximumNoOfControlNumbersToTest = 6
        elif loraRange == 'L':
            maximumNoOfControlNumbersToTest = 6
        elif loraRange == 'ML':
            maximumNoOfControlNumbersToTest = 4
        elif loraRange == 'MF' or loraRange == 'MS':
            maximumNoOfControlNumbersToTest = 3
        elif loraRange == 'F' or loraRange == 'S':
            maximumNoOfControlNumbersToTest = 2
        elif loraRange == 'XF':
            maximumNoOfControlNumbersToTest = 2
        elif loraRange == 'UF':
            maximumNoOfControlNumbersToTest = 2

        controlNumbers = [(controlNumber & 0xFF) for controlNumber in sorted(self.ReceivedPunchMessageDict.keys(),
                                                                             key=lambda k:
                                                                             self.ReceivedPunchMessageDict[
                                                                                 k].timeCreated, reverse=True)]

        controlNumber8bit = (loraMsg.GetControlNumber() & 0xFF)
        # prepend the message's own control number if it is not in the list, or move it to the front if it is already in the list
        if controlNumber8bit not in controlNumbers:
            controlNumbers.insert(0, controlNumber8bit)
        else:
            controlNumbers.insert(0, controlNumbers.pop(controlNumbers.index(controlNumber8bit)))
        controlNumbers = controlNumbers[:maximumNoOfControlNumbersToTest]


        cn1Plus = None
        if self.LastPunchMessage is not None:
            cn1Plus = [self.LastPunchMessage.GetByteArray()[LoraRadioMessagePunchReDCoSRS.CN1Plus]]

        TH = None
        if self.LastPunchMessageTime is not None:
            retryDelay = totalRetryDelaySeconds if totalRetryDelaySeconds is not None else SettingsClass.GetTotalRetryDelaySeconds()
            noOfSecondsSinceLastMessage = int(time.monotonic() - self.LastPunchMessageTime)
            lowestTimeWeAssumeCanBeCorrect = max(self.LastPunchMessage.GetTwelveHourTimerAsInt() \
                                                 + noOfSecondsSinceLastMessage - retryDelay,
                                                 self.LastPunchMessage.GetTwelveHourTimerAsInt())
            highestTimeWeAssumeCanBeCorrect = self.LastPunchMessage.GetTwelveHourTimerAsInt() \
                + noOfSecondsSinceLastMessage + 2*retryDelay
            if ((lowestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8) <= loraMsg.GetTwelveHourTimer()[0] \
                    <= ((highestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8):
                # the TH is very reasonable so assume it is correct
                TH = [loraMsg.GetTwelveHourTimer()[0]]
                #print("TH: " + str(TH))
            else:
                TH = list(range((lowestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8, ((highestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8) + 1))
                #print("TH: " + str(TH))

        fixedValues = [LoraRadioMessagePunchReDCoSRS.H, LoraRadioMessagePunchReDCoSRS.CN0]
        possibilities: list[list[int] | None] = [None]*LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunchReDCoS]
        possibilities[LoraRadioMessagePunchReDCoSRS.H] = headers
        possibilities[LoraRadioMessagePunchReDCoSRS.CN0] = controlNumbers
        possibilities[LoraRadioMessagePunchReDCoSRS.CN1Plus] = cn1Plus
        if cn1Plus is not None:
            possibilities[LoraRadioMessagePunchReDCoSRS.CN1Plus] = cn1Plus
            fixedValues += [LoraRadioMessagePunchReDCoSRS.CN1Plus]
        if TH is not None:
            possibilities[LoraRadioMessagePunchReDCoSRS.TH] = TH
            fixedValues += [LoraRadioMessagePunchReDCoSRS.TH]
        # print("possibilities: " + str(possibilities))
        messageData = loraMsg.GetByteArray()
        generatedMessages = self._GenerateMessageAlternatives(bytearray(), possibilities, messageData)

        fixedErasures = self._FindReDCoSPunchErasures(loraMsg, totalRetryDelaySeconds)
        fixedErasures = bytearray(set(fixedErasures) - set(fixedValues))
        return generatedMessages, fixedValues, fixedErasures

    def _GetPunchSubSecondMessageAlternatives(self, loraMsg: LoraRadioMessagePunchSubSecondRS, totalRetryDelaySeconds: float = None) -> Tuple[List[bytearray], list, bytearray]:
        headers = [(loraMsg.GetHeaderData()[0] & ~LoraRadioMessageRS.MessageTypeBitMask) | LoraRadioMessageRS.MessageTypeSIPunchSubSecond]
        if self.LastPunchSubSecondMessage is not None:
            if (self.LastPunchSubSecondMessage.GetHeaderData()[0] & ~LoraRadioMessageRS.MessageTypeBitMask) != \
                    (loraMsg.GetHeaderData()[0] & ~LoraRadioMessageRS.MessageTypeBitMask):
                headers += [(self.LastPunchSubSecondMessage.GetHeaderData()[0] & ~LoraRadioMessageRS.MessageTypeBitMask) | LoraRadioMessageRS.MessageTypeSIPunchSubSecond]

        # Only use a maximum of 8 control numbers, use the latest
        maximumNoOfControlNumbersToTest = 2
        loraRange = SettingsClass.GetLoraRange()
        if loraRange == 'UL':
            maximumNoOfControlNumbersToTest = 8
        elif loraRange == 'XL':
            maximumNoOfControlNumbersToTest = 6
        elif loraRange == 'L':
            maximumNoOfControlNumbersToTest = 6
        elif loraRange == 'ML':
            maximumNoOfControlNumbersToTest = 4
        elif loraRange == 'MF' or loraRange == 'MS':
            maximumNoOfControlNumbersToTest = 3
        elif loraRange == 'F' or loraRange == 'S':
            maximumNoOfControlNumbersToTest = 2
        elif loraRange == 'XF':
            maximumNoOfControlNumbersToTest = 2
        elif loraRange == 'UF':
            maximumNoOfControlNumbersToTest = 2

        controlNumbers = [(controlNumber & 0xFF) for controlNumber in sorted(self.ReceivedPunchMessageDict.keys(),
                                                                             key=lambda k:
                                                                             self.ReceivedPunchMessageDict[
                                                                                 k].timeCreated, reverse=True)]

        controlNumber8bit = (loraMsg.GetControlNumber() & 0xFF)
        # prepend the message's own control number if it is not in the list, or move it to the front if it is already in the list
        if controlNumber8bit not in controlNumbers:
            controlNumbers.insert(0, controlNumber8bit)
        else:
            controlNumbers.insert(0, controlNumbers.pop(controlNumbers.index(controlNumber8bit)))
        controlNumbers = controlNumbers[:maximumNoOfControlNumbersToTest]


        cn1Plus = None
        if self.LastPunchSubSecondMessage is not None:
            cn1Plus = [self.LastPunchSubSecondMessage.GetByteArray()[LoraRadioMessagePunchSubSecondRS.CN1Plus]]

        TH = None
        if self.LastPunchSubSecondMessageTime is not None:
            retryDelay = totalRetryDelaySeconds if totalRetryDelaySeconds is not None else SettingsClass.GetTotalRetryDelaySeconds()
            noOfSecondsSinceLastMessage = int(time.monotonic() - self.LastPunchSubSecondMessageTime)
            lowestTimeWeAssumeCanBeCorrect = max(self.LastPunchSubSecondMessage.GetTwelveHourTimerAsInt() \
                                                 + noOfSecondsSinceLastMessage - retryDelay,
                                                 self.LastPunchSubSecondMessage.GetTwelveHourTimerAsInt())
            highestTimeWeAssumeCanBeCorrect = self.LastPunchSubSecondMessage.GetTwelveHourTimerAsInt() \
                + noOfSecondsSinceLastMessage + 2*retryDelay
            if ((lowestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8) <= loraMsg.GetTwelveHourTimer()[0] \
                    <= ((highestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8):
                # the TH is very reasonable so assume it is correct
                TH = [loraMsg.GetTwelveHourTimer()[0]]
            else:
                TH = list(range((lowestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8, ((highestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8) + 1))

        fixedValues = [LoraRadioMessagePunchSubSecondRS.H, LoraRadioMessagePunchSubSecondRS.CN0]
        possibilities: list[list[int] | None] = [None]*LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunchSubSecond]
        possibilities[LoraRadioMessagePunchSubSecondRS.H] = headers
        possibilities[LoraRadioMessagePunchSubSecondRS.CN0] = controlNumbers
        possibilities[LoraRadioMessagePunchSubSecondRS.CN1Plus] = cn1Plus
        if cn1Plus is not None:
            possibilities[LoraRadioMessagePunchSubSecondRS.CN1Plus] = cn1Plus
            fixedValues += [LoraRadioMessagePunchSubSecondRS.CN1Plus]
        if TH is not None:
            possibilities[LoraRadioMessagePunchSubSecondRS.TH] = TH
            fixedValues += [LoraRadioMessagePunchSubSecondRS.TH]
        messageData = loraMsg.GetByteArray()
        generatedMessages = self._GenerateMessageAlternatives(bytearray(), possibilities, messageData)

        fixedErasures = self._FindReDCoSPunchSubSecondErasures(loraMsg, totalRetryDelaySeconds)
        fixedErasures = bytearray(set(fixedErasures) - set(fixedValues))
        return generatedMessages, fixedValues, fixedErasures

    def _GenerateMessageAlternatives(self, generatedMessage: bytearray, possibilities, origMessageData: bytearray) -> List[bytearray]:
        generatedMessages = []
        byteIndex = len(generatedMessage)
        if byteIndex >= len(possibilities):
            return [generatedMessage]
        if possibilities[byteIndex] is not None:
            for possibility in possibilities[byteIndex]:
                generatedMessages += self._GenerateMessageAlternatives(generatedMessage + bytearray([possibility]), possibilities, origMessageData)
        else:
            generatedMessages += self._GenerateMessageAlternatives(generatedMessage + bytearray([origMessageData[byteIndex]]), possibilities,
                                                                        origMessageData)
        return generatedMessages

    def _AddFixedErasursToCombinationIterator(self, erasureCominationIterator, fixedErasures: bytearray):
        for comb in erasureCominationIterator:
            yield comb + fixedErasures

    def _GetReDCoSErasureCombinations(self, loraMsg, fixedValues, fixedErasures: bytearray, eccBytesToNotUse):
        messageData = loraMsg.GetByteArray()
        lengthOfMessage = len(messageData)
        lengthOfDataWithoutCRC = lengthOfMessage - loraMsg.NoOfCRCBytes
        indexInMessageThatMayOrMayNotHaveErrors = list(set(range(lengthOfDataWithoutCRC))-set(fixedValues) - set(fixedErasures))
        #print("fixed values: " + str(fixedValues))
        #print("fixed erasures: " + str(fixedErasures))
        #print("ecc bytes not used: " + str(eccBytesToNotUse))
        erasureCombinationIterator = itertools.combinations(indexInMessageThatMayOrMayNotHaveErrors, loraMsg.NoOfECCBytes - len(fixedErasures) - eccBytesToNotUse)
        # change to a list of bytearrays (instead of list of tuple)
        erasureCombinationIterator = [bytearray(tup) for tup in erasureCombinationIterator]
        #print("combinations: " + str(list(erasureCombinationIterator)))
        return self._AddFixedErasursToCombinationIterator(erasureCombinationIterator, fixedErasures)

    def _FindReDCoSPunchErasures(self, loraMsg: LoraRadioMessagePunchReDCoSRS, totalRetryDelaySeconds: float = None) -> bytearray:
        return self._FindSingleMessageErasures(loraMsg, self.LastPunchMessage, self.LastPunchMessageTime, totalRetryDelaySeconds)

    def _FindReDCoSPunchSubSecondErasures(self, loraMsg: LoraRadioMessagePunchSubSecondRS, totalRetryDelaySeconds: float = None) -> bytearray:
        return self._FindSingleMessageErasures(loraMsg, self.LastPunchSubSecondMessage, self.LastPunchSubSecondMessageTime, totalRetryDelaySeconds)

    def _FindSingleMessageErasures(self, loraMsg: LoraRadioMessageReDCoSRS, lastSingleMessage: LoraRadioMessageReDCoSRS | None, lastSingleMessageTime: float | None, totalRetryDelaySeconds: float = None) -> bytearray:
        """Shared: single punch and single subsecond messages; positions come from loraMsg.__class__."""
        # The returned index is relative to the beginning of the message, including header. This is to match the fixedValues array.
        msgCls = loraMsg.__class__
        controlNumber = loraMsg.GetControlNumber()
        controlNumber8bit = (controlNumber & 0xFF)
        controlNumberToUse = controlNumber if controlNumber in self.ReceivedPunchMessageDict else controlNumber8bit

        erasures = bytearray()
        if controlNumberToUse in self.ReceivedPunchMessageDict:
            # found a previously cached message from same controlnumber => probably correct controlnumber
            previousMsgAndMetadata = self.ReceivedPunchMessageDict[controlNumberToUse]
            previousMsg = previousMsgAndMetadata.GetLoraRadioMessageRS()
        elif len(self.ReceivedPunchMessageDict) > 0:
            erasures.append(msgCls.CN0)

        cardNoByteArray = loraMsg.GetSICardNoByteArray()
        #print("cardNoByteArray: " + Utils.GetDataInHex(cardNoByteArray, logging.DEBUG))
        cardNo = Utils.toInt(cardNoByteArray)
        if 0x4FFFF < cardNo < 500000: # 500 000 = 0x7A120
            erasures.append(msgCls.SN2) # at least SN2 should be wrong

        # check that TH isn't higher than possible
        if loraMsg.GetTwelveHourTimer()[0] > 0xA8:
            erasures.append(msgCls.TH)

        if lastSingleMessage is not None:
            loraPayload = loraMsg.GetPayloadByteArray()
            loraTwelveHourTimer = loraMsg.GetTwelveHourTimer()
            cn1PlusWrong = lastSingleMessage.GetPayloadByteArray()[msgCls.CN1Plus - 1] != \
                loraPayload[msgCls.CN1Plus - 1]
            # If the byte with AM/PM (6) is found to be wrong then assume AM/PM has not changed and compare the TH, TL
            if cn1PlusWrong or (lastSingleMessage.GetTwentyFourHour() == loraMsg.GetTwentyFourHour()):
                noOfSecondsSinceLastMessage = int(time.monotonic() - lastSingleMessageTime)
                totalRetryDelay = totalRetryDelaySeconds if totalRetryDelaySeconds is not None else SettingsClass.GetTotalRetryDelaySeconds()
                lastPunchTimerAsInt = lastSingleMessage.GetTwelveHourTimerAsInt()
                loraTimerAsInt = loraMsg.GetTwelveHourTimerAsInt()
                lowestTimeWeAssumeCanBeCorrect = lastPunchTimerAsInt - totalRetryDelay
                # We are more permissive here than compared to when creating alternatives. Here is is more important not to
                # point to an erasure that shouldn't be an erasure. And when getting alternatives it is more important to limit the
                # number of alternatives
                highestTimeWeAssumeCanBeCorrect = lastPunchTimerAsInt \
                    + noOfSecondsSinceLastMessage + 4*totalRetryDelay
                if loraTimerAsInt < lowestTimeWeAssumeCanBeCorrect:
                    if loraTwelveHourTimer[0] != lastSingleMessage.GetTwelveHourTimer()[0]:
                        # TH differs so this must be the reason for time being too low (assume TL is correct)
                        erasures.append(msgCls.TH)
                    else:
                        erasures.append(msgCls.TL)
                elif loraTimerAsInt > highestTimeWeAssumeCanBeCorrect:
                    if loraTwelveHourTimer[0] > ((highestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8):
                        # TH differs so this must be the reason for time being too high (assume TL is correct)
                        erasures.append(msgCls.TH)
                    else:
                        erasures.append(msgCls.TL)

            # check that TL isn't higher than possible. Only check when TH is the highest value and not believed
            # to be wrong
            if loraTwelveHourTimer[0] == 0xA8 and loraTwelveHourTimer[1] > 0xC0 \
                    and msgCls.TH not in erasures:
                erasures.append(msgCls.TL)

        LoraRadioDataHandler.WiRocLogger.verbose(
            "LoraRadioDataHandler::_FindReDCoSPunchErasures " + str(len(erasures)) + " erasures found. " + str(erasures))
        return bytearray(set(erasures))

    def _GetPunchReDCoSTupleFromPunchDouble(self, loraDoubleMsg: LoraRadioMessagePunchDoubleReDCoSRS):
        payload = loraDoubleMsg.GetByteArray()
        loraMsgLength = LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunchReDCoS]
        # recreate two message arrays and find the erasures for each
        firstMsgByteArray = payload[0:loraMsgLength-LoraRadioMessagePunchReDCoSRS.NoOfECCBytes-LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes] + bytearray(LoraRadioMessagePunchReDCoSRS.NoOfECCBytes) + bytearray(LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes)
        firstMsgByteArray[LoraRadioMessageRS.H] = (firstMsgByteArray[LoraRadioMessageRS.H] & ~LoraRadioMessageRS.MessageTypeBitMask) | LoraRadioMessageRS.MessageTypeSIPunchReDCoS
        secondMsgByteArray = bytearray([firstMsgByteArray[LoraRadioMessageRS.H]]) + \
            payload[loraMsgLength - LoraRadioMessagePunchReDCoSRS.NoOfECCBytes - LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes:-LoraRadioMessagePunchDoubleReDCoSRS.NoOfECCBytes-LoraRadioMessagePunchDoubleReDCoSRS.NoOfCRCBytes] + \
            bytearray(LoraRadioMessagePunchReDCoSRS.NoOfECCBytes) + bytearray(LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes)
        loraPMsg1 = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(firstMsgByteArray)
        loraPMsg2 = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(secondMsgByteArray)
        return loraPMsg1, loraPMsg2

    def _GetPunchReDCoSTupleFromPunchDoubleSubSecond(self, loraDoubleMsg: LoraRadioMessagePunchDoubleSubSecondRS):
        payload = loraDoubleMsg.GetByteArray()
        loraMsgLength = LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunchSubSecond]
        # recreate two sub second message arrays, TSS follows the first half and TSS_2 the second
        firstMsgByteArray = payload[0:loraMsgLength-LoraRadioMessagePunchSubSecondRS.NoOfECCBytes-LoraRadioMessagePunchSubSecondRS.NoOfCRCBytes] + bytearray(LoraRadioMessagePunchSubSecondRS.NoOfECCBytes) + bytearray(LoraRadioMessagePunchSubSecondRS.NoOfCRCBytes)
        firstMsgByteArray[LoraRadioMessageRS.H] = (firstMsgByteArray[LoraRadioMessageRS.H] & ~LoraRadioMessageRS.MessageTypeBitMask) | LoraRadioMessageRS.MessageTypeSIPunchSubSecond
        secondMsgByteArray = bytearray([firstMsgByteArray[LoraRadioMessageRS.H]]) + \
            payload[loraMsgLength - LoraRadioMessagePunchSubSecondRS.NoOfECCBytes - LoraRadioMessagePunchSubSecondRS.NoOfCRCBytes:-LoraRadioMessagePunchDoubleSubSecondRS.NoOfECCBytes-LoraRadioMessagePunchDoubleSubSecondRS.NoOfCRCBytes] + \
            bytearray(LoraRadioMessagePunchSubSecondRS.NoOfECCBytes) + bytearray(LoraRadioMessagePunchSubSecondRS.NoOfCRCBytes)
        loraPMsg1 = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(firstMsgByteArray)
        loraPMsg2 = LoraRadioMessageCreator.GetPunchSubSecondMessageByFullMessageData(secondMsgByteArray)
        return loraPMsg1, loraPMsg2

    def _FindReDCoSPunchDoubleErasures(self, loraDoubleMsg: LoraRadioMessagePunchDoubleReDCoSRS, totalRetryDelaySeconds: float = None) -> bytearray:
        loraPMsg1, loraPMsg2 = self._GetPunchReDCoSTupleFromPunchDouble(loraDoubleMsg)
        erasures1 = self._FindReDCoSPunchErasures(loraPMsg1, totalRetryDelaySeconds)
        erasures2 = self._FindReDCoSPunchErasures(loraPMsg2, totalRetryDelaySeconds)
        for i in range(len(erasures2)):
            # Add the length of the first part of the double message minus the RSCodes minus the header of the second
            loraMsgLength = LoraRadioMessagePunchReDCoSRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunchReDCoS]
            erasures2[i] += loraMsgLength - LoraRadioMessagePunchReDCoSRS.NoOfECCBytes - LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes - 1
        erasures1.extend(erasures2)

        LoraRadioDataHandler.WiRocLogger.verbose(
            "LoraRadioDataHandler::_FindReDCoSPunchDoubleErasures " + str(len(erasures1)) + " erasures found. " + str(erasures1))

        return erasures1

    def _FindReDCoSPunchDoubleSubSecondErasures(self, loraDoubleMsg: LoraRadioMessagePunchDoubleSubSecondRS, totalRetryDelaySeconds: float = None) -> bytearray:
        loraPMsg1, loraPMsg2 = self._GetPunchReDCoSTupleFromPunchDoubleSubSecond(loraDoubleMsg)
        erasures1 = self._FindReDCoSPunchSubSecondErasures(loraPMsg1, totalRetryDelaySeconds)
        erasures2 = self._FindReDCoSPunchSubSecondErasures(loraPMsg2, totalRetryDelaySeconds)
        for i in range(len(erasures2)):
            # Add the length of the first part of the double message minus the RSCodes minus the header of the second
            loraMsgLength = LoraRadioMessagePunchSubSecondRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunchSubSecond]
            erasures2[i] += loraMsgLength - LoraRadioMessagePunchSubSecondRS.NoOfECCBytes - LoraRadioMessagePunchSubSecondRS.NoOfCRCBytes - 1
        erasures1.extend(erasures2)

        LoraRadioDataHandler.WiRocLogger.verbose(
            "LoraRadioDataHandler::_FindReDCoSPunchDoubleSubSecondErasures " + str(len(erasures1)) + " erasures found. " + str(erasures1))

        return erasures1

    def _CheckAndRemoveLoraModuleRXError(self) -> None:
        if len(self.DataReceived) >= 10:
            if self.DataReceived[0:10] == bytearray('rx error\r\n'.encode('latin-1')):
                LoraRadioDataHandler.WiRocLogger.debug(
                    "LoraRadioDataHandler::CheckAndRemoveLoraModuleRXError 'rx error' returned by module")
                self.RxError = True
                self.DataReceived = self.DataReceived[10:]

    def _GetSingleMessageWithErasures(self, messageDataToConsider: bytearray, rssiValue: int, snrValue: int, statusValue: int, erasures: bytearray = None, totalRetryDelaySeconds: float = None, lastSingleMessage: LoraRadioMessageReDCoSRS | None = None, lastSingleMessageTime: float | None = None) -> LoraRadioMessageReDCoSRS | None:
        """Shared: single punch and single subsecond decode with erasures."""
        loraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(messageDataToConsider,
                                                                           rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
        msgCls = loraMsg.__class__
        #print("erasures received: " + str(erasures))
        erasuresToUse = erasures + self._FindSingleMessageErasures(loraMsg, lastSingleMessage, lastSingleMessageTime, totalRetryDelaySeconds)
        # No point in having more erasures than ECCBytes, and no point in having odd number of erasures
        # when number of ECC bytes is even
        erasuresToUse = list(set(erasuresToUse))
        #print("erasures: " + str(erasuresToUse))
        if len(erasuresToUse) > 1:
            try:

                if len(erasuresToUse) >= msgCls.NoOfECCBytes:
                    erasuresToUse = erasuresToUse[0:msgCls.NoOfECCBytes]
                elif len(erasuresToUse) % 2 != 0:
                    # Odd number
                    numberOfErasuresToUse = len(erasuresToUse) - 1
                    erasuresToUse = erasuresToUse[0:numberOfErasuresToUse]

                LoraRadioDataHandler.WiRocLogger.debug(
                    "LoraRadioDataHandler::_GetSingleMessageWithErasures() ErasuresToUse: " + str(erasuresToUse))
                messageDataToConsiderWithoutCRC = messageDataToConsider[:-msgCls.NoOfCRCBytes]
                correctedData2 = RSCoderLora.decode(messageDataToConsiderWithoutCRC, bytearray(erasuresToUse))
                if not RSCoderLora.check(correctedData2):
                    # for some reason sometimes decode just returns the corrupted message with no change
                    # and no exception thrown. So check the decoded message to make sure we don't return
                    # a message that is clearly wrong
                    return None

                shake = hashlib.shake_128()
                shake.update(correctedData2[1:])
                theCRCHash = shake.digest(2)
                if (theCRCHash[0] == messageDataToConsider[msgCls.CRC0] or
                        theCRCHash[1] == messageDataToConsider[msgCls.CRC1]):
                    correctedData2.extend(messageDataToConsider[-msgCls.NoOfCRCBytes:])
                    loraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(correctedData2, rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
                    return loraMsg
                else:
                    return None
            except Exception as err2:
                LoraRadioDataHandler.WiRocLogger.error(
                    "LoraRadioDataHandler::_GetSingleMessageWithErasures() RS decoding failed also with erasures with exception: " + str(err2))
                return None
        else:
            LoraRadioDataHandler.WiRocLogger.error("LoraRadioDataHandler::_GetSingleMessageWithErasures() No erasures found so could not decode")
            return None

    def _GetSingleMessageUsingReDCoS(self, messageDataToConsider: bytearray, rssiValue: int) -> LoraRadioMessageReDCoSRS | None:
        """Shared: single punch and single subsecond ReDCoS decode (multiprocessing)."""
        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()
        loraMsgWithErrors = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(messageDataToConsider, rssiValue)
        msgCls = loraMsgWithErrors.__class__
        if loraMsgWithErrors.__class__ is LoraRadioMessagePunchSubSecondRS:
            alts, fixedValues, fixedErasures = self._GetPunchSubSecondMessageAlternatives(loraMsgWithErrors, totalRetryDelaySeconds)
        else:
            alts, fixedValues, fixedErasures = self._GetPunchMessageAlternatives(loraMsgWithErrors, totalRetryDelaySeconds)
        lengthOfDataThatRSCalculatedOverWithoutRSCode = len(
            loraMsgWithErrors.GetPayloadByteArray() + loraMsgWithErrors.GetHeaderData()) - len(fixedValues) - len(fixedErasures)

        erasuresCombinationIterator = self._GetReDCoSErasureCombinations(loraMsgWithErrors, fixedValues, fixedErasures, 0)
        erasuresCombinationList = list(erasuresCombinationIterator)
        LoraRadioDataHandler.WiRocLogger.verbose("LoraRadioDataHandler::_GetSingleMessageUsingReDCoS() No of erasure in each combination: " + str(loraMsgWithErrors.NoOfECCBytes))
        LoraRadioDataHandler.WiRocLogger.verbose("LoraRadioDataHandler::_GetSingleMessageUsingReDCoS() No of total combinations: " + str(len(erasuresCombinationList) * len(alts)))
        noOfHalfMatchesRequired =lengthOfDataThatRSCalculatedOverWithoutRSCode + 1
        LoraRadioDataHandler.WiRocLogger.verbose("LoraRadioDataHandler::_GetSingleMessageUsingReDCoS() No of half matches required: " + str(noOfHalfMatchesRequired))


        for startMessageDataComboToTry in alts:
            LoraRadioDataHandler.WiRocLogger.verbose("alternative: " + str(Utils.GetDataInHex(startMessageDataComboToTry, logging.DEBUG)))
            corruptedData = startMessageDataComboToTry[0:-msgCls.NoOfCRCBytes]
            tasks = [(corruptedData, combo) for combo in erasuresCombinationList]
            crcDictionary = {}
            LoraRadioDataHandler.WiRocLogger.verbose("Erasure combination list: " + str([b.hex() for b in erasuresCombinationList]))
            res = _get_decode_pool().map(_decode_single_redcos, tasks)
            for decoded in res:
                if decoded is None:
                    continue
                LoraRadioDataHandler.WiRocLogger.verbose("Decoded msg: " + Utils.GetDataInHex(decoded, logging.DEBUG))
                shake = hashlib.shake_128()
                shake.update(decoded[1:])
                theCRCHash = shake.digest(2)
                if theCRCHash in crcDictionary:
                    crcDictionary[theCRCHash] += 1
                else:
                    crcDictionary[theCRCHash] = 1
                if theCRCHash == loraMsgWithErrors.GetByteArray()[-msgCls.NoOfCRCBytes:]:
                    LoraRadioDataHandler.WiRocLogger.info("LoraRadioDataHandler::_GetSingleMessageUsingReDCoS() CRC matches, return message")
                    return LoraRadioMessageCreator.GetPunchMessageByFullMessageData(decoded + theCRCHash)
                else:
                    if crcDictionary[theCRCHash] == lengthOfDataThatRSCalculatedOverWithoutRSCode+1:
                        # We found many messages that after decoding has same CRC. If one of the two
                        # CRC bytes matches then we assume we found a correctly decoded message.
                        if theCRCHash[0] == startMessageDataComboToTry[msgCls.CRC0] or \
                                theCRCHash[1] == startMessageDataComboToTry[msgCls.CRC1]:
                            LoraRadioDataHandler.WiRocLogger.info("LoraRadioDataHandler::_GetSingleMessageUsingReDCoS() Found a CRC half match, return message")
                            return LoraRadioMessageCreator.GetPunchMessageByFullMessageData(decoded + theCRCHash)

        LoraRadioDataHandler.WiRocLogger.info("LoraRadioDataHandler::_GetSingleMessageUsingReDCoS() Could not decode with ReDCoS")
        return None

    def _GetNoOfCombinations(self, n, k):
        """
        A fast way to calculate binomial coefficients by Andrew Dalke (contrib).
        """
        if 0 <= k <= n:
            ntok = 1
            ktok = 1
            for t in range(1, min(k, n - k) + 1):
                ntok *= n
                ktok *= t
                n -= 1
            return ntok // ktok
        else:
            return 0

    def _GetNoOfHalfMatchesRequired(self, lengthOfDataErasureCombinationsAreCalculatedOver: int, noOfECCBytes: int, noOfFixedErasures: int, noOfErasuresToDecreaseWith: int) -> int:
        if noOfErasuresToDecreaseWith == 0:
            # should only be called when we decrease the no of erasures in the combinations
            raise Exception("This functions should not be called with noOfErasuresToDecreaseWith = 0")

        noOfErasuresInACombination = noOfECCBytes - noOfFixedErasures - noOfErasuresToDecreaseWith  # Remove two erasures to decrease the number of combinations. The two left over ECC bytes can correct one error that is not pointed out by the erasure combination
        noOfBytesAssumedCorrect = lengthOfDataErasureCombinationsAreCalculatedOver - noOfErasuresInACombination - (noOfErasuresToDecreaseWith // 2)
        noOfBytesAssumedIncorrect = lengthOfDataErasureCombinationsAreCalculatedOver - noOfBytesAssumedCorrect

        noOfHalfMatchesRequired = self._GetNoOfCombinations(noOfBytesAssumedIncorrect, noOfErasuresInACombination)
        return noOfHalfMatchesRequired

    def _GetDoubleMessageUsingReDCoS(self, messageDataToConsider: bytearray, rssiValue: int) -> LoraRadioMessageReDCoSRS | None:
        """Shared: punch double and punch subsecond double ReDCoS decode (multiprocessing)."""
        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()
        loraMsgWithErrors = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(messageDataToConsider, rssiValue)
        msgCls = loraMsgWithErrors.__class__
        if loraMsgWithErrors.__class__ is LoraRadioMessagePunchDoubleSubSecondRS:
            alts, fixedValues, fixedErasures = self._GetPunchDoubleSubSecondMessageAlternatives(loraMsgWithErrors, totalRetryDelaySeconds)
        else:
            alts, fixedValues, fixedErasures = self._GetPunchDoubleMessageAlternatives(loraMsgWithErrors, totalRetryDelaySeconds)
        lengthOfDataThatRSCalculatedOverWithoutRSCode = len(
            loraMsgWithErrors.GetPayloadByteArray() + loraMsgWithErrors.GetHeaderData()) - len(fixedValues) - len(fixedErasures)
        noOfHalfMatchesRequired = lengthOfDataThatRSCalculatedOverWithoutRSCode + 1

        receivedCRC = loraMsgWithErrors.GetByteArray()[-msgCls.NoOfCRCBytes:]
        erasuresCombinationIterator = self._GetReDCoSErasureCombinations(loraMsgWithErrors, fixedValues, fixedErasures, 0)
        erasuresCombinationList = list(erasuresCombinationIterator)
        # When we end up with too many combinations to test we will reduce the erasure combination length by 2
        # And then calculate how many combinations that makes. Reducing by two means two ECC bytes are free to correct a
        # single error byte with unknown position. For the case where the CRC is half corrupted we need to calculate
        # a new number of how many combinations giving the same CRC that we need to consider it to be a possible correct
        # CRC. This is done by calculating the number of combinations that should give correct CRC when the number of
        # errors is one less than the number of errors that should be decodable
        if len(erasuresCombinationList) * len(alts) > SettingsClass.GetReDCoSCombinationThreshold():
            nOfErasuresToDecreaseWith = 2
            erasuresCombinationIterator = self._GetReDCoSErasureCombinations(loraMsgWithErrors, fixedValues, fixedErasures, nOfErasuresToDecreaseWith)
            erasuresCombinationList = list(erasuresCombinationIterator)

            if len(erasuresCombinationList) * len(alts) > SettingsClass.GetReDCoSCombinationThreshold():
                nOfErasuresToDecreaseWith = 4
                erasuresCombinationIterator = self._GetReDCoSErasureCombinations(loraMsgWithErrors, fixedValues, fixedErasures, nOfErasuresToDecreaseWith)
                erasuresCombinationList = list(erasuresCombinationIterator)

                if len(erasuresCombinationList) * len(alts) > SettingsClass.GetReDCoSCombinationThreshold():
                    nOfErasuresToDecreaseWith = 6
                    erasuresCombinationIterator = self._GetReDCoSErasureCombinations(loraMsgWithErrors, fixedValues, fixedErasures, nOfErasuresToDecreaseWith)
                    erasuresCombinationList = list(erasuresCombinationIterator)

                    if len(erasuresCombinationList) * len(alts) > SettingsClass.GetReDCoSCombinationThreshold():
                        return None
                    else:
                        lengthOfDataErasureCombinationsAreCalculatedOver = len(loraMsgWithErrors.GetByteArray()) - loraMsgWithErrors.NoOfCRCBytes - len(fixedValues) - len(fixedErasures)
                        noOfHalfMatchesRequired = self._GetNoOfHalfMatchesRequired(lengthOfDataErasureCombinationsAreCalculatedOver, loraMsgWithErrors.NoOfECCBytes,len(fixedErasures), nOfErasuresToDecreaseWith)
                        LoraRadioDataHandler.WiRocLogger.debug("LoraRadioDataHandler::_GetDoubleMessageUsingReDCoS() No of erasure in each combination reduced by six to: " + str(loraMsgWithErrors.NoOfECCBytes - nOfErasuresToDecreaseWith))
                else:
                    lengthOfDataErasureCombinationsAreCalculatedOver = len(loraMsgWithErrors.GetByteArray()) - loraMsgWithErrors.NoOfCRCBytes - len(fixedValues) - len(fixedErasures)
                    noOfHalfMatchesRequired = self._GetNoOfHalfMatchesRequired(lengthOfDataErasureCombinationsAreCalculatedOver, loraMsgWithErrors.NoOfECCBytes,len(fixedErasures), nOfErasuresToDecreaseWith)
                    LoraRadioDataHandler.WiRocLogger.debug("LoraRadioDataHandler::_GetDoubleMessageUsingReDCoS() No of erasure in each combination reduced by four to: " + str(loraMsgWithErrors.NoOfECCBytes - nOfErasuresToDecreaseWith))
            else:
                lengthOfDataErasureCombinationsAreCalculatedOver = len(loraMsgWithErrors.GetByteArray()) - loraMsgWithErrors.NoOfCRCBytes - len(fixedValues) - len(fixedErasures)
                noOfHalfMatchesRequired = self._GetNoOfHalfMatchesRequired(lengthOfDataErasureCombinationsAreCalculatedOver, loraMsgWithErrors.NoOfECCBytes,len(fixedErasures), nOfErasuresToDecreaseWith)
                LoraRadioDataHandler.WiRocLogger.debug("LoraRadioDataHandler::_GetDoubleMessageUsingReDCoS() No of erasure in each combination reduced by two to: " + str(loraMsgWithErrors.NoOfECCBytes - nOfErasuresToDecreaseWith))

        LoraRadioDataHandler.WiRocLogger.debug("LoraRadioDataHandler::_GetDoubleMessageUsingReDCoS() No of total combinations: " + str(len(erasuresCombinationList) * len(alts)))
        LoraRadioDataHandler.WiRocLogger.debug("LoraRadioDataHandler::_GetDoubleMessageUsingReDCoS() No of half matches required: " + str(noOfHalfMatchesRequired))

        global createDecodeDouble

        for startMessageDataComboToTry in alts:
            LoraRadioDataHandler.WiRocLogger.debug("ALternative message: " + Utils.GetDataInHex(startMessageDataComboToTry, logging.DEBUG))
            corruptedData = startMessageDataComboToTry[0:-msgCls.NoOfCRCBytes]
            tasks = [(corruptedData, combo) for combo in erasuresCombinationList]
            crcDictionary = {}
            res = _get_decode_pool().map(_decode_double_redcos, tasks)

            for decoded in res:
                if decoded is None:
                    continue

                shake = hashlib.shake_128()
                shake.update(decoded[1:])
                theCRCHash = shake.digest(2)
                if theCRCHash in crcDictionary:
                    crcDictionary[theCRCHash] += 1
                else:
                    crcDictionary[theCRCHash] = 1
                if theCRCHash == receivedCRC:
                    LoraRadioDataHandler.WiRocLogger.info("LoraRadioDataHandler::_GetDoubleMessageUsingReDCoS() CRC matches, return message")
                    return LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(decoded + theCRCHash)
                else:
                    if crcDictionary[theCRCHash] == noOfHalfMatchesRequired:
                        # We found many messages that after decoding has same CRC. If one of the two
                        # CRC bytes matches then we assume we found a correctly decoded message.
                        if theCRCHash[0] == receivedCRC[0] or theCRCHash[1] == receivedCRC[1]:
                            LoraRadioDataHandler.WiRocLogger.info("LoraRadioDataHandler::_GetDoubleMessageUsingReDCoS() Found a CRC half match, return message")
                            return LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(decoded + theCRCHash)

        LoraRadioDataHandler.WiRocLogger.info("LoraRadioDataHandler::_GetDoubleMessageUsingReDCoS() Could not decode using ReDCoS")
        return None

    def _GetPunchSubSecondMessage(self) -> LoraRadioMessagePunchSubSecondRS | None:
        """Decode a sub second punch message (type 0x0B)."""
        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()
        expectedMessageLength = LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunchSubSecond]
        if len(self.DataReceived) < expectedMessageLength + self.rssiByteCount + self.SNRByteCount + self.StatusByteCount:
            return None

        messageDataToConsider = LoraRadioMessagePunchSubSecondRS.DeInterleaveFromAirOrder(self.DataReceived[0:expectedMessageLength])
        LoraRadioDataHandler.WiRocLogger.debug(
            "LoraRadioDataHandler::_GetPunchSubSecondMessage() Deinterleaved message to consider: " + Utils.GetDataInHex(messageDataToConsider, logging.DEBUG))
        messageDataToConsider[LoraRadioMessageRS.H] = (messageDataToConsider[LoraRadioMessageRS.H] & ~LoraRadioMessageRS.MessageTypeBitMask) | LoraRadioMessageRS.MessageTypeSIPunchSubSecond
        rssiValue = None
        if self.rssiByteCount > 0:
            if self.rssiByteCount == 2:
                # RAK3172 sends two byte signed (negative number dbm)
                rssiValue = int.from_bytes(self.DataReceived[expectedMessageLength:expectedMessageLength+self.rssiByteCount], byteorder='big', signed=True)
            else:
                # DRF1268DS sends one byte, a positive number.
                rssiValue = int.from_bytes(self.DataReceived[expectedMessageLength:expectedMessageLength+self.rssiByteCount], byteorder='big', signed=False)
        snrValue = None
        if self.SNRByteCount > 0:
            snrValue = int.from_bytes(self.DataReceived[expectedMessageLength + self.rssiByteCount:expectedMessageLength + self.rssiByteCount + self.SNRByteCount], byteorder='big', signed=True)
        statusValue = None
        if self.StatusByteCount > 0:
            statusValue = int.from_bytes(
                self.DataReceived[expectedMessageLength + self.rssiByteCount + self.SNRByteCount:expectedMessageLength + self.rssiByteCount + self.SNRByteCount + self.StatusByteCount], byteorder='big')

        messageDataToConsiderMinusCRC = messageDataToConsider[:-LoraRadioMessagePunchSubSecondRS.NoOfCRCBytes]
        if RSCoderLora.check(messageDataToConsiderMinusCRC):
            # everything checks out, message should be correct
            loraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(messageDataToConsider, rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
            return loraMsg
        else:
            correctedData = None
            try:
                correctedData = RSCoderLora.decode(messageDataToConsiderMinusCRC)
            except Exception as err:
                LoraRadioDataHandler.WiRocLogger.error("LoraRadioDataHandler::_GetPunchSubSecondMessage() RS decoding failed with exception: " + str(err))

            if correctedData is not None and RSCoderLora.check(correctedData):
                LoraRadioDataHandler.WiRocLogger.info("LoraRadioDataHandler::_GetPunchSubSecondMessage() Decoded, corrected data correctly it seems")
                correctedData.extend(messageDataToConsider[-LoraRadioMessagePunchSubSecondRS.NoOfCRCBytes:])
                loraPunchMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(correctedData, rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
                return loraPunchMsg
            else:
                loraMsgWithErrors = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(messageDataToConsider, rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
                alts, fixedValues, fixedErasures = self._GetPunchSubSecondMessageAlternatives(loraMsgWithErrors, totalRetryDelaySeconds)
                LoraRadioDataHandler.WiRocLogger.debug("alternatives: " + str(alts))
                for messageAlt in alts:
                    LoraRadioDataHandler.WiRocLogger.debug(
                        "LoraRadioDataHandler::_GetPunchSubSecondMessage() alternatives: " + Utils.GetDataInHex(messageAlt, logging.DEBUG) + " fixedValues: " + str(fixedValues) + " fixedErasures: " + str(fixedErasures))

                for messageAlt in alts:
                    LoraRadioDataHandler.WiRocLogger.debug("messageAlt: " + str(messageAlt))
                    try:
                        correctedData = RSCoderLora.decode(bytearray(messageAlt[:-LoraRadioMessagePunchSubSecondRS.NoOfCRCBytes]))
                    except Exception as err:
                        LoraRadioDataHandler.WiRocLogger.debug("LoraRadioDataHandler::_GetPunchSubSecondMessage() 2 RS decoding of messageAlt: " + str(
                                messageAlt) + " failed with exception: " + str(err))
                    if correctedData is not None and RSCoderLora.check(correctedData):
                        loraPunchMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
                            correctedData + messageDataToConsider[-LoraRadioMessagePunchSubSecondRS.NoOfCRCBytes:], rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
                        return loraPunchMsg
                    else:
                        loraPunchMsg3 = self._GetSingleMessageWithErasures(bytearray(messageAlt), rssiValue, snrValue, statusValue, erasures=fixedErasures, totalRetryDelaySeconds=totalRetryDelaySeconds,
                                                                          lastSingleMessage=self.LastPunchSubSecondMessage, lastSingleMessageTime=self.LastPunchSubSecondMessageTime)
                        if loraPunchMsg3 is not None:
                            LoraRadioDataHandler.WiRocLogger.info("LoraRadioDataHandler::_GetPunchSubSecondMessage() DECODED one of the message alternatives decoded with erasures")
                            return loraPunchMsg3

                # The alternatives could not be decoded without ReDCoS so try using ReDCos to decode the message
                loraPunchMsg2 = self._GetSingleMessageUsingReDCoS(messageDataToConsider, rssiValue)
                if loraPunchMsg2 is None:
                    loraMsgWithErrors = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(messageDataToConsider, rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
                    if self.LastPunchSubSecondMessage is not None and self._IsSameSingleMessage(self.LastPunchSubSecondMessage, loraMsgWithErrors):
                        LoraRadioDataHandler.WiRocLogger.info("LoraRadioDataHandler::_GetPunchSubSecondMessage() Same message as last received, use last received instead")
                        return self.LastPunchSubSecondMessage
                    else:
                        return None
                else:
                    return loraPunchMsg2

    def _GetPunchDoubleSubSecondMessage(self) -> LoraRadioMessagePunchDoubleSubSecondRS | None:
        """Decode a double sub second punch message (type 0x0C)."""
        expectedMessageLength = LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunchDoubleSubSecond]
        if len(self.DataReceived) < expectedMessageLength + self.rssiByteCount + self.SNRByteCount + self.StatusByteCount:
            return None
        erasures = []
        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()

        messageDataToConsider = LoraRadioMessagePunchDoubleSubSecondRS.DeInterleaveFromAirOrder(self.DataReceived[0:expectedMessageLength])
        LoraRadioDataHandler.WiRocLogger.debug(
            "LoraRadioDataHandler::_GetPunchDoubleSubSecondMessage() Deinterleaved message to consider: " + Utils.GetDataInHex(messageDataToConsider, logging.DEBUG))
        messageDataToConsider[LoraRadioMessageRS.H] = (messageDataToConsider[LoraRadioMessageRS.H] & ~LoraRadioMessageRS.MessageTypeBitMask) | LoraRadioMessageRS.MessageTypeSIPunchDoubleSubSecond
        rssiValue = None
        if self.rssiByteCount > 0:
            if self.rssiByteCount == 2:
                # RAK3172 sends two byte signed (negative number dbm)
                rssiValue = int.from_bytes(self.DataReceived[expectedMessageLength:expectedMessageLength+self.rssiByteCount], byteorder='big', signed=True)
            else:
                # DRF1268DS sends one byte, a positive number.
                rssiValue = int.from_bytes(self.DataReceived[expectedMessageLength:expectedMessageLength+self.rssiByteCount], byteorder='big', signed=False)
        snrValue = None
        if self.SNRByteCount > 0:
            snrValue = int.from_bytes(
                self.DataReceived[expectedMessageLength + self.rssiByteCount:expectedMessageLength + self.rssiByteCount + self.SNRByteCount], byteorder='big', signed=True)
        statusValue = None
        if self.StatusByteCount > 0:
            statusValue = int.from_bytes(
                self.DataReceived[expectedMessageLength + self.rssiByteCount + self.SNRByteCount:expectedMessageLength + self.rssiByteCount + self.SNRByteCount + self.StatusByteCount], byteorder='big')

        messageDataToConsiderWithoutCRC = messageDataToConsider[:-LoraRadioMessagePunchDoubleSubSecondRS.NoOfCRCBytes]

        if RSCoderLora.checkLong(messageDataToConsiderWithoutCRC):
            # everything checks out, message should be correct
            loraDoubleMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(messageDataToConsider,
                                                                           rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
            return loraDoubleMsg
        else:
            try:
                correctedData = None
                try:
                    correctedData = RSCoderLora.decodeLong(messageDataToConsiderWithoutCRC)
                except Exception as err:
                    LoraRadioDataHandler.WiRocLogger.error("LoraRadioDataHandler::_GetPunchDoubleSubSecondMessage() RS decoding failed with exception: " + str(err))
                if correctedData is not None and RSCoderLora.checkLong(correctedData):
                    LoraRadioDataHandler.WiRocLogger.info("LoraRadioDataHandler::_GetPunchDoubleSubSecondMessage() Decoded, corrected data correctly it seems")
                    loraPunchMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(correctedData + messageDataToConsider[-LoraRadioMessagePunchDoubleSubSecondRS.NoOfCRCBytes:],
                                                                                                        rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
                    return loraPunchMsg
                else:
                    LoraRadioDataHandler.WiRocLogger.info("LoraRadioDataHandler::_GetPunchDoubleSubSecondMessage() Could not decode correctly, try with erasures next")
                    tmpLoraMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(messageDataToConsider, rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
                    erasures.extend(self._FindReDCoSPunchDoubleSubSecondErasures(tmpLoraMsg, totalRetryDelaySeconds))
                    loraPunchMsg = _get_double_message_with_erasures(messageDataToConsider, rssiValue, snrValue, statusValue, erasures=erasures)
                    if loraPunchMsg is None:
                        loraMsgWithErrors = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(messageDataToConsider, rssiValue)
                        alts, fixedValues, fixedErasures = self._GetPunchDoubleSubSecondMessageAlternatives(loraMsgWithErrors, totalRetryDelaySeconds)
                        for messageAlt in alts:
                            LoraRadioDataHandler.WiRocLogger.debug(
                                "LoraRadioDataHandler::_GetPunchDoubleSubSecondMessage() alternatives: " + Utils.GetDataInHex(messageAlt, logging.DEBUG) + " fixedValues: " + str(fixedValues) + " fixedErasures: " + str(fixedErasures))

                        # Pre-compute erasures for each alt (done to easily be run in own processes, but that doesn't speed it up)
                        tasks = []
                        for messageAlt in alts:
                            tmpLoraMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(
                                bytearray(messageAlt), rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
                            altErasures = list(fixedErasures) + list(self._FindReDCoSPunchDoubleSubSecondErasures(tmpLoraMsg, totalRetryDelaySeconds))
                            tasks.append((bytearray(messageAlt), rssiValue, snrValue, statusValue, altErasures))

                        for task in tasks:
                            _, loraPunchMsg = _try_decode_double_alt(task)
                            if loraPunchMsg is not None:
                                LoraRadioDataHandler.WiRocLogger.info(
                                    "LoraRadioDataHandler::_GetPunchDoubleSubSecondMessage() DECODED one of the message alternatives decoded")
                                return loraPunchMsg

                        # The alternatives could not be decoded without ReDCoS so try using ReDCos to decode the message
                        loraPunchMsg2 = self._GetDoubleMessageUsingReDCoS(messageDataToConsider, rssiValue)

                        if loraPunchMsg2 is None:
                            loraDoubleMsgWithErrors = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(messageDataToConsider, rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
                            if self.LastPunchDoubleSubSecondMessage is not None and self._IsSameDoubleMessage(self.LastPunchDoubleSubSecondMessage, loraDoubleMsgWithErrors):
                                LoraRadioDataHandler.WiRocLogger.info(
                                    "LoraRadioDataHandler::_GetPunchDoubleSubSecondMessage() DECODED Same message as last received, use last received instead")
                                return self.LastPunchDoubleSubSecondMessage
                        else:
                            LoraRadioDataHandler.WiRocLogger.info(
                                "LoraRadioDataHandler::_GetPunchDoubleSubSecondMessage() DECODED with ReDCoS")
                            return loraPunchMsg2
                    else:
                        LoraRadioDataHandler.WiRocLogger.info(
                            "LoraRadioDataHandler::_GetPunchDoubleSubSecondMessage() DECODED decoded with erasures")
                        return loraPunchMsg
            except Exception as err:
                LoraRadioDataHandler.WiRocLogger.error(
                    "LoraRadioDataHandler::_GetPunchDoubleSubSecondMessage() RS decoding failed with exception: " + str(err))
                tmpLoraMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(messageDataToConsider, rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
                erasures.extend(self._FindReDCoSPunchDoubleSubSecondErasures(tmpLoraMsg, totalRetryDelaySeconds))
                loraPunchMsg = _get_double_message_with_erasures(messageDataToConsider, rssiValue, snrValue, statusValue, erasures=erasures)
                return loraPunchMsg

    def _GetPunchReDCoSMessage(self) -> LoraRadioMessagePunchReDCoSRS | None:
        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()
        expectedMessageLength = LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunchReDCoS]
        if len(self.DataReceived) < expectedMessageLength + self.rssiByteCount + self.SNRByteCount + self.StatusByteCount:
            return None

        messageDataToConsider = LoraRadioMessagePunchReDCoSRS.DeInterleaveFromAirOrder(self.DataReceived[0:expectedMessageLength])
        LoraRadioDataHandler.WiRocLogger.debug(
            "LoraRadioDataHandler::_GetPunchReDCoSMessage() Deinterleaved message to consider: " + Utils.GetDataInHex(messageDataToConsider, logging.DEBUG))
        messageDataToConsider[LoraRadioMessageRS.H] = (messageDataToConsider[LoraRadioMessageRS.H] & ~LoraRadioMessageRS.MessageTypeBitMask) | LoraRadioMessageRS.MessageTypeSIPunchReDCoS
        rssiValue = None
        if self.rssiByteCount > 0:
            if self.rssiByteCount == 2:
                # RAK3172 sends two byte signed (negative number dbm)
                rssiValue = int.from_bytes(self.DataReceived[expectedMessageLength:expectedMessageLength+self.rssiByteCount], byteorder='big', signed=True)
            else:
                # DRF1268DS sends one byte, a positive number.
                rssiValue = int.from_bytes(self.DataReceived[expectedMessageLength:expectedMessageLength+self.rssiByteCount], byteorder='big', signed=False)
        snrValue = None
        if self.SNRByteCount > 0:
            snrValue = int.from_bytes(self.DataReceived[expectedMessageLength + self.rssiByteCount:expectedMessageLength + self.rssiByteCount + self.SNRByteCount], byteorder='big', signed=True)
        statusValue = None
        if self.StatusByteCount > 0:
            statusValue = int.from_bytes(
                self.DataReceived[expectedMessageLength + self.rssiByteCount + self.SNRByteCount:expectedMessageLength + self.rssiByteCount + self.SNRByteCount + self.StatusByteCount], byteorder='big')

        messageDataToConsiderMinusCRC = messageDataToConsider[:-LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes]
        if RSCoderLora.check(messageDataToConsiderMinusCRC):
            # everything checks out, message should be correct
            loraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(messageDataToConsider, rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
            return loraMsg
        else:
            correctedData = None
            try:
                correctedData = RSCoderLora.decode(messageDataToConsiderMinusCRC)
            except Exception as err:
                LoraRadioDataHandler.WiRocLogger.error("LoraRadioDataHandler::_GetPunchReDCoSMessage() RS decoding failed with exception: " + str(err))

            if correctedData is not None and RSCoderLora.check(correctedData):
                LoraRadioDataHandler.WiRocLogger.info("LoraRadioDataHandler::_GetPunchReDCoSMessage() Decoded, corrected data correctly it seems")
                correctedData.extend(messageDataToConsider[-LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes:])
                loraPunchMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(correctedData, rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
                return loraPunchMsg
            else:
                loraMsgWithErrors = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(messageDataToConsider, rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
                alts, fixedValues, fixedErasures = self._GetPunchMessageAlternatives(loraMsgWithErrors, totalRetryDelaySeconds)
                LoraRadioDataHandler.WiRocLogger.debug("alternatives: " + str(alts))
                for messageAlt in alts:
                    LoraRadioDataHandler.WiRocLogger.debug(
                        "LoraRadioDataHandler::_GetPunchReDCoSMessage() alternatives: " + Utils.GetDataInHex(messageAlt, logging.DEBUG) + " fixedValues: " + str(fixedValues) + " fixedErasures: " + str(fixedErasures))

                for messageAlt in alts:
                    LoraRadioDataHandler.WiRocLogger.debug("messageAlt: " + str(messageAlt))
                    try:
                        correctedData = RSCoderLora.decode(bytearray(messageAlt[:-LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes]))
                    except Exception as err:
                        LoraRadioDataHandler.WiRocLogger.debug("LoraRadioDataHandler::_GetPunchReDCoSMessage() 2 RS decoding of messageAlt: " + str(
                                messageAlt) + " failed with exception: " + str(err))
                    #print(correctedData)
                    if correctedData is not None and RSCoderLora.check(correctedData):
                        loraPunchMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(
                            correctedData + messageDataToConsider[-LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes:], rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
                        #print("Corrected message: " + Utils.GetDataInHex(loraPunchMsg.GetByteArray(), logging.DEBUG))
                        return loraPunchMsg
                    else:
                        loraPunchMsg3 = self._GetSingleMessageWithErasures(bytearray(messageAlt), rssiValue, snrValue, statusValue, erasures=fixedErasures, totalRetryDelaySeconds=totalRetryDelaySeconds,
                                                                          lastSingleMessage=self.LastPunchMessage, lastSingleMessageTime=self.LastPunchMessageTime)
                        if loraPunchMsg3 is not None:
                            LoraRadioDataHandler.WiRocLogger.info("LoraRadioDataHandler::_GetPunchReDCoSMessage() DECODED one of the message alternatives decoded with erasures")
                            return loraPunchMsg3

                # The alternatives could not be decoded without ReDCoS so try using ReDCos to decode the message
                loraPunchMsg2 = self._GetSingleMessageUsingReDCoS(messageDataToConsider, rssiValue)
                if loraPunchMsg2 is None:
                    loraMsgWithErrors = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(messageDataToConsider, rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
                    if self.LastPunchMessage is not None and self._IsSameSingleMessage(self.LastPunchMessage, loraMsgWithErrors):
                        LoraRadioDataHandler.WiRocLogger.info("LoraRadioDataHandler::_GetPunchReDCoSMessage() Same message as last received, use last received instead")
                        #print("Same as last message")
                        return self.LastPunchMessage
                    else:
                        return None
                else:
                    return loraPunchMsg2

    def _GetPunchDoubleReDCoSMessage(self) -> LoraRadioMessagePunchDoubleReDCoSRS | None:
        expectedMessageLength = LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunchDoubleReDCoS]
        if len(self.DataReceived) < expectedMessageLength + self.rssiByteCount + self.SNRByteCount + self.StatusByteCount:
            return None
        erasures = []
        totalRetryDelaySeconds = SettingsClass.GetTotalRetryDelaySeconds()

        messageDataToConsider = LoraRadioMessagePunchDoubleReDCoSRS.DeInterleaveFromAirOrder(self.DataReceived[0:expectedMessageLength])
        LoraRadioDataHandler.WiRocLogger.debug(
            "LoraRadioDataHandler::_GetPunchDoubleReDCoSMessage() Deinterleaved message to consider: " + Utils.GetDataInHex(messageDataToConsider, logging.DEBUG))
        messageDataToConsider[LoraRadioMessageRS.H] = (messageDataToConsider[LoraRadioMessageRS.H] & ~LoraRadioMessageRS.MessageTypeBitMask) | LoraRadioMessageRS.MessageTypeSIPunchDoubleReDCoS
        rssiValue = None
        if self.rssiByteCount > 0:
            if self.rssiByteCount == 2:
                # RAK3172 sends two byte signed (negative number dbm)
                rssiValue = int.from_bytes(self.DataReceived[expectedMessageLength:expectedMessageLength+self.rssiByteCount], byteorder='big', signed=True)
            else:
                # DRF1268DS sends one byte, a positive number.
                rssiValue = int.from_bytes(self.DataReceived[expectedMessageLength:expectedMessageLength+self.rssiByteCount], byteorder='big', signed=False)
        snrValue = None
        if self.SNRByteCount > 0:
            snrValue = int.from_bytes(
                self.DataReceived[expectedMessageLength + self.rssiByteCount:expectedMessageLength + self.rssiByteCount + self.SNRByteCount], byteorder='big', signed=True)
        statusValue = None
        if self.StatusByteCount > 0:
            statusValue = int.from_bytes(
                self.DataReceived[expectedMessageLength + self.rssiByteCount + self.SNRByteCount:expectedMessageLength + self.rssiByteCount + self.SNRByteCount + self.StatusByteCount], byteorder='big')

        messageDataToConsiderWithoutCRC = messageDataToConsider[:-LoraRadioMessagePunchDoubleReDCoSRS.NoOfCRCBytes]

        if RSCoderLora.checkLong(messageDataToConsiderWithoutCRC):
            # everything checks out, message should be correct
            loraDoubleMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(messageDataToConsider,
                                                                           rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
            return loraDoubleMsg
        else:
            try:
                correctedData = None
                try:
                    correctedData = RSCoderLora.decodeLong(messageDataToConsiderWithoutCRC)
                except Exception as err:
                    LoraRadioDataHandler.WiRocLogger.error("LoraRadioDataHandler::_GetPunchDoubleReDCoSMessage() RS decoding failed with exception: " + str(err))
                if correctedData is not None and RSCoderLora.checkLong(correctedData):
                    LoraRadioDataHandler.WiRocLogger.info("LoraRadioDataHandler::_GetPunchDoubleReDCoSMessage() Decoded, corrected data correctly it seems")
                    loraPunchMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(correctedData + messageDataToConsider[-LoraRadioMessagePunchDoubleReDCoSRS.NoOfCRCBytes:],
                                                                                                        rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
                    return loraPunchMsg
                else:
                    LoraRadioDataHandler.WiRocLogger.info("LoraRadioDataHandler::_GetPunchDoubleReDCoSMessage() Could not decode correctly, try with erasures next")
                    tmpLoraMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(messageDataToConsider, rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
                    erasures.extend(self._FindReDCoSPunchDoubleErasures(tmpLoraMsg, totalRetryDelaySeconds))
                    loraPunchMsg = _get_double_message_with_erasures(messageDataToConsider, rssiValue, snrValue, statusValue, erasures=erasures)
                    if loraPunchMsg is None:
                        loraMsgWithErrors = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(messageDataToConsider, rssiValue)
                        alts, fixedValues, fixedErasures = self._GetPunchDoubleMessageAlternatives(loraMsgWithErrors, totalRetryDelaySeconds)
                        for messageAlt in alts:
                            LoraRadioDataHandler.WiRocLogger.debug(
                                "LoraRadioDataHandler::_GetPunchDoubleReDCoSMessage() alternatives: " + Utils.GetDataInHex(messageAlt, logging.DEBUG) + " fixedValues: " + str(fixedValues) + " fixedErasures: " + str(fixedErasures))

                        # Pre-compute erasures for each alt (done to easily be run in own processes, but that doesn't speed it up)
                        tasks = []
                        for messageAlt in alts:
                            tmpLoraMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(
                                bytearray(messageAlt), rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
                            altErasures = list(fixedErasures) + list(self._FindReDCoSPunchDoubleErasures(tmpLoraMsg, totalRetryDelaySeconds))
                            tasks.append((bytearray(messageAlt), rssiValue, snrValue, statusValue, altErasures))

                        for task in tasks:
                            _, loraPunchMsg = _try_decode_double_alt(task)
                            if loraPunchMsg is not None:
                                LoraRadioDataHandler.WiRocLogger.info(
                                    "LoraRadioDataHandler::_GetPunchDoubleReDCoSMessage() DECODED one of the message alternatives decoded")
                                return loraPunchMsg

                        # The alternatives could not be decoded without ReDCoS so try using ReDCos to decode the message
                        loraPunchMsg2 = self._GetDoubleMessageUsingReDCoS(messageDataToConsider, rssiValue)

                        if loraPunchMsg2 is None:
                            loraDoubleMsgWithErrors = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(messageDataToConsider, rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
                            if self.LastPunchDoubleMessage is not None and self._IsSameDoubleMessage(self.LastPunchDoubleMessage, loraDoubleMsgWithErrors):
                                LoraRadioDataHandler.WiRocLogger.info(
                                    "LoraRadioDataHandler::_GetPunchDoubleReDCoSMessage() DECODED Same message as last received, use last received instead")
                                return self.LastPunchDoubleMessage
                        else:
                            LoraRadioDataHandler.WiRocLogger.info(
                                "LoraRadioDataHandler::_GetPunchDoubleReDCoSMessage() DECODED with ReDCoS")
                            return loraPunchMsg2
                    else:
                        LoraRadioDataHandler.WiRocLogger.info(
                            "LoraRadioDataHandler::_GetPunchDoubleReDCoSMessage() DECODED decoded with erasures")
                        return loraPunchMsg
            except Exception as err:
                LoraRadioDataHandler.WiRocLogger.error(
                    "LoraRadioDataHandler::_GetPunchDoubleReDCoSMessage() RS decoding failed with exception: " + str(err))
                tmpLoraMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(messageDataToConsider, rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
                erasures.extend(self._FindReDCoSPunchDoubleErasures(tmpLoraMsg, totalRetryDelaySeconds))
                loraPunchMsg = _get_double_message_with_erasures(messageDataToConsider, rssiValue, snrValue, statusValue, erasures=erasures)
                return loraPunchMsg

    def _GetAckMessage(self):
        messageTypeToTry = LoraRadioMessageRS.MessageTypeLoraAck
        expectedMessageLength = LoraRadioMessageRS.MessageLengths[messageTypeToTry]
        if len(self.DataReceived) < expectedMessageLength + self.rssiByteCount + self.SNRByteCount + self.StatusByteCount:
            return None

        messageDataToConsider = self.DataReceived[0:expectedMessageLength]
        headerByte = (messageDataToConsider[LoraRadioMessageRS.H] & ~LoraRadioMessageRS.MessageTypeBitMask) | messageTypeToTry
        # Clear battery low, it is always 0 in Ack messages
        headerByte = headerByte & 0xBF
        messageDataToConsider[LoraRadioMessageRS.H] = headerByte
        LoraRadioDataHandler.WiRocLogger.debug(
            "LoraRadioDataHandler::_GetAckMessage() MessageDataToConsider: " + Utils.GetDataInHex(messageDataToConsider, logging.DEBUG))
        rssiValue = None
        if self.rssiByteCount > 0:
            if self.rssiByteCount == 2:
                # RAK3172 sends two byte signed (negative number dbm)
                rssiValue = int.from_bytes(self.DataReceived[expectedMessageLength:expectedMessageLength+self.rssiByteCount], byteorder='big', signed=True)
            else:
                # DRF1268DS sends one byte, a positive number.
                rssiValue = int.from_bytes(self.DataReceived[expectedMessageLength:expectedMessageLength+self.rssiByteCount], byteorder='big', signed=False)
        snrValue = None
        if self.SNRByteCount > 0:
            snrValue = int.from_bytes(
                self.DataReceived[expectedMessageLength + self.rssiByteCount:expectedMessageLength + self.rssiByteCount + self.SNRByteCount], byteorder='big', signed=True)
        statusValue = None
        if self.StatusByteCount > 0:
            statusValue = int.from_bytes(
                self.DataReceived[expectedMessageLength + self.rssiByteCount + self.SNRByteCount:expectedMessageLength + self.rssiByteCount + self.SNRByteCount + self.StatusByteCount], byteorder='big')

        if (messageDataToConsider[LoraRadioMessageAckRS.HASH0] == messageDataToConsider[LoraRadioMessageAckRS.HASH0_2] or messageDataToConsider[LoraRadioMessageAckRS.HASH0_2] == messageDataToConsider[LoraRadioMessageAckRS.HASH0_3] or messageDataToConsider[LoraRadioMessageAckRS.HASH0] == messageDataToConsider[LoraRadioMessageAckRS.HASH0_3]) and \
            (messageDataToConsider[LoraRadioMessageAckRS.HASH1] == messageDataToConsider[LoraRadioMessageAckRS.HASH1_2] or messageDataToConsider[LoraRadioMessageAckRS.HASH1_2] == messageDataToConsider[LoraRadioMessageAckRS.HASH1_3] or messageDataToConsider[LoraRadioMessageAckRS.HASH1] == messageDataToConsider[LoraRadioMessageAckRS.HASH1_3]):
            hash0 = messageDataToConsider[LoraRadioMessageAckRS.HASH0] if messageDataToConsider[LoraRadioMessageAckRS.HASH0] == messageDataToConsider[LoraRadioMessageAckRS.HASH0_2] or messageDataToConsider[LoraRadioMessageAckRS.HASH0] == messageDataToConsider[LoraRadioMessageAckRS.HASH0_3] else messageDataToConsider[LoraRadioMessageAckRS.HASH0_2]
            hash1 = messageDataToConsider[LoraRadioMessageAckRS.HASH1] if messageDataToConsider[LoraRadioMessageAckRS.HASH1] == messageDataToConsider[LoraRadioMessageAckRS.HASH1_2] or messageDataToConsider[LoraRadioMessageAckRS.HASH1] == messageDataToConsider[LoraRadioMessageAckRS.HASH1_3] else messageDataToConsider[LoraRadioMessageAckRS.HASH1_2]
            ackMsg = LoraRadioMessageAckRS()
            ackMsg.SetHeader(messageDataToConsider[0:1])
            ackMsg.AddPayload(bytearray([hash0, hash1]))
            ackMsg.AddPayload(bytearray([hash0, hash1]))
            ackMsg.AddPayload(bytearray([hash0, hash1]))
            ackMsg.SetRSSIValue(rssiValue)
            ackMsg.SetSNRValue(snrValue)
            ackMsg.SetStatusValue(statusValue)
            LoraRadioDataHandler.WiRocLogger.debug("LoraRadioDataHandler::_GetAckMessage() Ack found, At least two of the three CRC0 are same, and at least two of the three CRC1 are same")
            return ackMsg
        else:
            expectedMessageID = SettingsClass.GetMessageIDOfLastLoraMessageSent()
            if expectedMessageID is None:
                LoraRadioDataHandler.WiRocLogger.error(
                    "LoraRadioDataHandler::_GetAckMessage() No message could be decoded. No expected message ID exists")
                return None
            #print("ExpectedMessageID: " + str(expectedMessageID))
            first4bitDifference1 = (expectedMessageID[0] ^ messageDataToConsider[LoraRadioMessageAckRS.HASH0]) & 0xF0
            first4bitDifference2 = (expectedMessageID[0] ^ messageDataToConsider[LoraRadioMessageAckRS.HASH0_2]) & 0xF0
            first4bitDifference3 = (expectedMessageID[0] ^ messageDataToConsider[LoraRadioMessageAckRS.HASH0_3]) & 0xF0
            #print(bin(first4bitDifference1))
            #print(bin(first4bitDifference2))
            #print(bin(first4bitDifference3))
            second4bitDifference1 = (expectedMessageID[0] ^ messageDataToConsider[LoraRadioMessageAckRS.HASH0]) & 0x0F
            second4bitDifference2 = (expectedMessageID[0] ^ messageDataToConsider[LoraRadioMessageAckRS.HASH0_2]) & 0x0F
            second4bitDifference3 = (expectedMessageID[0] ^ messageDataToConsider[LoraRadioMessageAckRS.HASH0_3]) & 0x0F
            #print(bin(second4bitDifference1))
            #print(bin(second4bitDifference2))
            #print(bin(second4bitDifference3))

            third4bitDifference1 = (expectedMessageID[1] ^ messageDataToConsider[LoraRadioMessageAckRS.HASH1]) & 0xF0
            third4bitDifference2 = (expectedMessageID[1] ^ messageDataToConsider[LoraRadioMessageAckRS.HASH1_2]) & 0xF0
            third4bitDifference3 = (expectedMessageID[1] ^ messageDataToConsider[LoraRadioMessageAckRS.HASH1_3]) & 0xF0
            #print(bin(third4bitDifference1))
            #print(bin(third4bitDifference2))
            #print(bin(third4bitDifference3))

            fourth4bitDifference1 = (expectedMessageID[1] ^ messageDataToConsider[LoraRadioMessageAckRS.HASH1]) & 0x0F
            fourth4bitDifference2 = (expectedMessageID[1] ^ messageDataToConsider[LoraRadioMessageAckRS.HASH1_2]) & 0x0F
            fourth4bitDifference3 = (expectedMessageID[1] ^ messageDataToConsider[LoraRadioMessageAckRS.HASH1_3]) & 0x0F
            #print(bin(fourth4bitDifference1))
            #print(bin(fourth4bitDifference2))
            #print(bin(fourth4bitDifference3))

            first4bitNoOfBitErrorsMin = min(bin(first4bitDifference1).count("1"), bin(first4bitDifference2).count("1"), bin(first4bitDifference3).count("1"))
            #print(first4bitNoOfBitErrorsMin)
            second4bitNoOfBitErrorsMin = min(bin(second4bitDifference1).count("1"), bin(second4bitDifference2).count("1"), bin(second4bitDifference3).count("1"))
            #print(second4bitNoOfBitErrorsMin)
            third4bitNoOfBitErrorsMin = min(bin(third4bitDifference1).count("1"), bin(third4bitDifference2).count("1"), bin(third4bitDifference3).count("1"))
            #print(third4bitNoOfBitErrorsMin)
            fourth4bitNoOfBitErrorsMin = min(bin(fourth4bitDifference1).count("1"), bin(fourth4bitDifference2).count("1"), bin(fourth4bitDifference3).count("1"))
            #print(fourth4bitNoOfBitErrorsMin)

            noOfBitErrors = first4bitNoOfBitErrorsMin + second4bitNoOfBitErrorsMin + third4bitNoOfBitErrorsMin + fourth4bitNoOfBitErrorsMin

            if noOfBitErrors <= 1:
                LoraRadioDataHandler.WiRocLogger.debug("LoraRadioDataHandler::_GetAckMessage() Selecting best 4bit groups resulted in " + str(noOfBitErrors) + " bit errors compared to expected CRC")
                loraAckMessage = LoraRadioMessageAckRS()
                loraAckMessage.SetHeader(messageDataToConsider[0:1])
                loraAckMessage.AddPayload(expectedMessageID)
                loraAckMessage.AddPayload(expectedMessageID)
                loraAckMessage.AddPayload(expectedMessageID)
                loraAckMessage.SetRSSIValue(rssiValue)
                loraAckMessage.SetSNRValue(snrValue)
                loraAckMessage.SetStatusValue(statusValue)
                return loraAckMessage
            else:
                LoraRadioDataHandler.WiRocLogger.error("LoraRadioDataHandler::_GetAckMessage() No message could be decoded. Selecting best 4bit groups resulted in " + str(noOfBitErrors) + " bit errors compared to expected CRC")
                return None

    def _GetStatus2Message(self) -> LoraRadioMessageStatus2RS | None:
        messageTypeToTry = LoraRadioMessageRS.MessageTypeStatus2
        expectedMessageLength = LoraRadioMessageRS.MessageLengths[messageTypeToTry]
        if len(self.DataReceived) < expectedMessageLength + self.rssiByteCount + self.SNRByteCount + self.StatusByteCount:
            return None

        messageDataToConsider = self.DataReceived[0:expectedMessageLength]
        messageDataToConsider[LoraRadioMessageRS.H] = (messageDataToConsider[LoraRadioMessageRS.H] & ~LoraRadioMessageRS.MessageTypeBitMask) | messageTypeToTry
        LoraRadioDataHandler.WiRocLogger.debug(
            "LoraRadioDataHandler::_GetStatus2Message() MessageDataToConsider: " + Utils.GetDataInHex(messageDataToConsider,
                                                                                                  logging.DEBUG))
        rssiValue = None
        if self.rssiByteCount > 0:
            if self.rssiByteCount == 2:
                # RAK3172 sends two byte signed (negative number dbm)
                rssiValue = int.from_bytes(self.DataReceived[expectedMessageLength:expectedMessageLength+self.rssiByteCount], byteorder='big', signed=True)
            else:
                # DRF1268DS sends one byte, a positive number.
                rssiValue = int.from_bytes(self.DataReceived[expectedMessageLength:expectedMessageLength+self.rssiByteCount], byteorder='big', signed=False)
      
        snrValue = None
        if self.SNRByteCount > 0:
            snrValue = int.from_bytes(self.DataReceived[expectedMessageLength + self.rssiByteCount:expectedMessageLength + self.rssiByteCount + self.SNRByteCount], byteorder='big', signed=True)
        statusValue = None
        if self.StatusByteCount > 0:
            statusValue = int.from_bytes(
                self.DataReceived[expectedMessageLength + self.rssiByteCount + self.SNRByteCount:expectedMessageLength + self.rssiByteCount + self.SNRByteCount + self.StatusByteCount], byteorder='big')

        if RSCoderLora.check(messageDataToConsider):
            # everything checks out, message should be correct
            loraStatusMsg = LoraRadioMessageCreator.GetStatus2MessageByFullMessageData(messageDataToConsider, rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
            return loraStatusMsg
        else:
            correctedData = None
            try:
                correctedData = RSCoderLora.decode(messageDataToConsider)
            except Exception as err:
                LoraRadioDataHandler.WiRocLogger.error("LoraRadioDataHandler::_GetStatus2Message() RS decoding failed with exception: " + str(err))

            if correctedData is not None and RSCoderLora.check(correctedData):
                LoraRadioDataHandler.WiRocLogger.info("LoraRadioDataHandler::_GetStatus2Message() Decoded, corrected data correctly it seems")
                loraStatusMsg = LoraRadioMessageCreator.GetStatus2MessageByFullMessageData(correctedData, rssiValue=rssiValue, snrValue=snrValue, statusValue=statusValue)
                return loraStatusMsg

        LoraRadioDataHandler.WiRocLogger.info("LoraRadioDataHandler::_GetStatus2Message() Could not decode correctly")
        LoraRadioDataHandler.WiRocLogger.error("LoraRadioDataHandler::_GetStatus2Message() No message could be decoded")
        return None

    def _GetMessageTypesByLength(self):
        expectedMessageLengths = [LoraRadioMessageRS.MessageLengths[idx] + self.rssiByteCount + self.SNRByteCount + self.StatusByteCount for idx in
                                  LoraRadioDataHandler.MessageTypesExpected]
        messageTypesByLength = []
        for idx, msgLength in enumerate(expectedMessageLengths):
            if len(self.DataReceived) == msgLength:
                messageTypeByLength = LoraRadioDataHandler.MessageTypesExpected[idx]
                messageTypesByLength.append(messageTypeByLength)
        return messageTypesByLength

    def _GetLikelyMessageTypes(self):
        messageTypes = []
        # Adds the message type in the header if that message type fits within the received data
        headerMessageType = LoraRadioDataHandler.GetHeaderMessageType(self.DataReceived)
        headerTypeMatchesLength = False
        if headerMessageType in LoraRadioDataHandler.MessageTypesExpected:
            expectedMessageLength = LoraRadioMessageRS.MessageLengths[headerMessageType] + self.rssiByteCount + self.SNRByteCount + self.StatusByteCount
            if len(self.DataReceived) == expectedMessageLength:
                messageTypes.append(headerMessageType)
                headerTypeMatchesLength = True
            elif len(self.DataReceived) > expectedMessageLength:
                messageTypes.append(headerMessageType)

        # Adds the message type(s) that exactly matches the current length of the data
        messageTypesByLength = self._GetMessageTypesByLength()
        for messageTypeByLength in messageTypesByLength:
            if messageTypeByLength not in messageTypes:
                if headerTypeMatchesLength:
                    # The header's type has exactly this length too, so another type also matches by
                    # length: try the header's type first. Trying the other type first can let
                    # Reed-Solomon "correct" a good message into a valid message of the wrong type, and the
                    # same bytes are then misread on every retry.
                    messageTypes.append(messageTypeByLength)
                else:
                    # try the one that matches by length first if there is also another that matches only by message type in header
                    messageTypes.insert(0, messageTypeByLength)

        return messageTypes

    @staticmethod
    def GetHeaderMessageType(messageData):
        if len(messageData) < 1:
            return -1
        headerMessageType = messageData[LoraRadioMessageRS.H] & LoraRadioMessageRS.MessageTypeBitMask
        return headerMessageType

    @staticmethod
    def GetRepeater(messageData):
        repeater = (messageData[LoraRadioMessageRS.H] & LoraRadioMessageRS.RepeaterBitMask) > 0
        return repeater

    @staticmethod
    def GetAckRequested(messageData):
        ackReq = (messageData[LoraRadioMessageRS.H] & LoraRadioMessageRS.AckBitMask) > 0
        return ackReq

    def _TryGetMessage(self) -> LoraRadioMessageAckRS | LoraRadioMessageStatus2RS | LoraRadioMessagePunchReDCoSRS | LoraRadioMessagePunchDoubleReDCoSRS | LoraRadioMessagePunchSubSecondRS | LoraRadioMessagePunchDoubleSubSecondRS | None:
        if not self._IsLongEnoughToBeMessage():
            return None

        self._CheckAndRemoveLoraModuleRXError()

        if not self._IsLongEnoughToBeMessage():
            return None

        messageTypes = self._GetLikelyMessageTypes()
        LoraRadioDataHandler.WiRocLogger.debug("LoraRadioDataHandler::_TryGetMessage() MessageTypes: " + str(messageTypes))

        for messageType in messageTypes:
            LoraRadioDataHandler.WiRocLogger.debug("LoraRadioDataHandler::_TryGetMessage() Message type to try: " + str(messageType))
            if messageType == LoraRadioMessageRS.MessageTypeLoraAck:
                loraAckMessage = self._GetAckMessage()
                if loraAckMessage is not None:
                    messageLength = LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeLoraAck]
                    self._removeBytesFromDataReceived(messageLength + self.rssiByteCount + self.SNRByteCount + self.StatusByteCount)
                    return loraAckMessage
            elif messageType == LoraRadioMessageRS.MessageTypeStatus2:
                loraStatus2Message = self._GetStatus2Message()
                if loraStatus2Message is not None:
                    messageLength = LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeStatus2]
                    self._removeBytesFromDataReceived(messageLength + self.rssiByteCount + self.SNRByteCount + self.StatusByteCount)
                    return loraStatus2Message
            elif messageType == LoraRadioMessageRS.MessageTypeSIPunchReDCoS:
                loraPunchMessage = self._GetPunchReDCoSMessage()
                if loraPunchMessage is not None:
                    self._CachePunchMessage(loraPunchMessage)
                    messageLength = LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunchReDCoS]
                    self._removeBytesFromDataReceived(messageLength + self.rssiByteCount + self.SNRByteCount + self.StatusByteCount)
                    return loraPunchMessage
            elif messageType == LoraRadioMessageRS.MessageTypeSIPunchSubSecond:
                loraSubSecondMessage = self._GetPunchSubSecondMessage()
                if loraSubSecondMessage is not None:
                    self._CachePunchSubSecondMessage(loraSubSecondMessage)
                    messageLength = LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunchSubSecond]
                    self._removeBytesFromDataReceived(messageLength + self.rssiByteCount + self.SNRByteCount + self.StatusByteCount)
                    return loraSubSecondMessage
            elif messageType == LoraRadioMessageRS.MessageTypeSIPunchDoubleSubSecond:
                loraSubSecondDoubleMessage = self._GetPunchDoubleSubSecondMessage()
                if loraSubSecondDoubleMessage is not None:
                    self._CacheDoublePunchSubSecondMessage(loraSubSecondDoubleMessage)
                    messageLength = LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunchDoubleSubSecond]
                    self._removeBytesFromDataReceived(messageLength + self.rssiByteCount + self.SNRByteCount + self.StatusByteCount)
                    return loraSubSecondDoubleMessage
            elif messageType == LoraRadioMessageRS.MessageTypeSIPunchDoubleReDCoS:
                loraPunchDoubleMessage = self._GetPunchDoubleReDCoSMessage()
                if loraPunchDoubleMessage is not None:
                    self._CacheDoublePunchMessage(loraPunchDoubleMessage)
                    messageLength = LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunchDoubleReDCoS]
                    self._removeBytesFromDataReceived(messageLength + self.rssiByteCount + self.SNRByteCount + self.StatusByteCount)
                    return loraPunchDoubleMessage
            else:
                pass

        return None

    # Call GetMessage only when you believe you might have a message
    def GetMessage(self) -> LoraRadioMessageAckRS | LoraRadioMessagePunchReDCoSRS | LoraRadioMessagePunchDoubleReDCoSRS | None:
        LoraRadioDataHandler.WiRocLogger.debug("Data considered (airorder): " + Utils.GetDataInHex(self.DataReceived, logging.DEBUG))

        message = self._TryGetMessage()
        if message is not None:
            return message

        self.ClearDataReceived()
        return None
