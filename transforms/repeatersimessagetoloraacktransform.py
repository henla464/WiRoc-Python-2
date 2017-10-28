from datamodel.datamodel import LoraRadioMessage
from datamodel.datamodel import SIMessage
from battery import Battery
from settings.settings import SettingsClass

class RepeaterSIMessageToLoraAckTransform(object):

    @staticmethod
    def GetInputMessageType():
        return "REPEATER"

    @staticmethod
    def GetInputMessageSubType():
        return "SIMessage"

    @staticmethod
    def GetOutputMessageType():
        return "LORA"

    @staticmethod
    def GetName():
        return "RepeaterSIMessageToLoraAckTransform"

    @staticmethod
    def GetWaitThisNumberOfBytes(messageBoxData, msgSub, subAdapter):
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

        # when repeater is requested ack is sent directly from receiveloraadapter
        if loraMsg.GetAcknowledgementRequested() and not loraMsg.GetRepeaterBit():
            incomingMsgType = loraMsg.GetMessageType()
            messageType = LoraRadioMessage.MessageTypeLoraAck
            loraMessage2 = LoraRadioMessage(5, messageType, False, False)
            if incomingMsgType == loraMsg.MessageTypeStatus:
                loraMessage2 = LoraRadioMessage(0, messageType, False, False)
            loraMessage2.SetAcknowledgementRequested(msgSub.AckReceivedFromReceiver)  # indicate ack received from receiver
            loraMessage2.SetRepeaterBit(True)  # indicate this ack comes from repeater
            loraMessage2.SetMessageIDToAck(loraMsg.GetMessageID())
            loraMessage2.UpdateChecksum()
            return {"Data": loraMessage2.GetByteArray(), "MessageID": loraMessage2.GetMessageID()}
        return None