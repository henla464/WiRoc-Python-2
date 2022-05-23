import logging

from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator


class LoraSIMessageDoubleToSITransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType():
        return "LORA"

    @staticmethod
    def GetInputMessageSubType():
        return "SIMessageDouble"

    @staticmethod
    def GetOutputMessageType():
        return "SI"

    @staticmethod
    def GetOutputMessageSubType():
        return "Punch"

    @staticmethod
    def GetName():
        return "LoraSIMessageDoubleToSITransform"

    @staticmethod
    def GetBatchSize():
        return 1

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
    def Transform(msgSubBatch, subscriberAdapter):
        LoraSIMessageDoubleToSITransform.WiRocLogger.debug("LoraSIMessageToSITransform::Transform() MessageTypeSIPunchDouble")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        loraPunchDoubleMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(payloadData)
        messageByteTuple = loraPunchDoubleMsg.GetSIMessageByteTuple()
        return {"Data": messageByteTuple, "MessageID": None}
