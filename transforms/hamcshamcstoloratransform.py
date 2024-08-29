from datamodel.datamodel import MessageSubscriptionBatch
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from settings.settings import SettingsClass
from battery import Battery
import logging


class HAMCSHamcsToLoraTransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType() -> str:
        return "HAMCS"

    @staticmethod
    def GetInputMessageSubType() -> str:
        return "Hamcs"

    @staticmethod
    def GetOutputMessageType() -> str:
        return "LORA"

    @staticmethod
    def GetOutputMessageSubType() -> str:
        return "Hamcs"

    @staticmethod
    def GetName() -> str:
        return "HAMCSHamcsToLoraTransform"

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
        HAMCSHamcsToLoraTransform.WiRocLogger.debug("HAMCSHamcsToLoraTransform::Transform() Message type Hamcs")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        return {"Data": (payloadData,), "MessageID": None}
