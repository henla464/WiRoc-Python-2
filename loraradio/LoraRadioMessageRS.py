__author__ = 'henla464'

import hashlib
from struct import *
from datamodel.datamodel import SIMessage
from loraradio.RSCoderLora import RSCoderLora
from utils.utils import Utils


class LoraRadioMessageRS(object):
    # Six bits for message type
    MessageTypeSIPunch = 3
    MessageTypeStatus = 4
    MessageTypeLoraAck = 5
    MessageTypeSIPunchDouble = 6
    MessageLengths = [24, 16, 7, 14, 13, 7, 27]

    def __init__(self):
        self.messageType = None
        self.batteryLow = False
        self.ackRequest = False
        self.repeater = False
        self.payloadData = bytearray()
        self.rsCodeData = bytearray()
        self.rssiByte = bytearray()

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

    def SetBatteryLow(self, batteryLow = False):
        self.batteryLow = batteryLow

    def GetBatteryLow(self):
        return self.batteryLow

    def SetAckRequested(self,ackReq):
        self.ackRequest = ackReq

    def GetAckRequested(self):
        return self.ackRequest

    def SetRepeater(self, reqRepeaterOrRepeaterAck):
        self.repeater = reqRepeaterOrRepeaterAck

    def GetRepeater(self):
        return self.repeater

    def SetRSSIByte(self, rssiByte):
        if  rssiByte is None:
            self.rssiByte = bytearray()
            return
        if len(self.rssiByte) > 0:
            self.rssiByte[0] = rssiByte
        else:
            self.rssiByte.append(rssiByte)

    def GetRSSIValue(self):
        if len(self.rssiByte) > 0:
            return self.rssiByte[0]
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

    def GenerateRSCode(self):
        rsMessageData = self.GetHeaderData() + self.payloadData
        rsCodeOnly = RSCoderLora.encode(rsMessageData)
        self.rsCodeData = rsCodeOnly

    def AddRSCode(self, rsCode):
        self.rsCodeData = rsCode


class LoraRadioMessagePunchRS(LoraRadioMessageRS):
    def __init__(self):
        super().__init__()
        self.messageType = LoraRadioMessageRS.MessageTypeSIPunch

    def GetControlNumber(self):
        return (self.payloadData[5] & 0x40) << 2 | self.payloadData[0]

    def GetSICardNoByteArray(self):
        return self.payloadData[1:5]

    def GetSICardNo(self):
        return Utils.DecodeCardNr(self.GetSICardNoByteArray())

    def GetFourWeekCounter(self):
        return self.payloadData[5] & 0x30

    def GetDayOfWeek(self):
        return self.payloadData[5] & 0x0E

    def GetTwentyFourHour(self):
        return self.payloadData[5] & 0x01

    def GetTwelveHourTimer(self):
        return self.payloadData[6:8]

    def GetSubSecondRaw(self):
        return self.payloadData[8]

    def GetSubSecondAsTenthOfSeconds(self):
        return int(self.payloadData[8] // 25.6)

    def GetTimeAsTenthOfSeconds(self):
        time = ((self.GetTwelveHourTimer()[0] << 8) + self.GetTwelveHourTimer()[1]) * 10 + self.GetSubSecondAsTenthOfSeconds()
        if self.GetTwentyFourHour() == 1:
            time += 36000 * 12
        return time

    def GetHour(self):
        return int(self.GetTimeAsTenthOfSeconds() // 36000)

    def GetMinute(self):
        tenthOfSecs = self.GetTimeAsTenthOfSeconds()
        numberOfMinutesInTenthOfSecs = (tenthOfSecs - self.GetHour()*36000)
        return numberOfMinutesInTenthOfSecs // 600

    def GetSeconds(self):
        tenthOfSecs = self.GetTimeAsTenthOfSeconds()
        numberOfSecondsInTenthOfSecs = (tenthOfSecs - self.GetHour() * 36000 - self.GetMinute()*600)
        return numberOfSecondsInTenthOfSecs // 10

    def GetTwelveHourTimerAsInt(self):
        return ((self.GetTwelveHourTimer()[0] << 8) + self.GetTwelveHourTimer()[1])

    def GetSICardNoRawByteArray(self):
        return self.payloadData[1:5]

    def GetSIMessageByteArray(self):
        siMsg = SIMessage()
        siMsg.AddHeader(SIMessage.SIPunch)
        siMsg.AddByte((self.GetControlNumber() >> 8) & 0xFF)
        siMsg.AddByte(self.GetControlNumber() & 0xFF)
        siCardNoByteArray = self.GetSICardNoRawByteArray()
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
        self.payloadData = bytearray([0,0,0,0,0,0,0,0,0])
        self.payloadData[0] = siMessageByteArray[4]
        self.payloadData[1] = siMessageByteArray[5]
        self.payloadData[2] = siMessageByteArray[6]
        self.payloadData[3] = siMessageByteArray[7]
        self.payloadData[4] = siMessageByteArray[8]
        self.payloadData[5] = siMessageByteArray[9] | ((siMessageByteArray[3] & 0x01) << 6)
        self.payloadData[6] = siMessageByteArray[10]
        self.payloadData[7] = siMessageByteArray[11]
        self.payloadData[8] = siMessageByteArray[12]

    #def GetSIMessageByteArray(self):
    #    siMessageByteArray = bytearray([0,0,0,0,0, 0,0,0,0,0, 0,0,0,0,0, 0,0,0,0])
    #    siMessageByteArray[0] = 0x02
    #    siMessageByteArray[1] = 0xD3
    #    siMessageByteArray[2] = 0x0D
    #    siMessageByteArray[3] = (self.payloadData[5] & 0x40) >> 6
    #    siMessageByteArray[4] = self.payloadData[0]
    #    siMessageByteArray[5] = self.payloadData[1]
    #    siMessageByteArray[6] = self.payloadData[2]
    #    siMessageByteArray[7] = self.payloadData[3]
    #    siMessageByteArray[8] = self.payloadData[4]
    #    siMessageByteArray[9] = self.payloadData[5] & 0x3F
    #    siMessageByteArray[10] = self.payloadData[6]
    #    siMessageByteArray[11] = self.payloadData[7]
    #    siMessageByteArray[12] = self.payloadData[8]
    #    siMessageByteArray[13] = 0x00
    #    siMessageByteArray[14] = 0x00
    #    siMessageByteArray[15] = 0x00
    #    partToCalculateCRSOn = siMessageByteArray[1:-3]
    #    calculatedCrc = Utils.CalculateCRC(partToCalculateCRSOn)
    #    siMessageByteArray[16] = calculatedCrc[0]
    #    siMessageByteArray[17] = calculatedCrc[1]
    #    siMessageByteArray[18] = 0x03  # ETX
    #    return siMessageByteArray

    def GetMessageCategory(self):
        return "DATA"

    def GetMessageSubType(self):
        return "SIMessage"


class LoraRadioMessagePunchDoubleRS(LoraRadioMessageRS):
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
        #loraPunchMessage.AddRSCode()
        loraPunchMessage1.SetRSSIByte(self.rssiByte)
        firstSIMessageByteArray = loraPunchMessage1.GetSIMessageByteArray()

        loraPunchMessage2 = LoraRadioMessagePunchRS()
        loraPunchMessage2.SetHeader(bytearray([header]))
        loraPunchMessage2.AddPayload(secondArray)
        # loraPunchMessage.AddRSCode()
        loraPunchMessage2.SetRSSIByte(self.rssiByte)
        secondSIMessageByteArray = loraPunchMessage2.GetSIMessageByteArray()
        return firstSIMessageByteArray, secondSIMessageByteArray

    def GenerateRSCode(self):
        rsMessageData = self.GetHeaderData() + self.payloadData
        rsCodeOnly = RSCoderLora.encodeLong(rsMessageData)
        self.rsCodeData = rsCodeOnly

    def GetMessageCategory(self):
        return "DATA"

    def GetMessageSubType(self):
        return "SIMessageDouble"


class LoraRadioMessageAckRS(LoraRadioMessageRS):
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
    def __init__(self):
        super().__init__()
        self.messageType = LoraRadioMessageRS.MessageTypeStatus

    def GetLastRelayPathNoFromStatusMessage(self):
        if self.GetMessageType() != LoraRadioMessageRS.MessageTypeStatus:
            raise Exception('Lora message is not a status message!')

        if self.payloadData[6] != 0x00 or self.payloadData[7] != 0x00:
            return (self.payloadData[7] & 0x07) + 1
        elif self.payloadData[4] != 0x00 or self.payloadData[5] == 0x00:
            return (self.payloadData[5] & 0x07) + 1
        elif self.payloadData[2] != 0x00 or self.payloadData[3] == 0x00:
            return (self.payloadData[3] & 0x07) + 1
        else:
            return (self.payloadData[1] & 0x07) + 1

    def AddThisWiRocToStatusMessage(self, siStationNumber, batteryPercent4Bits):
        if self.GetMessageType() != LoraRadioMessageRS.MessageTypeStatus:
            raise Exception('Lora message is not a status message!')

        # batteryPercent | siStationNo      |  pathNo  |
        #      ####            ####  #####      ###    |
        #       high byte          |       low byte    |
        indexToWriteTo = -1
        realWiRocRelayPathNo = -1
        if self.payloadData[0] == 0x00 and self.payloadData[1] == 0x00:
            indexToWriteTo = 0
            realWiRocRelayPathNo = 0
        elif self.payloadData[2] == 0x00 and self.payloadData[3] == 0x00:
            indexToWriteTo = 2
            realWiRocRelayPathNo = 1
        elif self.payloadData[4] == 0x00 and self.payloadData[5] == 0x00:
            indexToWriteTo = 4
            realWiRocRelayPathNo = 2
        elif self.payloadData[6] == 0x00 and self.payloadData[7] == 0x00:
            indexToWriteTo = 6
            realWiRocRelayPathNo = 3
        else:
            indexToWriteTo = 6
            realWiRocRelayPathNo = self.payloadData[7] & 0x07

        highByte = batteryPercent4Bits << 4 | ((siStationNumber & 0x1E0) >> 5)
        lowByte = ((siStationNumber & 0x1F) << 3) | realWiRocRelayPathNo
        self.payloadData[indexToWriteTo] = highByte
        self.payloadData[indexToWriteTo+1] = lowByte
        self.GenerateRSCode()

    def GetMessageCategory(self):
        return "DATA"

    def GetMessageSubType(self):
        return "Status"
