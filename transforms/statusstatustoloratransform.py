from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from settings.settings import SettingsClass
import logging


class StatusStatusToLoraTransform(object):
    DeleteAfterSent = False
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType():
        return "STATUS"

    @staticmethod
    def GetInputMessageSubType():
        return "Status"

    @staticmethod
    def GetOutputMessageType():
        return "LORA"

    @staticmethod
    def GetOutputMessageSubType():
        return "Status"

    @staticmethod
    def GetName():
        return "StatusStatusToLoraTransform"

    @staticmethod
    def GetBatchSize():
        return 1

    @staticmethod
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter):
        return 0

    @staticmethod
    def GetDeleteAfterSent():
        StatusStatusToLoraTransform.DeleteAfterSent = not SettingsClass.GetStatusAcknowledgementRequested()
        return StatusStatusToLoraTransform.DeleteAfterSent

    @staticmethod
    def GetDeleteAfterSentChanged():
        return StatusStatusToLoraTransform.DeleteAfterSent != (not SettingsClass.GetStatusAcknowledgementRequested())

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSubBatch, subscriberAdapter):
        StatusStatusToLoraTransform.WiRocLogger.debug("StatusStatusToLoraTransform::Transform()")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        loraStatusMsg = LoraRadioMessageCreator.GetStatusMessageByFullMessageData(payloadData)
        reqRepeater = False
        if SettingsClass.GetLoraMode() == "SENDER":
            reqRepeater = subscriberAdapter.GetShouldRequestRepeater()
        loraStatusMsg.SetRepeater(reqRepeater)
        loraStatusMsg.GenerateRSCode()
        return {"Data": (loraStatusMsg.GetByteArray(),), "MessageID": loraStatusMsg.GetHash()}
