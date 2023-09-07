from datamodel.datamodel import SIMessage, MessageSubscriptionBatch
import logging


class SRRSRRMessageToSITransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType() -> str:
        return "SRR"

    @staticmethod
    def GetInputMessageSubType() -> str:
        return "SRRMessage"

    @staticmethod
    def GetOutputMessageType() -> str:
        return "SI"

    @staticmethod
    def GetOutputMessageSubType() -> str:
        return "Punch"

    @staticmethod
    def GetName() -> str:
        return "SRRSRRMessageToSITransform"

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
        SRRSRRMessageToSITransform.WiRocLogger.debug("SRRSRRMessageToSITransform::Transform()")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        siMsg = SIMessage()
        siMsg.AddHeader(SIMessage.SIPunch)
        siMsg.AddPayload(payloadData[18:31])
        siMsg.AddFooter()
        return {"Data": (siMsg.GetByteArray(),), "MessageID": None}
