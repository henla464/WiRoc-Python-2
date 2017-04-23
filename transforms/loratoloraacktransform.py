from datamodel.datamodel import LoraRadioMessage

class LoraToLoraAckTransform(object):

    @staticmethod
    def GetInputMessageType():
        return "LORA"

    @staticmethod
    def GetOutputMessageType():
        return "LORA"

    @staticmethod
    def GetName():
        return "LoraToLoraAckTransform"

    #payloadData is a bytearray
    @staticmethod
    def Transform(payloadData):
        ackRequested = (payloadData[2] & 0x80) > 0
        if ackRequested:
            messageNumberToAck = payloadData[3]
            messageType = LoraRadioMessage.MessageTypeLoraAck
            loraMessage = LoraRadioMessage(1, messageType, False, False)
            loraMessage.AddPayload(bytearray([messageNumberToAck]))
            return {"Data": loraMessage.GetByteArray(), "CustomData":loraMessage.GetMessageNumber()}
        else:
            return None
