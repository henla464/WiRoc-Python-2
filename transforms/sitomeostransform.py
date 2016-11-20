from utils.utils import Utils
from struct import pack

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

    #payloadData is a bytearray
    @staticmethod
    def Transform(payloadData):
        return Utils.GetMeosDataFromSIData(payloadData)
