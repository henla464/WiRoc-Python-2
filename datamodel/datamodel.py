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
    columns = [("Name", str), ("InputMessageTypeId", int), ("OutputMessageTypeId", int), ("Enabled", bool)]

    def __init__(self, Name=None, InputMessageTypeId=None, OutputMessageTypeId=None, Enabled=True):
        self.id = None
        self.Name = Name
        self.InputMessageTypeId = InputMessageTypeId
        self.OutputMessageTypeId = OutputMessageTypeId
        self.Enabled = Enabled


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
    columns = [("CustomData", str), ("SentDate", datetime), ("SendFailedDate", datetime),
               ("FindAdapterTryDate", datetime), ("FindAdapterTries", int),
               ("NoOfSendTries", int), ("AckReceivedDate", datetime), ("MessageBoxId", int),
               ("SubscriptionId", int)]

    def __init__(self, CustomData=None, SentDate=None, SendFailedDate=None,
                 FindAdapterTryDate=None,FindAdapterTries=0, AckReceivedDate=None,
                 NoOfSendTries=0, MessageBoxId=None, SubscriptionId=None):
        self.id = None
        self.CustomData = CustomData
        self.SentDate = SentDate
        self.SendFailedDate = SendFailedDate
        self.NoOfSendTries = NoOfSendTries
        self.FindAdapterTryDate = FindAdapterTryDate
        self.FindAdapterTries = FindAdapterTries
        self.AckReceivedDate = AckReceivedDate
        self.MessageBoxId = MessageBoxId
        self.SubscriptionId = SubscriptionId


class MessageSubscriptionArchiveData(object):
    columns = [ ("OrigId", int), ("CustomData", str),
                ("SentDate", datetime), ("SendFailedDate", datetime),
                ("FindAdapterTryDate", datetime),("FindAdapterTries", int),
                ("NoOfSendTries", int), ("AckReceivedDate", datetime),
                ("MessageBoxId", int), ("SubscriptionId", int)]

    def __init__(self, CustomData=None, SentDate=None, SendFailedDate=None,
                 FindAdapterTryDate=None,FindAdapterTries=0, AckReceivedDate=None,
                 NoOfSendTries=0, MessageBoxId=None, SubscriptionId=None):
        self.id = None
        self.CustomData = CustomData
        self.SentDate = SentDate
        self.SendFailedDate = SendFailedDate
        self.FindAdapterTryDate = FindAdapterTryDate
        self.FindAdapterTries = FindAdapterTries
        self.NoOfSendTries = NoOfSendTries
        self.AckReceivedDate = AckReceivedDate
        self.MessageBoxId = MessageBoxId
        self.SubscriptionId = SubscriptionId


class MessageSubscriptionView(object):
    columns = [("CustomData", str), ("SentDate", datetime), ("SendFailedDate", datetime),
               ("FindAdapterTryDate", datetime), ("FindAdapterTries", int),
               ("NoOfSendTries", int), ("AckReceivedDate", datetime), ("MessageBoxId", int),
               ("SubscriptionId", int),
               ("DeleteAfterSent", bool), ("Enabled", bool), ("SubscriberId", int),
               ("SubscriberTypeName", str), ("SubscriberInstanceName", str),
               ("TransformName", str), ("MessageData", bytearray)]

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

class SubscriberView(object):
    columns = [("TypeName", str), ("InstanceName", str), ("Enabled", bool), ("MessageInName", str), ("MessageOutName", str)]

    def __init__(self):
        self.id = None
        self.TypeName = None
        self.InstanceName = None
        self.Enabled = False
        self.MessageInName = None
        self.MessageOutName = None

class InputAdapterInstances(object):
    columns = [("TypeName", str), ("InstanceName", str), ("ToBeDeleted", bool)]

    def __init__(self):
        self.id = None
        self.TypeName = None
        self.InstanceName = None
        self.ToBeDeleted = False

class BlenoPunchData(object):
    columns = [("StationNumber", int), ("SICardNumber", int), ("TwentyFourHour", int), ("TwelveHourTime", int), ("SubSecond", int)]

    def __init__(self):
        self.id = None
        self.StationNumber = None
        self.SICardNumber = None
        self.TwentyFourHour = None
        self.TwelveHourTime = None
        self.SubSecond = None

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
            LoraRadioMessage.CurrentMessageNumber = (LoraRadioMessage.CurrentMessageNumber + 1) % 256
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


