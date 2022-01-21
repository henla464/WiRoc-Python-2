from loraradio.LoraRadioDataHandler import LoraRadioDataHandler
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from loraradio.LoraRadioMessageRS import LoraRadioMessageRS
from settings.settings import SettingsClass
import logging

class RepeaterSIMessageToLoraAckTransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

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
    def GetOutputMessageSubType():
        return "Ack"

    @staticmethod
    def GetName():
        return "RepeaterSIMessageToLoraAckTransform"

    @staticmethod
    def GetBatchSize():
        return 1

    @staticmethod
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter):
        payloadData = messageBoxData.MessageData
        ackReq = LoraRadioDataHandler.GetAckRequested(payloadData)
        repeater = LoraRadioDataHandler.GetRepeater(payloadData)
        # when repeater is requested, ack is sent directly from receiveloraadapter
        if ackReq and not repeater:
            return LoraRadioMessageRS.GetLoraMessageTimeSendingTimeSByMessageType(LoraRadioMessageRS.MessageTypeLoraAck) + 0.15 #ack 10, waiting for the destination wiroc to reply with ack + 0.15 delay
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
        RepeaterSIMessageToLoraAckTransform.WiRocLogger.debug("RepeaterSIMessageToLoraAckTransform::Transform()")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        ackReq = LoraRadioDataHandler.GetAckRequested(payloadData)
        repeaterReq = LoraRadioDataHandler.GetRepeater(payloadData)

        # when repeater is requested, ack is sent directly from receiveloraadapter
        if ackReq and not repeaterReq:
            incomingMsgType = LoraRadioDataHandler.GetHeaderMessageType(payloadData)
            # never ack status messages
            if incomingMsgType == LoraRadioMessageRS.MessageTypeStatus:
                return None

            loraPunchMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(payloadData, rssiByte=None)
            md5Hash = loraPunchMsg.GetHash()
            loraAck = LoraRadioMessageCreator.GetAckMessage(md5Hash)
            loraAck.SetAckRequested(msgSubBatch.AckReceivedFromReceiver)  # indicate ack received from receiver
            loraAck.SetRepeater(True)  # indicate this ack comes from repeater
            loraAck.GenerateRSCode()
            return {"Data": (loraAck.GetByteArray(),), "MessageID": None}
        return None