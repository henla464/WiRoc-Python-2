from datamodel.datamodel import LoraRadioMessage
from settings.settings import SettingsClass
from battery import Battery

class StatusToLoraTransform(object):
    DeleteAfterSent = False

    @staticmethod
    def GetInputMessageType():
        return "STATUS"

    @staticmethod
    def GetOutputMessageType():
        return "LORA"

    @staticmethod
    def GetName():
        return "StatusToLoraTransform"

    @staticmethod
    def GetWaitThisNumberOfBytes():
        return 0

    @staticmethod
    def GetDeleteAfterSent():
        StatusToLoraTransform.DeleteAfterSent = not SettingsClass.GetStatusAcknowledgementRequested()
        return StatusToLoraTransform.DeleteAfterSent

    @staticmethod
    def GetDeleteAfterSentChanged():
        return StatusToLoraTransform.DeleteAfterSent != (not SettingsClass.GetStatusAcknowledgementRequested())

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSub, subscriberAdapter):
        payloadData = msgSub.MessageData
        loraMessage = LoraRadioMessage()
        loraMessage.AddPayload(payloadData)
        loraMessage.AddThisWiRocToStatusMessage(SettingsClass.GetSIStationNumber(), Battery.GetBatteryPercent4Bits())
        loraMessage.SetMessageNumber(msgSub.MessageNumber)
        ackReq = SettingsClass.GetStatusAcknowledgementRequested()
        loraMessage.SetAcknowledgementRequested(ackReq)
        reqRepeater = subscriberAdapter.GetShouldRequestRepeater()
        loraMessage.SetRepeaterBit(reqRepeater)
        loraMessage.UpdateChecksum()
        return {"Data": loraMessage.GetByteArray(), "CustomData": loraMessage.GetMessageID()}
