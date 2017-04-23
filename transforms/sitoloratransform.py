from datamodel.datamodel import LoraRadioMessage
from settings.settings import SettingsClass

class SIToLoraTransform(object):

    @staticmethod
    def GetInputMessageType():
        return "SI"

    @staticmethod
    def GetOutputMessageType():
        return "LORA"

    @staticmethod
    def GetName():
        return "SIToLoraTransform"

    #payloadData is a bytearray
    @staticmethod
    def Transform(payloadData):
        payloadDataLength = len(payloadData)
        messageType = LoraRadioMessage.MessageTypeSIPunch
        batteryLow = False
        ackReq = SettingsClass.GetAcknowledgementRequested()
        loraMessage = LoraRadioMessage(payloadDataLength, messageType, batteryLow, ackReq)
        loraMessage.AddPayload(payloadData)
        return {"Data": loraMessage.GetByteArray(), "CustomData": loraMessage.GetMessageNumber()}
