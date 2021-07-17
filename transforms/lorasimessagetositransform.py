import logging

from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator

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
        LoraSIMessageToSITransform.WiRocLogger.debug("LoraSIMessageToSITransform::Transform() MessageTypeSIPunch")
        payloadData = msgSub.MessageData
        loraPunchMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(payloadData)
        return {"Data": loraPunchMsg.GetSIMessageByteArray(), "MessageID": None}
