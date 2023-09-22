from datamodel.datamodel import SIMessage, MessageSubscriptionBatch, SRRMessage, SRRBoardPunch, AirPlusPunchOneOfMultiple, AirPlusPunch
import logging

from utils.utils import Utils


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
        siMsg: SIMessage | None = None
        headerSize: int = SRRMessage.GetHeaderSize()
        if payloadData[0] >= headerSize:
            srrMessage = SRRMessage()
            srrMessage.AddPayload(payloadData[0:headerSize])
            messageType: int = srrMessage.GetMessageType()
            if messageType == SRRMessage.SRRBoardPunch:
                srrBoardPunch = SRRBoardPunch()
                srrBoardPunch.AddPayload(payloadData)
                siMsg = srrBoardPunch.GetSIMessage()
            elif messageType == SRRMessage.AirPlusPunch:
                airPlusPunch = AirPlusPunch()
                airPlusPunch.AddPayload(payloadData)
                siMsg = airPlusPunch.GetSIMessage()
            elif messageType == SRRMessage.AirPlusPunchOneOfMultiple:
                airPlusPunchOneOfMultiple = AirPlusPunchOneOfMultiple()
                airPlusPunchOneOfMultiple.AddPayload(payloadData)
                siMsg = airPlusPunchOneOfMultiple.GetSIMessage()

        if siMsg is None:
            SRRSRRMessageToSITransform.WiRocLogger.error("SRRSRRMessageToSITransform::Transform() Couldn't identify SRR message type. Data: " +  + Utils.GetDataInHex(payloadData, logging.ERROR))
            return None
        else:
            return {"Data": (siMsg.GetByteArray(),), "MessageID": None}
