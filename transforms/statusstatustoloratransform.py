from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from settings.settings import SettingsClass
from battery import Battery

class StatusStatusToLoraTransform(object):
    DeleteAfterSent = False

    @staticmethod
    def GetInputMessageType():
        return "STATUS"

    @staticmethod
    def GetInputMessageSubType():
        return "Status"

    @staticmethod
    def GetOutputMessageType():
        return "LORA"

    @staticmethod
    def GetName():
        return "StatusStatusToLoraTransform"

    @staticmethod
    def GetBatchSize():
        return 1

    @staticmethod
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter):
        return 0

    @staticmethod
    def GetDeleteAfterSent():
        StatusStatusToLoraTransform.DeleteAfterSent = not SettingsClass.GetStatusAcknowledgementRequested()
        return StatusStatusToLoraTransform.DeleteAfterSent

    @staticmethod
    def GetDeleteAfterSentChanged():
        return StatusStatusToLoraTransform.DeleteAfterSent != (not SettingsClass.GetStatusAcknowledgementRequested())

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSub, subscriberAdapter):
        payloadData = msgSub.MessageData
        loraStatusMsg = LoraRadioMessageCreator.GetStatusMessageByFullMessageData(payloadData)
        loraStatusMsg.AddThisWiRocToStatusMessage(SettingsClass.GetSIStationNumber(), Battery.GetBatteryPercent4Bits())
        ackReq = SettingsClass.GetStatusAcknowledgementRequested()
        loraStatusMsg.SetAckRequested(ackReq)
        reqRepeater = False
        if SettingsClass.GetLoraMode() == "SENDER":
            reqRepeater = subscriberAdapter.GetShouldRequestRepeater()
        loraStatusMsg.SetRepeater(reqRepeater)
        loraStatusMsg.GenerateRSCode()
        return {"Data": loraStatusMsg.GetByteArray(), "MessageID": loraStatusMsg.GetHash()}
