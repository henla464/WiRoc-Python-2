from datamodel.datamodel import LoraRadioMessage
from datamodel.datamodel import SIMessage
from battery import Battery
from settings.settings import SettingsClass

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

    @staticmethod
    def GetWaitThisNumberOfBytes():
        # ack (10), waiting for repeater to reply with ack
        # and send message (23) to receiver
        # + little delay
        return 10+23+2

    @staticmethod
    def GetDeleteAfterSent():
        return True

    @staticmethod
    def GetDeleteAfterSentChanged():
        return False

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSub, subscriberAdapter):
        # This transform is only used to send ack message from the receiver
        # when repeater is requested (because then we should delay sending ack)
        if SettingsClass.GetWiRocMode() == "RECEIVER":
            payloadData = msgSub.MessageData
            loraMsg = LoraRadioMessage()
            loraMsg.AddPayload(payloadData)
            incomingMsgType = loraMsg.GetMessageType()

            if (incomingMsgType == LoraRadioMessage.MessageTypeSIPunch or
                incomingMsgType == LoraRadioMessage.MessageTypeStatus) and \
                loraMsg.GetRepeaterBit() and loraMsg.GetAcknowledgementRequested():

                messageType = LoraRadioMessage.MessageTypeLoraAck
                loraMessage2 = LoraRadioMessage(5, messageType, False, False)
                if incomingMsgType == loraMsg.MessageTypeStatus:
                    loraMessage2 = LoraRadioMessage(0, messageType, False, False)
                loraMessage2.SetAcknowledgementRequested(True)  # indicate ack sent from receiver
                loraMessage2.SetRepeaterBit(False)  # indicate this ack doesn't come from repeater
                loraMessage2.SetMessageIDToAck(loraMsg.GetMessageID())
                loraMessage2.UpdateChecksum()
                return {"Data": loraMessage2.GetByteArray(), "MessageID": loraMessage2.GetMessageID()}
        return None