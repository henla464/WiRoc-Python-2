__author__ = 'henla464'

from datetime import datetime
from struct import *
from constants import *
from utils.utils import Utils
import logging

class SettingData(object):
    columns = [("Key", str), ("Value", str)]

    def __init__(self):
        self.id = None
        self.Key = None
        self.Value = None


class ChannelData(object):
    columns = [("Channel", int), ("DataRate", int),
               ("Frequency", int), ("SlopeCoefficient", int),
               ("M", int), ("RfFactor", int), ("RfBw", int)]

    def __init__(self, Channel=None, DataRate=None,
                 Frequency=None, SlopeCoefficient=None,
                 M=None, RfFactor=None, RfBw=None):
        self.id = None
        self.Channel = Channel
        self.DataRate = DataRate
        self.Frequency = Frequency
        self.SlopeCoefficient = SlopeCoefficient
        self.M = M
        self.RfFactor = RfFactor
        self.RfBw = RfBw


class MessageBoxData(object):
    columns = [("MessageData", bytearray), ("PowerCycleCreated", int),
               ("MessageTypeName", str), ("InstanceName", str),
               ("MessageSubTypeName", str),
               ("ChecksumOK", bool), ("CreatedDate", datetime)]

    def __init__(self, MessageData=None, PowerCycleCreated=None,
                 MessageTypeName=None, InstanceName = None,
                 MessageSubTypeName=None,
                 ChecksumOK=None, CreatedDate=None):
        self.id = None
        self.MessageData = MessageData
        self.PowerCycleCreated = PowerCycleCreated
        self.MessageTypeName = MessageTypeName
        self.InstanceName = InstanceName
        self.MessageSubTypeName = MessageSubTypeName
        self.ChecksumOK = ChecksumOK
        self.CreatedDate = CreatedDate


class MessageBoxArchiveData(object):
    columns = [("OrigId", int), ("MessageData", bytes), ("PowerCycleCreated", int),
               ("MessageTypeName", str), ("InstanceName", str),
               ("MessageSubTypeName", str),
               ("ChecksumOK", bool), ("CreatedDate", datetime)]

    def __init__(self, OrigId=None, MessageData=None, PowerCycleCreated=None,
                 MessageTypeName=None, InstanceName=None,
                 MessageSubTypeName=None,
                 ChecksumOK=None, CreatedDate=None):
        self.id = None
        self.OrigId = OrigId
        self.MessageData = MessageData
        self.PowerCycleCreated = PowerCycleCreated
        self.MessageTypeName = MessageTypeName
        self.InstanceName = InstanceName
        self.MessageSubTypeName = MessageSubTypeName
        self.ChecksumOK = ChecksumOK
        self.CreatedDate = CreatedDate


class SubscriberData(object):
    columns = [("TypeName", str), ("InstanceName", str)]

    def __init__(self, TypeName=None, InstanceName=None):
        self.id = None
        self.TypeName = TypeName
        self.InstanceName = InstanceName


class MessageTypeData(object):
    columns = [("Name", str)]

    def __init__(self, Name=None):
        self.id = None
        self.Name = Name


class TransformData(object):
    columns = [("Name", str), ("InputMessageTypeId", int), ("OutputMessageTypeId", int), ("Enabled", bool)]

    def __init__(self, Name=None, InputMessageTypeId=None, OutputMessageTypeId=None, Enabled=True):
        self.id = None
        self.Name = Name
        self.InputMessageTypeId = InputMessageTypeId
        self.OutputMessageTypeId = OutputMessageTypeId
        self.Enabled = Enabled


class SubscriptionData(object):
    columns = [("DeleteAfterSent", bool), ("Enabled", bool),
               ("SubscriberId", int), ("TransformId", int),
               ("WaitUntilAckSent", bool)]

    def __init__(self, DeleteAfterSent=None, Enabled=None,
                 SubscriberId=None, TransformId=None, WaitUntilAckSent = False):
        self.id = None
        self.DeleteAfterSent = DeleteAfterSent
        self.Enabled = Enabled
        self.SubscriberId = SubscriberId
        self.TransformId = TransformId
        self.WaitUntilAckSent = WaitUntilAckSent


class MessageSubscriptionData(object):
    columns = [("CustomData", str), ("SentDate", datetime), ("SendFailedDate", datetime),
               ("FindAdapterTryDate", datetime), ("FindAdapterTries", int),
               ("NoOfSendTries", int), ("AckReceivedDate", datetime),
               ("ScheduledTime", datetime), ("MessageBoxId", int),
               ("SubscriptionId", int)]

    def __init__(self, CustomData=None, SentDate=None, SendFailedDate=None,
                 FindAdapterTryDate=None,FindAdapterTries=0, AckReceivedDate=None,
                 NoOfSendTries=0, ScheduledTime=None, MessageBoxId=None, SubscriptionId=None):
        self.id = None
        self.CustomData = CustomData
        self.SentDate = SentDate
        self.SendFailedDate = SendFailedDate
        self.NoOfSendTries = NoOfSendTries
        self.FindAdapterTryDate = FindAdapterTryDate
        self.FindAdapterTries = FindAdapterTries
        self.AckReceivedDate = AckReceivedDate
        self.ScheduledTime = ScheduledTime
        self.MessageBoxId = MessageBoxId
        self.SubscriptionId = SubscriptionId

class MessageSubscriptionArchiveData(object):
    columns = [ ("OrigId", int), ("CustomData", str),
                ("SentDate", datetime), ("SendFailedDate", datetime),
                ("FindAdapterTryDate", datetime),("FindAdapterTries", int),
                ("NoOfSendTries", int), ("AckReceivedDate", datetime),
                ("ScheduledTime", datetime), ("MessageBoxId", int),
                ("SubscriptionId", int),
                ("SubscriberTypeName", str), ("TransformName", str),]

    def __init__(self, CustomData=None, SentDate=None, SendFailedDate=None,
                 FindAdapterTryDate=None,FindAdapterTries=0, AckReceivedDate=None,
                 NoOfSendTries=0, ScheduledTime=None, MessageBoxId=None,
                 SubscriptionId=None,
                 SubscriberTypeName = None, TransformName = None):
        self.id = None
        self.CustomData = CustomData
        self.SentDate = SentDate
        self.SendFailedDate = SendFailedDate
        self.FindAdapterTryDate = FindAdapterTryDate
        self.FindAdapterTries = FindAdapterTries
        self.NoOfSendTries = NoOfSendTries
        self.AckReceivedDate = AckReceivedDate
        self.MessageBoxId = MessageBoxId
        self.ScheduledTime = ScheduledTime
        self.SubscriptionId = SubscriptionId
        self.SubscriberTypeName = SubscriberTypeName
        self.TransformName = TransformName


class MessageSubscriptionView(object):
    columns = [("CustomData", str), ("SentDate", datetime), ("SendFailedDate", datetime),
               ("FindAdapterTryDate", datetime), ("FindAdapterTries", int),
               ("NoOfSendTries", int), ("AckReceivedDate", datetime), ("MessageBoxId", int),
               ("SubscriptionId", int),
               ("DeleteAfterSent", bool), ("Enabled", bool), ("SubscriberId", int),
               ("SubscriberTypeName", str), ("SubscriberInstanceName", str),
               ("TransformName", str), ("MessageData", bytearray),
               #("CreatedDate", datetime)
               ]

    def __init__(self):
        self.id = None
        self.CustomData = None
        self.SentDate = None
        self.SendFailedDate = None
        self.FindAdapterTryDate = None
        self.FindAdapterTries = None
        self.NoOfSendTries = None
        self.AckReceivedDate = None
        self.MessageBoxId = None
        self.SubscriptionId = None
        self.DeleteAfterSent = None
        self.Enabled = None
        self.SubscriberId = None
        self.SubscriberTypeName = None
        self.SubscriberInstanceName = None
        self.TransformName = None
        self.MessageData = None
        self.CreatedDate = None


class SubscriberView(object):
    columns = [("TypeName", str), ("InstanceName", str), ("Enabled", bool), ("MessageInName", str),
               ("MessageOutName", str), ("TransformEnabled", bool), ("TransformName", str)]

    def __init__(self):
        self.id = None
        self.TypeName = None
        self.InstanceName = None
        self.Enabled = False
        self.MessageInName = None
        self.MessageOutName = None
        self.TransformEnabled = False
        self.TransformName = False


class InputAdapterInstances(object):
    columns = [("TypeName", str), ("InstanceName", str), ("ToBeDeleted", bool)]

    def __init__(self):
        self.id = None
        self.TypeName = None
        self.InstanceName = None
        self.ToBeDeleted = False


class BlenoPunchData(object):
    columns = [("StationNumber", int), ("SICardNumber", int), ("TwentyFourHour", int), ("TwelveHourTimer", int), ("SubSecond", int)]

    def __init__(self):
        self.id = None
        self.StationNumber = None
        self.SICardNumber = None
        self.TwentyFourHour = None
        self.TwelveHourTimer = None
        self.SubSecond = None

class TestPunchData(object):
    columns = [("BatchGuid", str), ("MessageBoxId", int), ("TwentyFourHour", int),("TwelveHourTimer", int),("SICardNumber", int), ("AddedToMessageBox", bool), ("Fetched", bool)]

    def __init__(self):
        self.id = None
        self.BatchGuid = None
        self.MessageBoxId = None
        self.TwentyFourHour = 1
        self.TwelveHourTimer = 0
        self.SICardNumber = 0
        self.AddedToMessageBox = 0
        self.Fetched = 0


class TestPunchView(object):
    columns = [("BatchGuid", str), ("MessageBoxId", int), ("TwentyFourHour", int), ("TwelveHourTimer", int),
               ("SICardNumber", int), ("Fetched", bool), ("NoOfSendTries", int), ("Status", str)]

    def __init__(self):
        self.id = None
        self.BatchGuid = None
        self.MessageBoxId = None
        self.TwentyFourHour = 1
        self.TwelveHourTimer = 0
        self.SICardNumber = 0
        self.Fetched = 0
        self.NoOfSendTries = 0
        self.Status = None


# Non database objects
class LoraRadioMessage(object):
    # Six bits for message type
    MessageTypeSIPunch = 0
    MessageTypeLoraAck = 1
    # Payload for LoraAck is 1 byte with the message number that is acked
    MessageTypeStatus = 2
    # Payload is two bytes, 4 bits of battery %, 12 bits ID number
    # (consisting of 9 bits SI station code + 3 bit number increased with each WiRoc in the path)

    CurrentMessageNumber = 0

    def __init__(self, payloadDataLength=None, messageType=None, batteryLow = False, ackReq = False):
        if payloadDataLength is not None:
            batteryLowBit = 0
            ackReqBit = 0
            if batteryLow:
                batteryLowBit = 1
            if ackReq:
                ackReqBit = 1
            self.MessageData = bytearray(pack(LoraRadioMessage.getHeaderFormatString(), bytes([STX]),
                                              bytes([payloadDataLength]),
                                              bytes([(ackReqBit << 7) | (batteryLowBit << 6) | messageType]),
                                              bytes([LoraRadioMessage.CurrentMessageNumber]),
                                              bytes([0])))
            LoraRadioMessage.CurrentMessageNumber = (LoraRadioMessage.CurrentMessageNumber + 1) % 256
        else:
            self.MessageData = bytearray()

    def GetMessageNumber(self):
        return self.MessageData[3]

    def UpdateMessageNumber(self):
        self.MessageData[3] = LoraRadioMessage.CurrentMessageNumber
        LoraRadioMessage.CurrentMessageNumber = (LoraRadioMessage.CurrentMessageNumber + 1) % 256

    @staticmethod
    def getHeaderFormatString():
        return "<ccccc"

    @staticmethod
    def GetHeaderSize():
        return calcsize(LoraRadioMessage.getHeaderFormatString())

    def GetMessageType(self):
        if len(self.MessageData) >= 3:
            return self.MessageData[2] & 0x3F
        return None

    def GetIsChecksumOK(self):
        if self.IsFilled():
            crcInMessage = self.MessageData[4]
            self.MessageData[4] = 0
            calculatedCrc = Utils.CalculateCRC(self.MessageData)
            oneByteCalculatedCrc = calculatedCrc[0] ^ calculatedCrc[1]
            isOK = (crcInMessage == oneByteCalculatedCrc)
            self.MessageData[4] = crcInMessage #restore the message
            return isOK
        return False

    def UpdateChecksum(self):
        self.MessageData[4] = 0
        crc = Utils.CalculateCRC(self.MessageData)
        self.MessageData[4] = crc[0] ^ crc[1]
        return True

    def UpdateLength(self):
        self.MessageData[1] = len(self.MessageData) - self.GetHeaderSize()

    def SetBatteryLowBit(self, batteryLow):
        if batteryLow:
            self.MessageData[2] = 0x40 | self.MessageData[2]
        else:
            self.MessageData[2] = 0xBF & self.MessageData[2]

    def GetBatteryLowBit(self):
        return (self.MessageData[2] & 0x40) > 0

    def SetAcknowledgementRequested(self, ackReq):
        if ackReq:
            self.MessageData[2] = 0x80 | self.MessageData[2]
        else:
            self.MessageData[2] = 0x7F & self.MessageData[2]

    def GetAcknowledgementRequested(self):
        return (self.MessageData[2] & 0x80) > 0

    def IsFilled(self):
        if len(self.MessageData) >= 2:
            if len(self.MessageData) == self.MessageData[1] + 5:
                return True
        return False

    def GetByteArray(self):
        return self.MessageData

    def AddByte(self, newByte):
        if self.IsFilled():
            logging.error("Error, trying to fill LoraRadioMessage with bytes, but it is already full")
        else:
            self.MessageData.append(newByte)

    def AddPayload(self, payloadArray):
        self.MessageData.extend(payloadArray)
        self.UpdateChecksum()

    def GetLastRelayPathNoFromStatusMessage(self):
        if self.GetMessageType() != LoraRadioMessage.MessageTypeStatus:
            raise Exception('Lora message is not a status message!')

        relayPathNo = (self.MessageData[-1] & 0x07) + 1
        return relayPathNo

    def AddThisWiRocToStatusMessage(self, siStationNumber, batteryPercent4Bits):
        if self.GetMessageType() != LoraRadioMessage.MessageTypeStatus:
            raise Exception('Lora message is not a status message!')

        # batteryPercent | siStationNo      |  pathNo  |
        #      ####            ####  #####      ###    |
        #       high byte          |       low byte    |
        lengthPayload = len(self.MessageData) - self.GetHeaderSize()
        wiRocRelayPathNo = int(lengthPayload / 2)
        # we limit the payload length so when there are too many WiRocs in the path
        # then the path no will not match the index in the payload
        realWiRocRelayPathNo = wiRocRelayPathNo
        if wiRocRelayPathNo > 0:
            highBytePrevWiRocIndex = self.GetHeaderSize() + (wiRocRelayPathNo - 1) * 2
            realWiRocRelayPathNo = (self.MessageData[highBytePrevWiRocIndex + 1] & 0x07) + 1
            if siStationNumber == 0:
                siStationNumber = ((self.MessageData[highBytePrevWiRocIndex] & 0x0F) << 5) | \
                                  ((self.MessageData[highBytePrevWiRocIndex + 1] & 0xF8) >> 3)

        highByte = batteryPercent4Bits << 4 | ((siStationNumber & 0x1E0) >> 5)
        lowByte = ((siStationNumber & 0x1F) << 3) | realWiRocRelayPathNo
        if wiRocRelayPathNo <= 3:
            self.MessageData[1] = 255 # set length to 255 to allow adding bytes
            self.AddByte(highByte)
            self.AddByte(lowByte)
        else:
            # overwrite last bytes instead, to limit message size
            self.MessageData[-2] = highByte
            self.MessageData[-1] = lowByte
        self.UpdateLength()
        self.UpdateChecksum()



class SIMessage(object):
    IAmAWiRocDevice = 0x01
    # 0x02 is used for STX
    # 0x03 is used for ETX
    WiRocToWiRoc = 0x04
    SIPunch = 0xD3

    def __init__(self):
        self.MessageData = bytearray()

    def AddHeader(self, msgType):
        if len(self.MessageData) == 0:
            self.MessageData.append(0x02)
            self.MessageData.append(msgType)
            self.MessageData.append(255)  # set max length temporarily

    def GetHeaderSize(self):
        return 3

    def GetFooterSize(self):
        return 3

    def GetMessageType(self):
        if len(self.MessageData) >= 2:
            return self.MessageData[1]
        return None

    def GetIsChecksumOK(self):
        if self.IsFilled():
            crcInMessage1 = self.MessageData[-3]
            crcInMessage2 = self.MessageData[-2]
            partToCalculateCRSOn = self.MessageData[1:-3]
            calculatedCrc = Utils.CalculateCRC(partToCalculateCRSOn)
            isOK = (crcInMessage1 == calculatedCrc[0] and crcInMessage2 == calculatedCrc[1])
            return isOK
        return False

    def UpdateChecksum(self):
        if self.IsFilled():
            partToCalculateCRSOn = self.MessageData[1:-3]
            crc = Utils.CalculateCRC(partToCalculateCRSOn)
            self.MessageData[-3] = crc[0]
            self.MessageData[-2] = crc[1]
            return True
        return False

    def UpdateLength(self):
        self.MessageData[2] = len(self.MessageData) - self.GetHeaderSize() - self.GetFooterSize()

    def IsFilled(self):
        if len(self.MessageData) >= 3:
            if len(self.MessageData) == self.MessageData[2] + self.GetHeaderSize() + self.GetFooterSize():
                return True
        return False

    def GetByteArray(self):
        return self.MessageData

    def AddByte(self, newByte):
        if self.IsFilled():
            logging.error("Error, trying to fill SIMessageData with bytes, but it is already full")
        else:
            self.MessageData.append(newByte)

    def AddPayload(self, payloadArray):
        self.MessageData.extend(payloadArray)

    def AddFooter(self):
        self.MessageData.append(0x00)  # crc1
        self.MessageData.append(0x00)  # crc2
        self.MessageData.append(0x03)  # ETX
        self.UpdateLength()
        self.UpdateChecksum()

    def GetStationNumber(self):
        return (self.MessageData[3] << 8) + self.MessageData[4]

    def GetSICardNumber(self):
        return Utils.DecodeCardNr(self.MessageData[5:9])

    def GetTwentyFourHour(self):
        return self.MessageData[9] & 0x01

    def GetTwelveHourTimer(self):
        return self.MessageData[10:12]

    def GetSubSecondAsTenthOfSeconds(self):
        return int(self.MessageData[12] // 25.6)

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
