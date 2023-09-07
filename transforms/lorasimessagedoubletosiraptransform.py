from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from utils.utils import Utils
from datamodel.datamodel import SIMessage, MessageSubscriptionBatch
import logging


class LoraSIMessageDoubleToSirapTransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType() -> str:
        return "LORA"

    @staticmethod
    def GetInputMessageSubType() -> str:
        return "SIMessageDouble"

    @staticmethod
    def GetOutputMessageType() -> str:
        return "SIRAP"

    @staticmethod
    def GetOutputMessageSubType() -> str:
        return "Punch"

    @staticmethod
    def GetName() -> str:
        return "LoraSIMessageDoubleToSirapTransform"

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
        LoraSIMessageDoubleToSirapTransform.WiRocLogger.debug("LoraSIMessageDoubleToSirapTransform::Transform()")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        msg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(payloadData, rssiByte=None)
        siPayloadDatas = msg.GetSIMessageByteTuple()
        siMsg = SIMessage()
        siMsg.AddPayload(siPayloadDatas[0])
        sirapData = Utils.GetSirapDataFromSIData(siMsg)

        siMsg2 = SIMessage()
        siMsg2.AddPayload(siPayloadDatas[1])
        sirapData2 = Utils.GetSirapDataFromSIData(siMsg2)
        sirapDataTuple = (sirapData, sirapData2)
        return {"Data": sirapDataTuple, "MessageID": None}
