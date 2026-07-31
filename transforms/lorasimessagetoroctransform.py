from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from datamodel.datamodel import SIMessage, MessageSubscriptionBatch
import logging


class LoraSIMessageToRocTransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType() -> str:
        return "LORA"

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
        return "LoraSIMessageToRocTransform"

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
        msg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(payloadData, rssiValue=None)
        if msg is None:
            return None
        siPayloadData = msg.GetSIMessageByteArray()
        siMsg = SIMessage()
        siMsg.AddPayload(siPayloadData)
        return {
            "stationNumber": siMsg.GetStationNumber(),
            "cardNumber": siMsg.GetSICardNumber(),
            "twentyFourHour": siMsg.GetTwentyFourHour(),
            "hour": siMsg.GetHour(),
            "minute": siMsg.GetMinute(),
            "second": siMsg.GetSeconds(),
            "subSecondMs": siMsg.GetSubSecondAsMilliSeconds(),
            "rawPunchData": siPayloadData.hex().upper(),
        }

    @staticmethod
    def Transform(msgSubBatch: MessageSubscriptionBatch, subscriberAdapter):
        LoraSIMessageToRocTransform.WiRocLogger.debug("LoraSIMessageToRocTransform::Transform()")
        data = []
        for item in msgSubBatch.MessageSubscriptionBatchItems:
            punch = LoraSIMessageToRocTransform._extractPunchData(item.MessageData)
            if punch is not None:
                data.append(punch)
        if len(data) == 0:
            return None
        return {"Data": tuple(data), "MessageID": None}
