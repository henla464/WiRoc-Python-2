__author__ = 'henla464'

import hashlib
from struct import *
from datamodel.datamodel import SIMessage
from loraradio.RSCoderLora import RSCoderLora
from utils.utils import Utils
from battery import *
from settings.settings import SettingsClass


class LoraRadioMessageRS(object):
    MessageTypeBitMask = 0b00011111
    RepeaterBitMask = 0b00100000
    BatLowBitMask = 0b01000000
    AckBitMask = 0b10000000
    # Six bits for message type
    MessageTypeSIPunch = 3
    MessageTypeStatus = 4
    MessageTypeLoraAck = 5
    MessageTypeSIPunchDouble = 6
    MessageTypeSIPunchReDCoS = 7
    MessageTypeSIPunchDoubleReDCoS = 8
    MessageLengths = [24, 16, 7, 14, 14, 7, 27, 15, 27]

    # Positions within the message
    H = 0

    def __init__(self):
        self.messageType = None
        self.batteryLow = False
        self.ackRequest = False
        self.repeater = False
        self.payloadData = bytearray()
        self.rsCodeData = bytearray()
        self.rssiByteArray = bytearray()

    @staticmethod
    def GetLoraMessageTimeSendingTimeSByMessageType(messageType):
        noOfBytes = LoraRadioMessageRS.MessageLengths[messageType]
        return SettingsClass.GetLoraMessageTimeSendingTimeS(noOfBytes)

    @staticmethod
    def getHeaderFormatString():
        return "<c"

    @staticmethod
    def GetHeaderSize():
        return calcsize(LoraRadioMessageRS.getHeaderFormatString())

    def GetMessageType(self):
        return self.messageType

    def GetHash(self):
        shake = hashlib.shake_128()
        shake.update(self.payloadData)
        theHash = shake.digest(2)
        return theHash

    def SetBatteryLow(self, batteryLow=False):
        self.batteryLow = batteryLow

    def GetBatteryLow(self):
        return self.batteryLow

    def SetAckRequested(self, ackReq):
        self.ackRequest = ackReq

    def GetAckRequested(self):
        return self.ackRequest

    def SetRepeater(self, reqRepeaterOrRepeaterAck):
        self.repeater = reqRepeaterOrRepeaterAck

    def GetRepeater(self):
        return self.repeater

    def SetRSSIByte(self, rssiByte):
        if rssiByte is None:
            self.rssiByteArray = bytearray()
            return
        if len(self.rssiByteArray) > 0:
            self.rssiByteArray[0] = rssiByte
        else:
            self.rssiByteArray.append(rssiByte)

    def GetRSSIValue(self):
        if len(self.rssiByteArray) > 0:
            return self.rssiByteArray[0]
        else:
            return 0

    def SetHeader(self, headerData):
        self.ackRequest = (headerData[0] & 0x80) > 0
        self.batteryLow = (headerData[0] & 0x40) > 0
        self.repeater = (headerData[0] & 0x20) > 0
        self.messageType = headerData[0] & 0x1F

    def GetHeaderData(self):
        headerData = bytearray(pack(LoraRadioMessageRS.getHeaderFormatString(),
                                    bytes([((1 if self.ackRequest else 0) << 7) |
                                           ((1 if self.batteryLow else 0) << 6) |
                                           ((1 if self.repeater else 0) << 5) |
                                           self.messageType])
                                    ))
        return headerData

    def GetByteArray(self):
        headerData = self.GetHeaderData()
        return headerData + self.payloadData + self.rsCodeData

    def GetPayloadByteArray(self):
        return self.payloadData

    def AddPayload(self, payloadArray):
        self.payloadData.extend(payloadArray)

    def GenerateAndAddRSCode(self):
        rsMessageData = self.GetHeaderData() + self.payloadData
        rsCodeOnly = RSCoderLora.encode(rsMessageData)
        self.rsCodeData = rsCodeOnly

    def AddRSCode(self, rsCode):
        self.rsCodeData = rsCode

    def GetRSCode(self):
        return self.rsCodeData


class LoraRadioMessagePunchRS(LoraRadioMessageRS):
    NoOfECCBytes = 4
    # Positions within the message
    CN0 = 1 # Control number - bit 0-7
    SN3 = 2 # SI Number, highest byte
    SN2 = 3
    SN1 = 4
    SN0 = 5
    CN1Plus = 6 # bit 6 is the eights bit of control number. Bit 5-4 4-week counter, Bit3-1 Day of week, Bit 0 AM/PM
    TH = 7 # 12 hour timer, high byte, number of seconds
    TL = 8  # 12 hour timer, high byte, number of seconds
    TSS = 9 # sub second values 1/256 sec
    ECC0 = 10 # Error correcting code
    ECC1 = 11  # Error correcting code
    ECC2 = 12  # Error correcting code
    ECC3 = 13  # Error correcting code

    def __init__(self):
        super().__init__()
        self.messageType = LoraRadioMessageRS.MessageTypeSIPunch

    def GetControlNumber(self):
        return (self.payloadData[self.CN1Plus - 1] & 0x40) << 2 | self.payloadData[self.CN0 - 1]

    def GetSICardNoByteArray(self):
        return self.payloadData[self.SN3 - 1:self.SN0]

    def GetSICardNo(self):
        return Utils.DecodeCardNr(self.GetSICardNoByteArray())

    def GetFourWeekCounter(self):
        return self.payloadData[self.CN1Plus - 1] & 0x30

    def GetDayOfWeek(self):
        return self.payloadData[self.CN1Plus - 1] & 0x0E

    def GetTwentyFourHour(self):
        return self.payloadData[self.CN1Plus - 1] & 0x01

    def GetTwelveHourTimer(self):
        return self.payloadData[self.TH - 1:self.TL]

    def GetSubSecondRaw(self):
        if len(self.payloadData) > 8:
            return self.payloadData[self.TSS-1]
        return 0

    def GetSubSecondAsTenthOfSeconds(self):
        return int(self.payloadData[self.TSS-1] // 25.6)

    def GetTimeAsTenthOfSeconds(self):
        time = ((self.GetTwelveHourTimer()[0] << 8) + self.GetTwelveHourTimer()[
            1]) * 10 + self.GetSubSecondAsTenthOfSeconds()
        if self.GetTwentyFourHour() == 1:
            time += 36000 * 12
        return time

    def GetHour(self):
        return int(self.GetTimeAsTenthOfSeconds() // 36000)

    def GetMinute(self):
        tenthOfSecs = self.GetTimeAsTenthOfSeconds()
        numberOfMinutesInTenthOfSecs = (tenthOfSecs - self.GetHour() * 36000)
        return numberOfMinutesInTenthOfSecs // 600

    def GetSeconds(self):
        tenthOfSecs = self.GetTimeAsTenthOfSeconds()
        numberOfSecondsInTenthOfSecs = (tenthOfSecs - self.GetHour() * 36000 - self.GetMinute() * 600)
        return numberOfSecondsInTenthOfSecs // 10

    def GetTwelveHourTimerAsInt(self):
        return (self.GetTwelveHourTimer()[0] << 8) + self.GetTwelveHourTimer()[1]

    def GetSIMessageByteArray(self):
        siMsg = SIMessage()
        siMsg.AddHeader(SIMessage.SIPunch)
        siMsg.AddByte((self.GetControlNumber() >> 8) & 0xFF)
        siMsg.AddByte(self.GetControlNumber() & 0xFF)
        siCardNoByteArray = self.GetSICardNoByteArray()
        siMsg.AddByte(siCardNoByteArray[0])
        siMsg.AddByte(siCardNoByteArray[1])
        siMsg.AddByte(siCardNoByteArray[2])
        siMsg.AddByte(siCardNoByteArray[3])
        twentyFourHour = self.GetFourWeekCounter() | self.GetDayOfWeek() | self.GetTwentyFourHour()
        siMsg.AddByte(twentyFourHour)
        twelveHourTimer = self.GetTwelveHourTimer()
        siMsg.AddByte(twelveHourTimer[0])
        siMsg.AddByte(twelveHourTimer[1])
        siMsg.AddByte(self.GetSubSecondRaw())
        siMsg.AddByte(0)
        siMsg.AddByte(0)
        siMsg.AddByte(0)
        siMsg.AddFooter()
        return siMsg.GetByteArray()

    def SetSIMessageByteArray(self, siMessageByteArray):
        self.payloadData = bytearray([0, 0, 0, 0, 0, 0, 0, 0, 0])
        self.payloadData[self.CN0-1] = siMessageByteArray[4]
        self.payloadData[self.SN3-1] = siMessageByteArray[5]
        self.payloadData[self.SN2-1] = siMessageByteArray[6]
        self.payloadData[self.SN1-1] = siMessageByteArray[7]
        self.payloadData[self.SN0-1] = siMessageByteArray[8]
        self.payloadData[self.CN1Plus-1] = siMessageByteArray[9] | ((siMessageByteArray[3] & 0x01) << 6)
        self.payloadData[self.TH-1] = siMessageByteArray[10]
        self.payloadData[self.TL-1] = siMessageByteArray[11]
        self.payloadData[self.TSS-1] = siMessageByteArray[12]

    def GetMessageCategory(self):
        return "DATA"

    def GetMessageSubType(self):
        return "SIMessage"


class LoraRadioMessagePunchDoubleRS(LoraRadioMessageRS):
    NoOfECCBytes = 8

    # Positions within the message
    CN0 = 1 # Control number - bit 0-7
    SN3 = 2 # SI Number, highest byte
    SN2 = 3
    SN1 = 4
    SN0 = 5
    CN1Plus = 6 # bit 6 is the eights bit of control number. Bit 5-4 4-week counter, Bit3-1 Day of week, Bit 0 AM/PM
    TH = 7 # 12 hour timer, high byte, number of seconds
    TL = 8  # 12 hour timer, high byte, number of seconds
    TSS = 9 # sub second values 1/256 sec
    # Second punch positions
    CN0_2 = 10
    SN3_2 = 11  # SI Number, highest byte
    SN2_2 = 12
    SN1_2 = 13
    SN0_2 = 14
    CN1Plus_2 = 15  # bit 6 is the eights bit of control number. Bit 5-4 4-week counter, Bit3-1 Day of week, Bit 0 AM/PM
    TH_2 = 16  # 12 hour timer, high byte, number of seconds
    TL_2 = 17  # 12 hour timer, high byte, number of seconds
    TSS_2 = 18  # sub second values 1/256 sec
    ECC0 = 19 # Error correcting code
    ECC1 = 20  # Error correcting code
    ECC2 = 21  # Error correcting code
    ECC3 = 22  # Error correcting code
    ECC4 = 23  # Error correcting code
    ECC5 = 24  # Error correcting code
    ECC6 = 25  # Error correcting code
    ECC7 = 26  # Error correcting code

    def __init__(self):
        super().__init__()
        self.messageType = LoraRadioMessageRS.MessageTypeSIPunchDouble

    def SetSIMessageByteArrays(self, firstSIMessageByteArray, secondSIMessageByteArray):
        msg = LoraRadioMessagePunchRS()
        msg.SetSIMessageByteArray(firstSIMessageByteArray)
        firstArray = msg.GetPayloadByteArray()
        msg.SetSIMessageByteArray(secondSIMessageByteArray)
        secondArray = msg.GetPayloadByteArray()
        self.payloadData = firstArray + secondArray

    def GetSIMessageByteTuple(self):
        firstArray = self.payloadData[0:9]
        secondArray = self.payloadData[9:18]
        loraPunchMessage1 = LoraRadioMessagePunchRS()
        header = 0x00
        if self.ackRequest:
            header = header | 0x80
        if self.batteryLow:
            header = header | 0x40
        if self.repeater:
            header = header | 0x20
        if self.messageType:
            header = header | self.messageType
        loraPunchMessage1.SetHeader(bytearray([header]))
        loraPunchMessage1.AddPayload(firstArray)
        # loraPunchMessage.AddRSCode()
        if len(self.rssiByteArray) > 0:
            loraPunchMessage1.SetRSSIByte(self.rssiByteArray[0])
        firstSIMessageByteArray = loraPunchMessage1.GetSIMessageByteArray()

        loraPunchMessage2 = LoraRadioMessagePunchRS()
        loraPunchMessage2.SetHeader(bytearray([header]))
        loraPunchMessage2.AddPayload(secondArray)
        # loraPunchMessage.AddRSCode()
        if len(self.rssiByteArray) > 0:
            loraPunchMessage2.SetRSSIByte(self.rssiByteArray[0])
        secondSIMessageByteArray = loraPunchMessage2.GetSIMessageByteArray()
        return firstSIMessageByteArray, secondSIMessageByteArray

    def GenerateAndAddRSCode(self):
        rsMessageData = self.GetHeaderData() + self.payloadData
        rsCodeOnly = RSCoderLora.encodeLong(rsMessageData)
        self.rsCodeData = rsCodeOnly

    def GetMessageCategory(self):
        return "DATA"

    def GetMessageSubType(self):
        return "SIMessageDouble"


class LoraRadioMessageReDCoSRS(LoraRadioMessageRS):
    def __init__(self):
        super().__init__()
        self.crcData = bytearray()

    def GenerateAndGetCRC(self):
        # note: header excluded
        crcMessageData = self.payloadData + self.rsCodeData
        shake = hashlib.shake_128()
        shake.update(crcMessageData)
        theCRCHash = shake.digest(2)
        return bytearray(theCRCHash)

    def GenerateAndAddCRC(self):
        # note: header excluded
        crcMessageData = self.payloadData + self.rsCodeData
        shake = hashlib.shake_128()
        shake.update(crcMessageData)
        theCRCHash = shake.digest(2)
        self.crcData = bytearray(theCRCHash)

    def AddCRC(self, crcData):
        self.crcData = crcData

    def GetCRC(self):
        return self.crcData

    def GetByteArray(self):
        return self.GetHeaderData() + self.GetPayloadByteArray() + self.GetRSCode() + self.GetCRC()


class LoraRadioMessagePunchReDCoSRS(LoraRadioMessageReDCoSRS):

    NoOfECCBytes = 4
    NoOfCRCBytes = 2
    # Positions within the message, after deinterleaving or before interleaving
    CN0 = 1  # Control number - bit 0-7
    SN3 = 2  # SI Number, highest byte
    SN2 = 3
    SN1 = 4
    SN0 = 5
    CN1Plus = 6 # bit 6 is the eights bit of control number. Bit 5-4 4-week counter, Bit3-1 Day of week, Bit 0 AM/PM
    TH = 7  # 12 hour timer, high byte, number of seconds
    TL = 8  # 12 hour timer, high byte, number of seconds
    ECC0 = 9  # Error correcting code
    ECC1 = 10  # Error correcting code
    ECC2 = 11  # Error correcting code
    ECC3 = 12  # Error correcting code
    CRC0 = 13  # CRC first byte
    CRC1 = 14  # CRC second byte

    InterleavingInAirOrder = [LoraRadioMessageReDCoSRS.H, CRC1, SN2, SN1, CN0, SN0, TH, TL, SN3, ECC0, ECC1, CN1Plus, ECC2, ECC3, CRC0]

    def __init__(self):
        super().__init__()
        self.messageType = LoraRadioMessageRS.MessageTypeSIPunchReDCoS

    @staticmethod
    def InterleaveToAirOrder(messageData):
        interleaved = bytearray(len(messageData))
        for i in range(len(messageData)):
            interleaved[i] = messageData[LoraRadioMessagePunchReDCoSRS.InterleavingInAirOrder[i]]
        return interleaved

    @staticmethod
    def DeInterleaveFromAirOrder(interleavedMessageData):
        messageData = bytearray(len(interleavedMessageData))
        for i in range(len(interleavedMessageData)):
            messageData[LoraRadioMessagePunchReDCoSRS.InterleavingInAirOrder[i]] = interleavedMessageData[i]
        return messageData

    def GetControlNumber(self):
        return (self.payloadData[self.CN1Plus-1] & 0x40) << 2 | self.payloadData[self.CN0-1]

    def GetSICardNoByteArray(self):
        return self.payloadData[self.SN3-1:self.SN0]

    def GetSICardNo(self):
        return Utils.DecodeCardNr(self.GetSICardNoByteArray())

    def GetFourWeekCounter(self):
        return self.payloadData[self.CN1Plus-1] & 0x30

    def GetDayOfWeek(self):
        return self.payloadData[self.CN1Plus-1] & 0x0E

    def GetTwentyFourHour(self):
        return self.payloadData[self.CN1Plus-1] & 0x01

    def GetTwelveHourTimer(self):
        return self.payloadData[self.TH-1:self.TL]

    def GetSubSecondRaw(self):
        return 0

    def GetSubSecondAsTenthOfSeconds(self):
        return 0

    def GetTimeAsTenthOfSeconds(self):
        time = ((self.GetTwelveHourTimer()[0] << 8) + self.GetTwelveHourTimer()[
            1]) * 10 + self.GetSubSecondAsTenthOfSeconds()
        if self.GetTwentyFourHour() == 1:
            time += 36000 * 12
        return time

    def GetHour(self):
        return int(self.GetTimeAsTenthOfSeconds() // 36000)

    def GetMinute(self):
        tenthOfSecs = self.GetTimeAsTenthOfSeconds()
        numberOfMinutesInTenthOfSecs = (tenthOfSecs - self.GetHour() * 36000)
        return numberOfMinutesInTenthOfSecs // 600

    def GetSeconds(self):
        tenthOfSecs = self.GetTimeAsTenthOfSeconds()
        numberOfSecondsInTenthOfSecs = (tenthOfSecs - self.GetHour() * 36000 - self.GetMinute() * 600)
        return numberOfSecondsInTenthOfSecs // 10

    def GetTwelveHourTimerAsInt(self):
        return (self.GetTwelveHourTimer()[0] << 8) + self.GetTwelveHourTimer()[1]

    def GetSIMessageByteArray(self):
        siMsg = SIMessage()
        siMsg.AddHeader(SIMessage.SIPunch)
        siMsg.AddByte((self.GetControlNumber() >> 8) & 0xFF)
        siMsg.AddByte(self.GetControlNumber() & 0xFF)
        siCardNoByteArray = self.GetSICardNoByteArray()
        siMsg.AddByte(siCardNoByteArray[0])
        siMsg.AddByte(siCardNoByteArray[1])
        siMsg.AddByte(siCardNoByteArray[2])
        siMsg.AddByte(siCardNoByteArray[3])
        twentyFourHour = self.GetFourWeekCounter() | self.GetDayOfWeek() | self.GetTwentyFourHour()
        siMsg.AddByte(twentyFourHour)
        twelveHourTimer = self.GetTwelveHourTimer()
        siMsg.AddByte(twelveHourTimer[0])
        siMsg.AddByte(twelveHourTimer[1])
        siMsg.AddByte(self.GetSubSecondRaw())
        siMsg.AddByte(0)
        siMsg.AddByte(0)
        siMsg.AddByte(0)
        siMsg.AddFooter()
        return siMsg.GetByteArray()

    def SetSIMessageByteArray(self, siMessageByteArray):
        self.payloadData = bytearray([0, 0, 0, 0, 0, 0, 0, 0, 0])
        self.payloadData[self.CN0-1] = siMessageByteArray[4]
        self.payloadData[self.SN3-1] = siMessageByteArray[5]
        self.payloadData[self.SN2-1] = siMessageByteArray[6]
        self.payloadData[self.SN1-1] = siMessageByteArray[7]
        self.payloadData[self.SN0-1] = siMessageByteArray[8]
        self.payloadData[self.CN1Plus-1] = siMessageByteArray[9] | ((siMessageByteArray[3] & 0x01) << 6)
        self.payloadData[self.TH-1] = siMessageByteArray[10]
        self.payloadData[self.TL-1] = siMessageByteArray[11]

    def GetMessageCategory(self):
        return "DATA"

    def GetMessageSubType(self):
        return "SIMessage"


class LoraRadioMessagePunchDoubleReDCoSRS(LoraRadioMessageReDCoSRS):
    NoOfECCBytes = 8
    NoOfCRCBytes = 2

    # Positions within the message
    CN0 = 1 # Control number - bit 0-7
    SN3 = 2 # SI Number, highest byte
    SN2 = 3
    SN1 = 4
    SN0 = 5
    CN1Plus = 6 # bit 6 is the eights bit of control number. Bit 5-4 4-week counter, Bit3-1 Day of week, Bit 0 AM/PM
    TH = 7 # 12 hour timer, high byte, number of seconds
    TL = 8  # 12 hour timer, high byte, number of seconds
    # Second punch positions
    CN0_2 = 9
    SN3_2 = 10  # SI Number, highest byte
    SN2_2 = 11
    SN1_2 = 12
    SN0_2 = 13
    CN1Plus_2 = 14  # bit 6 is the eights bit of control number. Bit 5-4 4-week counter, Bit3-1 Day of week, Bit 0 AM/PM
    TH_2 = 15  # 12 hour timer, high byte, number of seconds
    TL_2 = 16  # 12 hour timer, high byte, number of seconds
    ECC0 = 17 # Error correcting code
    ECC1 = 18  # Error correcting code
    ECC2 = 19  # Error correcting code
    ECC3 = 20  # Error correcting code
    ECC4 = 21  # Error correcting code
    ECC5 = 22  # Error correcting code
    ECC6 = 23  # Error correcting code
    ECC7 = 24  # Error correcting code
    CRC0 = 25  # CRC0 byte
    CRC1 = 26  # CRC1 byte

    InterleavingInAirOrder = [LoraRadioMessageReDCoSRS.H, CRC0, SN2, SN1, SN0, CN0, TH, TL, SN2_2, SN1_2, SN3, SN0_2, TH_2, TL_2, CN1Plus, ECC0, ECC1, ECC2, CN0_2, ECC3, ECC4, ECC5, SN3_2, ECC6, ECC7, CN1Plus_2, CRC1]

    def __init__(self):
        super().__init__()
        self.messageType = LoraRadioMessageRS.MessageTypeSIPunchDoubleReDCoS

    def InterleaveToAirOrder(self, messageData):
        interleaved = bytearray(len(messageData))
        for i in range(len(messageData)):
            interleaved[i] = messageData[self.InterleavingInAirOrder[i]]
        return interleaved

    def DeInterleaveFromAirOrder(self, interleavedMessageData):
        messageData = bytearray(len(interleavedMessageData))
        for i in range(len(interleavedMessageData)):
            messageData[self.InterleavingInAirOrder[i]] = interleavedMessageData[i]
        return messageData

    def GetControlNumber(self):
        return (self.payloadData[self.CN1Plus - 1] & 0x40) << 2 | self.payloadData[self.CN0 - 1]

    def GetControlNumber_2(self):
        return (self.payloadData[self.CN1Plus_2 - 1] & 0x40) << 2 | self.payloadData[self.CN0_2 - 1]

    def GetTwelveHourTimer(self):
        return self.payloadData[self.TH-1:self.TL]

    def GetTwelveHourTimer_2(self):
        return self.payloadData[self.TH_2-1:self.TL_2]

    def SetSIMessageByteArrays(self, firstSIMessageByteArray, secondSIMessageByteArray):
        msg = LoraRadioMessagePunchRS()
        msg.SetSIMessageByteArray(firstSIMessageByteArray)
        firstArray = msg.GetPayloadByteArray()
        msg.SetSIMessageByteArray(secondSIMessageByteArray)
        secondArray = msg.GetPayloadByteArray()
        self.payloadData = firstArray + secondArray

    def GetSIMessageByteTuple(self):
        firstArray = self.payloadData[0:9]
        secondArray = self.payloadData[9:18]
        loraPunchMessage1 = LoraRadioMessagePunchRS()
        header = 0x00
        if self.ackRequest:
            header = header | 0x80
        if self.batteryLow:
            header = header | 0x40
        if self.repeater:
            header = header | 0x20
        if self.messageType:
            header = header | self.messageType
        loraPunchMessage1.SetHeader(bytearray([header]))
        loraPunchMessage1.AddPayload(firstArray)
        # loraPunchMessage.AddRSCode()
        if len(self.rssiByteArray) > 0:
            loraPunchMessage1.SetRSSIByte(self.rssiByteArray[0])
        firstSIMessageByteArray = loraPunchMessage1.GetSIMessageByteArray()

        loraPunchMessage2 = LoraRadioMessagePunchRS()
        loraPunchMessage2.SetHeader(bytearray([header]))
        loraPunchMessage2.AddPayload(secondArray)
        # loraPunchMessage.AddRSCode()
        if len(self.rssiByteArray) > 0:
            loraPunchMessage2.SetRSSIByte(self.rssiByteArray[0])
        secondSIMessageByteArray = loraPunchMessage2.GetSIMessageByteArray()
        return firstSIMessageByteArray, secondSIMessageByteArray

    def GenerateAndAddRSCode(self):
        rsMessageData = self.GetHeaderData() + self.payloadData
        rsCodeOnly = RSCoderLora.encodeLong(rsMessageData)
        self.rsCodeData = rsCodeOnly

    def GetMessageCategory(self):
        return "DATA"

    def GetMessageSubType(self):
        return "SIMessageDouble"


class LoraRadioMessageAckRS(LoraRadioMessageRS):
    # Positions within the message
    HASH0 = 1
    HASH1 = 2
    ECC0 = 3  # Error correcting code
    ECC1 = 4  # Error correcting code
    ECC2 = 5  # Error correcting code
    ECC3 = 6  # Error correcting code

    def __init__(self):
        super().__init__()
        self.messageType = LoraRadioMessageRS.MessageTypeLoraAck

    def GetMessageIDThatIsAcked(self):
        return self.payloadData

    def GetMessageCategory(self):
        return "ACK"

    def GetMessageSubType(self):
        return "Ack"


class LoraRadioMessageStatusRS(LoraRadioMessageRS):
    NoOfECCBytes = 4
    # Positions within the message
    BAT = 1
    CN0 = 2
    RELAYPATHNO = 3
    BT0 = 4
    BT1 = 5
    BT2 = 6
    BT3 = 7
    BT4 = 8
    BT5 = 9
    ECC0 = 10  # Error correcting code
    ECC1 = 11  # Error correcting code
    ECC2 = 12  # Error correcting code
    ECC3 = 13  # Error correcting code

    def __init__(self):
        super().__init__()
        self.messageType = LoraRadioMessageRS.MessageTypeStatus
        siStationNumber = SettingsClass.GetSIStationNumber()
        batteryPercent = Battery.GetBatteryPercent()
        relayPathNo = SettingsClass.GetRelayPathNumber()
        btAddressAsInt = SettingsClass.GetBTAddressAsInt()
        self.payloadData = bytearray(bytes([batteryPercent, siStationNumber, relayPathNo,
                                            (btAddressAsInt & 0xFF0000000000) >> 40,
                                            (btAddressAsInt & 0x00FF00000000) >> 32,
                                            (btAddressAsInt & 0x0000FF000000) >> 24,
                                            (btAddressAsInt & 0x000000FF0000) >> 16,
                                            (btAddressAsInt & 0x00000000FF00) >> 8,
                                            (btAddressAsInt & 0x0000000000FF),
                                            ]))
        self.GenerateAndAddRSCode()

    def GetBatteryPercent(self):
        return self.payloadData[0]

    def GetSIStationNumber(self):
        return self.payloadData[1]

    def GetRelayPathNo(self):
        return self.payloadData[2]

    def SetPayload(self, payload):
        self.payloadData = payload

    def GetBTAddressAsInt(self):
        return (self.payloadData[3] << 40) | \
               (self.payloadData[4] << 32) | \
               (self.payloadData[5] << 24) | \
               (self.payloadData[6] << 16) | \
               (self.payloadData[7] << 8) | \
               self.payloadData[8]

    def GetBTAddress(self):
        btAddrAsInt = self.GetBTAddressAsInt()
        btAddress = '{:x}'.format(btAddrAsInt).upper()
        btAddress = btAddress[0:2] + ':' + btAddress[2:4] + ':' + btAddress[4:6] + \
            ':' + btAddress[6:8] + ':' + btAddress[8:10] + ':' + btAddress[10:12]
        return btAddress

    def GetMessageCategory(self):
        return "DATA"

    def GetMessageSubType(self):
        return "Status"
