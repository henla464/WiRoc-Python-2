from datamodel.datamodel import SIMessage, MessageSubscriptionBatch, SRRMessage
import logging


class SRRSRRMessageToRocTransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType() -> str:
        return "SRR"

    @staticmethod
    def GetInputMessageSubType() -> str:
        return "SRRMessage"

    @staticmethod
    def GetOutputMessageType() -> str:
        return "ROC"

    @staticmethod
    def GetOutputMessageSubType() -> str:
        return "Punch"

    @staticmethod
    def GetName() -> str:
        return "SRRSRRMessageToRocTransform"

    @staticmethod
    def GetBatchSize() -> int:
        return 10

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
    def GetMaxTries() -> int:
        return 5

    @staticmethod
    def Transform(msgSubBatch: MessageSubscriptionBatch, subscriberAdapter):
        SRRSRRMessageToRocTransform.WiRocLogger.debug("SRRSRRMessageToRocTransform::Transform()")
        data = []
        for item in msgSubBatch.MessageSubscriptionBatchItems:
            siMsg: SIMessage = SRRMessage.GetSIMsg(item.MessageData)
            if siMsg is None:
                continue
            punch = {
                "stationNumber": siMsg.GetStationNumber(),
                "cardNumber": siMsg.GetSICardNumber(),
                "twentyFourHour": siMsg.GetTwentyFourHour(),
                "hour": siMsg.GetHour(),
                "minute": siMsg.GetMinute(),
                "second": siMsg.GetSeconds(),
                "subSecondMs": siMsg.GetSubSecondAsMilliSeconds(),
                "rawPunchData": item.MessageData.hex().upper(),
            }
            data.append(punch)
        if len(data) == 0:
            return None
        return {"Data": tuple(data), "MessageID": None}
