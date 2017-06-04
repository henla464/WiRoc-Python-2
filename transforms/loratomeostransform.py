from utils.utils import Utils
from datamodel.datamodel import LoraRadioMessage
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
    def Transform(msgSub):
        payloadData = msgSub.MessageData
        msg = LoraRadioMessage()
        msg.AddPayload(payloadData)
        if msg.GetMessageType() == LoraRadioMessage.MessageTypeSIPunch:
            loraHeaderSize = datamodel.datamodel.LoraRadioMessage.GetHeaderSize()
            siPayloadData = payloadData[loraHeaderSize:]
            return {"Data": Utils.GetMeosDataFromSIData(siPayloadData), "CustomData": None}
        return None
