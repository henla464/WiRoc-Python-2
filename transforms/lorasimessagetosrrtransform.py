from datamodel.datamodel import MessageSubscriptionBatch
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
import logging


class LoraSIMessageToSRRTransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType() -> str:
        return "LORA"

    @staticmethod
    def GetInputMessageSubType() -> str:
        return "SIMessage"

    @staticmethod
    def GetOutputMessageType() -> str:
        return "SRR"

    @staticmethod
    def GetOutputMessageSubType() -> str:
        return "SRRMessage"

    @staticmethod
    def GetName() -> str:
        return "LoraSIMessageToSRRTransform"

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
    def GetMaxTries() -> int:
        return 1


    @staticmethod
    def Transform(msgSubBatch: MessageSubscriptionBatch, subscriberAdapter):
        LoraSIMessageToSRRTransform.WiRocLogger.debug("LoraSIMessageToSRRTransform::Transform()")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        loraMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(payloadData)
        siMsgByteArray = loraMsg.GetSIMessageByteArray()
        # Extract the 15-byte SI punch payload (skip STX header, include MsgType, Length and data)
        siPayload = siMsgByteArray[1:16]
        return {"Data": (siPayload,), "MessageID": loraMsg.GetHash()}
