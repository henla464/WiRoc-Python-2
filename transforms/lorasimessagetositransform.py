from datamodel.datamodel import LoraRadioMessage
import logging

class LoraSIMessageToSITransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

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
        LoraSIMessageToSITransform.WiRocLogger.debug("LoraSIMessageToSITransform::Transform() MessageTypeSIPunch")
        return {"Data":payloadData[LoraRadioMessage.GetHeaderSize():], "MessageID": None}
