from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from datamodel.datamodel import SIMessage, MessageSubscriptionBatch
import logging


class LoraSIMessageDoubleToRocTransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType() -> str:
        return "LORA"

    @staticmethod
    def GetInputMessageSubType() -> str:
        return "SIMessageDouble"

    @staticmethod
    def GetOutputMessageType() -> str:
        return "ROC"

    @staticmethod
    def GetOutputMessageSubType() -> str:
        return "Punch"

    @staticmethod
    def GetName() -> str:
        return "LoraSIMessageDoubleToRocTransform"

    @staticmethod
    def GetBatchSize() -> int:
        return 5  # 5 messages * 2 punches each = 10 punches max

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
    def _extractPunchData(siPayloadData: bytearray) -> dict | None:
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
        LoraSIMessageDoubleToRocTransform.WiRocLogger.debug("LoraSIMessageDoubleToRocTransform::Transform()")
        data = []
        for item in msgSubBatch.MessageSubscriptionBatchItems:
            msg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(item.MessageData, rssiValue=None)
            if msg is None:
                continue
            siPayloadTuple = msg.GetSIMessageByteTuple()
            punch1 = LoraSIMessageDoubleToRocTransform._extractPunchData(siPayloadTuple[0])
            if punch1 is not None:
                data.append(punch1)
            punch2 = LoraSIMessageDoubleToRocTransform._extractPunchData(siPayloadTuple[1])
            if punch2 is not None:
                data.append(punch2)
        if len(data) == 0:
            return None
        return {"Data": tuple(data), "MessageID": None}
