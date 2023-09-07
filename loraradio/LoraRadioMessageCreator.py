__author__ = 'henla464'

import logging
from utils.utils import Utils
from loraradio.LoraRadioMessageRS import LoraRadioMessageAckRS, \
    LoraRadioMessageStatusRS, LoraRadioMessagePunchReDCoSRS, \
    LoraRadioMessagePunchDoubleReDCoSRS, LoraRadioMessageRS


class LoraRadioMessageCreator(object):
    @staticmethod
    def GetAckMessage(theHash: bytearray) -> LoraRadioMessageAckRS:
        loraAckMessage = LoraRadioMessageAckRS()
        loraAckMessage.SetAckRequested(False)
        loraAckMessage.SetBatteryLow(False)
        loraAckMessage.SetRepeater(False)
        loraAckMessage.AddPayload(theHash)
        loraAckMessage.AddPayload(theHash)
        loraAckMessage.AddPayload(theHash)
        return loraAckMessage

    @staticmethod
    def GetAckMessageByFullMessageData(fullMessageData: bytearray, rssiByte: int = None) -> LoraRadioMessageAckRS:
        loraAckMessage = LoraRadioMessageAckRS()
        loraAckMessage.SetHeader(fullMessageData[0:1])
        loraAckMessage.AddPayload(fullMessageData[1:])
        loraAckMessage.SetRSSIByte(rssiByte)
        return loraAckMessage
    #
    # @staticmethod
    # def GetPunchMessage(batteryLow, ackReq, payload=None):
    #     loraPunchMessage = LoraRadioMessagePunchRS()
    #     loraPunchMessage.SetBatteryLow(batteryLow)
    #     loraPunchMessage.SetAckRequested(ackReq)
    #     if payload is not None:
    #         loraPunchMessage.AddPayload(payload)
    #         loraPunchMessage.GenerateAndAddRSCode()
    #     return loraPunchMessage
    #
    # @staticmethod
    # def GetPunchMessageByFullMessageData(fullMessageData, rssiByte=None):
    #     if len(fullMessageData) < LoraRadioMessagePunchRS.MessageLengths[LoraRadioMessagePunchRS.MessageTypeSIPunch]:
    #         raise Exception('Message data too short for a LoraRadioMessagePunchRS message')
    #     loraPunchMessage = LoraRadioMessagePunchRS()
    #
    #     loraPunchMessage.SetHeader(fullMessageData[0:1])
    #     loraPunchMessage.AddPayload(fullMessageData[1:-LoraRadioMessagePunchRS.NoOfECCBytes])
    #     #print("punchmessage payload: " + Utils.GetDataInHex(fullMessageData[1:-LoraRadioMessagePunchRS.NoOfECCBytes], logging.DEBUG))
    #     loraPunchMessage.AddRSCode(fullMessageData[-LoraRadioMessagePunchRS.NoOfECCBytes:])
    #     loraPunchMessage.SetRSSIByte(rssiByte)
    #     return loraPunchMessage

    # @staticmethod
    # def GetPunchDoubleMessage(batteryLow, ackReq, payload=None):
    #     loraPunchDoubleMessage = LoraRadioMessagePunchDoubleRS()
    #     loraPunchDoubleMessage.SetBatteryLow(batteryLow)
    #     loraPunchDoubleMessage.SetAckRequested(ackReq)
    #     if payload is not None:
    #         loraPunchDoubleMessage.AddPayload(payload)
    #         loraPunchDoubleMessage.GenerateAndAddRSCode()
    #     return loraPunchDoubleMessage
    #
    # @staticmethod
    # def GetPunchDoubleMessageByFullMessageData(fullMessageData, rssiByte=None):
    #     loraPunchDoubleMessage = LoraRadioMessagePunchDoubleRS()
    #     loraPunchDoubleMessage.SetHeader(fullMessageData[0:1])
    #     loraPunchDoubleMessage.AddPayload(fullMessageData[1:-LoraRadioMessagePunchDoubleRS.NoOfECCBytes])
    #     loraPunchDoubleMessage.AddRSCode(fullMessageData[-LoraRadioMessagePunchDoubleRS.NoOfECCBytes:])
    #     loraPunchDoubleMessage.SetRSSIByte(rssiByte)
    #     return loraPunchDoubleMessage

    @staticmethod
    def GetPunchReDCoSMessage(batteryLow: bool, ackReq: bool, payload: bytearray = None) -> LoraRadioMessagePunchReDCoSRS:
        loraPunchMessage = LoraRadioMessagePunchReDCoSRS()
        loraPunchMessage.SetBatteryLow(batteryLow)
        loraPunchMessage.SetAckRequested(ackReq)
        if payload is not None:
            loraPunchMessage.AddPayload(payload)
            loraPunchMessage.GenerateAndAddRSCode()
            loraPunchMessage.GenerateAndAddCRC()
        return loraPunchMessage

    @staticmethod
    def GetPunchReDCoSMessageByFullMessageData(fullMessageDataDeinterleaved: bytearray, rssiByte: int = None) -> LoraRadioMessagePunchReDCoSRS:
        if len(fullMessageDataDeinterleaved) < LoraRadioMessageRS.MessageLengths[LoraRadioMessageRS.MessageTypeSIPunchReDCoS]:
            raise Exception('Message data too short for a LoraRadioMessagePunchRedCoSRS message')
        loraPunchMessage = LoraRadioMessagePunchReDCoSRS()
        loraPunchMessage.SetHeader(fullMessageDataDeinterleaved[0:1])
        loraPunchMessage.AddPayload(fullMessageDataDeinterleaved[1:-LoraRadioMessagePunchReDCoSRS.NoOfECCBytes-LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes])
        # print("punchmessage payload: " + Utils.GetDataInHex(fullMessageDataDeinterleaved[1:-LoraRadioMessagePunchReDCoSRS.NoOfECCBytes-LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes],
        #                                                    logging.DEBUG))
        loraPunchMessage.AddRSCode(fullMessageDataDeinterleaved[-LoraRadioMessagePunchReDCoSRS.NoOfECCBytes-LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes:-LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes])
        loraPunchMessage.AddCRC(fullMessageDataDeinterleaved[-LoraRadioMessagePunchReDCoSRS.NoOfCRCBytes:])
        loraPunchMessage.SetRSSIByte(rssiByte)
        return loraPunchMessage

    @staticmethod
    def GetPunchDoubleReDCoSMessage(batteryLow: bool, ackReq: bool, payload: bytearray = None) -> LoraRadioMessagePunchDoubleReDCoSRS:
        loraPunchDoubleMessage = LoraRadioMessagePunchDoubleReDCoSRS()
        loraPunchDoubleMessage.SetBatteryLow(batteryLow)
        loraPunchDoubleMessage.SetAckRequested(ackReq)
        if payload is not None:
            loraPunchDoubleMessage.AddPayload(payload)
            loraPunchDoubleMessage.GenerateAndAddRSCode()
            loraPunchDoubleMessage.GenerateAndAddCRC()

        return loraPunchDoubleMessage

    @staticmethod
    def GetPunchDoubleReDCoSMessageByFullMessageData(fullMessageDataDeinterleaved: bytearray, rssiByte: int = None) -> LoraRadioMessagePunchDoubleReDCoSRS:
        loraPunchDoubleMessage = LoraRadioMessagePunchDoubleReDCoSRS()
        loraPunchDoubleMessage.SetHeader(fullMessageDataDeinterleaved[0:1])
        loraPunchDoubleMessage.AddPayload(fullMessageDataDeinterleaved[1:-LoraRadioMessagePunchDoubleReDCoSRS.NoOfECCBytes-LoraRadioMessagePunchDoubleReDCoSRS.NoOfCRCBytes])
        loraPunchDoubleMessage.AddRSCode(fullMessageDataDeinterleaved[-LoraRadioMessagePunchDoubleReDCoSRS.NoOfECCBytes-LoraRadioMessagePunchDoubleReDCoSRS.NoOfCRCBytes:-LoraRadioMessagePunchDoubleReDCoSRS.NoOfCRCBytes])
        loraPunchDoubleMessage.AddCRC(fullMessageDataDeinterleaved[-LoraRadioMessagePunchDoubleReDCoSRS.NoOfCRCBytes:])
        loraPunchDoubleMessage.SetRSSIByte(rssiByte)
        return loraPunchDoubleMessage

    @staticmethod
    def GetStatusMessage(batteryLow: bool) -> LoraRadioMessageStatusRS:
        loraStatusMessage = LoraRadioMessageStatusRS()
        loraStatusMessage.SetBatteryLow(batteryLow)
        loraStatusMessage.SetAckRequested(False)
        loraStatusMessage.SetRepeater(False)
        loraStatusMessage.GenerateAndAddRSCode()
        return loraStatusMessage

    @staticmethod
    def GetStatusMessageByFullMessageData(fullMessageData: bytearray, rssiByte: int = None) -> LoraRadioMessageStatusRS:
        loraStatusMessage = LoraRadioMessageStatusRS()
        loraStatusMessage.SetHeader(fullMessageData[0:1])
        loraStatusMessage.SetPayload(fullMessageData[1:-LoraRadioMessageStatusRS.NoOfECCBytes])
        loraStatusMessage.AddRSCode(fullMessageData[-LoraRadioMessageStatusRS.NoOfECCBytes:])
        loraStatusMessage.SetRSSIByte(rssiByte)
        return loraStatusMessage
