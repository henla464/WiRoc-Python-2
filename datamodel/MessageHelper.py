__author__ = 'henla464'

from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from datamodel.datamodel import SIMessage, SRRMessage, SRRBoardPunch, AirPlusPunch, AirPlusPunchOneOfMultiple
from datamodel.datamodel import MessageBoxData, RepeaterMessageBoxData
from loraradio.LoraRadioMessageRS import LoraRadioMessagePunchDoubleReDCoSRS, LoraRadioMessagePunchReDCoSRS, LoraRadioMessageAckRS, LoraRadioMessageStatusRS, LoraRadioMessageStatus2RS
from typing import Union


class MessageHelper:
    @staticmethod
    def GetMessageBoxData(messageSource: str, messageTypeName: str, messageSubTypeName: str, instanceName: str, powerCycle: int, SIStationSerialNumber: str,
                          loraMessage: LoraRadioMessagePunchReDCoSRS | LoraRadioMessagePunchDoubleReDCoSRS | LoraRadioMessageAckRS | LoraRadioMessageStatusRS
                                       | LoraRadioMessageStatus2RS | None,
                          messageData: bytearray) -> MessageBoxData:
        siPayloadData = None
        siPayloadData2 = None

        mbd = MessageBoxData()
        mbd.MessageData = messageData
        mbd.MessageTypeName = messageTypeName
        mbd.PowerCycleCreated = powerCycle
        mbd.InstanceName = instanceName
        mbd.MessageSubTypeName = messageSubTypeName
        mbd.MessageSource = messageSource
        mbd.SIStationSerialNumber = SIStationSerialNumber

        if loraMessage is not None:
            mbd.RSSIValue = loraMessage.GetRSSIValue()
            mbd.lowBattery = loraMessage.GetBatteryLow()
            mbd.ackRequested = loraMessage.GetAckRequested()
            mbd.repeater = loraMessage.GetRepeater()

        if messageTypeName == "LORA" and messageSubTypeName == "SIMessage":
            siPayloadData = loraMessage.GetSIMessageByteArray()
        elif messageTypeName == "REPEATER" and messageSubTypeName == "SIMessage":
            siPayloadData = loraMessage.GetSIMessageByteArray()
        elif messageTypeName == "LORA" and messageSubTypeName == "SIMessageDouble":
            siPayloadData = loraMessage.GetSIMessageByteTuple()[0]
            siPayloadData2 = loraMessage.GetSIMessageByteTuple()[1]
        elif messageTypeName == "REPEATER" and messageSubTypeName == "SIMessageDouble":
            siPayloadData = loraMessage.GetSIMessageByteTuple()[0]
            siPayloadData2 = loraMessage.GetSIMessageByteTuple()[1]
        elif messageSubTypeName == "SIMessage":
            # source WiRoc, SIStation
            siPayloadData = messageData
        elif messageSubTypeName == "SRRMessage":
            siMsg = SIMessage()
            srrMessage = SRRMessage()
            headerSize: int = SRRMessage.GetHeaderSize()
            srrMessage.AddPayload(messageData[0:headerSize])
            messageType: int = srrMessage.GetMessageType()
            if messageType == SRRMessage.SRRBoardPunch:
                srrBoardPunch = SRRBoardPunch()
                srrBoardPunch.AddPayload(messageData)
                siMsg = srrBoardPunch.GetSIMessage()
            elif messageType == SRRMessage.AirPlusPunch:
                airPlusPunch = AirPlusPunch()
                airPlusPunch.AddPayload(messageData)
                siMsg = airPlusPunch.GetSIMessage()
            elif messageType == SRRMessage.AirPlusPunchOneOfMultiple:
                airPlusPunchOneOfMultiple = AirPlusPunchOneOfMultiple()
                airPlusPunchOneOfMultiple.AddPayload(messageData)
                siMsg = airPlusPunchOneOfMultiple.GetSIMessage()

            siPayloadData = siMsg.GetByteArray()
            mbd.RSSIValue = messageData[-3]
            mbd.ChecksumOK = messageData[-2] & 0x80
            linkQuality = messageData[-2] & 0x7F
            channel = messageData[-1]
        elif messageSubTypeName == "Test":
            # source recievetestpunches adapter
            siPayloadData = messageData

        if siPayloadData is not None:
            siMsg = SIMessage()
            siMsg.AddPayload(siPayloadData)
            mbd.SICardNumber = siMsg.GetSICardNumber()
            mbd.SportIdentHour = siMsg.GetHour()
            mbd.SportIdentMinute = siMsg.GetMinute()
            mbd.SportIdentSecond = siMsg.GetSeconds()
            mbd.MemoryAddress = siMsg.GetBackupMemoryAddressAsInt()
            mbd.SIStationNumber = siMsg.GetStationNumber()
        if siPayloadData2 is not None:
            siMsg = SIMessage()
            siMsg.AddPayload(siPayloadData2)
            mbd.SICardNumber2 = siMsg.GetSICardNumber()
            mbd.SportIdentHour2 = siMsg.GetHour()
            mbd.SportIdentMinute2 = siMsg.GetMinute()
            mbd.SportIdentSecond2 = siMsg.GetSeconds()
            mbd.SIStationNumber2 = siMsg.GetStationNumber()

        if mbd.ChecksumOK is None:
            mbd.ChecksumOK = True

        return mbd

    @staticmethod
    def GetRepeaterMessageBoxData(messageSource: str, messageTypeName: str, messageSubTypeName: str, instanceName: str,
                                         checksumOK: bool,
                                         powerCycle: int, serialNumber: str,
                                         loraMessage: LoraRadioMessagePunchReDCoSRS | LoraRadioMessagePunchDoubleReDCoSRS | LoraRadioMessageAckRS
                                                      | LoraRadioMessageStatusRS | LoraRadioMessageStatus2RS | None,
                                         messageData: bytearray,
                                         messageID: bytearray | None):

        siPayloadData = None
        siPayloadData2 = None

        if messageTypeName == "LORA" and messageSubTypeName == "SIMessage":
            siPayloadData = loraMessage.GetSIMessageByteArray()
        elif messageTypeName == "LORA" and messageSubTypeName == "SIMessageDouble":
            siPayloadData = loraMessage.GetSIMessageByteTuple()[0]
            siPayloadData2 = loraMessage.GetSIMessageByteTuple()[1]

        rmbd = RepeaterMessageBoxData()
        rmbd.MessageData = messageData
        rmbd.MessageTypeName = messageTypeName
        rmbd.PowerCycleCreated = powerCycle
        rmbd.ChecksumOK = checksumOK
        rmbd.InstanceName = instanceName
        rmbd.MessageSubTypeName = messageSubTypeName
        rmbd.MessageSource = messageSource
        rmbd.SIStationSerialNumber = serialNumber
        rmbd.NoOfTimesSeen = 1
        rmbd.NoOfTimesAckSeen = 0
        rmbd.SIStationNumber = None
        rmbd.SIStationSerialNumber = None
        rmbd.MessageID = messageID
        if loraMessage is not None:
            rmbd.RSSIValue = loraMessage.GetRSSIValue()
            rmbd.LowBattery = loraMessage.GetBatteryLow()
            rmbd.AckRequested = loraMessage.GetAckRequested()
            rmbd.RepeaterRequested = loraMessage.GetRepeater()

        if siPayloadData is not None:
            siMsg = SIMessage()
            siMsg.AddPayload(siPayloadData)
            rmbd.SICardNumber = siMsg.GetSICardNumber()
            rmbd.SportIdentHour = siMsg.GetHour()
            rmbd.SportIdentMinute = siMsg.GetMinute()
            rmbd.SportIdentSecond = siMsg.GetSeconds()
            rmbd.SIStationNumber = siMsg.GetStationNumber()

        if siPayloadData2 is not None:
            siMsg = SIMessage()
            siMsg.AddPayload(siPayloadData2)
            rmbd.SICardNumber2 = siMsg.GetSICardNumber()
            rmbd.SportIdentHour2 = siMsg.GetHour()
            rmbd.SportIdentMinute2 = siMsg.GetMinute()
            rmbd.SportIdentSecond2 = siMsg.GetSeconds()
            rmbd.SIStationNumber2 = siMsg.GetStationNumber()

        return rmbd