from datamodel.datamodel import LoraRadioMessage

class SIToLoraTransform(object):

    @staticmethod
    def GetInputMessageType():
        return "SI"

    @staticmethod
    def GetOutputMessageType():
        return "Lora"

    @staticmethod
    def GetName():
        return "SIToLoraTransform"

    #payloadData is a bytearray
    @staticmethod
    def Transform(payloadData):
        payloadDataLength = len(payloadData)
        messageType = LoraRadioMessage.MessageTypeSIPunch
        batteryLow = False
        ackReq = False
        loraMessage = LoraRadioMessage(payloadDataLength, messageType, batteryLow, ackReq)
        loraMessage.AddPayload(payloadData)
        return loraMessage.GetByteArray()