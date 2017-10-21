from utils.utils import Utils
from datamodel.datamodel import SIMessage

class SIToMeosTransform(object):

    @staticmethod
    def GetInputMessageType():
        return "SI"

    @staticmethod
    def GetOutputMessageType():
        return "MEOS"

    @staticmethod
    def GetName():
        return "SIToMeosTransform"

    @staticmethod
    def GetWaitThisNumberOfBytes():
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
        siMsg = SIMessage()
        siMsg.AddPayload(payloadData)
        if siMsg.GetMessageType() == SIMessage.SIPunch:
            return {"Data": Utils.GetMeosDataFromSIData(siMsg), "MessageID": None}
        return None
