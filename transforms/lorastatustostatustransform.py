from datamodel.datamodel import MessageSubscriptionBatch
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from settings.settings import SettingsClass
from battery import Battery
import logging

class LoraStatusToStatusTransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType() -> str:
        return "LORA"

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
        return "LoraStatusToStatusTransform"

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

    #msgSub.MessageData is a bytearray
    @staticmethod
    def Transform(msgSubBatch: MessageSubscriptionBatch, subscriberAdapter):
        LoraStatusToStatusTransform.WiRocLogger.debug("LoraStatusToStatusTransform::Transform() Message type status")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        return {"Data": (payloadData,), "MessageID": None}
