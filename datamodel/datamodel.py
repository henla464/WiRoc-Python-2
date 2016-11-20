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
               ("MessageTypeId", int), ("InstanceName", str),
               ("ChecksumOK", bool), ("CreatedDate", datetime)]

    def __init__(self, MessageData=None, PowerCycleCreated=None,
                 MessageTypeId=None, InstanceName = None,
                 ChecksumOK=None, CreatedDate=None):
        self.id = None
        self.MessageData = MessageData
        self.PowerCycleCreated = PowerCycleCreated
        self.MessageTypeId = MessageTypeId
        self.InstanceName = InstanceName
        self.ChecksumOK = ChecksumOK
        self.CreatedDate = CreatedDate



class MessageBoxArchiveData(object):
    columns = [("OrigId", int), ("MessageData", bytes), ("PowerCycleCreated", int),
               ("MessageTypeId", int), ("InstanceName", str),
               ("ChecksumOK", bool), ("CreatedDate", datetime)]

    def __init__(self, OrigId=None, MessageData=None, PowerCycleCreated=None,
                 MessageTypeId=None, InstanceName=None, ChecksumOK=None, CreatedDate=None):
        self.id = None
        self.OrigId = OrigId
        self.MessageData = MessageData
        self.PowerCycleCreated = PowerCycleCreated
        self.MessageTypeId = MessageTypeId
        self.InstanceName = InstanceName
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
    columns = [("Name", str), ("InputMessageTypeId", int), ("OutputMessageTypeId", int)]

    def __init__(self, Name=None, InputMessageTypeId=None, OutputMessageTypeId=None):
        self.id = None
        self.Name = Name
        self.InputMessageTypeId = InputMessageTypeId
        self.OutputMessageTypeId = OutputMessageTypeId


class SubscriptionData(object):
    columns = [("DeleteAfterSent", bool), ("Enabled", bool),
               ("SubscriberId", int), ("TransformId", int)]

    def __init__(self, DeleteAfterSent=None, Enabled=None,
                 SubscriberId=None, TransformId=None, ):
        self.id = None
        self.DeleteAfterSent = DeleteAfterSent
        self.Enabled = Enabled
        self.SubscriberId = SubscriberId
        self.TransformId = TransformId


class MessageSubscriptionData(object):
    columns = [("CustomData", str), ("SentDate", datetime),
               ("NoOfSendTries", int), ("AckReceivedDate", datetime), ("MessageBoxId", int),
               ("SubscriptionId", int)]

    def __init__(self, CustomData=None, SentDate=None, AckReceivedDate=None,
                 NoOfSendTries=0, MessageBoxId=None, SubscriptionId=None):
        self.id = None
        self.CustomData = CustomData
        self.SentDate = SentDate
        self.NoOfSendTries = NoOfSendTries
        self.AckReceivedDate = AckReceivedDate
        self.MessageBoxId = MessageBoxId
        self.SubscriptionId = SubscriptionId

class MessageSubscriptionArchiveData(object):
    columns = [ ("OrigId", int), ("CustomData", str),
                ("SentDate", datetime), ("NoOfSendTries", int), ("AchReceivedDate", datetime),
                ("MessageBoxId", int), ("SubscriptionId", int)]

    def __init__(self, CustomData=None, SentDate=None, AckReceivedDate=None,
                 NoOfSendTries=0, MessageBoxId=None, SubscriptionId=None):
        self.id = None
        self.CustomData = CustomData
        self.SentDate = SentDate
        self.NoOfSendTries = NoOfSendTries
        self.AckReceivedDate = AckReceivedDate
        self.MessageBoxId = MessageBoxId
        self.SubscriptionId = SubscriptionId


class MessageSubscriptionView(object):
    columns = [("CustomData", str), ("SentDate", datetime),
               ("NoOfSendTries", int), ("AckReceivedDate", datetime), ("MessageBoxId", int),
               ("SubscriptionId", int),
               ("DeleteAfterSent", bool), ("Enabled", bool), ("SubscriberId", int),
               ("SubscriberTypeName", str), ("SubscriberInstanceName", str),
               ("TransformName", str), ("MessageData", bytearray)]

    def __init__(self):
        self.id = None
        self.CustomData = None
        self.SentDate = None
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


class MessageSubscriptionArchiveData(object):
    columns = [("CustomData", str), ("SentDate", datetime),
               ("NoOfSendTries", int), ("MessageBoxId", int), ("SubscriptionId", int)]

    def __init__(self, OrigId=None, CustomData=None, SentDate=None,
                 NoOfSendTries=None, MessageBoxId=None, SubscriptionId=None):
        self.id = None
        self.OrigId = OrigId
        self.CustomData = CustomData
        self.SentDate = SentDate
        self.NoOfSendTries = NoOfSendTries
        self.MessageBoxId = MessageBoxId
        self.SubscriptionId = SubscriptionId


# Non database objects
class LoraRadioMessage(object):
    MessageTypeSIPunch = 0
    MessageTypeLoraAck = 1

    CurrentMessageNumber = 0

    def __init__(self, payloadDataLength=None, messageType=None, batteryLow = False, ackReq = False):
        if payloadDataLength is not None:
            batteryLowBit = 0
            ackReqBit = 0
            if batteryLow:
                batteryLowBit = 1
            if ackReq:
                ackReqBit = 1
            self.messageData = bytearray(pack(LoraRadioMessage.getHeaderFormatString(), bytes([STX]),
                                              bytes([payloadDataLength]),
                                              bytes([(ackReqBit << 7) | (batteryLowBit << 6) | messageType]),
                                              bytes([LoraRadioMessage.CurrentMessageNumber]),
                                              bytes([0])))
            LoraRadioMessage.CurrentMessageNumber = LoraRadioMessage.CurrentMessageNumber + 1
        else:
            self.messageData = bytearray()

    @staticmethod
    def getHeaderFormatString():
        return "<ccccc"

    @staticmethod
    def GetHeaderSize():
        return calcsize(LoraRadioMessage.getHeaderFormatString())

    def GetMessageType(self):
        if len(self.messageData) >= 3:
            return self.messageData[2] & 0x3F
        return None

    def GetIsChecksumOK(self):
        if self.IsFilled():
            crcInMessage = self.messageData[4]
            self.messageData[4] = 0
            calculatedCrc = Utils.CalculateCRC(self.messageData)
            oneByteCalculatedCrc = calculatedCrc[0] ^ calculatedCrc[1]
            isOK = (crcInMessage == oneByteCalculatedCrc)
            self.messageData[4] = crcInMessage #restore the message
            return isOK
        return False

    def UpdateChecksum(self):
        if self.IsFilled():
            self.messageData[4] = 0
            crc = Utils.CalculateCRC(self.messageData)
            self.messageData[4] = crc[0] ^ crc[1]
            return True
        return False

    def IsFilled(self):
        if len(self.messageData) >= 2:
            if len(self.messageData) == self.messageData[1] + 5:
                return True
        return False

    def GetByteArray(self):
        return self.messageData

    def AddByte(self, newByte):
        if self.IsFilled():
            logging.error("Error, trying to fill RadioMessageData with bytes, but it is already full")
        else:
            self.messageData.append(newByte)

    def AddPayload(self, payloadArray):
        self.messageData.extend(payloadArray)
        self.UpdateChecksum()


#--
class PunchData(object):
    columns = [("siCardNumber", int), ("twentyFourHour", int), ("weekDay", int),
               ("fourWeekCounter", int), ("twelveHourTimer", int), ("subSecond", int),
               ("origFromNode", int), ("radioMessageId", int), ("sentToMeos", bool),
               ("stationNumberNotFound", bool),
               ("createdDate", datetime)]

    def __init__(self):
        self.id = None
        self.siCardNumber = None
        self.twentyFourHour = 0
        self.weekDay = 0
        self.fourWeekCounter = 0
        self.twelveHourTimer = 0
        self.subSecond = 0
        self.origFromNode = None
        self.radioMessageId = None
        self.createdDate = None
        self.sentToMeos = False
        self.stationNumberNotFound = False

    @staticmethod
    def getFormatString():
        return "<icHc"

    @staticmethod
    def GetSize():
        return calcsize(PunchData.getFormatString())


    def GetByteArray(self):
        twentyFourHourAndWeekDayAndForWeekAndFill = self.twentyFourHour | self.weekDay << 1 | \
            self.fourWeekCounter << 4
        byteArr = bytearray(pack(self.getFormatString(), self.siCardNumber,
                                 bytes([twentyFourHourAndWeekDayAndForWeekAndFill]), self.twelveHourTimer, bytes([self.subSecond])))
        return byteArr

    def UpdateFromByteArray(self, byteArr):
        if len(byteArr) == self.GetSize():
            siCardNumber, twentyFourHourAndWeekDayAndForWeekAndFill, \
                twelveHourTimer, subSecond = unpack(self.getFormatString(), byteArr)
            origFromNode = None
        else:
            siCardNumber, twentyFourHourAndWeekDayAndForWeekAndFill, \
                twelveHourTimer, subSecond, origFromNode = unpack(self.getFormatString() + "c", byteArr)

        self.siCardNumber = siCardNumber
        self.twentyFourHour = (twentyFourHourAndWeekDayAndForWeekAndFill[0]) & 0x01
        self.weekDay = (twentyFourHourAndWeekDayAndForWeekAndFill[0] >> 1) & 0x07
        self.fourWeekCounter = (twentyFourHourAndWeekDayAndForWeekAndFill[0] >> 4) & 0x03
        self.twelveHourTimer = twelveHourTimer
        self.subSecond = subSecond[0]
        if origFromNode is not None:
            self.origFromNode = origFromNode[0]

    def GetMeosByteArray(self, stationNumber):
        punch = 0 # type of data
        codeDay = 0 # obsolete

        #time = (self.fourWeekCounter*6048000) + \
        #       (self.weekDay * 864000) + \
        time = self.twelveHourTimer*10 + int(self.subSecond//25.6)
        if self.twentyFourHour == 1:
            time += 36000*12
        byteArr = bytearray(pack("<cHIII", bytes([punch]), stationNumber, self.siCardNumber, codeDay, time))

        return byteArr


class TimeSlotData(object):
    def __init__(self, timeSlotLength = None, nodeNumber = None, messageNumber = None):
        self.timeSlotLength = timeSlotLength  #: 3;
        self.nodeNumber = nodeNumber #: 5;
        self.messageNumber = messageNumber

    @staticmethod
    def getFormatString():
        return "<cc"

    @staticmethod
    def GetSize():
        return calcsize(TimeSlotData.getFormatString())

    def GetByteArray(self):
        timeSlotLengthAndNodeNumber = self.timeSlotLength | self.nodeNumber << 3
        byteArr = bytearray(pack(self.getFormatString(),
                                 bytes([timeSlotLengthAndNodeNumber]),
                                 bytes([self.messageNumber])))
        return byteArr

    def UpdateFromByteArray(self, byteArr):
        timeSlotLengthAndNodeNumber, self.messageNumber = unpack(self.getFormatString(), byteArr)
        self.timeSlotLength = timeSlotLengthAndNodeNumber & 0x07
        self.nodeNumber = (timeSlotLengthAndNodeNumber >> 3) & 0x1F


class RadioMessageSimpleAckData(object):
    def __init__(self):
        self.stx = STX
        self.dataLength = 0
        self.messageVersion = RADIO_MESSAGE_SIMPLE_ACK_VERSION
        self.messageNumberToAck = 0
        self.checkSum = 0x00
        self.theInByteArray = bytearray([])

    @staticmethod
    def getFormatString():
        return "<cccc"

    @staticmethod
    def GetSize():
        return calcsize(RadioMessageSimpleAckData.getFormatString())

    def AddByte(self, newByte):
        if self.theInByteArray == None:
            logging.error("Error, trying to fill RadioMessageData with bytes, but it is already full")
        else:
            self.theInByteArray.append(newByte)
            self.updateMessageFromTheInByteArray()

    def ShouldAddMoreBytes(self):
        if self.theInByteArray == None:
            return False
        else:
            return True

    def IsUnInitialized(self):
        if (len(self.theInByteArray) == 0):
            return True
        else:
            return False

    def GetByteArray(self):
        dataLengthAndMessageVersion = self.dataLength | self.messageVersion << 6
        byteArr = bytearray(pack(self.getFormatString(), bytes([self.stx]), bytes([dataLengthAndMessageVersion]),
                                 bytes([self.messageNumberToAck]), bytes([self.checkSum])))
        return byteArr

    def updateMessageFromTheInByteArray(self):
        if len(self.theInByteArray) == RadioMessageSimpleAckData.GetSize():
            self.stx, dataLengthAndMessageVersion, self.messageNumberToAck, self.checkSum = \
                unpack(self.getFormatString(), self.theInByteArray)
            self.dataLength = dataLengthAndMessageVersion & 0x3F
            self.messageVersion = (dataLengthAndMessageVersion >> 6) & 0x03
            self.theInByteArray = None

    def UpdateChecksum(self):
        return None

