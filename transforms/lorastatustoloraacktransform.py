from datamodel.datamodel import LoraRadioMessage
from settings.settings import SettingsClass

class LoraStatusToLoraAckTransform(object):

    @staticmethod
    def GetInputMessageType():
        return "LORA"

    @staticmethod
    def GetInputMessageSubType():
        return "Status"

    @staticmethod
    def GetOutputMessageType():
        return "LORA"

    @staticmethod
    def GetName():
        return "LoraStatusToLoraAckTransform"

    @staticmethod
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter):
        if SettingsClass.GetLoraMode() == "RECEIVER":
            payloadData = messageBoxData.MessageData
            loraMsg = LoraRadioMessage()
            loraMsg.AddPayload(payloadData)
            if loraMsg.GetRepeaterBit() and loraMsg.GetAcknowledgementRequested():
                # ack (10), waiting for repeater to reply with ack
                # and send message (23) to receiver
                # + little delay 0.1 sec
                return SettingsClass.GetLoraMessageTimeSendingTimeS(10) + SettingsClass.GetLoraMessageTimeSendingTimeS(23)+0.1
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
        if SettingsClass.GetLoraMode() == "RECEIVER":
            payloadData = msgSub.MessageData
            loraMsg = LoraRadioMessage()
            loraMsg.AddPayload(payloadData)

            if loraMsg.GetRepeaterBit() and loraMsg.GetAcknowledgementRequested():
                messageType = LoraRadioMessage.MessageTypeLoraAck
                incomingMsgType = loraMsg.GetMessageType()
                loraMessage2 = None
                if incomingMsgType == loraMsg.MessageTypeStatus:
                    loraMessage2 = LoraRadioMessage(0, messageType, False, False)
                else:
                    loraMessage2 = LoraRadioMessage(5, messageType, False, False)
                loraMessage2.SetAcknowledgementRequested(True)  # indicate ack sent from receiver
                loraMessage2.SetRepeaterBit(False)  # indicate this ack doesn't come from repeater
                loraMessage2.SetMessageIDToAck(loraMsg.GetMessageID())
                loraMessage2.UpdateChecksum()
                return {"Data": loraMessage2.GetByteArray(), "MessageID": loraMessage2.GetMessageID()}
        return None