from utils.utils import Utils
from datamodel.datamodel import LoraRadioMessage
from datamodel.datamodel import SIMessage

class LoraSIMessageToMeosTransform(object):

    @staticmethod
    def GetInputMessageType():
        return "LORA"

    @staticmethod
    def GetInputMessageSubType():
        return "SIMessage"

    @staticmethod
    def GetOutputMessageType():
        return "MEOS"

    @staticmethod
    def GetName():
        return "LoraSIMessageToMeosTransform"

    @staticmethod
    def GetWaitThisNumberOfBytes(messageBoxData, msgSub, subAdapter):
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
        msg = LoraRadioMessage()
        msg.AddPayload(payloadData)
        loraHeaderSize = LoraRadioMessage.GetHeaderSize()
        siPayloadData = payloadData[loraHeaderSize:]
        siMsg = SIMessage()
        siMsg.AddPayload(siPayloadData)
        return {"Data": Utils.GetMeosDataFromSIData(siMsg), "MessageID": None}
