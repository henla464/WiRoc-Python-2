from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from utils.utils import Utils
from datamodel.datamodel import SIMessage

class LoraSIMessageToSirapTransform(object):

    @staticmethod
    def GetInputMessageType():
        return "LORA"

    @staticmethod
    def GetInputMessageSubType():
        return "SIMessage"

    @staticmethod
    def GetOutputMessageType():
        return "SIRAP"

    @staticmethod
    def GetName():
        return "LoraSIMessageToSirapTransform"

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
    def Transform(msgSub, subscriberAdapter):
        payloadData = msgSub.MessageData
        msg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(payloadData, rssiByte=None)
        siPayloadData = msg.GetSIMessageByteArray()
        siMsg = SIMessage()
        siMsg.AddPayload(siPayloadData)
        return {"Data": Utils.GetSirapDataFromSIData(siMsg), "MessageID": None}
