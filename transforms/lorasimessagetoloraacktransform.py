from settings.settings import SettingsClass
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from loraradio.LoraRadioDataHandler import LoraRadioDataHandler
from loraradio.LoraRadioMessageRS import LoraRadioMessageRS

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
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter):
        payloadData = messageBoxData.MessageData
        ackReq = LoraRadioDataHandler.GetAckRequested(payloadData)
        repeater = LoraRadioDataHandler.GetRepeater(payloadData)

        if repeater and ackReq and SettingsClass.GetLoraMode() == "RECEIVER":
            # ack, waiting for repeater to reply with ack
            # and send message to receiver
            # + little delay 0.15 sec
            incomingMsgType = LoraRadioDataHandler.GetHeaderMessageType(payloadData)
            return SettingsClass.GetLoraMessageTimeSendingTimeSByMessageType(LoraRadioMessageRS.MessageTypeLoraAck) + \
                SettingsClass.GetLoraMessageTimeSendingTimeSByMessageType(incomingMsgType) + \
                0.15  # ack sent from repeater + 0.15 delay

        return None

    @staticmethod
    def GetDeleteAfterSent():
        return True

    @staticmethod
    def GetDeleteAfterSentChanged():
        return False

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSubBatch, subscriberAdapter):
        # This transform is only used to send ack message from the receiver
        # when repeater is requested (because then we should delay sending ack)
        if SettingsClass.GetLoraMode() == "RECEIVER":
            payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
            ackReq = LoraRadioDataHandler.GetAckRequested(payloadData)
            repeaterReq = LoraRadioDataHandler.GetRepeater(payloadData)

            if repeaterReq and ackReq:
                incomingMsgType = LoraRadioDataHandler.GetHeaderMessageType(payloadData)
                # never ack status messages
                if incomingMsgType == LoraRadioMessageRS.MessageTypeStatus:
                    return None

                loraPunchMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(payloadData, rssiByte=None)
                md5Hash = loraPunchMsg.GetHash()
                loraAck = LoraRadioMessageCreator.GetAckMessage(md5Hash)
                loraAck.SetAckRequested(msgSubBatch.AckReceivedFromReceiver)  # indicate ack received from receiver
                loraAck.SetRepeater(False)  # indicate this ack comes from receiver
                loraAck.GenerateRSCode()
                return {"Data": (loraAck.GetByteArray(),), "MessageID": None}
        return None
