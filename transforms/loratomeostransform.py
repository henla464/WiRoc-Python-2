from utils.utils import Utils
from datamodel.datamodel import LoraRadioMessage
from datamodel.datamodel import SIMessage

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
            loraHeaderSize = LoraRadioMessage.GetHeaderSize()
            siPayloadData = payloadData[loraHeaderSize:]
            siMsg = SIMessage()
            siMsg.AddPayload(siPayloadData)
            return {"Data": Utils.GetMeosDataFromSIData(siMsg), "CustomData": None}
        return None
