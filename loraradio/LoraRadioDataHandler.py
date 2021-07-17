__author__ = 'henla464'

import logging
import time

from loraradio.LoraRadioMessageAndMetadata import LoraRadioMessageAndMetadata
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from loraradio.LoraRadioMessageRS import LoraRadioMessageRS
from loraradio.RSCoderLora import RSCoderLora
from utils.utils import Utils


class LoraRadioDataHandler(object):
    WiRocLogger = logging.getLogger('WiRoc')
    MessageTypesExpected = [3, 4, 5]
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

    def AddData(self, dataByte):
        self.DataReceived.extend(dataByte)

    def _IsLongEnoughToBeMessage(self):
        return len(self.DataReceived) >= min(LoraRadioMessageRS.MessageLengths) + self.RSSIByteCount

    def _CacheMessage(self, loraMsg):
        controlNumber = loraMsg.GetControlNumber()
        msgAndMetadata = LoraRadioMessageAndMetadata(loraMsg)
        self.ReceivedPunchMessageDict[controlNumber] = msgAndMetadata
        self.LastPunchMessageTime = msgAndMetadata.GetTimeCreated()
        self.LastPunchMessage = loraMsg
        self.RxError = False
        # remove the bytes belonging to this lora message from DataReceived
        self.DataReceived = self.DataReceived[len(loraMsg.GetByteArray()):]

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
                    and loraMsg.GetTwelveHourTimerAsInt > 20 * 60:
                erasures.append(6)
            elif self.LastPunchMessage.GetTwentyFourHour() == 1 and loraMsg.GetTwentyFourHour() == 0 \
                    and loraMsg.GetTwelveHourTimerAsInt > 20 * 60:
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
                # print("highestTimeWeAssumeCanBeCorrect: " + str(highestTimeWeAssumeCanBeCorrect))
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
                print("Erasures to use: " + str(erasuresToUse))
                LoraRadioDataHandler.WiRocLogger.debug(
                    "LoraRadioDataHandler::_GetPunchMessageWithErasures() ErasuresToUse: " + Utils.GetDataInHex(erasuresToUse, logging.debug))
                correctedData2 = RSCoderLora.decode(messageDataToConsider, erasuresToUse)
                if not RSCoderLora.check(correctedData2):
                    # for some reason sometimes decode just returnes the corrupted message with not change
                    # and no exception thrown. So check the decoded message to make sure we dont return
                    # a message that is clearly wrong
                    return None
                loraMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(correctedData2,
                                                                                   rssiByte=rssiByteValue)
                self._CacheMessage(loraMsg)
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

    def _GetPunchMessage(self, messageTypeToTry, erasures=None):
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
            return loraMsg
        else:
            try:
                print("messageDataToConsider: " + str(messageDataToConsider))
                if not RSCoderLora.check(messageDataToConsider):
                    print("Error Check 1")
                correctedData = RSCoderLora.decode(messageDataToConsider)

                if RSCoderLora.check(correctedData):
                    LoraRadioDataHandler.WiRocLogger.info(
                        "LoraRadioDataHandler::_GetPunchMessage() Decoded, corrected data correctly it seems")
                    loraPunchMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(correctedData, rssiByte=rssiByteValue)
                    self._CacheMessage(loraPunchMsg)
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

    def _GetAckMessage(self, messageTypeToTry, erasures=None):
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
            return loraAckMsg
        else:
            try:
                correctedData = RSCoderLora.decode(messageDataToConsider)
                if RSCoderLora.check(correctedData):
                    LoraRadioDataHandler.WiRocLogger.info(
                        "LoraRadioDataHandler::_GetAckMessage() Decoded, corrected data correctly it seems")
                    loraAckMsg = LoraRadioMessageCreator.GetAckMessageByFullMessageData(correctedData, rssiByte=rssiByteValue)
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

    def _GetStatusMessage(self, messageTypeToTry, erasures=None):
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
        if len(self.DataReceived) in expectedMessageLengths:
            indexwithinMessageTypesExpected = expectedMessageLengths.index(
                len(self.DataReceived))
            messageTypeByLength = LoraRadioDataHandler.MessageTypesExpected[
                indexwithinMessageTypesExpected]
            return messageTypeByLength

    def _GetLikelyMessageTypes(self):
        messageTypes = []
        headerMessageType = LoraRadioDataHandler.GetHeaderMessageType(self.DataReceived)
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
        expectedMessageLength = LoraRadioMessageRS.MessageLengths[headerMessageType]
        if len(self.DataReceived) == expectedMessageLength:
            # the message length match the header message type, but could not be decoded
            # discard it
            self.DataReceived = self.DataReceived[expectedMessageLength:]
            return True
        else:
            expectedMessageLengths = [LoraRadioMessageRS.MessageLengths[idx] + self.RSSIByteCount for idx in
                                      LoraRadioDataHandler.MessageTypesExpected]
            if len(self.DataReceived) > max(expectedMessageLengths):
                # too many bytes for a single message. We should remove one likely message
                likelyStartOfNextMessage = self.LikelyStartOfMessageIndex.pop(0)
                LoraRadioDataHandler.DataReceived = LoraRadioDataHandler.DataReceived[likelyStartOfNextMessage:]
                for i in range(len(self.LikelyStartOfMessageIndex)):
                    self.LikelyStartOfMessageIndex[i] -= likelyStartOfNextMessage
                return True

    def _TryGetMessage(self):
        if not self._IsLongEnoughToBeMessage():
            return None

        self._CheckAndRemoveLoraModuleRXError()

        if not self._IsLongEnoughToBeMessage():
            return None

        messageTypes = self._GetLikelyMessageTypes()
        for messageType in messageTypes:
            if messageType == LoraRadioMessageRS.MessageTypeSIPunch:
                loraPunchMessage = self._GetPunchMessage(messageTypeToTry=messageType)
                if loraPunchMessage is not None:
                    return loraPunchMessage
            elif messageType == LoraRadioMessageRS.MessageTypeLoraAck:
                loraAckMessage = self._GetAckMessage(messageTypeToTry=messageType)
                if loraAckMessage is not None:
                    return loraAckMessage
            elif messageType == LoraRadioMessageRS.MessageTypeStatus:
                loraStatusMessage = self._GetStatusMessage(messageTypeToTry=messageType)
                if loraStatusMessage is not None:
                    return loraStatusMessage
            else:
                pass

        return None

    # Call GetMessage only when you believe you might have a message
    def GetMessage(self):
        self.LikelyStartOfMessageIndex.append(len(self.DataReceived))

        firstTimeOrMessageRemoved = True
        while firstTimeOrMessageRemoved:
            message = self._TryGetMessage()
            if message is not None:
                return message
            firstTimeOrMessageRemoved = self._RemoveLikelyMessage()

        return None

# Set likely message boundaries (with separate function?)
# remove data that cannot be decoded