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
    def GetSIMsg(srrPayloadData: bytearray) -> SIMessage:
        siMsg: SIMessage | None = None
        headerSize: int = SRRMessage.GetHeaderSize()

        if srrPayloadData[0] >= headerSize:
            srrMessage = SRRMessage()
            srrMessage.AddPayload(srrPayloadData[0:headerSize])
            messageType: int = srrMessage.GetMessageType()
            if messageType == SRRMessage.SRRBoardPunch:
                srrBoardPunch = SRRBoardPunch()
                srrBoardPunch.AddPayload(srrPayloadData)
                siMsg = srrBoardPunch.GetSIMessage()
            elif messageType == SRRMessage.AirPlusPunch:
                airPlusPunch = AirPlusPunch()
                airPlusPunch.AddPayload(srrPayloadData)
                siMsg = airPlusPunch.GetSIMessage()
            elif messageType == SRRMessage.AirPlusPunchOneOfMultiple:
                airPlusPunchOneOfMultiple = AirPlusPunchOneOfMultiple()
                airPlusPunchOneOfMultiple.AddPayload(srrPayloadData)
                siMsg = airPlusPunchOneOfMultiple.GetSIMessage()

        return siMsg

    @staticmethod
    def Transform(msgSubBatch: MessageSubscriptionBatch, subscriberAdapter):
        SRRSRRMessageToSirapTransform.WiRocLogger.debug("SRRSRRMessageToSirapTransform::Transform()")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        siMsg: SIMessage = SRRSRRMessageToSirapTransform.GetSIMsg(payloadData)
        return {"Data": (Utils.GetSirapDataFromSIData(siMsg),), "MessageID": None}
