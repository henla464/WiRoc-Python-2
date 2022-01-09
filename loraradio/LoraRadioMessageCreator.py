__author__ = 'henla464'

import logging
from utils.utils import Utils
from loraradio.LoraRadioMessageRS import LoraRadioMessageAckRS, LoraRadioMessagePunchRS, \
    LoraRadioMessageStatusRS, LoraRadioMessagePunchDoubleRS


class LoraRadioMessageCreator(object):
    @staticmethod
    def GetAckMessage(theHash):
        loraAckMessage = LoraRadioMessageAckRS()
        loraAckMessage.SetAckRequested(False)
        loraAckMessage.SetBatteryLow(False)
        loraAckMessage.SetRepeater(False)
        loraAckMessage.AddPayload(theHash)
        loraAckMessage.GenerateRSCode()
        return loraAckMessage

    @staticmethod
    def GetAckMessageByFullMessageData(fullMessageData, rssiByte=None):
        loraAckMessage = LoraRadioMessageAckRS()
        loraAckMessage.SetHeader(fullMessageData[0:1])
        loraAckMessage.AddPayload(fullMessageData[1:-4])
        loraAckMessage.AddRSCode(fullMessageData[-4:])
        loraAckMessage.SetRSSIByte(rssiByte)
        return loraAckMessage

    @staticmethod
    def GetPunchMessage(batteryLow, ackReq, payload=None):
        loraPunchMessage = LoraRadioMessagePunchRS()
        loraPunchMessage.SetBatteryLow(batteryLow)
        loraPunchMessage.SetAckRequested(ackReq)
        if payload is not None:
            loraPunchMessage.AddPayload(payload)
            loraPunchMessage.GenerateRSCode()
        return loraPunchMessage

    @staticmethod
    def GetPunchMessageByFullMessageData(fullMessageData, rssiByte=None):
        if len(fullMessageData) < 14:
            raise Exception('Message data too short for a LoraRadioMessagePunchRS message')
        loraPunchMessage = LoraRadioMessagePunchRS()
        loraPunchMessage.SetHeader(fullMessageData[0:1])
        loraPunchMessage.AddPayload(fullMessageData[1:-4])
        print("punchmessage payload: " + Utils.GetDataInHex(fullMessageData[1:-4], logging.DEBUG))
        loraPunchMessage.AddRSCode(fullMessageData[-4:])
        loraPunchMessage.SetRSSIByte(rssiByte)
        return loraPunchMessage

    @staticmethod
    def GetPunchDoubleMessage(batteryLow, ackReq, payload=None):
        loraPunchDoubleMessage = LoraRadioMessagePunchDoubleRS()
        loraPunchDoubleMessage.SetBatteryLow(batteryLow)
        loraPunchDoubleMessage.SetAckRequested(ackReq)
        if payload is not None:
            loraPunchDoubleMessage.AddPayload(payload)
            loraPunchDoubleMessage.GenerateRSCode()
        return loraPunchDoubleMessage

    @staticmethod
    def GetPunchDoubleMessageByFullMessageData(fullMessageData, rssiByte=None):
        loraPunchDoubleMessage = LoraRadioMessagePunchDoubleRS()
        loraPunchDoubleMessage.SetHeader(fullMessageData[0:1])
        loraPunchDoubleMessage.AddPayload(fullMessageData[1:-8])
        loraPunchDoubleMessage.AddRSCode(fullMessageData[-8:])
        loraPunchDoubleMessage.SetRSSIByte(rssiByte)
        return loraPunchDoubleMessage

    @staticmethod
    def GetStatusMessage(batteryLow, siStationNumber, batteryPercent):
        loraStatusMessage = LoraRadioMessageStatusRS()
        loraStatusMessage.SetBatteryLow(batteryLow)
        loraStatusMessage.SetAckRequested(False)
        loraStatusMessage.SetRepeater(False)
        loraStatusMessage.GenerateRSCode()
        return loraStatusMessage

    @staticmethod
    def GetStatusMessageByFullMessageData(fullMessageData, rssiByte=None):
        loraStatusMessage = LoraRadioMessageStatusRS()
        loraStatusMessage.SetHeader(fullMessageData[0:1])
        loraStatusMessage.AddPayload(fullMessageData[1:-4])
        loraStatusMessage.AddRSCode(fullMessageData[-4:])
        loraStatusMessage.SetRSSIByte(rssiByte)
        return loraStatusMessage
