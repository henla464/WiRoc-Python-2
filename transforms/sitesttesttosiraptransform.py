from utils.utils import Utils
from datamodel.datamodel import SIMessage

class SITestTestToSirapTransform(object):

    @staticmethod
    def GetInputMessageType():
        return "SITEST"

    @staticmethod
    def GetInputMessageSubType():
        return "Test"

    @staticmethod
    def GetOutputMessageType():
        return "SIRAP"

    @staticmethod
    def GetName():
        return "SITestTestToSirapTransform"

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
        siMsg = SIMessage()
        siMsg.AddPayload(payloadData)
        return {"Data": Utils.GetSirapDataFromSIData(siMsg), "MessageID": None}
