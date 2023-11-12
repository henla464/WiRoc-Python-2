__author__ = 'henla464'

from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from datamodel.datamodel import SIMessage
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
            siMsg.AddHeader(SIMessage.SIPunch)
            siMsg.AddPayload(messageData[18:31])
            siMsg.AddFooter()
            siPayloadData = siMsg.GetByteArray()
            mbd.ChecksumOK = messageData[32] & 0x80
            mbd.RSSIValue = messageData[31]
            linkQuality = messageData[32] & 0x7F
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
