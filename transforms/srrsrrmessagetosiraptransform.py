from utils.utils import Utils
from datamodel.datamodel import SIMessage, MessageSubscriptionBatch, SRRMessage, SRRBoardPunch, AirPlusPunch, \
    AirPlusPunchOneOfMultiple
import logging


class SRRSRRMessageToSirapTransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType() -> str:
        return "SRR"

    @staticmethod
    def GetInputMessageSubType() -> str:
        return "SRRMessage"

    @staticmethod
    def GetOutputMessageType() -> str:
        return "SIRAP"

    @staticmethod
    def GetOutputMessageSubType() -> str:
        return "Punch"

    @staticmethod
    def GetName() -> str:
        return "SRRSRRMessageToSirapTransform"

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
        SRRSRRMessageToSirapTransform.WiRocLogger.debug("SRRSRRMessageToSirapTransform::Transform()")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        siMsg: SIMessage = SRRMessage.GetSIMsg(payloadData)

        if siMsg is None:
            SRRSRRMessageToSirapTransform.WiRocLogger.error("SRRSRRMessageToSirapTransform::Transform() Couldn't identify SRR message type. Data: " + Utils.GetDataInHex(payloadData, logging.ERROR))
            return None
        else:
            return {"Data": (Utils.GetSirapDataFromSIData(siMsg),), "MessageID": None}



