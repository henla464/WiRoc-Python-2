from datamodel.datamodel import SIMessage
from datamodel.datamodel import LoraRadioMessage
from settings.settings import SettingsClass
from battery import Battery
import logging

class LoraSIMessageToSITransform(object):
    @staticmethod
    def GetInputMessageType():
        return "LORA"

    @staticmethod
    def GetInputMessageSubType():
        return "SIMessage"

    @staticmethod
    def GetOutputMessageType():
        return "SI"

    @staticmethod
    def GetName():
        return "LoraSIMessageToSITransform"

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
        #loraMessage = LoraRadioMessage()
        #loraMessage.AddPayload(payloadData)
        logging.debug("LoraSIMessageToSITransform::Transform() MessageTypeSIPunch")
        return {"Data":payloadData[LoraRadioMessage.GetHeaderSize():], "MessageID": None}
