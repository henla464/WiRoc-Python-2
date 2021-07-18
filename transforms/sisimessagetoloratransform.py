from battery import Battery
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from loraradio.LoraRadioMessageRS import LoraRadioMessageRS
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
    def GetBatchSize():
        return 2

    @staticmethod
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter):
        if messageBoxData.MessageSource == "WiRoc":
            return SettingsClass.GetLoraMessageTimeSendingTimeSByMessageType(LoraRadioMessageRS.MessageTypeLoraAck)+0.1 # ack 10 bytes + 2 loop
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
        batteryLow = Battery.GetIsBatteryLow()
        ackReq = SettingsClass.GetAcknowledgementRequested()
        loraPunchMsg = LoraRadioMessageCreator.GetPunchMessage(batteryLow, ackReq, None)
        loraPunchMsg.SetSIMessageByteArray(payloadData)
        reqRepeater = subscriberAdapter.GetShouldRequestRepeater()
        loraPunchMsg.SetRepeater(reqRepeater)
        loraPunchMsg.GenerateRSCode()
        return {"Data": loraPunchMsg.GetByteArray(), "MessageID": loraPunchMsg.GetHash()}
