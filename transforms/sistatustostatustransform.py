from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from loraradio.LoraRadioDataHandler import LoraRadioDataHandler
from loraradio.LoraRadioMessageRS import LoraRadioMessageRS
import logging


class SIStatusToStatusTransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType():
        return "SI"

    @staticmethod
    def GetInputMessageSubType():
        return "Status"

    @staticmethod
    def GetOutputMessageType():
        return "STATUS"

    @staticmethod
    def GetOutputMessageSubType():
        return "Status"

    @staticmethod
    def GetName():
        return "SIStatusToStatusTransform"

    @staticmethod
    def GetBatchSize():
        return 1

    @staticmethod
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter):
        return 0

    @staticmethod
    def GetDeleteAfterSent():
        return True

    @staticmethod
    def GetDeleteAfterSentChanged():
        return False

    # msgSub.MessageData is a bytearray
    @staticmethod
    def Transform(msgSubBatch, subscriberAdapter):
        SIStatusToStatusTransform.WiRocLogger.debug("SIStatusToStatusTransform::Transform() Message type status")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        # WiRoc to WiRoc message
        unwrappedMessage = payloadData[3:-3]
        # Assume it is a LoraRadioMessage that is wrapped
        headerMessageType = LoraRadioDataHandler.GetHeaderMessageType(unwrappedMessage)
        if headerMessageType == LoraRadioMessageRS.MessageTypeStatus:
            loraStatusMsg = LoraRadioMessageCreator.GetStatusMessageByFullMessageData(unwrappedMessage)
            return {"Data": (loraStatusMsg.GetByteArray(),), "MessageID": None}
        else:
            return None
