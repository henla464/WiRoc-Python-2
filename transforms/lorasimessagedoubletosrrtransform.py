from datamodel.datamodel import MessageSubscriptionBatch
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
import logging


class LoraSIMessageDoubleToSRRTransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType() -> str:
        return "LORA"

    @staticmethod
    def GetInputMessageSubType() -> str:
        return "SIMessageDouble"

    @staticmethod
    def GetOutputMessageType() -> str:
        return "SRR"

    @staticmethod
    def GetOutputMessageSubType() -> str:
        return "SRRMessage"

    @staticmethod
    def GetName() -> str:
        return "LoraSIMessageDoubleToSRRTransform"

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
        LoraSIMessageDoubleToSRRTransform.WiRocLogger.debug("LoraSIMessageDoubleToSRRTransform::Transform()")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        msg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(payloadData)
        siPayloadDatas = msg.GetSIMessageByteTuple()
        # Extract 13-byte SI punch payloads from each SIMessage (skip STX, MsgType, Length, CRC, ETX)
        siPayload1 = siPayloadDatas[0][3:16]
        siPayload2 = siPayloadDatas[1][3:16]
        return {"Data": (siPayload1, siPayload2), "MessageID": msg.GetHash()}
