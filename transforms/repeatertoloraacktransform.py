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
    def Transform(msgSub, subscriberAdapter):
        payloadData = msgSub.MessageData
        loraMsg = LoraRadioMessage()
        loraMsg.AddPayload(payloadData)

        if loraMsg.GetAcknowledgementRequested():
            incomingMsgType = loraMsg.GetMessageType()
            messageType = LoraRadioMessage.MessageTypeLoraAck
            loraMessage2 = LoraRadioMessage(5, messageType, False, False)
            if incomingMsgType == loraMsg.MessageTypeStatus:
                loraMessage2 = LoraRadioMessage(0, messageType, False, False)
            loraMessage2.SetRepeaterBit(True)  # indicate this ack comes from repeater
            loraMessage2.SetMessageIDToAck(loraMsg.GetMessageID())
            loraMessage2.UpdateChecksum()
            return {"Data": loraMessage2.GetByteArray(), "CustomData": loraMessage2.GetMessageID()}
        return None