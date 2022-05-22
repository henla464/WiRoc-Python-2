__author__ = 'henla464'

import itertools
import logging
import time
from multiprocessing import Pool

from loraradio.LoraRadioMessageAndMetadata import LoraRadioMessageAndMetadata
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from loraradio.LoraRadioMessageRS import LoraRadioMessageRS, LoraRadioMessagePunchRS, LoraRadioMessagePunchDoubleRS
from loraradio.LoraRadioMessageRS import LoraRadioMessagePunchReDCoSRS, LoraRadioMessagePunchDoubleReDCoSRS
from loraradio.RSCoderLora import RSCoderLora
from settings.settings import SettingsClass
from utils.utils import Utils
from collections.abc import Iterable
import hashlib


class LoraRadioDataHandler(object):
    WiRocLogger = logging.getLogger('WiRoc')
    MessageTypesExpected = [LoraRadioMessageRS.MessageTypeSIPunchReDCoS, LoraRadioMessageRS.MessageTypeStatus, LoraRadioMessageRS.MessageTypeLoraAck, LoraRadioMessageRS.MessageTypeSIPunchDoubleReDCoS]
    RSSIByteCount = 0

    def __init__(self, rssiByteExpected):
        self.DataReceived = bytearray()
        # Dictionary of correctly received Punch message by control number
        self.ReceivedPunchMessageDict = {}
        self.LastPunchMessage = None
        self.LastPunchMessageTime = None
        self.RxError = False
        if rssiByteExpected:
            self.RSSIByteCount = 1
        else:
            self.RSSIByteCount = 0

    def AddData(self, dataByteOrArray):
        if isinstance(dataByteOrArray, Iterable):
            self.DataReceived.extend(dataByteOrArray)
        else:
            self.DataReceived.append(dataByteOrArray)

    def _IsLongEnoughToBeMessage(self):
        return len(self.DataReceived) >= (min(LoraRadioMessageRS.MessageLengths) + self.RSSIByteCount)

    def _CacheMessage(self, loraMsg):
        controlNumber = loraMsg.GetControlNumber()
        msgAndMetadata = LoraRadioMessageAndMetadata(loraMsg)
        self.ReceivedPunchMessageDict[controlNumber] = msgAndMetadata
        self.LastPunchMessageTime = msgAndMetadata.GetTimeCreated()
        self.LastPunchMessage = loraMsg
        self.RxError = False

    def ClearDataReceived(self):
        self.DataReceived = bytearray([])

    def _removeBytesFromDataReceived(self, noOfBytesToRemove):
        self.DataReceived = self.DataReceived[noOfBytesToRemove:]

    def _GetPunchReDCoSErasures(self, loraMsg):
        lengthOfThePartOfTheMessageToFindErasuresFor = len(loraMsg.GetPayloadByteArray()) + len(loraMsg.GetRSCode())
        # Add one for header
        possibleErasureIndices = [i+1 for i in range(lengthOfThePartOfTheMessageToFindErasuresFor)]
        listOfTuplesOfErasurePositions = itertools.combinations(possibleErasureIndices, LoraRadioMessagePunchReDCoSRS.NoOfECCBytes)
        listOfListOfErasurePositions = [list(x) for x in listOfTuplesOfErasurePositions]
        return listOfListOfErasurePositions

    def _GetPunchDoubleMessageAlternatives(self, loraMsg):
        possibilities = [None] * LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunchDoubleReDCoS]

        headers = None
        if self.LastPunchMessage is not None:

            headers = [(self.LastPunchMessage.GetHeaderData()[0] & ~LoraRadioMessageRS.MessageTypeBitMask) | LoraRadioMessageRS.MessageTypeSIPunchDoubleReDCoS]
            if (self.LastPunchMessage.GetHeaderData()[0] & ~LoraRadioMessageRS.MessageTypeBitMask) != \
                    (loraMsg.GetHeaderData()[0] & ~LoraRadioMessageRS.MessageTypeBitMask):
                headers += [(loraMsg.GetHeaderData()[0] & ~LoraRadioMessageRS.MessageTypeBitMask) | LoraRadioMessageRS.MessageTypeSIPunchDoubleReDCoS]

        controlNumbers = [controlNumber for controlNumber in self.ReceivedPunchMessageDict]
        controlNumber8bit = (loraMsg.GetControlNumber() & 0xFF)
        if controlNumber8bit not in controlNumbers:
            controlNumbers += [controlNumber8bit]
        sn3 = [0]
        if loraMsg.GetByteArray()[LoraRadioMessagePunchDoubleReDCoSRS.SN3] != 0:
            sn3 += [loraMsg.GetByteArray()[LoraRadioMessagePunchDoubleReDCoSRS.SN3]]

        cn1Plus = None
        if self.LastPunchMessage is not None:
            cn1Plus = [self.LastPunchMessage.GetByteArray()[LoraRadioMessagePunchDoubleReDCoSRS.CN1Plus]]
        TH = None
        if self.LastPunchMessageTime is not None:
            noOfSecondsSinceLastMessage = int(time.monotonic() - self.LastPunchMessageTime)
            lowestTimeWeAssumeCanBeCorrect = max(self.LastPunchMessage.GetTwelveHourTimerAsInt() \
                                                + noOfSecondsSinceLastMessage - 60,
                                                 self.LastPunchMessage.GetTwelveHourTimerAsInt())
            # Assuming a delay of delivery of a message of max 5 minutes
            highestTimeWeAssumeCanBeCorrect = self.LastPunchMessage.GetTwelveHourTimerAsInt() \
                                          + noOfSecondsSinceLastMessage + 120
            if (lowestTimeWeAssumeCanBeCorrect & 0xFF00) <= loraMsg.GetTwelveHourTimer()[0] <= (highestTimeWeAssumeCanBeCorrect & 0xFF00):
                # the TH is very reasonable so assume it is correct
                TH = [loraMsg.GetTwelveHourTimer()[0]]
            else:
                TH = list(range((lowestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8, ((highestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8)+1))


        # Message 2
        controlNumbers_2 = [controlNumber for controlNumber in self.ReceivedPunchMessageDict]
        controlNumber8bit_2 = (loraMsg.GetControlNumber_2() & 0xFF)
        if controlNumber8bit_2 not in controlNumbers_2:
            controlNumbers_2 += [controlNumber8bit_2]
        sn3_2 = [0]
        if loraMsg.GetPayloadByteArray()[LoraRadioMessagePunchDoubleReDCoSRS.SN3_2 - 1] != 0:
            sn3_2 += [loraMsg.GetPayloadByteArray()[LoraRadioMessagePunchDoubleReDCoSRS.SN3_2 - 1]]
        cn1Plus_2 = None
        if self.LastPunchMessage is not None:
            cn1Plus_2 = [self.LastPunchMessage.GetPayloadByteArray()[LoraRadioMessagePunchReDCoSRS.CN1Plus - 1]]
        TH2 = None
        if self.LastPunchMessageTime is not None:
            noOfSecondsSinceLastMessage = int(time.monotonic() - self.LastPunchMessageTime)
            lowestTimeWeAssumeCanBeCorrect = max(self.LastPunchMessage.GetTwelveHourTimerAsInt() \
                                                 + noOfSecondsSinceLastMessage - 60,
                                                 self.LastPunchMessage.GetTwelveHourTimerAsInt())
            highestTimeWeAssumeCanBeCorrect = self.LastPunchMessage.GetTwelveHourTimerAsInt() \
                + noOfSecondsSinceLastMessage + 120
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
        possibilities[LoraRadioMessagePunchDoubleReDCoSRS.SN3] = sn3
        fixedValues += [LoraRadioMessagePunchDoubleReDCoSRS.SN3]
        if cn1Plus is not None:
            possibilities[LoraRadioMessagePunchDoubleReDCoSRS.CN1Plus] = cn1Plus
            fixedValues += [LoraRadioMessagePunchDoubleReDCoSRS.CN1Plus]
        if TH is not None:
            possibilities[LoraRadioMessagePunchDoubleReDCoSRS.TH] = TH
            fixedValues += [LoraRadioMessagePunchDoubleReDCoSRS.TH]
        possibilities[LoraRadioMessagePunchDoubleReDCoSRS.CN0_2] = controlNumbers_2
        fixedValues += [LoraRadioMessagePunchDoubleReDCoSRS.CN0_2]
        possibilities[LoraRadioMessagePunchDoubleReDCoSRS.SN3_2] = sn3_2
        fixedValues += [LoraRadioMessagePunchDoubleReDCoSRS.SN3_2]
        if cn1Plus_2 is not None:
            possibilities[LoraRadioMessagePunchDoubleReDCoSRS.CN1Plus_2] = cn1Plus_2
            fixedValues += [LoraRadioMessagePunchDoubleReDCoSRS.CN1Plus_2]
        if TH2 is not None:
            possibilities[LoraRadioMessagePunchDoubleReDCoSRS.TH_2] = TH2
            fixedValues += [LoraRadioMessagePunchDoubleReDCoSRS.TH_2]

        messageData = loraMsg.GetByteArray()
        generatedMessages = self._GenerateMessageAlternatives([], possibilities, messageData)
        fixedErasures = self._FindReDCoSPunchDoubleErasures(loraMsg)
        fixedErasures = list(set(fixedErasures) - set(fixedValues))
        return generatedMessages, fixedValues, fixedErasures

    def _GetPunchMessageAlternatives(self, loraMsg):
        headers = [(loraMsg.GetHeaderData()[0] & ~LoraRadioMessageRS.MessageTypeBitMask) | LoraRadioMessageRS.MessageTypeSIPunchReDCoS]
        if self.LastPunchMessage is not None:
            if (self.LastPunchMessage.GetHeaderData()[0] & ~LoraRadioMessageRS.MessageTypeBitMask) != \
                    (loraMsg.GetHeaderData()[0] & ~LoraRadioMessageRS.MessageTypeBitMask):
                headers += [(self.LastPunchMessage.GetHeaderData()[0] & ~LoraRadioMessageRS.MessageTypeBitMask) | LoraRadioMessageRS.MessageTypeSIPunchReDCoS]

        controlNumbers = [controlNumber for controlNumber in self.ReceivedPunchMessageDict]
        controlNumber8bit = (loraMsg.GetControlNumber() & 0xFF)
        if controlNumber8bit not in controlNumbers:
            controlNumbers += [controlNumber8bit]
        sn3 = [0]
        if loraMsg.GetByteArray()[LoraRadioMessagePunchReDCoSRS.SN3] != 0:
            sn3 += [loraMsg.GetByteArray()[LoraRadioMessagePunchReDCoSRS.SN3]]
        cn1Plus = None
        if self.LastPunchMessage is not None:
            cn1Plus = [self.LastPunchMessage.GetByteArray()[LoraRadioMessagePunchReDCoSRS.CN1Plus]]

        TH = None
        if self.LastPunchMessageTime is not None:
            noOfSecondsSinceLastMessage = int(time.monotonic() - self.LastPunchMessageTime)
            lowestTimeWeAssumeCanBeCorrect = max(self.LastPunchMessage.GetTwelveHourTimerAsInt() \
                                                 + noOfSecondsSinceLastMessage - 60,
                                                 self.LastPunchMessage.GetTwelveHourTimerAsInt())
            highestTimeWeAssumeCanBeCorrect = self.LastPunchMessage.GetTwelveHourTimerAsInt() \
                + noOfSecondsSinceLastMessage + 120
            if ((lowestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8) <= loraMsg.GetTwelveHourTimer()[0] \
                    <= ((highestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8):
                # the TH is very reasonable so assume it is correct
                TH = [loraMsg.GetTwelveHourTimer()[0]]
            else:
                TH = list(range((lowestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8, (highestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8))

        fixedValues = [LoraRadioMessagePunchReDCoSRS.H, LoraRadioMessagePunchReDCoSRS.CN0,
                       LoraRadioMessagePunchReDCoSRS.SN3, LoraRadioMessagePunchReDCoSRS.CN1Plus]
        possibilities = [None]*LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunchReDCoS]
        possibilities[LoraRadioMessagePunchReDCoSRS.H] = headers
        possibilities[LoraRadioMessagePunchReDCoSRS.CN0] = controlNumbers
        possibilities[LoraRadioMessagePunchReDCoSRS.SN3] = sn3
        possibilities[LoraRadioMessagePunchReDCoSRS.CN1Plus] = cn1Plus
        if cn1Plus is not None:
            possibilities[LoraRadioMessagePunchReDCoSRS.CN1Plus] = cn1Plus
            fixedValues += [LoraRadioMessagePunchReDCoSRS.CN1Plus]
        if TH is not None:
            possibilities[LoraRadioMessagePunchReDCoSRS.TH] = TH
            fixedValues += [LoraRadioMessagePunchReDCoSRS.TH]

        messageData = loraMsg.GetByteArray()
        generatedMessages = self._GenerateMessageAlternatives([], possibilities, messageData)

        fixedErasures = self._FindReDCoSPunchErasures(loraMsg)
        fixedErasures = list(set(fixedErasures) - set(fixedValues))
        return generatedMessages, fixedValues, fixedErasures

    def _GenerateMessageAlternatives(self, generatedMessage, possibilities, origMessageData):
        generatedMessages = []
        byteIndex = len(generatedMessage)
        if byteIndex >= len(possibilities):
            return [generatedMessage]
        if possibilities[byteIndex] is not None:
            for possibility in possibilities[byteIndex]:
                generatedMessages += self._GenerateMessageAlternatives(generatedMessage + [possibility], possibilities, origMessageData)
        else:
            generatedMessages += self._GenerateMessageAlternatives(generatedMessage + [origMessageData[byteIndex]], possibilities,
                                                                        origMessageData)
        return generatedMessages

    def _AddFixedErasursToCombinationIterator(self, erasureCominationIterator, fixedErasures):
        fixedErasureTuple = tuple(fixedErasures)
        for comb in erasureCominationIterator:
            yield comb + fixedErasureTuple

    def _GetReDCoSErasureCombinations(self, loraMsg, fixedValues, fixedErasures, eccBytesToNotUse):
        messageData = loraMsg.GetByteArray()
        lengthOfMessage = len(messageData)
        lengthOfDataWithoutCRC = lengthOfMessage - loraMsg.NoOfCRCBytes
        indexInMessageThatMayOrMayNotHaveErrors = list(set(range(lengthOfDataWithoutCRC))-set(fixedValues) - set(fixedErasures))
        erasureCombinationIterator = itertools.combinations(indexInMessageThatMayOrMayNotHaveErrors, loraMsg.NoOfECCBytes - len(fixedErasures) - eccBytesToNotUse)
        return self._AddFixedErasursToCombinationIterator(erasureCombinationIterator, fixedErasures)

    def _FindReDCoSPunchErasures(self, loraMsg):
        # The returned index is relative to the beginning of the message, including header. This is to match the fixedValues array.
        controlNumber = loraMsg.GetControlNumber()
        controlNumber8bit = (controlNumber & 0xFF)
        controlNumberToUse = controlNumber if controlNumber in self.ReceivedPunchMessageDict else controlNumber8bit

        erasures = []
        if controlNumberToUse in self.ReceivedPunchMessageDict:
            # found a previously cached message from same controlnumber => probably correct controlnumber
            previousMsgAndMetadata = self.ReceivedPunchMessageDict[controlNumberToUse]
            previousMsg = previousMsgAndMetadata.GetLoraRadioMessageRS()
        else:
            erasures.append(LoraRadioMessagePunchReDCoSRS.CN0)

        cardNoByteArray = loraMsg.GetSICardNoByteArray()[0:4]
        cardNo = Utils.toInt(cardNoByteArray)
        if 0x4FFFF < cardNo < 500000: # 500 000 = 0x7A120
            erasures.append(LoraRadioMessagePunchReDCoSRS.SN2) # at least SN2 should be wrong
        if cardNoByteArray[0] != 0x00: # SN3 not currently used so should always be 0
            erasures.append(LoraRadioMessagePunchReDCoSRS.SN3)

        # check that TH isn't higher than possible
        if loraMsg.GetTwelveHourTimer()[0] > 0xA8:
            erasures.append(LoraRadioMessagePunchReDCoSRS.TH)

        if self.LastPunchMessage is not None:
            cn1PlusWrong = self.LastPunchMessage.GetPayloadByteArray()[LoraRadioMessagePunchReDCoSRS.CN1Plus - 1] != \
                loraMsg.GetPayloadByteArray()[LoraRadioMessagePunchReDCoSRS.CN1Plus - 1]
            # If the byte with AM/PM (6) is found to be wrong then assume AM/PM has not changed and compare the TH, TL
            if cn1PlusWrong or (self.LastPunchMessage is not None and self.LastPunchMessage.GetTwentyFourHour() == loraMsg.GetTwentyFourHour()):
                noOfSecondsSinceLastMessage = int(time.monotonic() - self.LastPunchMessageTime)
                lowestTimeWeAssumeCanBeCorrect = self.LastPunchMessage.GetTwelveHourTimerAsInt() - 60
                highestTimeWeAssumeCanBeCorrect = self.LastPunchMessage.GetTwelveHourTimerAsInt() \
                    + noOfSecondsSinceLastMessage + 2 * 60
                if loraMsg.GetTwelveHourTimerAsInt() < lowestTimeWeAssumeCanBeCorrect:
                    if loraMsg.GetTwelveHourTimer()[0] != self.LastPunchMessage.GetTwelveHourTimer()[0]:
                        # TH differs so this must be the reason for time being too low (assume TL is correct)
                        erasures.append(LoraRadioMessagePunchReDCoSRS.TH)
                    else:
                        erasures.append(LoraRadioMessagePunchReDCoSRS.TL)
                elif loraMsg.GetTwelveHourTimerAsInt() > highestTimeWeAssumeCanBeCorrect:
                    if loraMsg.GetTwelveHourTimer()[0] > ((highestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8):
                        # TH differs so this must be the reason for time being too high (assume TL is correct)
                        erasures.append(LoraRadioMessagePunchReDCoSRS.TH)
                    else:
                        erasures.append(LoraRadioMessagePunchReDCoSRS.TL)

            # check that TL isn't higher than possible. Only check when TH is the highest value and not believed
            # to be wrong
            if loraMsg.GetTwelveHourTimer()[0] == 0xA8 and loraMsg.GetTwelveHourTimer()[1] > 0xC0 \
                    and LoraRadioMessagePunchReDCoSRS.TH not in erasures:
                erasures.append(LoraRadioMessagePunchReDCoSRS.TL)

        LoraRadioDataHandler.WiRocLogger.debug(
            "LoraRadioDataHandler::_FindReDCoSPunchErasures " + str(len(erasures)) + " erasures found. " + str(erasures))
        return list(set(erasures))

    def _FindPunchErasures(self, loraMsg):
        controlNumber = loraMsg.GetControlNumber()
        controlNumber8bit = (controlNumber & 0xFF)
        controlNumberToUse = controlNumber if controlNumber in self.ReceivedPunchMessageDict else controlNumber8bit
        erasures = []
        if controlNumberToUse in self.ReceivedPunchMessageDict:
            # found a previously cached message from same controlnumber => probably correct controlnumber
            previousMsgAndMetadata = self.ReceivedPunchMessageDict[controlNumberToUse]
            previousMsg = previousMsgAndMetadata.GetLoraRadioMessageRS()

            if previousMsg.GetAckRequested() != loraMsg.GetAckRequested():
                erasures.append(0)
            elif previousMsg.GetBatteryLow() != loraMsg.GetBatteryLow():
                erasures.append(0)
            elif previousMsg.GetRepeater() != loraMsg.GetRepeater():
                erasures.append(0)
        else:
            # technically it could be CN1 bit 8 that is wrong, but since higher number than 255 is almost never used
            # it is extremely unlikely. The oldest SI cards don't even support > 255.
            erasures.append(1)

        cardNoByteArray = loraMsg.GetSICardNoByteArray()[0:4]
        cardNo = Utils.toInt(cardNoByteArray)
        if 0x4FFFF < cardNo < 500000: # 500 000 = 0x7A120
            erasures.append(LoraRadioMessagePunchRS.SN2) # at least SN2 should be wrong
        if cardNoByteArray[0] != 0x00: # SN3 not currently used so should always be 0
            erasures.append(LoraRadioMessagePunchRS.SN3)
        if controlNumberToUse != controlNumber:
            # bit CN1 bit8 of stationcode/controlnumber is almost certainly wrong
            erasures.append(LoraRadioMessagePunchRS.CN1Plus)
        elif self.LastPunchMessage is not None:
            if self.LastPunchMessage.GetFourWeekCounter() != loraMsg.GetFourWeekCounter():
                erasures.append(LoraRadioMessagePunchRS.CN1Plus)
            elif self.LastPunchMessage.GetDayOfWeek() != loraMsg.GetDayOfWeek():
                erasures.append(LoraRadioMessagePunchRS.CN1Plus)
            elif self.LastPunchMessage.GetTwentyFourHour() == 0 and loraMsg.GetTwentyFourHour() == 1 \
                    and loraMsg.GetTwelveHourTimerAsInt() > 20 * 60:
                erasures.append(LoraRadioMessagePunchRS.CN1Plus)
            elif self.LastPunchMessage.GetTwentyFourHour() == 1 and loraMsg.GetTwentyFourHour() == 0 \
                    and loraMsg.GetTwelveHourTimerAsInt() > 20 * 60:
                erasures.append(LoraRadioMessagePunchRS.CN1Plus)

        # check that TH isn't higher than possible
        if loraMsg.GetTwelveHourTimer()[0] > 0xA8:
            erasures.append(LoraRadioMessagePunchRS.TH)

        # If the byte with AM/PM (6) is found to be wrong then assume AM/PM has not changed and compare the TH, TL
        if 6 in erasures or (self.LastPunchMessage is not None and self.LastPunchMessage.GetTwentyFourHour() == loraMsg.GetTwentyFourHour()):
            noOfSecondsSinceLastMessage = int(time.monotonic() - self.LastPunchMessageTime)
            lowestTimeWeAssumeCanBeCorrect = self.LastPunchMessage.GetTwelveHourTimerAsInt()
            # Assuming a delay of delivery of a message of max 5 minutes
            highestTimeWeAssumeCanBeCorrect = self.LastPunchMessage.GetTwelveHourTimerAsInt() \
                + noOfSecondsSinceLastMessage + 5 * 60

            if loraMsg.GetTwelveHourTimerAsInt() < lowestTimeWeAssumeCanBeCorrect:
                if loraMsg.GetTwelveHourTimer()[0] != self.LastPunchMessage.GetTwelveHourTimer()[0]:
                    # TH differs so this must be the reason for time being too low (assume TL is correct)
                    erasures.append(LoraRadioMessagePunchRS.TH)
                else:
                    erasures.append(LoraRadioMessagePunchRS.TL)
            elif loraMsg.GetTwelveHourTimerAsInt() > highestTimeWeAssumeCanBeCorrect:
                if loraMsg.GetTwelveHourTimer()[0] > ((highestTimeWeAssumeCanBeCorrect & 0xFF00) >> 8):
                    # TH differs so this must be the reason for time being too high (assume TL is correct)
                    erasures.append(LoraRadioMessagePunchRS.TH)
                else:
                    # Unless we change the highestTimeWeAssumeCanBeCorrect to something less than the extra 5 min
                    # it should never reach this
                    erasures.append(LoraRadioMessagePunchRS.TL)

            # check that TL isn't higher than possible. Only check when TH is the highest value and not believed
            # to be wrong
            if loraMsg.GetTwelveHourTimer()[0] == 0xA8 and loraMsg.GetTwelveHourTimer()[1] > 0xC0 \
                    and LoraRadioMessagePunchRS.TH not in erasures:
                erasures.append(LoraRadioMessagePunchRS.TL)

        LoraRadioDataHandler.WiRocLogger.debug(
            "LoraRadioDataHandler::FindPunchErasures " + str(len(erasures)) + " erasures found. " + str(erasures))
        return list(set(erasures))

    def _GetPunchReDCoSTupleFromPunchDouble(self, loraDoubleMsg):
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

    def _GetPunchTupleFromPunchDouble(self, loraDoubleMsg):
        payload = loraDoubleMsg.GetByteArray()
        loraMsgLength = LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunch]
        # recreate two message arrays and find the erasures for each
        firstMsgByteArray = payload[0:loraMsgLength - LoraRadioMessagePunchRS.NoOfECCBytes] + bytearray(LoraRadioMessagePunchRS.NoOfECCBytes)
        firstMsgByteArray[LoraRadioMessageRS.H] = (firstMsgByteArray[LoraRadioMessageRS.H] & ~LoraRadioMessageRS.MessageTypeBitMask) | LoraRadioMessageRS.MessageTypeSIPunch
        secondMsgByteArray = bytearray([firstMsgByteArray[LoraRadioMessageRS.H]]) + \
            payload[loraMsgLength - LoraRadioMessagePunchRS.NoOfECCBytes:-LoraRadioMessagePunchDoubleRS.NoOfECCBytes] + \
            bytearray(LoraRadioMessagePunchRS.NoOfECCBytes)
        loraPMsg1 = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(firstMsgByteArray)
        loraPMsg2 = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(secondMsgByteArray)
        return loraPMsg1, loraPMsg2

    def _FindPunchDoubleErasures(self, loraDoubleMsg):
        loraPMsg1, loraPMsg2 = self._GetPunchTupleFromPunchDouble(loraDoubleMsg)
        erasures1 = self._FindPunchErasures(loraPMsg1)
        erasures2 = self._FindPunchErasures(loraPMsg2)
        for i in range(len(erasures2)-1,-1,-1):
            if erasures2[i] == LoraRadioMessagePunchRS.H:
                # header is wrong, it was picked up for message 2, but doesn't actually exist twice in the double message
                # since we change the positions in erasure2 to the real positions in the double message we need to remove
                # it here. And add it to erasures1 if it isn't already there
                erasures2.pop(i)
                if LoraRadioMessagePunchRS.H not in erasures1:
                    # header is wrong, and it was not picked up for message 1
                    erasures1.append(LoraRadioMessagePunchRS.H)

        for i in range(len(erasures2)):
            # Add the length of the first part of the double message minus the RSCodes minus the header of the second
            loraMsgLength = LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunch]
            erasures2[i] += loraMsgLength - LoraRadioMessagePunchRS.NoOfECCBytes - 1
        erasures1.extend(erasures2)
        LoraRadioDataHandler.WiRocLogger.debug(
            "LoraRadioDataHandler::_FindPunchDoubleErasures " + str(len(erasures1)) + " erasures found. " + str(erasures1))
        return erasures1

    def _FindReDCoSPunchDoubleErasures(self, loraDoubleMsg):
        loraPMsg1, loraPMsg2 = self._GetPunchReDCoSTupleFromPunchDouble(loraDoubleMsg)
        erasures1 = self._FindReDCoSPunchErasures(loraPMsg1)
        erasures2 = self._FindReDCoSPunchErasures(loraPMsg2)
        for i in range(len(erasures2)):
            # Add the length of the first part of the double message minus the RSCodes minus the header of the second
            loraMsgLength = LoraRadioMessagePunchReDCoSRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunchReDCoS]
            erasures2[i] += loraMsgLength - LoraRadioMessagePunchReDCoSRS.NoOfECCBytes - LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes - 1
        erasures1.extend(erasures2)

        LoraRadioDataHandler.WiRocLogger.debug(
            "LoraRadioDataHandler::_FindReDCoSPunchDoubleErasures " + str(len(erasures1)) + " erasures found. " + str(erasures1))

        return erasures1

    def _CheckAndRemoveLoraModuleRXError(self):
        if len(self.DataReceived) >= 10:
            if self.DataReceived[0:10] == bytearray('rx error\r\n'.encode('latin-1')):
                LoraRadioDataHandler.WiRocLogger.debug(
                    "LoraRadioDataHandler::CheckAndRemoveLoraModuleRXError 'rx error' returned by module")
                self.RxError = True
                self.DataReceived = self.DataReceived[10:]

    def _GetPunchMessageWithErasures(self, messageDataToConsider, rssiByteValue, erasures=None):
        loraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(messageDataToConsider,
                                                                           rssiByte=rssiByteValue)
        erasures.extend(self._FindPunchErasures(loraMsg))
        if len(erasures) > 0:
            try:
                # No point in having more erasures than ECCBytes, and no point in having odd number of erasures
                # when number of ECC bytes is even
                erasuresToUse = list(set(erasures))
                if len(erasuresToUse) >= LoraRadioMessagePunchRS.NoOfECCBytes:
                    erasuresToUse = erasuresToUse[0:LoraRadioMessagePunchRS.NoOfECCBytes]
                elif len(erasuresToUse) % 2 != 0:
                    # Odd number
                    numberOfErasuresToUse = len(erasuresToUse) - 1
                    erasuresToUse = erasuresToUse[0:numberOfErasuresToUse]

                LoraRadioDataHandler.WiRocLogger.debug(
                    "LoraRadioDataHandler::_GetPunchMessageWithErasures() ErasuresToUse: " + str(erasuresToUse), logging.debug)
                correctedData2 = RSCoderLora.decode(messageDataToConsider, erasuresToUse)
                if not RSCoderLora.check(correctedData2):
                    # for some reason sometimes decode just returns the corrupted message with not change
                    # and no exception thrown. So check the decoded message to make sure we dont return
                    # a message that is clearly wrong
                    return None
                loraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(correctedData2,
                                                                                   rssiByte=rssiByteValue)
                self._CacheMessage(loraMsg)
                self._removeBytesFromDataReceived(len(messageDataToConsider) + self.RSSIByteCount)
                return loraMsg
            except Exception as err2:
                LoraRadioDataHandler.WiRocLogger.error(
                    "LoraRadioDataHandler::_GetPunchMessageWithErasures() RS decoding failed also with erasures with exception: " + str(
                        err2))
                return None
        else:
            LoraRadioDataHandler.WiRocLogger.error(
                "LoraRadioDataHandler::GetPunchMessageWithErasures() No erasures found so could not decode")
            return None

    def _GetPunchReDCoSMessageWithErasures(self, messageDataToConsider, rssiByteValue, erasures=None):
        loraMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(messageDataToConsider,
                                                                           rssiByte=rssiByteValue)
        erasures.extend(self._FindReDCoSPunchErasures(loraMsg))
        if len(erasures) > 1:
            try:
                # No point in having more erasures than ECCBytes, and no point in having odd number of erasures
                # when number of ECC bytes is even
                erasuresToUse = list(set(erasures))
                if len(erasuresToUse) >= LoraRadioMessagePunchReDCoSRS.NoOfECCBytes:
                    erasuresToUse = erasuresToUse[0:LoraRadioMessagePunchReDCoSRS.NoOfECCBytes]
                elif len(erasuresToUse) % 2 != 0:
                    # Odd number
                    numberOfErasuresToUse = len(erasuresToUse) - 1
                    erasuresToUse = erasuresToUse[0:numberOfErasuresToUse]

                LoraRadioDataHandler.WiRocLogger.debug(
                    "LoraRadioDataHandler::_GetPunchReDCoSMessageWithErasures() ErasuresToUse: " + str(erasuresToUse), logging.debug)
                messageDataToConsiderWithoutCRC = messageDataToConsider[:-LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes]
                correctedData2 = RSCoderLora.decode(messageDataToConsiderWithoutCRC, erasuresToUse)
                if not RSCoderLora.check(correctedData2):
                    # for some reason sometimes decode just returns the corrupted message with no change
                    # and no exception thrown. So check the decoded message to make sure we don't return
                    # a message that is clearly wrong
                    return None
                correctedData2.extend(messageDataToConsider[-LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes:])
                loraMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(correctedData2,
                                                                                   rssiByte=rssiByteValue)
                self._CacheMessage(loraMsg)
                self._removeBytesFromDataReceived(len(messageDataToConsider) + self.RSSIByteCount)
                return loraMsg
            except Exception as err2:
                LoraRadioDataHandler.WiRocLogger.error(
                    "LoraRadioDataHandler::_GetPunchReDCoSMessageWithErasures() RS decoding failed also with erasures with exception: " + str(err2))
                return None
        else:
            LoraRadioDataHandler.WiRocLogger.error("LoraRadioDataHandler::_GetPunchReDCoSMessageWithErasures() No erasures found so could not decode")
            return None

    def _GetPunchMessage(self, erasures=None):
        messageTypeToTry = LoraRadioMessageRS.MessageTypeSIPunch
        expectedMessageLength = LoraRadioMessageRS.MessageLengths[messageTypeToTry]
        if len(self.DataReceived) < expectedMessageLength + self.RSSIByteCount:
            return None
        if erasures is None:
            erasures = []

        messageDataToConsider = self.DataReceived[0:expectedMessageLength]
        messageDataToConsider[LoraRadioMessageRS.H] = (messageDataToConsider[LoraRadioMessageRS.H] & ~LoraRadioMessagePunchRS.MessageTypeBitMask) | messageTypeToTry
        rssiByteValue = self.DataReceived[expectedMessageLength] if self.RSSIByteCount == 1 else None

        if RSCoderLora.check(messageDataToConsider):
            # everything checks out, message should be correct
            loraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(messageDataToConsider, rssiByte=rssiByteValue)
            self._CacheMessage(loraMsg)
            self._removeBytesFromDataReceived(expectedMessageLength+self.RSSIByteCount)
            return loraMsg
        else:
            try:
                correctedData = RSCoderLora.decode(messageDataToConsider)

                if RSCoderLora.check(correctedData):
                    LoraRadioDataHandler.WiRocLogger.info(
                        "LoraRadioDataHandler::_GetPunchMessage() Decoded, corrected data correctly it seems")
                    loraPunchMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(correctedData, rssiByte=rssiByteValue)
                    self._CacheMessage(loraPunchMsg)
                    self._removeBytesFromDataReceived(expectedMessageLength + self.RSSIByteCount)
                    return loraPunchMsg
                else:
                    LoraRadioDataHandler.WiRocLogger.info(
                        "LoraRadioDataHandler::_GetPunchMessage() Could not decode correctly, try with erasures next")
                    loraPunchMsg = self._GetPunchMessageWithErasures(messageDataToConsider, rssiByteValue, erasures=erasures)
                    return loraPunchMsg
            except Exception as err:
                LoraRadioDataHandler.WiRocLogger.error(
                    "LoraRadioDataHandler::GetPunchMessage() RS decoding failed with exception: " + str(err))
                loraPunchMsg = self._GetPunchMessageWithErasures(messageDataToConsider, rssiByteValue, erasures=erasures)
                return loraPunchMsg

    def _GetPunchUsingReDCoSDecoding(self, messageDataToConsider, rssiByteValue):
        loraMsgWithErrors = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(messageDataToConsider, rssiByteValue)
        alts, fixedValues, fixedErasures = self._GetPunchMessageAlternatives(loraMsgWithErrors)
        lengthOfDataThatRSCalculatedOverWithoutRSCode = len(
            loraMsgWithErrors.GetPayloadByteArray() + loraMsgWithErrors.GetHeaderData()) - len(fixedValues) - len(fixedErasures)

        erasuresCombinationIterator = self._GetReDCoSErasureCombinations(loraMsgWithErrors, fixedValues, fixedErasures, 0)
        erasuresCombinationList = list(erasuresCombinationIterator)

        global createDecodePunch

        def createDecodePunch(innerCorruptedMessageData):
            global decodePunch

            def decodePunch(innerErasuresCombination):
                try:
                    res2 = RSCoderLora.decode(innerCorruptedMessageData, innerErasuresCombination)
                except Exception as ex:
                    res2 = None
                return res2

            return decodePunch

        for startMessageDataComboToTry in alts:
            theDecodeFunction = createDecodePunch(startMessageDataComboToTry[0:-LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes])
            crcDictionary = {}
            with Pool(5) as p:
                res = p.map(theDecodeFunction, erasuresCombinationList)
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
                    if theCRCHash == loraMsgWithErrors.GetByteArray()[-LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes:]:
                        LoraRadioDataHandler.WiRocLogger.info("LoraRadioDataHandler::_GetPunchUsingReDCoSDecoding() CRC matches, return message")
                        return LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(decoded.extend(theCRCHash))
                    else:
                        if crcDictionary[theCRCHash] == lengthOfDataThatRSCalculatedOverWithoutRSCode+1:
                            # We found many messages that after decoding has same CRC. If one of the two
                            # CRC bytes matches then we assume we found a correctly decoded message.
                            if theCRCHash[0] == startMessageDataComboToTry[LoraRadioMessagePunchReDCoSRS.CRC0] or \
                                    theCRCHash[1] == startMessageDataComboToTry[LoraRadioMessagePunchReDCoSRS.CRC1]:
                                LoraRadioDataHandler.WiRocLogger.info("LoraRadioDataHandler::_GetPunchDoubleUsingReDCoSDecoding() Found a CRC half match, return message")
                                return LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(decoded.extend(theCRCHash))

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

    def _GetNoOfHalfMatchesRequired(self, lengthOfDataErasureCombinationsAreCalculatedOver, noOfECCBytes, noOfFixedErasures, noOfErasuresToDecreaseWith):
        if noOfErasuresToDecreaseWith == 0:
            # should only be called when we decrease the no of erasures in the combinations
            raise Exception("This functions should not be called with noOfErasuresToDecreaseWith = 0")

        noOfErasuresInACombination = noOfECCBytes - noOfFixedErasures - noOfErasuresToDecreaseWith  # Remove two erasures to decrease the number of combinations. The two left over ECC bytes can correct one error that is not pointed out by the erasure combination
        noOfBytesAssumedCorrect = lengthOfDataErasureCombinationsAreCalculatedOver - noOfErasuresInACombination - (noOfErasuresToDecreaseWith // 2)
        noOfBytesAssumedIncorrect = lengthOfDataErasureCombinationsAreCalculatedOver - noOfBytesAssumedCorrect

        noOfHalfMatchesRequired = self._GetNoOfCombinations(noOfBytesAssumedIncorrect, noOfErasuresInACombination)
        return noOfHalfMatchesRequired

        #noOfBytesAssumedCorrect = lengthOfDataErasureCombinationsAreCalculatedOver - noOfErasuresInACombination + 1 - (noOfErasuresToDecreaseWith//2)
        #noOfBytesAssumedIncorrect = lengthOfDataErasureCombinationsAreCalculatedOver - noOfBytesAssumedCorrect
        #noOfHalfMatchesRequired = totalNoOfErasureCombinations
        # We should use 0 to noOfErasuresInACombination because one error is corrected by the two ECC bytes left over due to not using them all for erasures
        #for noOfErrorBytsCorrectlyChoosen in range(noOfErasuresInACombination - 1 + (noOfErasuresToDecreaseWith//2)):
        #    noOfHalfMatchesRequired -= self._GetNoOfCombinations(noOfBytesAssumedCorrect, noOfErasuresInACombination - noOfErrorBytsCorrectlyChoosen) * \
        #                               self._GetNoOfCombinations(noOfBytesAssumedIncorrect, noOfErrorBytsCorrectlyChoosen)
        #return noOfHalfMatchesRequired

    def _GetPunchDoubleUsingReDCoSDecoding(self, messageDataToConsider, rssiByteValue):
        loraMsgWithErrors = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(messageDataToConsider, rssiByteValue)
        alts, fixedValues, fixedErasures = self._GetPunchDoubleMessageAlternatives(loraMsgWithErrors)
        lengthOfDataThatRSCalculatedOverWithoutRSCode = len(
            loraMsgWithErrors.GetPayloadByteArray() + loraMsgWithErrors.GetHeaderData()) - len(fixedValues) - len(fixedErasures)
        noOfHalfMatchesRequired = lengthOfDataThatRSCalculatedOverWithoutRSCode + 1

        receivedCRC = loraMsgWithErrors.GetByteArray()[-LoraRadioMessagePunchDoubleReDCoSRS.NoOfCRCBytes:]
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
            lengthOfDataErasureCombinationsAreCalculatedOver = len(loraMsgWithErrors.GetByteArray()) - loraMsgWithErrors.NoOfCRCBytes - len(fixedValues) - len(fixedErasures)
            noOfHalfMatchesRequired = self._GetNoOfHalfMatchesRequired(lengthOfDataErasureCombinationsAreCalculatedOver, loraMsgWithErrors.NoOfECCBytes, len(fixedErasures), nOfErasuresToDecreaseWith)

            if len(erasuresCombinationList) * len(alts) > SettingsClass.GetReDCoSCombinationThreshold():
                nOfErasuresToDecreaseWith = 4
                erasuresCombinationIterator = self._GetReDCoSErasureCombinations(loraMsgWithErrors, fixedValues, fixedErasures, nOfErasuresToDecreaseWith)
                erasuresCombinationList = list(erasuresCombinationIterator)
                lengthOfDataErasureCombinationsAreCalculatedOver = len(loraMsgWithErrors.GetByteArray()) - loraMsgWithErrors.NoOfCRCBytes - len(fixedValues) - len(fixedErasures)
                noOfHalfMatchesRequired = self._GetNoOfHalfMatchesRequired(lengthOfDataErasureCombinationsAreCalculatedOver, loraMsgWithErrors.NoOfECCBytes, len(fixedErasures), nOfErasuresToDecreaseWith)
                LoraRadioDataHandler.WiRocLogger.debug("LoraRadioDataHandler::_GetPunchDoubleUsingReDCoSDecoding() No of erasure in each combination reduced by four")
            else:
                LoraRadioDataHandler.WiRocLogger.debug("LoraRadioDataHandler::_GetPunchDoubleUsingReDCoSDecoding() No of erasure in each combination reduced by two")

        LoraRadioDataHandler.WiRocLogger.debug("LoraRadioDataHandler::_GetPunchDoubleUsingReDCoSDecoding() No of total combinations: " + str(len(erasuresCombinationList) * len(alts)))
        LoraRadioDataHandler.WiRocLogger.debug("LoraRadioDataHandler::_GetPunchDoubleUsingReDCoSDecoding() No of half matches required: " + str(noOfHalfMatchesRequired))

        global createDecodeDouble

        def createDecodeDouble(innerCorruptedMessageData):
            global decodeDouble

            def decodeDouble(innerErasuresCombination):
                try:
                    res2 = RSCoderLora.decodeLong(innerCorruptedMessageData, innerErasuresCombination)
                except Exception as err:
                    res2 = None
                return res2

            return decodeDouble

        for startMessageDataComboToTry in alts:
            theDecodeFunction = createDecodeDouble(startMessageDataComboToTry[0:-LoraRadioMessagePunchDoubleReDCoSRS.NoOfCRCBytes])
            crcDictionary = {}
            with Pool(5) as p:
                res = p.map(theDecodeFunction, erasuresCombinationList)

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
                        LoraRadioDataHandler.WiRocLogger.info("LoraRadioDataHandler::_GetPunchDoubleUsingReDCoSDecoding() CRC matches, return message")
                        return LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(decoded + theCRCHash)
                    else:
                        if crcDictionary[theCRCHash] == noOfHalfMatchesRequired:
                            # We found many messages that after decoding has same CRC. If one of the two
                            # CRC bytes matches then we assume we found a correctly decoded message.
                            if theCRCHash[0] == receivedCRC[0] or theCRCHash[1] == receivedCRC[1]:
                                LoraRadioDataHandler.WiRocLogger.info("LoraRadioDataHandler::_GetPunchDoubleUsingReDCoSDecoding() Found a CRC half match, return message")
                                return LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(decoded + theCRCHash)

        LoraRadioDataHandler.WiRocLogger.info("LoraRadioDataHandler::_GetPunchDoubleUsingReDCoSDecoding() Could not decode using ReDCoS")
        return None

    def _GetPunchReDCoSMessage(self, erasures=None):
        messageTypeToTry = LoraRadioMessageRS.MessageTypeSIPunchReDCoS
        expectedMessageLength = LoraRadioMessageRS.MessageLengths[messageTypeToTry]
        if len(self.DataReceived) < expectedMessageLength + self.RSSIByteCount:
            return None
        if erasures is None:
            erasures = []

        messageDataToConsider = LoraRadioMessagePunchReDCoSRS.DeInterleaveFromAirOrder(self.DataReceived[0:expectedMessageLength])
        messageDataToConsider[LoraRadioMessageRS.H] = (messageDataToConsider[LoraRadioMessageRS.H] & ~LoraRadioMessagePunchRS.MessageTypeBitMask) | messageTypeToTry
        rssiByteValue = self.DataReceived[expectedMessageLength] if self.RSSIByteCount == 1 else None

        messageDataToConsiderMinusCRC = messageDataToConsider[:-LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes]
        if RSCoderLora.check(messageDataToConsiderMinusCRC):
            # everything checks out, message should be correct
            loraMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(messageDataToConsider, rssiByte=rssiByteValue)
            self._CacheMessage(loraMsg)
            self._removeBytesFromDataReceived(expectedMessageLength+self.RSSIByteCount)
            return loraMsg
        else:
            correctedData = None
            try:
                correctedData = RSCoderLora.decode(messageDataToConsiderMinusCRC)
            except Exception as err:
                LoraRadioDataHandler.WiRocLogger.error(
                    "LoraRadioDataHandler::_GetPunchReDCoSMessage() RS decoding failed with exception: " + str(err))

            if correctedData is not None and RSCoderLora.check(correctedData):
                LoraRadioDataHandler.WiRocLogger.info(
                    "LoraRadioDataHandler::_GetPunchReDCoSMessage() Decoded, corrected data correctly it seems")
                correctedData.extend(messageDataToConsider[-LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes:])
                loraPunchMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(correctedData, rssiByte=rssiByteValue)
                self._CacheMessage(loraPunchMsg)
                self._removeBytesFromDataReceived(expectedMessageLength + self.RSSIByteCount)
                return loraPunchMsg
            else:
                LoraRadioDataHandler.WiRocLogger.info("LoraRadioDataHandler::_GetPunchReDCoSMessage() Could not decode correctly, try with erasures next")
                loraPunchMsg = self._GetPunchReDCoSMessageWithErasures(messageDataToConsider, rssiByteValue, erasures=erasures)
                if loraPunchMsg is None:
                    # Try using ReDCos to decode the message
                    loraPunchMsg2 = self._GetPunchUsingReDCoSDecoding(messageDataToConsider, rssiByteValue)
                    return loraPunchMsg2
                else:
                    return loraPunchMsg

    def _GetPunchDoubleMessageWithErasures(self, messageDataToConsider, rssiByteValue, erasures=None):
        loraMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(messageDataToConsider, rssiByte=rssiByteValue)
        erasures.extend(self._FindPunchDoubleErasures(loraMsg))
        if len(erasures) > 0:
            try:
                erasuresToUse = list(set(erasures))
                if len(erasuresToUse) >= LoraRadioMessagePunchDoubleRS.NoOfECCBytes:
                    erasuresToUse = erasuresToUse[0:LoraRadioMessagePunchRS.NoOfECCBytes]
                elif len(erasuresToUse) % 2 != 0:
                    # Odd number
                    numberOfErasuresToUse = len(erasuresToUse) - 1
                    erasuresToUse = erasuresToUse[0:numberOfErasuresToUse]

                LoraRadioDataHandler.WiRocLogger.debug("LoraRadioDataHandler::_GetPunchDoubleMessageWithErasures() ErasuresToUse: " + str(erasuresToUse) + " ")
                correctedData2 = RSCoderLora.decodeLong(messageDataToConsider, erasuresToUse)

                if not RSCoderLora.checkLong(correctedData2):
                    # for some reason sometimes decode just returns the corrupted message with no change
                    # and no exception thrown. So check the decoded message to make sure we don't return
                    # a message that is clearly wrong
                    LoraRadioDataHandler.WiRocLogger.debug("LoraRadioDataHandler::_GetPunchDoubleMessageWithErasures() Could not decode with erasures")
                    return None
                loraMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(correctedData2,
                                                                                   rssiByte=rssiByteValue)
                loraPunchMsg1, loraPunchMsg2 = self._GetPunchTupleFromPunchDouble(loraMsg)
                # Cache individual messages but remove the whole double message from data received
                self._CacheMessage(loraPunchMsg1)
                self._CacheMessage(loraPunchMsg2)
                self._removeBytesFromDataReceived(len(messageDataToConsider) + self.RSSIByteCount)
                return loraMsg
            except Exception as err2:
                LoraRadioDataHandler.WiRocLogger.error("LoraRadioDataHandler::_GetPunchDoubleMessageWithErasures() RS decoding failed also with erasures with exception: " + str(err2))
                return None
        else:
            LoraRadioDataHandler.WiRocLogger.error(
                "LoraRadioDataHandler::_GetPunchDoubleMessageWithErasures() No erasures found so could not decode")
            return None

    def _GetPunchDoubleReDCoSMessageWithErasures(self, messageDataToConsider, rssiByteValue, erasures=None):
        loraMsg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(messageDataToConsider, rssiByte=rssiByteValue)
        erasures.extend(self._FindReDCoSPunchDoubleErasures(loraMsg))
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

                LoraRadioDataHandler.WiRocLogger.debug("LoraRadioDataHandler::_GetPunchDoubleReDCoSMessageWithErasures() ErasuresToUse: " + str(erasuresToUse))
                correctedData2 = RSCoderLora.decodeLong(messageDataToConsiderWithoutCRC, erasuresToUse)

                if not RSCoderLora.checkLong(correctedData2):
                    # for some reason sometimes decode just returns the corrupted message with no change
                    # and no exception thrown. So check the decoded message to make sure we don't return
                    # a message that is clearly wrong
                    LoraRadioDataHandler.WiRocLogger.debug("LoraRadioDataHandler::_GetPunchDoubleReDCoSMessageWithErasures() Could not decode with erasures")
                    return None
                loraMsg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(correctedData2 + messageDataToConsider[-LoraRadioMessagePunchDoubleReDCoSRS.NoOfCRCBytes:],
                                                                                   rssiByte=rssiByteValue)
                loraPunchMsg1, loraPunchMsg2 = self._GetPunchReDCoSTupleFromPunchDouble(loraMsg)
                # Cache individual messages but remove the whole double message from data received
                self._CacheMessage(loraPunchMsg1)
                self._CacheMessage(loraPunchMsg2)
                self._removeBytesFromDataReceived(len(messageDataToConsider) + self.RSSIByteCount)
                return loraMsg
            except Exception as err2:
                LoraRadioDataHandler.WiRocLogger.error(
                    "LoraRadioDataHandler::_GetPunchDoubleReDCoSMessageWithErasures() RS decoding failed also with erasures with exception: " + str(err2))
                return None
        else:
            LoraRadioDataHandler.WiRocLogger.error(
                "LoraRadioDataHandler::_GetPunchDoubleMessageWithErasures() No erasures found so could not decode")
            return None

    def _GetPunchDoubleMessage(self, erasures=None):
        messageTypeToTry = LoraRadioMessageRS.MessageTypeSIPunchDouble
        expectedMessageLength = LoraRadioMessageRS.MessageLengths[messageTypeToTry]
        if len(self.DataReceived) < expectedMessageLength + self.RSSIByteCount:
            return None
        if erasures is None:
            erasures = []
        messageDataToConsider = self.DataReceived[0:expectedMessageLength]
        messageDataToConsider[LoraRadioMessageRS.H] = (messageDataToConsider[LoraRadioMessageRS.H] & ~LoraRadioMessageRS.MessageTypeBitMask) | messageTypeToTry
        rssiByteValue = self.DataReceived[expectedMessageLength] if self.RSSIByteCount == 1 else None

        if RSCoderLora.checkLong(messageDataToConsider):
            # everything checks out, message should be correct
            loraDoubleMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(messageDataToConsider,
                                                                               rssiByte=rssiByteValue)
            loraPunchMsg1, loraPunchMsg2 = self._GetPunchTupleFromPunchDouble(loraDoubleMsg)
            # Cache individual messages but remove the whole double message from data received
            self._CacheMessage(loraPunchMsg1)
            self._CacheMessage(loraPunchMsg2)
            self._removeBytesFromDataReceived(expectedMessageLength + self.RSSIByteCount)
            return loraDoubleMsg
        else:
            try:
                correctedData = RSCoderLora.decodeLong(messageDataToConsider)

                if RSCoderLora.checkLong(correctedData):
                    LoraRadioDataHandler.WiRocLogger.info(
                        "LoraRadioDataHandler::_GetPunchDoubleMessage() Decoded, corrected data correctly it seems")
                    loraPunchMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(correctedData,
                                                                                            rssiByte=rssiByteValue)
                    loraPunchMsg1, loraPunchMsg2 = self._GetPunchTupleFromPunchDouble(loraPunchMsg)
                    # Cache individual messages but remove the whole double message from data received
                    self._CacheMessage(loraPunchMsg1)
                    self._CacheMessage(loraPunchMsg2)
                    self._removeBytesFromDataReceived(expectedMessageLength + self.RSSIByteCount)
                    return loraPunchMsg
                else:
                    LoraRadioDataHandler.WiRocLogger.info(
                        "LoraRadioDataHandler::_GetPunchDoubleMessage() Could not decode correctly, try with erasures next")
                    loraPunchMsg = self._GetPunchDoubleMessageWithErasures(messageDataToConsider, rssiByteValue, erasures=erasures)
                    return loraPunchMsg
            except Exception as err:
                LoraRadioDataHandler.WiRocLogger.error(
                    "LoraRadioDataHandler::_GetPunchDoubleMessage() RS decoding failed with exception: " + str(err))
                loraPunchMsg = self._GetPunchDoubleMessageWithErasures(messageDataToConsider, rssiByteValue, erasures=erasures)
                return loraPunchMsg

    def _GetPunchDoubleReDCoSMessage(self, erasures=None):
        messageTypeToTry = LoraRadioMessageRS.MessageTypeSIPunchDoubleReDCoS
        expectedMessageLength = LoraRadioMessageRS.MessageLengths[messageTypeToTry]
        if len(self.DataReceived) < expectedMessageLength + self.RSSIByteCount:
            return None
        if erasures is None:
            erasures = []

        messageDataToConsider = LoraRadioMessagePunchDoubleReDCoSRS.DeInterleaveFromAirOrder(self.DataReceived[0:expectedMessageLength])
        messageDataToConsider[LoraRadioMessageRS.H] = (messageDataToConsider[LoraRadioMessageRS.H] & ~LoraRadioMessageRS.MessageTypeBitMask) | messageTypeToTry
        rssiByteValue = self.DataReceived[expectedMessageLength] if self.RSSIByteCount == 1 else None
        messageDataToConsiderWithoutCRC = messageDataToConsider[:-LoraRadioMessagePunchDoubleReDCoSRS.NoOfCRCBytes]

        if RSCoderLora.checkLong(messageDataToConsiderWithoutCRC):
            # everything checks out, message should be correct
            loraDoubleMsg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(messageDataToConsider,
                                                                               rssiByte=rssiByteValue)
            loraPunchMsg1, loraPunchMsg2 = self._GetPunchReDCoSTupleFromPunchDouble(loraDoubleMsg)
            # Cache individual messages but remove the whole double message from data received
            self._CacheMessage(loraPunchMsg1)
            self._CacheMessage(loraPunchMsg2)
            self._removeBytesFromDataReceived(expectedMessageLength + self.RSSIByteCount)
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
                    loraPunchMsg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(correctedData + messageDataToConsider[-LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes:],
                                                                                            rssiByte=rssiByteValue)
                    loraPunchMsg1, loraPunchMsg2 = self._GetPunchReDCoSTupleFromPunchDouble(loraPunchMsg)
                    # Cache individual messages but remove the whole double message from data received
                    self._CacheMessage(loraPunchMsg1)
                    self._CacheMessage(loraPunchMsg2)
                    self._removeBytesFromDataReceived(expectedMessageLength + self.RSSIByteCount)
                    return loraPunchMsg
                else:
                    LoraRadioDataHandler.WiRocLogger.info("LoraRadioDataHandler::_GetPunchDoubleReDCoSMessage() Could not decode correctly, try with erasures next")
                    loraPunchMsg = self._GetPunchDoubleReDCoSMessageWithErasures(messageDataToConsider, rssiByteValue, erasures=erasures)
                    if loraPunchMsg is None:
                        loraMsgWithErrors = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(messageDataToConsider, rssiByteValue)
                        alts, fixedValues, fixedErasures = self._GetPunchDoubleMessageAlternatives(loraMsgWithErrors)
                        for messageAlt in alts:
                            try:
                                correctedData = RSCoderLora.decodeLong(bytearray(messageAlt[:-LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes]))
                            except Exception as err:
                                LoraRadioDataHandler.WiRocLogger.debug(
                                    "LoraRadioDataHandler::_GetPunchDoubleReDCoSMessage() 2 RS decoding of messageAlt: " + str(messageAlt) + " failed with exception: " + str(err))

                            if correctedData is not None and RSCoderLora.checkLong(correctedData):
                                loraPunchMsg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(
                                    correctedData + messageDataToConsider[-LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes:],
                                    rssiByte=rssiByteValue)
                                loraPunchMsg1, loraPunchMsg2 = self._GetPunchReDCoSTupleFromPunchDouble(loraPunchMsg)
                                # Cache individual messages but remove the whole double message from data received
                                self._CacheMessage(loraPunchMsg1)
                                self._CacheMessage(loraPunchMsg2)
                                self._removeBytesFromDataReceived(expectedMessageLength + self.RSSIByteCount)
                                return loraPunchMsg
                            else:

                                loraPunchMsg3 = self._GetPunchDoubleReDCoSMessageWithErasures(bytearray(messageAlt), rssiByteValue, erasures=fixedErasures)
                                if loraPunchMsg3 is not None:
                                    LoraRadioDataHandler.WiRocLogger.info(
                                        "LoraRadioDataHandler::_GetPunchDoubleReDCoSMessage() DECODED one of the message alternatives decoded with erasures")
                                    return loraPunchMsg3

                        # The alternatives could not be decoded wihtout ReDCoS so try using ReDCos to decode the message
                        loraPunchMsg2 = self._GetPunchDoubleUsingReDCoSDecoding(messageDataToConsider, rssiByteValue)
                        return loraPunchMsg2
                    else:
                        LoraRadioDataHandler.WiRocLogger.info(
                            "LoraRadioDataHandler::_GetPunchDoubleReDCoSMessage() DECODED decoded with erasures")
                        return loraPunchMsg
            except Exception as err:
                LoraRadioDataHandler.WiRocLogger.error(
                    "LoraRadioDataHandler::_GetPunchDoubleReDCoSMessage() RS decoding failed with exception: " + str(err))
                loraPunchMsg = self._GetPunchDoubleReDCoSMessageWithErasures(messageDataToConsider, rssiByteValue, erasures=erasures)
                return loraPunchMsg

    def _GetAckMessage(self):
        messageTypeToTry = LoraRadioMessageRS.MessageTypeLoraAck
        expectedMessageLength = LoraRadioMessageRS.MessageLengths[messageTypeToTry]
        if len(self.DataReceived) < expectedMessageLength + self.RSSIByteCount:
            return None

        messageDataToConsider = self.DataReceived[0:expectedMessageLength]
        messageDataToConsider[LoraRadioMessageRS.H] = (messageDataToConsider[LoraRadioMessageRS.H] & ~LoraRadioMessageRS.MessageTypeBitMask) | messageTypeToTry
        LoraRadioDataHandler.WiRocLogger.debug(
            "LoraRadioDataHandler::_GetAckMessage() MessageDataToConsider: " + Utils.GetDataInHex(messageDataToConsider, logging.DEBUG))
        rssiByteValue = self.DataReceived[expectedMessageLength] if self.RSSIByteCount == 1 else None

        if RSCoderLora.check(messageDataToConsider):
            # everything checks out, message should be correct
            loraAckMsg = LoraRadioMessageCreator.GetAckMessageByFullMessageData(messageDataToConsider, rssiByte=rssiByteValue)
            self._removeBytesFromDataReceived(expectedMessageLength + self.RSSIByteCount)
            return loraAckMsg
        else:
            try:
                correctedData = RSCoderLora.decode(messageDataToConsider)
                if RSCoderLora.check(correctedData):
                    LoraRadioDataHandler.WiRocLogger.info(
                        "LoraRadioDataHandler::_GetAckMessage() Decoded, corrected data correctly it seems")
                    loraAckMsg = LoraRadioMessageCreator.GetAckMessageByFullMessageData(correctedData, rssiByte=rssiByteValue)
                    self._removeBytesFromDataReceived(expectedMessageLength + self.RSSIByteCount)
                    return loraAckMsg
                else:
                    LoraRadioDataHandler.WiRocLogger.debug("LoraRadioDataHandler::_GetAckMessage() Could not decode correctly")
            except Exception as err:
                LoraRadioDataHandler.WiRocLogger.error("LoraRadioDataHandler::_GetAckMessage() RS decoding failed with exception: " + str(err))

            scrambledAckMsg = LoraRadioMessageCreator.GetAckMessageByFullMessageData(messageDataToConsider, rssiByte=rssiByteValue)
            messageIdAcked = scrambledAckMsg.GetMessageIDThatIsAcked()
            if messageIdAcked == SettingsClass.GetMessageIDOfLastLoraMessageSent():
                # ID matches so must be correct ID. Error codes incorrect...
                scrambledAckMsg.GenerateAndAddRSCode()
                LoraRadioDataHandler.WiRocLogger.info("LoraRadioDataHandler::_GetAckMessage() MessageID matches last sent message so must be ECC that is wrong.")
                return scrambledAckMsg

            LoraRadioDataHandler.WiRocLogger.error("LoraRadioDataHandler::_GetAckMessage() No message could be decoded")
            return None

    def _GetStatusMessage(self):
        messageTypeToTry = LoraRadioMessageRS.MessageTypeStatus
        expectedMessageLength = LoraRadioMessageRS.MessageLengths[messageTypeToTry]
        if len(self.DataReceived) < expectedMessageLength + self.RSSIByteCount:
            return None

        messageDataToConsider = self.DataReceived[0:expectedMessageLength]
        messageDataToConsider[LoraRadioMessageRS.H] = (messageDataToConsider[LoraRadioMessageRS.H] & ~LoraRadioMessageRS.MessageTypeBitMask) | messageTypeToTry
        LoraRadioDataHandler.WiRocLogger.debug(
            "LoraRadioDataHandler::_GetStatusMessage() MessageDataToConsider: " + Utils.GetDataInHex(messageDataToConsider,
                                                                                                  logging.DEBUG))
        rssiByteValue = self.DataReceived[expectedMessageLength] if self.RSSIByteCount == 1 else None

        if RSCoderLora.check(messageDataToConsider):
            # everything checks out, message should be correct
            loraStatusMsg = LoraRadioMessageCreator.GetStatusMessageByFullMessageData(messageDataToConsider, rssiByte=rssiByteValue)
            self._removeBytesFromDataReceived(expectedMessageLength + self.RSSIByteCount)
            return loraStatusMsg
        else:
            try:
                correctedData = RSCoderLora.decode(messageDataToConsider)
                if RSCoderLora.check(correctedData):
                    LoraRadioDataHandler.WiRocLogger.info(
                        "LoraRadioDataHandler::_GetStatusMessage() Decoded, corrected data correctly it seems")
                    loraStatusMsg = LoraRadioMessageCreator.GetStatusMessageByFullMessageData(correctedData, rssiByte=rssiByteValue)
                    self._removeBytesFromDataReceived(expectedMessageLength + self.RSSIByteCount)
                    return loraStatusMsg
                else:
                    LoraRadioDataHandler.WiRocLogger.info(
                        "LoraRadioDataHandler::_GetStatusMessage() Could not decode correctly")
                    LoraRadioDataHandler.WiRocLogger.error(
                        "LoraRadioDataHandler::_GetStatusMessage() No message could be decoded")
                    return None
            except Exception as err:
                LoraRadioDataHandler.WiRocLogger.error(
                    "LoraRadioDataHandler::_GetStatusMessage() RS decoding failed with exception: " + str(err))
                LoraRadioDataHandler.WiRocLogger.error(
                    "LoraRadioDataHandler::_GetStatusMessage() No message could be decoded")
                return None

    def _GetMessageTypesByLength(self):
        expectedMessageLengths = [LoraRadioMessageRS.MessageLengths[idx] + self.RSSIByteCount for idx in
                                  LoraRadioDataHandler.MessageTypesExpected]
        messageTypesByLength = []
        for idx, msgLength in enumerate(expectedMessageLengths):
            if len(self.DataReceived) == msgLength:
                messageTypeByLength = LoraRadioDataHandler.MessageTypesExpected[idx]
                messageTypesByLength.append(messageTypeByLength)
        return messageTypesByLength

    def _GetLikelyMessageTypes(self):
        messageTypes = []
        headerMessageType = LoraRadioDataHandler.GetHeaderMessageType(self.DataReceived)
        if headerMessageType in LoraRadioDataHandler.MessageTypesExpected:
            expectedMessageLength = LoraRadioMessageRS.MessageLengths[headerMessageType] + self.RSSIByteCount
            if len(self.DataReceived) == expectedMessageLength:
                messageTypes.append(headerMessageType)
            elif len(self.DataReceived) > expectedMessageLength:
                messageTypes.append(headerMessageType)

        messageTypesByLength = self._GetMessageTypesByLength()
        for messageTypeByLength in messageTypesByLength:
            if messageTypeByLength not in messageTypes:
                messageTypes.append(messageTypeByLength)

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

    def _TryGetMessage(self):
        if not self._IsLongEnoughToBeMessage():
            return None

        self._CheckAndRemoveLoraModuleRXError()

        if not self._IsLongEnoughToBeMessage():
            return None

        messageTypes = self._GetLikelyMessageTypes()
        LoraRadioDataHandler.WiRocLogger.debug("LoraRadioDataHandler::_TryGetMessage() MessageTypes: " + str(messageTypes))

        for messageType in messageTypes:
            LoraRadioDataHandler.WiRocLogger.debug("LoraRadioDataHandler::_TryGetMessage() Message type to try: " + str(messageType))
            if messageType == LoraRadioMessageRS.MessageTypeSIPunch:
                loraPunchMessage = self._GetPunchMessage()
                if loraPunchMessage is not None:
                    return loraPunchMessage
            elif messageType == LoraRadioMessageRS.MessageTypeLoraAck:
                loraAckMessage = self._GetAckMessage()
                if loraAckMessage is not None:
                    return loraAckMessage
            elif messageType == LoraRadioMessageRS.MessageTypeStatus:
                loraStatusMessage = self._GetStatusMessage()
                if loraStatusMessage is not None:
                    return loraStatusMessage
            elif messageType == LoraRadioMessageRS.MessageTypeSIPunchDouble:
                loraPunchDoubleMessage = self._GetPunchDoubleMessage()
                if loraPunchDoubleMessage is not None:
                    return loraPunchDoubleMessage
            elif messageType == LoraRadioMessageRS.MessageTypeSIPunchReDCoS:
                loraPunchMessage = self._GetPunchReDCoSMessage()
                if loraPunchMessage is not None:
                    return loraPunchMessage
            elif messageType == LoraRadioMessageRS.MessageTypeSIPunchDoubleReDCoS:
                loraPunchDoubleMessage = self._GetPunchDoubleReDCoSMessage()
                if loraPunchDoubleMessage is not None:
                    return loraPunchDoubleMessage
            else:
                pass

        return None

    # Call GetMessage only when you believe you might have a message
    def GetMessage(self):
        LoraRadioDataHandler.WiRocLogger.debug("Data considered (airorder): " + Utils.GetDataInHex(self.DataReceived, logging.DEBUG))
        message = self._TryGetMessage()
        if message is not None:
            return message

        self.ClearDataReceived()
        return None
