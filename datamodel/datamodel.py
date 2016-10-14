__author__ = 'henla464'

from datetime import datetime
from struct import *
from constants import *
from utils.utils import Utils

class SettingData(object):
    columns = [("Key", str), ("Value", str)]

    def __init__(self):
        self.id = None
        self.Key = None
        self.Value = None



class RadioMessageData(object):
    columns = [("stx", int), ("dataLength", int), ("messageVersion", int),
               ("fromNode", int), ("messageType", int), ("messageNumber", int),
               ("checkSum", int), ("ackSent", bool), ("radioNumber", int), ("createdDate", datetime)]

    def __init__(self, messageType = None, nodeNumber = None):
        self.id = None
        self.stx = STX
        self.theInByteArray = bytearray([])
        self.createdDate = None
        self.dataRecordArray = None
        self.ackSent = False
        self.createdDate = None
        self.radioNumber = None
        if (messageType == None):
            self.dataLength = None
            self.messageVersion = None
            self.fromNode = None
            self.messageType = None
            self.messageNumber = None
            self.checkSum = None
        else:
            self.dataLength = 0
            self.messageVersion = RADIO_MESSAGE_VERSION
            self.fromNode = nodeNumber
            self.messageType = messageType
            self.messageNumber = 0
            self.checkSum = 0

    def UpdateChecksum(self):
        self.checkSum = 0
        crc = Utils.computeCRC(self.GetByteArray())
        self.checkSum = crc[0] + crc[1]

    def getFormatString(self):
        return "<ccccc"

    def GetHeaderSize(self):
        return calcsize(self.getFormatString())

    def GetByteArray(self):
        dataLengthAndMessageVersion = self.dataLength | self.messageVersion << 6
        fromNodeAndMessageType = self.fromNode | self.messageType << 5
        byteArr = bytearray(pack(self.getFormatString(), bytes([self.stx]),
                                 bytes([dataLengthAndMessageVersion]), bytes([fromNodeAndMessageType]),
                                 bytes([self.messageNumber]), bytes([self.checkSum])))
        for dataRecord in self.dataRecordArray:
            byteArr.extend(dataRecord.GetByteArray())
        return byteArr

    def AddByte(self, newByte):
        print(newByte,end=" ")
        if self.theInByteArray is None:
            print("Error, trying to fill RadioMessageData with bytes, but it is already full")
        else:
            self.theInByteArray.append(newByte)
            self.updateMessageFromTheInByteArray()

    def ShouldAddMoreBytes(self):
        if self.theInByteArray == None:
            return False
        else:
            return True

    def IsUnInitialized(self):
        if len(self.theInByteArray) == 0:
            return True
        else:
            return False

    def updateMessageFromTheInByteArray(self):
        if (len(self.theInByteArray) >= 2):
            stx, dataLengthAndMessageVersion = unpack('<cc', self.theInByteArray[0:2])
            #print("dataLengthAndMessageVersion: ", end="")
            #print(dataLengthAndMessageVersion[0])
            self.stx = stx[0]
            self.dataLength = dataLengthAndMessageVersion[0] & 0x3F
            self.messageVersion = (dataLengthAndMessageVersion[0] >> 6) & 0x03
            if len(self.theInByteArray) >= self.GetHeaderSize() + self.dataLength:
                fromNodeAndMessageType, messageNumber, checkSum = \
                    unpack('<ccc', self.theInByteArray[2:5])
                #print("fromNodeAndMessageType", end="")
                #print(fromNodeAndMessageType)
                self.fromNode = fromNodeAndMessageType[0] & 0x1F
                #print("fromNode: ", end="")
                #print(self.fromNode)
                self.messageType = (fromNodeAndMessageType[0] >> 5) & 0x07
                #print("messageType: ", end="")
                #print(self.messageType)
                self.messageNumber = messageNumber[0]
                self.checkSum = checkSum[0]
                self.dataRecordArray = []
                dataRecordSize = None
                if self.messageType == PUNCH:
                    dataRecordSize = PunchData.GetSize()
                elif self.messageType == ACKS_AND_TIMESLOT:
                    dataRecordSize = TimeSlotData.GetSize()
                elif self.messageType == COMBINED_PUNCH:
                    dataRecordSize = PunchData.GetSize() + 1
                else:
                    print("messageType: " + str(self.messageType))
                    print("dataLength: " + str(self.dataLength))
                    print("datarecordsize: " + str(dataRecordSize))
                for i in range(self.GetHeaderSize() + dataRecordSize,
                               self.GetHeaderSize() + self.dataLength + 1,
                               dataRecordSize):
                    dataRecord = None
                    if self.messageType == PUNCH:
                        dataRecord = PunchData()
                    elif self.messageType == COMBINED_PUNCH:
                        dataRecord = PunchData()
                    elif self.messageType == ACKS_AND_TIMESLOT:
                        dataRecord = TimeSlotData()
                    #print("updating dataRecord " + str(i-dataRecordSize) + " " + str(i))
                    dataRecord.UpdateFromByteArray(self.theInByteArray[i - dataRecordSize:i])
                    self.dataRecordArray.append(dataRecord)
                # mark theInByteArray as used, we will create message only once from bytes
                self.theInByteArray = None


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
        punch = 0
        codeDay = 0
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
            print("Error, trying to fill RadioMessageData with bytes, but it is already full")
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



class ChannelData(object):
    columns = [("FrequencyName", str), ("SpeedName", str),
               ("Frequency", int), ("SlopeCoefficient", float),
               ("M", int), ("RfFactor", int), ("RfBw", int)]

    def __init__(self, FrequencyName = None, SpeedName = None,
                 Frequency = None, SlopeCoefficient = None,
                 M = None, RfFactor = None, RfBw = None):
        self.id = None
        self.FrequencyName = FrequencyName
        self.SpeedName = SpeedName
        self.Frequency = Frequency
        self.SlopeCoefficient = SlopeCoefficient
        self.M = M
        self.RfFactor = RfFactor
        self.RfBw = RfBw

