from datamodel.datamodel import LoraRadioMessage
from datamodel.datamodel import SIMessage
from battery import Battery
from settings.settings import SettingsClass

class RepeaterSIMessageToLoraTransform(object):
    DeleteAfterSent = False

    @staticmethod
    def GetInputMessageType():
        return "REPEATER"

    @staticmethod
    def GetInputMessageSubType():
        return "SIMessage"

    @staticmethod
    def GetOutputMessageType():
        return "LORA"

    @staticmethod
    def GetName():
        return "RepeaterSIMessageToLoraTransform"

    @staticmethod
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter):
        loraRadioMessage = LoraRadioMessage()
        loraRadioMessage.AddPayload(messageBoxData.MessageData)
        if loraRadioMessage.GetRepeaterBit():
            # no ack expected from receiver, should be sent after repeater sent ack
            return 0
        else:
            # possible ack from receiver 10 + ack sent from repeater 10
            # since we are repeater we don't need to wait until repeater finished
            # sending, only until receiver finished sending ack, add 2 extra loop
            return SettingsClass.GetLoraMessageTimeSendingTimeS(20)+0.1

    @staticmethod
    def GetDeleteAfterSent():
        # check setting for ack
        RepeaterSIMessageToLoraTransform.DeleteAfterSent = not SettingsClass.GetAcknowledgementRequested()
        return RepeaterSIMessageToLoraTransform.DeleteAfterSent

    @staticmethod
    def GetDeleteAfterSentChanged():
        return RepeaterSIMessageToLoraTransform.DeleteAfterSent != (not SettingsClass.GetAcknowledgementRequested())

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSub, subscriberAdapter):
        payloadData = msgSub.MessageData
        loraMsg = LoraRadioMessage()
        loraMsg.AddPayload(payloadData)
        batteryLow = Battery.GetIsBatteryLow() or loraMsg.GetBatteryLowBit()
        ackReq = SettingsClass.GetAcknowledgementRequested()
        loraMsg.SetAcknowledgementRequested(ackReq)
        loraMsg.SetBatteryLowBit(batteryLow)
        loraMsg.SetMessageNumber(msgSub.MessageNumber)
        loraMsg.SetRepeaterBit(False)
        loraMsg.UpdateChecksum()
        return {"Data": loraMsg.GetByteArray(), "MessageID": loraMsg.GetMessageID()}
