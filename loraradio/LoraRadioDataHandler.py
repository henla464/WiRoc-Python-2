__author__ = 'henla464'

import logging
import time

from loraradio.LoraRadioMessageAndMetadata import LoraRadioMessageAndMetadata
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from loraradio.LoraRadioMessageRS import LoraRadioMessageRS
from loraradio.RSCoderLora import RSCoderLora
from utils.utils import Utils
from collections.abc import Iterable

class LoraRadioDataHandler(object):
    WiRocLogger = logging.getLogger('WiRoc')
    MessageTypesExpected = [3, 4, 5, 6]
    RSSIByteCount = 0

    def __init__(self, rssiByteExpected):
        self.DataReceived = bytearray()
        self.LikelyStartOfMessageIndex = []
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

    def _RemoveMessageFromDataReceived(self, loraMsg):
        # remove the bytes belonging to this lora message from DataReceived
        self.DataReceived = self.DataReceived[len(loraMsg.GetByteArray()) + self.RSSIByteCount:]

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

            cardNoByteArray = loraMsg.GetSICardNoByteArray()[0:4]
            cardNo = Utils.toInt(cardNoByteArray)
            if cardNo > 0x4FFFF and cardNo < 500000: #500 000 = 0x7A120
                erasures.append(3) # at least CN2 should be wrong
            if cardNoByteArray[0] != 0x00: # CN3 not currently used so should always be 0
                erasures.append(2)
            if controlNumberToUse != controlNumber:
                # bit CN1 bit8 of stationcode/controlnumber is almost certainly wrong
                erasures.append(6)
            elif self.LastPunchMessage.GetFourWeekCounter() != loraMsg.GetFourWeekCounter():
                erasures.append(6)
            elif self.LastPunchMessage.GetDayOfWeek() != loraMsg.GetDayOfWeek():
                erasures.append(6)
            elif self.LastPunchMessage.GetTwentyFourHour() == 0 and loraMsg.GetTwentyFourHour() == 1 \
                    and loraMsg.GetTwelveHourTimerAsInt() > 20 * 60:
                erasures.append(6)
            elif self.LastPunchMessage.GetTwentyFourHour() == 1 and loraMsg.GetTwentyFourHour() == 0 \
                    and loraMsg.GetTwelveHourTimerAsInt() > 20 * 60:
                erasures.append(6)

            # check that TH isn't higher than possible
            if loraMsg.GetTwelveHourTimer()[0] > 0xA8:
                erasures.append(7)

            if self.LastPunchMessage.GetTwentyFourHour() == loraMsg.GetTwentyFourHour():
                noOfSecondsSinceLastMessage = int(time.monotonic() - self.LastPunchMessageTime)
                # print("noOfSecondsSinceLastMessage: " + str(noOfSecondsSinceLastMessage))
                lowestTimeWeAssumeCanBeCorrect = self.LastPunchMessage.GetTwelveHourTimerAsInt()
                # print("lowestTimeWeAssumeCanBeCorrect: " + str(lowestTimeWeAssumeCanBeCorrect))
                # Assuming a delay of delivery of a message of max 5 minutes
                highestTimeWeAssumeCanBeCorrect = self.LastPunchMessage.GetTwelveHourTimerAsInt() \
                    + noOfSecondsSinceLastMessage + 5 * 60
                #print("highestTimeWeAssumeCanBeCorrect: " + str(highestTimeWeAssumeCanBeCorrect))
                #print("theTimeInTheMessage: " + str(loraMsg.GetTwelveHourTimerAsInt()))
                if loraMsg.GetTwelveHourTimerAsInt() < lowestTimeWeAssumeCanBeCorrect:
                    if loraMsg.GetTwelveHourTimer()[0] != self.LastPunchMessage.GetTwelveHourTimer()[0]:
                        # TH differs so this must be the reason for time being too low
                        erasures.append(7)
                    else:
                        erasures.append(8)
                elif loraMsg.GetTwelveHourTimerAsInt() > highestTimeWeAssumeCanBeCorrect:
                    # only an increase in TL can't make it higher than highestTimeWeAssumeCanBeCorrect
                    erasures.append(7)

                # check that TL isn't higher than possible. Only check when TH is highest value and not believed
                # to be wrong
                if loraMsg.GetTwelveHourTimer()[0] == 0xA8 and loraMsg.GetTwelveHourTimer()[1] > 0xC0 \
                        and 7 not in erasures:
                    erasures.append(8)
        else:
            # technically it could be CN1 bit 8 that is wrong, but since higher number than 255 is almost never used
            # it is extremely unlikely. The oldest SI cards don't even support > 255.
            erasures.append(1)

        LoraRadioDataHandler.WiRocLogger.debug(
            "LoraRadioDataHandler::FindPunchErasures " + str(len(erasures)) + " erasures found. " + str(erasures))
        return list(set(erasures))

    def _GetPunchTupleFromPunchDouble(self, loraDoubleMsg):
        payload = loraDoubleMsg.GetByteArray()
        loraMsgLength = LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunch]
        # recreate two message arrays and find the erasures for each
        firstMsgByteArray = payload[0:loraMsgLength - 4] + bytearray(bytes([0x00, 0x00, 0x00, 0x00]))
        firstMsgByteArray[0] = (firstMsgByteArray[0] & 0xE0) | LoraRadioMessageRS.MessageTypeSIPunch
        secondMsgByteArray = firstMsgByteArray[0:1] + payload[loraMsgLength - 4:loraMsgLength + loraMsgLength - 9] + bytearray(
            bytes([0x00, 0x00, 0x00, 0x00]))
        loraPMsg1 = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(firstMsgByteArray)
        loraPMsg2 = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(secondMsgByteArray)
        return loraPMsg1, loraPMsg2

    def _FindPunchDoubleErasures(self, loraDoubleMsg):
        loraPMsg1, loraPMsg2 = self._GetPunchTupleFromPunchDouble(loraDoubleMsg)
        erasures1 = self._FindPunchErasures(loraPMsg1)
        print("erasures 1: " + str(erasures1))
        erasures2 = self._FindPunchErasures(loraPMsg2)
        print("erasures 2: " + str(erasures2))
        for i in range(len(erasures2)):
            if erasures2[i] == 0:
                # if the header is wrong it is already added in erasures1.
                erasures2.pop(i)
            # Add the length of the first part of the double message minus the RSCodes (2) minus the header of the second
            loraMsgLength = LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunch]
            erasures2[i] += loraMsgLength-5
        erasures1.extend(erasures2)
        LoraRadioDataHandler.WiRocLogger.debug(
            "LoraRadioDataHandler::_FindPunchDoubleErasures " + str(len(erasures1)) + " erasures found. " + str(erasures1))
        return erasures1

    def _CheckAndRemoveLoraModuleRXError(self):
        if len(self.DataReceived) >= 10:
            if self.DataReceived[0:10] == bytearray('rx error\r\n'.encode('latin-1')):
                LoraRadioDataHandler.WiRocLogger.debug(
                    "LoraRadioDataHandler::CheckAndRemoveLoraModuleRXError 'rx error' returned by module")
                self.RxError = True
                self.DataReceived = self.DataReceived[10:]
                for i in range(len(self.LikelyStartOfMessageIndex)):
                    self.LikelyStartOfMessageIndex[i] -= 10
                for i in range(len(self.LikelyStartOfMessageIndex)):
                    if self.LikelyStartOfMessageIndex[i] <= 0:
                        self.LikelyStartOfMessageIndex.pop(i)

    def _GetPunchMessageWithErasures(self, messageDataToConsider, rssiByteValue, erasures=None):
        loraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(messageDataToConsider,
                                                                           rssiByte=rssiByteValue)
        print("erasures: " + str(erasures))
        erasures.extend(self._FindPunchErasures(loraMsg))
        if len(erasures) > 0:
            try:
                # erasures.extend(bytearray(bytes([0x01]))) # todo: remove this, this is just for testing
                erasuresToUse = list(set(erasures))
                if len(erasuresToUse) >= 4:
                    erasuresToUse = erasuresToUse[0:4]
                elif len(erasuresToUse) >= 2:
                    erasuresToUse = erasuresToUse[0:2]
                else:
                    erasuresToUse = []
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
                self._RemoveMessageFromDataReceived(loraMsg)
                return loraMsg
            except Exception as err2:
                LoraRadioDataHandler.WiRocLogger.error(
                    "LoraRadioDataHandler::_GetPunchMessageWithErasures() RS decoding failed also with erasures with exception: " + str(
                        err2))
                return None
        else:
            LoraRadioDataHandler.WiRocLogger.error(
                "LoraRadioDataHandler::GetPunchMessage() No erasures found so could not decode")
            return None

    def _GetPunchMessage(self, erasures=None):
        messageTypeToTry = LoraRadioMessageRS.MessageTypeSIPunch
        expectedMessageLength = LoraRadioMessageRS.MessageLengths[messageTypeToTry]
        if len(self.DataReceived) < expectedMessageLength + self.RSSIByteCount:
            return None
        if erasures is None:
            erasures = []

        messageDataToConsider = self.DataReceived[0:expectedMessageLength]
        messageDataToConsider[0] = (messageDataToConsider[0] & 0xE0) | messageTypeToTry
        rssiByteValue = self.DataReceived[expectedMessageLength] if self.RSSIByteCount == 1 else None

        if RSCoderLora.check(messageDataToConsider):
            # everything checks out, message should be correct
            loraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(messageDataToConsider, rssiByte=rssiByteValue)
            self._CacheMessage(loraMsg)
            self._RemoveMessageFromDataReceived(loraMsg)
            return loraMsg
        else:
            try:
                #print("messageDataToConsider: " + Utils.GetDataInHex(messageDataToConsider, logging.DEBUG))

                correctedData = RSCoderLora.decode(messageDataToConsider)

                if RSCoderLora.check(correctedData):
                    LoraRadioDataHandler.WiRocLogger.info(
                        "LoraRadioDataHandler::_GetPunchMessage() Decoded, corrected data correctly it seems")
                    loraPunchMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(correctedData, rssiByte=rssiByteValue)
                    self._CacheMessage(loraPunchMsg)
                    self._RemoveMessageFromDataReceived(loraPunchMsg)
                    return loraPunchMsg
                else:
                    LoraRadioDataHandler.WiRocLogger.info(
                        "LoraRadioDataHandler::_GetPunchMessage() Could not decode correctly, try with erasures next")
                    loraPunchMsg = self._GetPunchMessageWithErasures(messageDataToConsider, rssiByteValue,
                                                                     erasures=erasures)
                    return loraPunchMsg
            except Exception as err:
                LoraRadioDataHandler.WiRocLogger.error(
                    "LoraRadioDataHandler::GetPunchMessage() RS decoding failed with exception: " + str(err))
                loraPunchMsg = self._GetPunchMessageWithErasures(messageDataToConsider, rssiByteValue, erasures=erasures)
                return loraPunchMsg

    def _GetPunchDoubleMessageWithErasures(self, messageDataToConsider, rssiByteValue, erasures=None):
        loraMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(messageDataToConsider,
                                                                           rssiByte=rssiByteValue)
        erasures.extend(self._FindPunchDoubleErasures(loraMsg))
        if len(erasures) > 0:
            try:
                # erasures.extend(bytearray(bytes([0x01]))) # todo: remove this, this is just for testing
                erasuresToUse = list(set(erasures))
                if len(erasuresToUse) >= 8:
                    erasuresToUse = erasuresToUse[0:8]
                elif len(erasuresToUse) >= 6:
                    erasuresToUse = erasuresToUse[0:6]
                elif len(erasuresToUse) >= 4:
                    erasuresToUse = erasuresToUse[0:4]
                elif len(erasuresToUse) >= 2:
                    erasuresToUse = erasuresToUse[0:2]
                else:
                    erasuresToUse = []
                print("lasdfk laksfdjkla klasjdf "+ str(erasuresToUse))
                print("LoraRadioDataHandler::_GetPunchDoubleMessageWithErasures() ErasuresToUse: " + str(erasuresToUse))
                correctedData2 = RSCoderLora.decodeLong(messageDataToConsider, erasuresToUse)
                print("LoraRadioDataHandler::_GetPunchDoubleMessageWithErasures() CorrectedData2: " + Utils.GetDataInHex(correctedData2, logging.DEBUG))

                if not RSCoderLora.checkLong(correctedData2):
                    # for some reason sometimes decode just returns the corrupted message with not change
                    # and no exception thrown. So check the decoded message to make sure we dont return
                    # a message that is clearly wrong
                    return None
                loraMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(correctedData2,
                                                                                   rssiByte=rssiByteValue)
                loraPunchMsg1, loraPunchMsg2 = self._GetPunchTupleFromPunchDouble(loraMsg)
                # Cache individual messages but remove the whole double message from data received
                self._CacheMessage(loraPunchMsg1)
                self._CacheMessage(loraPunchMsg2)
                self._RemoveMessageFromDataReceived(loraMsg)
                return loraMsg
            except Exception as err2:
                LoraRadioDataHandler.WiRocLogger.error(
                    "LoraRadioDataHandler::_GetPunchDoubleMessageWithErasures() RS decoding failed also with erasures with exception: " + str(
                        err2))
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
        messageDataToConsider[0] = (messageDataToConsider[0] & 0xE0) | messageTypeToTry
        rssiByteValue = self.DataReceived[expectedMessageLength] if self.RSSIByteCount == 1 else None

        if RSCoderLora.checkLong(messageDataToConsider):
            # everything checks out, message should be correct
            loraDoubleMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(messageDataToConsider,
                                                                               rssiByte=rssiByteValue)
            loraPunchMsg1, loraPunchMsg2 = self._GetPunchTupleFromPunchDouble(loraDoubleMsg)
            # Cache individual messages but remove the whole double message from data received
            self._CacheMessage(loraPunchMsg1)
            self._CacheMessage(loraPunchMsg2)
            self._RemoveMessageFromDataReceived(loraDoubleMsg)
            return loraDoubleMsg
        else:
            try:
                #print("messageDataToConsider: " + str(messageDataToConsider))

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
                    self._RemoveMessageFromDataReceived(loraPunchMsg)
                    return loraPunchMsg
                else:
                    LoraRadioDataHandler.WiRocLogger.info(
                        "LoraRadioDataHandler::_GetPunchDoubleMessage() Could not decode correctly, try with erasures next")
                    loraPunchMsg = self._GetPunchDoubleMessageWithErasures(messageDataToConsider, rssiByteValue,
                                                                     erasures=erasures)
                    return loraPunchMsg
            except Exception as err:
                LoraRadioDataHandler.WiRocLogger.error(
                    "LoraRadioDataHandler::_GetPunchDoubleMessage() RS decoding failed with exception: " + str(err))
                loraPunchMsg = self._GetPunchDoubleMessageWithErasures(messageDataToConsider, rssiByteValue,
                                                                 erasures=erasures)
                return loraPunchMsg

    def _GetAckMessage(self, erasures=None):
        messageTypeToTry = LoraRadioMessageRS.MessageTypeLoraAck
        expectedMessageLength = LoraRadioMessageRS.MessageLengths[messageTypeToTry]
        if len(self.DataReceived) < expectedMessageLength + self.RSSIByteCount:
            return None

        messageDataToConsider = self.DataReceived[0:expectedMessageLength]
        messageDataToConsider[0] = (messageDataToConsider[0] & 0xE0) | messageTypeToTry
        LoraRadioDataHandler.WiRocLogger.debug(
            "LoraRadioDataHandler::_GetAckMessage() MessageDataToConsider: " + Utils.GetDataInHex(messageDataToConsider,
                                                                                                  logging.DEBUG))
        rssiByteValue = self.DataReceived[expectedMessageLength] if self.RSSIByteCount == 1 else None

        if RSCoderLora.check(messageDataToConsider):
            # everything checks out, message should be correct
            loraAckMsg = LoraRadioMessageCreator.GetAckMessageByFullMessageData(messageDataToConsider, rssiByte=rssiByteValue)
            self._RemoveMessageFromDataReceived(loraAckMsg)
            return loraAckMsg
        else:
            try:
                correctedData = RSCoderLora.decode(messageDataToConsider)
                if RSCoderLora.check(correctedData):
                    LoraRadioDataHandler.WiRocLogger.info(
                        "LoraRadioDataHandler::_GetAckMessage() Decoded, corrected data correctly it seems")
                    loraAckMsg = LoraRadioMessageCreator.GetAckMessageByFullMessageData(correctedData, rssiByte=rssiByteValue)
                    self._RemoveMessageFromDataReceived(loraAckMsg)
                    return loraAckMsg
                else:
                    LoraRadioDataHandler.WiRocLogger.info(
                        "LoraRadioDataHandler::_GetAckMessage() Could not decode correctly")
                    LoraRadioDataHandler.WiRocLogger.error(
                        "LoraRadioDataHandler::_GetAckMessage() No message could be decoded")
                    return None
            except Exception as err:
                LoraRadioDataHandler.WiRocLogger.error(
                    "LoraRadioDataHandler::_GetAckMessage() RS decoding failed with exception: " + str(err))
                LoraRadioDataHandler.WiRocLogger.error(
                    "LoraRadioDataHandler::_GetAckMessage() No message could be decoded")
                return None

    def _GetStatusMessage(self, erasures=None):
        messageTypeToTry = LoraRadioMessageRS.MessageTypeStatus
        expectedMessageLength = LoraRadioMessageRS.MessageLengths[messageTypeToTry]
        if len(self.DataReceived) < expectedMessageLength + self.RSSIByteCount:
            return None

        messageDataToConsider = self.DataReceived[0:expectedMessageLength]
        messageDataToConsider[0] = (messageDataToConsider[0] & 0xE0) | messageTypeToTry
        LoraRadioDataHandler.WiRocLogger.debug(
            "LoraRadioDataHandler::_GetAckMessage() MessageDataToConsider: " + Utils.GetDataInHex(messageDataToConsider,
                                                                                                  logging.DEBUG))
        rssiByteValue = self.DataReceived[expectedMessageLength] if self.RSSIByteCount == 1 else None

        if RSCoderLora.check(messageDataToConsider):
            # everything checks out, message should be correct
            loraStatusMsg = LoraRadioMessageCreator.GetStatusMessageByFullMessageData(messageDataToConsider, rssiByte=rssiByteValue)
            return loraStatusMsg
        else:
            try:
                correctedData = RSCoderLora.decode(messageDataToConsider)
                if RSCoderLora.check(correctedData):
                    LoraRadioDataHandler.WiRocLogger.info(
                        "LoraRadioDataHandler::_GetStatusMessage() Decoded, corrected data correctly it seems")
                    loraStatusMsg = LoraRadioMessageCreator.GetStatusMessageByFullMessageData(correctedData, rssiByte=rssiByteValue)
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


    def _GetMessageTypeByLength(self):
        expectedMessageLengths = [LoraRadioMessageRS.MessageLengths[idx] + self.RSSIByteCount for idx in
                                  LoraRadioDataHandler.MessageTypesExpected]
        #print("expectedMessageLengths: " + str(expectedMessageLengths))
        #print("length of datareceived: " + str(len(self.DataReceived)))
        if len(self.DataReceived) in expectedMessageLengths:
            indexwithinMessageTypesExpected = expectedMessageLengths.index(
                len(self.DataReceived))
            messageTypeByLength = LoraRadioDataHandler.MessageTypesExpected[
                indexwithinMessageTypesExpected]
            return messageTypeByLength

    def _GetLikelyMessageTypes(self):
        messageTypes = []
        headerMessageType = LoraRadioDataHandler.GetHeaderMessageType(self.DataReceived)
        #print(headerMessageType)
        if headerMessageType in LoraRadioDataHandler.MessageTypesExpected:
            expectedMessageLength = LoraRadioMessageRS.MessageLengths[headerMessageType] + self.RSSIByteCount
            if len(self.DataReceived) == expectedMessageLength:
                messageTypes.append(headerMessageType)
            elif len(self.DataReceived) > expectedMessageLength:
                messageTypes.append(headerMessageType)

                messageTypeByLength = self._GetMessageTypeByLength()
                if messageTypeByLength is not None:
                    messageTypes.append(messageTypeByLength)
            else:
                # shorter than the header message type
                messageTypeByLength = self._GetMessageTypeByLength()
                if messageTypeByLength is not None:
                    messageTypes.append(messageTypeByLength)
        else:
            messageTypeByLength = self._GetMessageTypeByLength()
            if messageTypeByLength is not None:
                messageTypes.append(messageTypeByLength)

        return messageTypes

    @staticmethod
    def GetHeaderMessageType(messageData):
        if len(messageData) < 1:
            return -1
        headerMessageType = messageData[0] & 0x1F
        return headerMessageType

    @staticmethod
    def GetRepeater(messageData):
        repeater = (messageData[0] & 0x20) > 0
        return repeater

    @staticmethod
    def GetAckRequested(messageData):
        ackReq = (messageData[0] & 0x80) > 0
        return ackReq

    def _RemoveLikelyMessage(self):
        headerMessageType = LoraRadioDataHandler.GetHeaderMessageType(self.DataReceived)
        expectedMessageLength = LoraRadioMessageRS.MessageLengths[headerMessageType] + self.RSSIByteCount if headerMessageType < len(LoraRadioMessageRS.MessageLengths) else -1
        if len(self.DataReceived) == expectedMessageLength:
            LoraRadioDataHandler.WiRocLogger.debug(
                "LoraRadioDataHandler::_RemoveLikelyMessage() The message length match the header message type, but could not be decoded. Discard it")
            self.DataReceived = self.DataReceived[expectedMessageLength:]
            return True
        else:
            expectedMessageLengths = [LoraRadioMessageRS.MessageLengths[idx] + self.RSSIByteCount for idx in
                                      LoraRadioDataHandler.MessageTypesExpected]
            #print("len datarec:" + str(len(self.DataReceived)))
            if len(self.DataReceived) > max(expectedMessageLengths):
                LoraRadioDataHandler.WiRocLogger.debug(
                    "LoraRadioDataHandler::_RemoveLikelyMessage() Too many bytes for a single message. We should remove one likely message.")
                if len(self.LikelyStartOfMessageIndex) > 0:
                    likelyStartOfNextMessage = self.LikelyStartOfMessageIndex.pop(0)
                    LoraRadioDataHandler.WiRocLogger.debug(
                        "LoraRadioDataHandler::_RemoveLikelyMessage() Likely start of next message: " + str(likelyStartOfNextMessage))
                    if likelyStartOfNextMessage < len(self.DataReceived):
                        self.DataReceived = self.DataReceived[likelyStartOfNextMessage:]
                        for i in range(len(self.LikelyStartOfMessageIndex)):
                            self.LikelyStartOfMessageIndex[i] -= likelyStartOfNextMessage
                    else:
                        self.DataReceived = bytearray()
                        self.LikelyStartOfMessageIndex = []
                else:
                    LoraRadioDataHandler.WiRocLogger.debug(
                        "LoraRadioDataHandler::_RemoveLikelyMessage() no likely message starts so reset DataReceived")
                    self.DataReceived = bytearray()
                    self.LikelyStartOfMessageIndex = []
                return True
        return False

    def _TryGetMessage(self):
        if not self._IsLongEnoughToBeMessage():
            return None

        self._CheckAndRemoveLoraModuleRXError()

        if not self._IsLongEnoughToBeMessage():
            return None
        print("After remove RX Error, after check long enough: " + Utils.GetDataInHex(self.DataReceived, logging.DEBUG))

        messageTypes = self._GetLikelyMessageTypes()
        print("MessageTypes: " + str(messageTypes))

        for messageType in messageTypes:
            if messageType == LoraRadioMessageRS.MessageTypeSIPunch:
                print("messagetypetotry: " + str(messageType))
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
            else:
                pass

        return None

    # Call GetMessage only when you believe you might have a message
    def GetMessage(self):
        self.LikelyStartOfMessageIndex.append(len(self.DataReceived))
        print("Data considered: " + Utils.GetDataInHex(self.DataReceived, logging.DEBUG))
        firstTimeOrMessageRemoved = True
        while firstTimeOrMessageRemoved:
            message = self._TryGetMessage()
            if message is not None:
                return message
            firstTimeOrMessageRemoved = self._RemoveLikelyMessage()

        return None

# Set likely message boundaries (with separate function?)
# remove data that cannot be decoded