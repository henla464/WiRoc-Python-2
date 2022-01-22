__author__ = 'henla464'

from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator


class MessageHelper:
    @staticmethod
    def GetLowBatterySIPayload(messageTypeName, messageSubTypeName, data):
        lowBattery = None
        siPayloadData = None
        if messageTypeName == "LORA" and messageSubTypeName == "SIMessage":
            loraPunchMessage = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(data)
            lowBattery = loraPunchMessage.GetBatteryLow()
            siPayloadData = loraPunchMessage.GetSIMessageByteArray()
        elif messageTypeName == "REPEATER" and messageSubTypeName == "SIMessage":
            loraPunchMessage = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(data)
            lowBattery = loraPunchMessage.GetBatteryLow()
            siPayloadData = loraPunchMessage.GetSIMessageByteArray()
        elif messageTypeName == "LORA" and messageSubTypeName == "SIMessageDouble":
            loraPunchMessage = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(data)
            lowBattery = loraPunchMessage.GetBatteryLow()
            siPayloadData = loraPunchMessage.GetSIMessageByteTuple()[0]
        elif messageTypeName == "REPEATER" and messageSubTypeName == "SIMessageDouble":
            loraPunchMessage = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(data)
            lowBattery = loraPunchMessage.GetBatteryLow()
            siPayloadData = loraPunchMessage.GetSIMessageByteTuple()[0]
        elif messageSubTypeName == "SIMessage":
            # source WiRoc, SIStation
            siPayloadData = data
        elif messageSubTypeName == "Test":
            # source recievetestpunches adapter
            siPayloadData = data

        return lowBattery, siPayloadData
