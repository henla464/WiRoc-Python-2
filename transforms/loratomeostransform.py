from utils.utils import Utils
import datamodel.datamodel

class LoraToMeosTransform(object):

    @staticmethod
    def GetInputMessageType():
        return "LORA"

    @staticmethod
    def GetOutputMessageType():
        return "MEOS"

    @staticmethod
    def GetName():
        return "LoraToMeosTransform"

    #payloadData is a bytearray
    @staticmethod
    def Transform(payloadData):
        loraHeaderSize = datamodel.datamodel.LoraRadioMessage.GetHeaderSize()
        siPayloadData = payloadData[loraHeaderSize:]
        return {"Data": Utils.GetMeosDataFromSIData(siPayloadData), "CustomData": None}
