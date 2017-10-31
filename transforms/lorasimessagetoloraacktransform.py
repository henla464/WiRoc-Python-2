from datamodel.datamodel import LoraRadioMessage
from datamodel.datamodel import SIMessage
from battery import Battery
from settings.settings import SettingsClass

class LoraSIMessageToLoraAckTransform(object):

    @staticmethod
    def GetInputMessageType():
        return "LORA"

    @staticmethod
    def GetInputMessageSubType():
        return "SIMessage"

    @staticmethod
    def GetOutputMessageType():
        return "LORA"

    @staticmethod
    def GetName():
        return "LoraSIMessageToLoraAckTransform"

    @staticmethod
    def GetWaitThisNumberOfBytes(messageBoxData, msgSub, subAdapter):
        loraMsg = LoraRadioMessage()
        loraMsg.AddPayload(messageBoxData.MessageData)

        if loraMsg.GetRepeaterBit() and \
                loraMsg.GetAcknowledgementRequested() \
                and SettingsClass.GetWiRocMode() == "RECEIVER":
            # ack (10), waiting for repeater to reply with ack
            # and send message (23) to receiver
            # + little delay (20) (two transmissions so need to include M for second)
            return 10+23+20
        return None

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

            if loraMsg.GetRepeaterBit() and loraMsg.GetAcknowledgementRequested():
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