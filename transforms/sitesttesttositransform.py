from datamodel.datamodel import SIMessage, MessageSubscriptionBatch
import logging


class SITestTestToSITransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType() -> str:
        return "SITEST"

    @staticmethod
    def GetInputMessageSubType() -> str:
        return "Test"

    @staticmethod
    def GetOutputMessageType() -> str:
        return "SI"

    @staticmethod
    def GetOutputMessageSubType() -> str:
        return "Punch"

    @staticmethod
    def GetName() -> str:
        return "SITestTestToSITransform"

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

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSubBatch: MessageSubscriptionBatch, subscriberAdapter):
        SITestTestToSITransform.WiRocLogger.debug("SITestTestToSITransform::Transform()")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        return {"Data": (payloadData,), "MessageID": None}
