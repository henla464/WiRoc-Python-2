
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

    #payloadData is a bytearray
    @staticmethod
    def Transform(payloadData):
        return payloadData