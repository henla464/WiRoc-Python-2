__author__ = 'henla464'

from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator


class MessageHelper:
    @staticmethod
    def GetLowBatterySIPayload(messageTypeName, messageSubTypeName, data):
        lowBattery = None
        ackRequested = None
        repeater = None
        siPayloadData = None

        if messageTypeName == "LORA" and messageSubTypeName == "SIMessage":
            loraPunchMessage = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(data)
            lowBattery = loraPunchMessage.GetBatteryLow()
            ackRequested = loraPunchMessage.GetAckRequested()
            repeater = loraPunchMessage.GetRepeater()
            siPayloadData = loraPunchMessage.GetSIMessageByteArray()
        elif messageTypeName == "REPEATER" and messageSubTypeName == "SIMessage":
            loraPunchMessage = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(data)
            lowBattery = loraPunchMessage.GetBatteryLow()
            ackRequested = loraPunchMessage.GetAckRequested()
            repeater = loraPunchMessage.GetRepeater()
            siPayloadData = loraPunchMessage.GetSIMessageByteArray()
        elif messageTypeName == "LORA" and messageSubTypeName == "SIMessageDouble":
            loraPunchMessage = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(data)
            lowBattery = loraPunchMessage.GetBatteryLow()
            ackRequested = loraPunchMessage.GetAckRequested()
            repeater = loraPunchMessage.GetRepeater()
            siPayloadData = loraPunchMessage.GetSIMessageByteTuple()[0]
        elif messageTypeName == "REPEATER" and messageSubTypeName == "SIMessageDouble":
            loraPunchMessage = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(data)
            lowBattery = loraPunchMessage.GetBatteryLow()
            ackRequested = loraPunchMessage.GetAckRequested()
            repeater = loraPunchMessage.GetRepeater()
            siPayloadData = loraPunchMessage.GetSIMessageByteTuple()[0]
        elif messageSubTypeName == "SIMessage":
            # source WiRoc, SIStation
            siPayloadData = data
        elif messageSubTypeName == "Test":
            # source recievetestpunches adapter
            siPayloadData = data

        return lowBattery, ackRequested, repeater, siPayloadData
