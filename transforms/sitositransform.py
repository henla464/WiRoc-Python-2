from datamodel.datamodel import SIMessage

class SIToSITransform(object):

    @staticmethod
    def GetInputMessageType():
        return "SI"

    @staticmethod
    def GetOutputMessageType():
        return "SI"

    @staticmethod
    def GetName():
        return "SIToSITransform"

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
            return {"Data":payloadData, "CustomData": None}
        return None