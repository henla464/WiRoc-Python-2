from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from utils.utils import Utils
from datamodel.datamodel import SIMessage
import logging


class LoraSIMessageDoubleToSirapTransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType():
        return "LORA"

    @staticmethod
    def GetInputMessageSubType():
        return "SIMessageDouble"

    @staticmethod
    def GetOutputMessageType():
        return "SIRAP"

    @staticmethod
    def GetOutputMessageSubType():
        return "Punch"

    @staticmethod
    def GetName():
        return "LoraSIMessageDoubleToSirapTransform"

    @staticmethod
    def GetBatchSize():
        return 1

    @staticmethod
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter):
        return 0

    @staticmethod
    def GetDeleteAfterSent():
        return True

    @staticmethod
    def GetDeleteAfterSentChanged():
        return False

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSubBatch, subscriberAdapter):
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
