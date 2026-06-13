from datamodel.datamodel import SIMessage, MessageSubscriptionBatch
import logging


class SITestTestToSRRTransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType() -> str:
        return "TEST"

    @staticmethod
    def GetInputMessageSubType() -> str:
        return "Test"

    @staticmethod
    def GetOutputMessageType() -> str:
        return "SRR"

    @staticmethod
    def GetOutputMessageSubType() -> str:
        return "SRRMessage"

    @staticmethod
    def GetName() -> str:
        return "SITestTestToSRRTransform"

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
        SITestTestToSRRTransform.WiRocLogger.debug("SITestTestToSRRTransform::Transform()")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        siMsg = SIMessage()
        siMsg.AddPayload(payloadData)
        if siMsg.GetMessageType() == SIMessage.SIPunch:
            # Extract the 15-byte SI punch payload (skip STX header, include MsgType, Length and data)
            siPayload = payloadData[1:16]
            return {"Data": (siPayload,), "MessageID": None}
        return None
