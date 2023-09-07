from utils.utils import Utils
from datamodel.datamodel import SIMessage, MessageSubscriptionBatch
import logging


class SITestTestToSirapTransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType() -> str:
        return "SITEST"

    @staticmethod
    def GetInputMessageSubType() -> str:
        return "Test"

    @staticmethod
    def GetOutputMessageType() -> str:
        return "SIRAP"

    @staticmethod
    def GetOutputMessageSubType() -> str:
        return "Punch"

    @staticmethod
    def GetName() -> str:
        return "SITestTestToSirapTransform"

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
        SITestTestToSirapTransform.WiRocLogger.debug("SITestTestToSirapTransform::Transform()")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        siMsg = SIMessage()
        siMsg.AddPayload(payloadData)
        return {"Data": (Utils.GetSirapDataFromSIData(siMsg),), "MessageID": None}
