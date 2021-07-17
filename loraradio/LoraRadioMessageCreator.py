__author__ = 'henla464'

from loraradio.LoraRadioMessageRS import LoraRadioMessageAckRS, LoraRadioMessagePunchRS, \
    LoraRadioMessageStatusRS


class LoraRadioMessageCreator(object):

    @staticmethod
    def GetAckMessage(hash):
        loraAckMessage = LoraRadioMessageAckRS()
        loraAckMessage.SetAckRequested(False)
        loraAckMessage.SetBatteryLow(False)
        loraAckMessage.SetRepeater(False)
        loraAckMessage.AddPayload(hash)
        loraAckMessage.GenerateRSCode()
        return loraAckMessage\

    @staticmethod
    def GetAckMessageByFullMessageData(fullMessageData, rssiByte=None):
        loraAckMessage = LoraRadioMessageAckRS()
        loraAckMessage.SetHeader(fullMessageData[0:1])
        loraAckMessage.AddPayload(fullMessageData[1:-4])
        loraAckMessage.AddRSCode(fullMessageData[-4:])
        loraAckMessage.SetRSSIByte(rssiByte)
        return loraAckMessage

    @staticmethod
    def GetPunchMessage(batteryLow, ackReq, payload = None):
        loraPunchMessage = LoraRadioMessagePunchRS()
        loraPunchMessage.SetBatteryLow(batteryLow)
        loraPunchMessage.SetAckRequested(ackReq)
        if payload is not None:
            loraPunchMessage.AddPayload(payload)
            loraPunchMessage.GenerateRSCode()
        return loraPunchMessage

    @staticmethod
    def GetPunchMessageByFullMessageData(fullMessageData, rssiByte = None):
        loraPunchMessage = LoraRadioMessagePunchRS()
        loraPunchMessage.SetHeader(fullMessageData[0:1])
        loraPunchMessage.AddPayload(fullMessageData[1:-4])
        loraPunchMessage.AddRSCode(fullMessageData[-4:])
        loraPunchMessage.SetRSSIByte(rssiByte)
        return loraPunchMessage

    @staticmethod
    def GetStatusMessage(batteryLow):
        loraStatusMessage = LoraRadioMessageStatusRS()
        loraStatusMessage.SetBatteryLow(batteryLow)
        loraStatusMessage.SetAckRequested(False)
        loraStatusMessage.SetRepeater(False)
        loraStatusMessage.GenerateRSCode()
        return loraStatusMessage

    @staticmethod
    def GetStatusMessageByFullMessageData(fullMessageData, rssiByte = None):
        loraStatusMessage = LoraRadioMessageStatusRS()
        loraStatusMessage.SetHeader(fullMessageData[0:1])
        loraStatusMessage.AddPayload(fullMessageData[1:-4])
        loraStatusMessage.AddRSCode(fullMessageData[-4:])
        loraStatusMessage.SetRSSIByte(rssiByte)
        return loraStatusMessage
