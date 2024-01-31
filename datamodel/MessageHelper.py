__author__ = 'henla464'

from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from datamodel.datamodel import SIMessage, SRRMessage, SRRBoardPunch, AirPlusPunch, AirPlusPunchOneOfMultiple
from datamodel.datamodel import MessageBoxData
from loraradio.LoraRadioMessageRS import LoraRadioMessagePunchDoubleReDCoSRS, LoraRadioMessagePunchReDCoSRS, LoraRadioMessageAckRS, LoraRadioMessageStatusRS
from typing import Union


class MessageHelper:
    @staticmethod
    def GetMessageBoxData(messageSource: str, messageTypeName: str, messageSubTypeName: str, instanceName: str, powerCycle: int, SIStationSerialNumber: str,
                          loraMessage: LoraRadioMessagePunchReDCoSRS | LoraRadioMessagePunchDoubleReDCoSRS | LoraRadioMessageAckRS | LoraRadioMessageStatusRS | None,
                          messageData: bytearray) -> MessageBoxData:
        siPayloadData = None

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
            # todo: expand table to store second message punch too
        elif messageTypeName == "REPEATER" and messageSubTypeName == "SIMessageDouble":
            siPayloadData = loraMessage.GetSIMessageByteTuple()[0]
            # todo: expand table to store second message punch too
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

        if mbd.ChecksumOK is None:
            mbd.ChecksumOK = True

        return mbd
