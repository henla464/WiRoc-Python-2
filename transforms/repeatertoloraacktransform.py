from datamodel.datamodel import LoraRadioMessage
from datamodel.datamodel import SIMessage
from battery import Battery
from settings.settings import SettingsClass

class SIToLoraTransform(object):

    @staticmethod
    def GetInputMessageType():
        return "REPEATER"

    @staticmethod
    def GetOutputMessageType():
        return "LORA"

    @staticmethod
    def GetName():
        return "RepeaterToLoraAckTransform"

    @staticmethod
    def GetWaitThisNumberOfBytes():
        return 10 #ack 10, waiting for the destination wiroc to reply with ack

    @staticmethod
    def GetDeleteAfterSent():
        return True

    @staticmethod
    def GetDeleteAfterSentChanged():
        return False

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSub):
        payloadData = msgSub.MessageData
        loraMsg = LoraRadioMessage()
        loraMsg.AddPayload(payloadData)

        messageType = LoraRadioMessage.MessageTypeLoraAck
        loraMessage2 = LoraRadioMessage(5, messageType, False, False)
        loraMessage2.SetMessageIDToAck(loraMsg.GetMessageID())


        if loraMsg.GetMessageType() == loraMsg.MessageTypeSIPunch \
            or loraMsg.GetMessageType() == loraMsg.MessageTypeStatus:
            if loraMsg.GetAcknowledgementRequested():
                messageType = LoraRadioMessage.MessageTypeLoraAck
                loraMessage2 = LoraRadioMessage(5, messageType, False, False)
                loraMessage2.SetMessageIDToAck(loraMsg.GetMessageID())
                loraMessage2.UpdateChecksum()
            return {"Data": loraMessage2.GetByteArray(), "CustomData": loraMsg.GetMessageID()}
        return None