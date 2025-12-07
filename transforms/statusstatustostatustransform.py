from datamodel.datamodel import MessageSubscriptionBatch
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from settings.settings import SettingsClass
from battery import Battery
import logging


class StatusStatusToStatusTransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType() -> str:
        return "STATUS"

    @staticmethod
    def GetInputMessageSubType() -> str:
        return "Status"

    @staticmethod
    def GetOutputMessageType() -> str:
        return "STATUS"

    @staticmethod
    def GetOutputMessageSubType() -> str:
        return "Status"

    @staticmethod
    def GetName() -> str:
        return "StatusStatusToStatusTransform"

    @staticmethod
    def GetBatchSize() -> int:
        return 1

    @staticmethod
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter) -> float | None:
        return 0

    @staticmethod
    def GetDeleteAfterSent() -> bool:
        return True

    @staticmethod
    def GetDeleteAfterSentChanged() -> bool:
        return False

    @staticmethod
    def Transform(msgSubBatch: MessageSubscriptionBatch, subscriberAdapter):
        StatusStatusToStatusTransform.WiRocLogger.debug("StatusStatusToStatusTransform::Transform()")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        #loraStatusMsg = LoraRadioMessageCreator.GetStatus2MessageByFullMessageData(payloadData)
        return {"Data": (payloadData,), "MessageID": None}
