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

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSub):
        payloadData = msgSub.MessageData
        siMsg = SIMessage()
        siMsg.AddPayload(payloadData)
        if siMsg.GetMessageType() == SIMessage.SIPunch:
            return {"Data": Utils.GetMeosDataFromSIData(siMsg), "CustomData": None}
        return None
