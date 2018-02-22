from datamodel.datamodel import LoraRadioMessage
from datamodel.datamodel import SIMessage
from battery import Battery
from settings.settings import SettingsClass

class SISIMessageToLoraTransform(object):
    DeleteAfterSent = False

    @staticmethod
    def GetInputMessageType():
        return "SI"

    @staticmethod
    def GetInputMessageSubType():
        return "SIMessage"

    @staticmethod
    def GetOutputMessageType():
        return "LORA"

    @staticmethod
    def GetName():
        return "SISIMessageToLoraTransform"

    @staticmethod
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter):
        if messageBoxData.MessageSource == "WiRoc":
            return SettingsClass.GetLoraMessageTimeSendingTimeS(10+2) # ack 10 bytes + 2 extra
        return 0

    @staticmethod
    def GetDeleteAfterSent():
        # check setting for ack
        SISIMessageToLoraTransform.DeleteAfterSent = not SettingsClass.GetAcknowledgementRequested()
        return SISIMessageToLoraTransform.DeleteAfterSent

    @staticmethod
    def GetDeleteAfterSentChanged():
        return SISIMessageToLoraTransform.DeleteAfterSent != (not SettingsClass.GetAcknowledgementRequested())

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSub, subscriberAdapter):
        payloadData = msgSub.MessageData
        siMsg = SIMessage()
        siMsg.AddPayload(payloadData)
        payloadDataLength = len(payloadData)
        messageType = LoraRadioMessage.MessageTypeSIPunch
        batteryLow = Battery.GetIsBatteryLow()
        ackReq = SettingsClass.GetAcknowledgementRequested()
        loraMessage = LoraRadioMessage(payloadDataLength, messageType, batteryLow, ackReq)
        loraMessage.AddPayload(payloadData)
        loraMessage.SetMessageNumber(msgSub.MessageNumber)
        reqRepeater = subscriberAdapter.GetShouldRequestRepeater()
        loraMessage.SetRepeaterBit(reqRepeater)
        loraMessage.UpdateChecksum()
        return {"Data": loraMessage.GetByteArray(), "MessageID": loraMessage.GetMessageID()}
