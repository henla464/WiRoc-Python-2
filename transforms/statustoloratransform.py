from datamodel.datamodel import LoraRadioMessage
from settings.settings import SettingsClass
from battery import Battery

class StatusToLoraTransform(object):

    @staticmethod
    def GetInputMessageType():
        return "STATUS"

    @staticmethod
    def GetOutputMessageType():
        return "LORA"

    @staticmethod
    def GetName():
        return "StatusToLoraTransform"

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSub):
        payloadData = msgSub.MessageData
        loraMessage = LoraRadioMessage()
        loraMessage.AddPayload(payloadData)
        loraMessage.AddThisWiRocToStatusMessage(SettingsClass.GetSIStationNumber(), Battery.GetBatteryPercent4Bits())
        loraMessage.UpdateMessageNumber()
        ackReq = SettingsClass.GetAcknowledgementRequested()
        loraMessage.SetAcknowledgementRequested(ackReq)
        loraMessage.UpdateChecksum()
        return {"Data": loraMessage.GetByteArray(), "CustomData": loraMessage.GetMessageID()}
