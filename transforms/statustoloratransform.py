from datamodel.datamodel import LoraRadioMessage
from settings.settings import SettingsClass
from battery import Battery

class LoraToLoraAckTransform(object):

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
    def Transform(payloadData):
        loraMessage = LoraRadioMessage()
        loraMessage.AddPayload(payloadData)
        loraMessage.AddThisWiRocToStatusMessage(SettingsClass.GetSIStationNumber(), Battery.GetBatteryPercent4Bits())
        return {"Data": loraMessage.GetByteArray(), "CustomData": None}
