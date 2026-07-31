from datamodel.datamodel import SIMessage, MessageSubscriptionBatch
import logging


class SISIMessageToRocTransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType() -> str:
        return "SI"

    @staticmethod
    def GetInputMessageSubType() -> str:
        return "SIMessage"

    @staticmethod
    def GetOutputMessageType() -> str:
        return "ROC"

    @staticmethod
    def GetOutputMessageSubType() -> str:
        return "Punch"

    @staticmethod
    def GetName() -> str:
        return "SISIMessageToRocTransform"

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
    def _extractPunchData(payloadData: bytearray) -> dict | None:
        siMsg = SIMessage()
        siMsg.AddPayload(payloadData)
        return {
            "stationNumber": siMsg.GetStationNumber(),
            "cardNumber": siMsg.GetSICardNumber(),
            "twentyFourHour": siMsg.GetTwentyFourHour(),
            "hour": siMsg.GetHour(),
            "minute": siMsg.GetMinute(),
            "second": siMsg.GetSeconds(),
            "subSecondMs": siMsg.GetSubSecondAsMilliSeconds(),
            "rawPunchData": payloadData.hex().upper(),
        }

    @staticmethod
    def Transform(msgSubBatch: MessageSubscriptionBatch, subscriberAdapter):
        SISIMessageToRocTransform.WiRocLogger.debug("SISIMessageToRocTransform::Transform()")
        data = []
        for item in msgSubBatch.MessageSubscriptionBatchItems:
            punch = SISIMessageToRocTransform._extractPunchData(item.MessageData)
            if punch is not None:
                data.append(punch)
        if len(data) == 0:
            return None
        return {"Data": tuple(data), "MessageID": None}
