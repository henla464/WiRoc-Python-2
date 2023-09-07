from datamodel.datamodel import MessageSubscriptionBatch
from loraradio.LoraRadioDataHandler import LoraRadioDataHandler
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from loraradio.LoraRadioMessageRS import LoraRadioMessageRS
from settings.settings import SettingsClass
import logging


class RepeaterSIMessageToLoraAckTransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType() -> str:
        return "REPEATER"

    @staticmethod
    def GetInputMessageSubType() -> str:
        return "SIMessage"

    @staticmethod
    def GetOutputMessageType() -> str:
        return "LORA"

    @staticmethod
    def GetOutputMessageSubType() -> str:
        return "Ack"

    @staticmethod
    def GetName() -> str:
        return "RepeaterSIMessageToLoraAckTransform"

    @staticmethod
    def GetBatchSize() -> int:
        return 1

    @staticmethod
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter) -> float | None:
        payloadData = messageBoxData.MessageData
        ackReq = LoraRadioDataHandler.GetAckRequested(payloadData)
        repeater = LoraRadioDataHandler.GetRepeater(payloadData)
        # when repeater is requested, ack is sent directly from receiveloraadapter
        if ackReq and not repeater:
            return LoraRadioMessageRS.GetLoraMessageTimeSendingTimeSByMessageType(LoraRadioMessageRS.MessageTypeLoraAck) + 0.15 #ack 10, waiting for the destination wiroc to reply with ack + 0.15 delay
        return None

    @staticmethod
    def GetDeleteAfterSent() -> bool:
        return True

    @staticmethod
    def GetDeleteAfterSentChanged() -> bool:
        return False

    # payloadData is a bytearray
    @staticmethod
    def Transform(msgSubBatch: MessageSubscriptionBatch, subscriberAdapter):
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

            loraPunchMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(payloadData, rssiByte=None)
            hash = loraPunchMsg.GetHash()
            loraAck = LoraRadioMessageCreator.GetAckMessage(hash)
            loraAck.SetAckRequested(msgSubBatch.AckReceivedFromReceiver)  # indicate ack received from receiver
            loraAck.SetRepeater(True)  # indicate this ack comes from repeater
            return {"Data": (loraAck.GetByteArray(),), "MessageID": None}
        return None
