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
    columns = [("Channel", int), ("DataRate", int),  ("LoraRange", str),
               ("Frequency", int), ("SlopeCoefficient", int),
               ("M", int), ("RfFactor", int), ("RfBw", int), ("LoraModem", str)]

    def __init__(self, Channel=None, DataRate=None, LoraRange=None,
                 Frequency=None, SlopeCoefficient=None,
                 M=None, RfFactor=None, RfBw=None, LoraModem=None):
        self.id = None
        self.Channel = Channel
        self.DataRate = DataRate
        self.LoraRange = LoraRange
        self.Frequency = Frequency
        self.SlopeCoefficient = SlopeCoefficient
        self.M = M
        self.RfFactor = RfFactor
        self.RfBw = RfBw
        self.LoraModem = LoraModem


class MessageBoxData(object):
    columns = [("MessageData", bytearray), ("PowerCycleCreated", int),
               ("MessageTypeName", str), ("InstanceName", str),
               ("MessageSubTypeName", str),("MemoryAddress", int),
               ("SICardNumber", str),
               ("SIStationSerialNumber", str), ("SportIdentHour", str),
               ("SportIdentMinute", str), ("SportIdentSecond", str),
               ("SIStationNumber", str),("LowBattery", str),("RSSIValue", int),
               ("ChecksumOK", bool), ("CreatedDate", datetime)]

    def __init__(self):
        self.id = None
        self.MessageData = None
        self.PowerCycleCreated = None
        self.MessageTypeName = None
        self.InstanceName = None
        self.MessageSubTypeName = None
        self.MemoryAddress = None
        self.SICardNumber = None
        self.SIStationSerialNumber = None
        self.SportIdentHour = None
        self.SportIdentMinute = None
        self.SportIdentSecond = None
        self.SIStationNumber = None
        self.LowBattery = None
        self.RSSIValue = None
        self.ChecksumOK = None
        self.CreatedDate = None


class MessageBoxArchiveData(object):
    columns = [("OrigId", int), ("MessageData", bytes), ("PowerCycleCreated", int),
               ("MessageTypeName", str), ("InstanceName", str),
               ("MessageSubTypeName", str),("MemoryAddress", int),
               ("SICardNumber", str),
               ("SIStationSerialNumber", str), ("SportIdentHour", str),
               ("SportIdentMinute", str), ("SportIdentSecond", str),
               ("SIStationNumber", str),("LowBattery", str),("RSSIValue", int),
               ("ChecksumOK", bool), ("CreatedDate", datetime)]

    def __init__(self):
        self.id = None
        self.OrigId = None
        self.MessageData = None
        self.PowerCycleCreated = None
        self.MessageTypeName = None
        self.InstanceName = None
        self.MessageSubTypeName = None
        self.MemoryAddress = None
        self.SICardNumber = None
        self.SIStationSerialNumber = None
        self.SportIdentHour = None
        self.SportIdentMinute = None
        self.SportIdentSecond = None
        self.SIStationNumber = None
        self.LowBattery = None
        self.RSSIValue = None
        self.ChecksumOK = None
        self.CreatedDate = None


class RepeaterMessageBoxData(object):
    columns = [("MessageData", bytes), ("MessageTypeName", str), ("PowerCycleCreated", int),
               ("InstanceName", str), ("MessageSubTypeName", str), ("ChecksumOK", bool),
               ("MessageSource", str), ("SICardNumber", int), ("SportIdentHour", int),
               ("SportIdentMinute", int), ("SportIdentSecond", int), ("MessageID", bytes),
               ("AckRequested", bool),("MemoryAddress", int), ("SIStationNumber", int),
               ("RepeaterRequested", bool), ("NoOfTimesSeen", int), ("NoOfTimesAckSeen", int),
               ("Acked", bool), ("AckedTime", datetime), ("MessageBoxId", int),("RSSIValue", int),("AckRSSIValue", int),
               ("LastSeenTime", datetime), ("CreatedDate", datetime)]

    def __init__(self):
        self.id = None
        self.MessageData = None
        self.MessageTypeName = None
        self.PowerCycleCreated = None
        self.InstanceName = None
        self.MessageSubTypeName = None
        self.ChecksumOK = None
        self.MessageSource = None
        self.SICardNumber = None
        self.SportIdentHour = None
        self.SportIdentMinute = None
        self.SportIdentSecond = None
        self.MessageID = None
        self.AckRequested = None
        self.MemoryAddress = None
        self.SIStationNumber = None
        self.RepeaterRequested = None
        self.NoOfTimesSeen = None
        self.NoOfTimesAckSeen = None
        self.Acked = False
        self.AckedTime = None
        self.MessageBoxId = None
        self.RSSIValue = None
        self.AckRSSIValue = None
        self.AddedToMessageBoxTime = None
        self.LastSeenTime = None
        self.CreatedDate = None

class RepeaterMessageBoxArchiveData(object):
    columns = [("OrigId", int) ,("MessageData", bytes), ("MessageTypeName", str), ("PowerCycleCreated", int),
               ("InstanceName", str), ("MessageSubTypeName", str), ("ChecksumOK", bool),
               ("MessageSource", str), ("SICardNumber", int), ("SportIdentHour", int),
               ("SportIdentMinute", int), ("SportIdentSecond", int), ("MessageID", bytes),
               ("AckRequested", bool),
               ("RepeaterRequested", bool), ("NoOfTimesSeen", int), ("NoOfTimesAckSeen", int),
               ("Acked", bool), ("AckedTime", datetime), ("MessageBoxId", int), ("RSSIValue", int), ("AckRSSIValue", int),
               ("AddedToMessageBoxTime", datetime), ("LastSeenTime", datetime), ("OrigCreatedDate", datetime),
               ("CreatedDate", datetime)]

    def __init__(self):
        self.id = None
        self.OrigId = None
        self.MessageData = None
        self.MessageTypeName = None
        self.PowerCycleCreated = None
        self.InstanceName = None
        self.MessageSubTypeName = None
        self.ChecksumOK = None
        self.MessageSource = None
        self.SICardNumber = None
        self.SportIdentHour = None
        self.SportIdentMinute = None
        self.SportIdentSecond = None
        self.MessageID = None
        self.AckRequested = None
        self.RepeaterRequested = None
        self.NoOfTimesSeen = None
        self.NoOfTimesAckSeen = None
        self.Acked = False
        self.AckedTime = None
        self.MessageBoxId = None
        self.RSSIValue = None
        self.AckRSSIValue = None
        self.AddedToMessageBoxTime = None
        self.LastSeenTime = None
        self.OrigCreatedDate = None
        self.CreatedDate = None

class SubscriberData(object):
    columns = [("TypeName", str), ("InstanceName", str)]

    def __init__(self, TypeName=None, InstanceName=None):
        self.id = None
        self.TypeName = TypeName
        self.InstanceName = InstanceName


class MessageTypeData(object):
    columns = [("Name", str), ("MessageSubTypeName", str)]

    def __init__(self, Name=None, MessageSubTypeName=None):
        self.id = None
        self.Name = Name
        self.MessageSubTypeName = MessageSubTypeName


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
               ("BatchSize", int)]

    def __init__(self, DeleteAfterSent=None, Enabled=None,
                 SubscriberId=None, TransformId=None, BatchSize=1):
        self.id = None
        self.DeleteAfterSent = DeleteAfterSent
        self.Enabled = Enabled
        self.SubscriberId = SubscriberId
        self.TransformId = TransformId
        self.BatchSize = BatchSize


class SubscriptionViewData(object):
    columns = [("DeleteAfterSent", bool), ("Enabled", bool),
               ("SubscriberId", int), ("TransformId", int),
               ("TransformName", str), ("SubscriberTypeName", str)]

    def __init__(self):
        self.id = None
        self.DeleteAfterSent = None
        self.Enabled = None
        self.SubscriberId = None
        self.TransformId = None
        self.TransformName = None
        self.SubscriberTypeName = None

class MessageSubscriptionData(object):
    columns = [("MessageID", bytes), ("AckReceivedFromReceiver", bool), ("MessageNumber", int),
               ("SentDate", datetime), ("SendFailedDate", datetime),
               ("FindAdapterTryDate", datetime), ("FindAdapterTries", int),
               ("NoOfSendTries", int), ("AckReceivedDate", datetime),
               ("Delay", int),
               ("RetryDelay", int),
               ("FindAdapterRetryDelay", int),
               ("MessageBoxId", int),
               ("SubscriptionId", int), ("FetchedForSending", datetime)]
    CurrentMessageNumber = 0

    def __init__(self, MessageID=None, AckReceivedFromReceiver=False, MessageNumber=None, SentDate=None, SendFailedDate=None,
                 FindAdapterTryDate=None,FindAdapterTries=0, AckReceivedDate=None,
                 NoOfSendTries=0,
                 Delay=0,
                 RetryDelay=0,
                 FindAdapterRetryDelay=0,
                 MessageBoxId=None, SubscriptionId=None, FetchedForSending=None):
        self.id = None
        self.MessageID = MessageID
        self.AckReceivedFromReceiver = AckReceivedFromReceiver
        self.MessageNumber = MessageNumber
        self.SentDate = SentDate
        self.SendFailedDate = SendFailedDate
        self.NoOfSendTries = NoOfSendTries
        self.FindAdapterTryDate = FindAdapterTryDate
        self.FindAdapterTries = FindAdapterTries
        self.AckReceivedDate = AckReceivedDate
        self.Delay = Delay
        self.RetryDelay = RetryDelay
        self.FindAdapterRetryDelay = FindAdapterRetryDelay
        self.MessageBoxId = MessageBoxId
        self.SubscriptionId = SubscriptionId
        self.FetchedForSending = FetchedForSending

    @staticmethod
    def GetNextMessageNumber():
        MessageSubscriptionData.CurrentMessageNumber = (MessageSubscriptionData.CurrentMessageNumber + 1) % 256
        return MessageSubscriptionData.CurrentMessageNumber


class MessageSubscriptionArchiveData(object):
    columns = [ ("OrigId", int), ("MessageID", bytes), ("MessageNumber", int),
                ("SentDate", datetime), ("SendFailedDate", datetime),
                ("FindAdapterTryDate", datetime),("FindAdapterTries", int),
                ("NoOfSendTries", int), ("AckReceivedDate", datetime),
                ("Delay", int),
                ("RetryDelay", int),
                ("FindAdapterRetryDelay", int),
                ("MessageBoxId", int),
                ("SubscriptionId", int),
                ("AckRSSIValue", int),
                ("SubscriberTypeName", str), ("TransformName", str),]

    def __init__(self):
        self.id = None
        self.MessageID = None
        self.MessageNumber = None
        self.SentDate = None
        self.SendFailedDate = None
        self.FindAdapterTryDate = None
        self.FindAdapterTries = 0
        self.NoOfSendTries = 0
        self.AckReceivedDate = None
        self.MessageBoxId = None
        self.Delay = 0
        self.RetryDelay = 0
        self.FindAdapterRetryDelay = 0
        self.SubscriptionId = None
        self.AckRSSIValue = 0
        self.SubscriberTypeName = None
        self.TransformName = None


class MessageSubscriptionView(object):
    columns = [("MessageID", bytes),  ("AckReceivedFromReceiver", bool),
               ("MessageNumber", int), ("SentDate", datetime), ("SendFailedDate", datetime),
               ("FindAdapterTryDate", datetime), ("FindAdapterTries", int),
               ("NoOfSendTries", int), ("AckReceivedDate", datetime),
               ("Delay", int),
               ("RetryDelay", int),
               ("FindAdapterRetryDelay", int),
               ("MessageBoxId", int), ("SubscriptionId", int), ("BatchSize", int),
               ("FetchedForSending", datetime),
               ("DeleteAfterSent", bool), ("Enabled", bool), ("SubscriberId", int),
               ("SubscriberTypeName", str), ("SubscriberInstanceName", str),
               ("TransformName", str), ("MessageData", bytearray),
               ("CreatedDate", datetime)
               ]

    def __init__(self):
        self.id = None
        self.MessageID = None
        self.AckReceivedFromReceiver = None
        self.MessageNumber = None
        self.SentDate = None
        self.SendFailedDate = None
        self.FindAdapterTryDate = None
        self.FindAdapterTries = None
        self.NoOfSendTries = None
        self.AckReceivedDate = None
        self.Delay = 0
        self.RetryDelay = 0
        self.FindAdapterRetryDelay = 0
        self.MessageBoxId = None
        self.SubscriptionId = None
        self.BatchSize = None
        self.FetchedForSending = None
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
               ("SICardNumber", int), ("Fetched", bool), ("NoOfSendTries", int), ("Status", str), ("AckRSSIValue", int)]

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
        self.AckRSSIValue = 0


class MessageStatsData(object):
        columns = [("AdapterInstanceName", str), ("MessageSubTypeName", str), ("Status", str),
                   ("NoOfMessages", int), ("Uploaded", bool),("FetchedForUpload", datetime),
                   ("CreatedDate", datetime)]

        def __init__(self):
            self.id = None
            self.AdapterInstanceName = None
            self.MessageSubTypeName = None
            self.Status = None
            self.NoOfMessages = None
            self.Uploaded = False
            self.FetchedForUpload = None
            self.CreatedDate = None


class BluetoothSerialPortData(object):
    columns = [("DeviceBTAddress", str),  ("Name", str), ("Status", str)]

    def __init__(self):
        self.id = None
        self.DeviceBTAddress = None
        self.Name = "N/A"
        self.Status = "NotConnected"


class SIMessage(object):
    # 0x02 is used for STX
    # 0x03 is used for ETX
    Status = 0x04 # own/custom message type
    SIPunch = 0xD3

    def __init__(self):
        self.MessageData = bytearray()

    def AddHeader(self, msgType):
        if len(self.MessageData) == 0:
            self.MessageData.append(0x02)
            self.MessageData.append(msgType)
            self.MessageData.append(255)  # set max length temporarily

    @staticmethod
    def GetHeaderSize():
        return 3

    @staticmethod
    def GetFooterSize():
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

    def GetMessageID(self, messageNumber):
        #messageNumber, CN0 SN3 SN2 SN1 SN0
        return bytearray(bytes([messageNumber, self.MessageData[4], self.MessageData[5],
                                self.MessageData[6], self.MessageData[7], self.MessageData[8]]))

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

    def GetBackupMemoryAddressAsInt(self):
        addr = self.MessageData[13] << 16 | self.MessageData[14] << 8 | self.MessageData[15]
        return addr


class MessageSubscriptionBatchItem(object):
    def __init__(self):
        self.id = None
        self.NoOfSendTries = None
        self.MessageData = None


class MessageSubscriptionBatch(object):
    def __init__(self):
        self.AckReceivedFromReceiver = None
        self.DeleteAfterSent = None
        self.SubscriberTypeName = None
        self.SubscriberInstanceName = None
        self.TransformName = None
        self.MessageSubscriptionBatchItems = []

