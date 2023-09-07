import logging

from datamodel.datamodel import MessageSubscriptionBatch
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator


class LoraSIMessageToSITransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType() -> str:
        return "LORA"

    @staticmethod
    def GetInputMessageSubType() -> str:
        return "SIMessage"

    @staticmethod
    def GetOutputMessageType() -> str:
        return "SI"

    @staticmethod
    def GetOutputMessageSubType() -> str:
        return "Punch"

    @staticmethod
    def GetName() -> str:
        return "LoraSIMessageToSITransform"

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
        LoraSIMessageToSITransform.WiRocLogger.debug("LoraSIMessageToSITransform::Transform() MessageTypeSIPunch")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        loraPunchMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(payloadData)
        return {"Data": (loraPunchMsg.GetSIMessageByteArray(),), "MessageID": None}
