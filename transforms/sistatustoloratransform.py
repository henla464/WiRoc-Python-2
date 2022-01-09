from loraradio.LoraRadioDataHandler import LoraRadioDataHandler
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from loraradio.LoraRadioMessageRS import LoraRadioMessageRS
from settings.settings import SettingsClass
import logging


class SIStatusToLoraTransform(object):
    DeleteAfterSent = False
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType():
        return "SI"

    @staticmethod
    def GetInputMessageSubType():
        return "Status"

    @staticmethod
    def GetOutputMessageType():
        return "LORA"

    @staticmethod
    def GetOutputMessageSubType():
        return "Punch"

    @staticmethod
    def GetName():
        return "SIStatusToLoraTransform"

    @staticmethod
    def GetBatchSize():
        return 1

    @staticmethod
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter):
        return 0

    @staticmethod
    def GetDeleteAfterSent():
        # check setting for ack
        SIStatusToLoraTransform.DeleteAfterSent = not SettingsClass.GetAcknowledgementRequested()
        return SIStatusToLoraTransform.DeleteAfterSent

    @staticmethod
    def GetDeleteAfterSentChanged():
        return SIStatusToLoraTransform.DeleteAfterSent != (not SettingsClass.GetAcknowledgementRequested())

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSubBatch, subscriberAdapter):
        SIStatusToLoraTransform.WiRocLogger.debug("SIStatusToLoraTransform::Transform()")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        #WiRoc to WiRoc message
        unwrappedMessage = payloadData[3:-3]
        # Assume it is a LoraRadioMessage that is wrapped
        headerMessageType = LoraRadioDataHandler.GetHeaderMessageType(unwrappedMessage)
        if headerMessageType == LoraRadioMessageRS.MessageTypeStatus:
            # We received a status message wrapped in a WiRoc to WiRoc message
            # We want to send it on, but add information about this WiRoc
            loraStatusMsg = LoraRadioMessageCreator.GetStatusMessageByFullMessageData(unwrappedMessage)
            reqRepeater = False
            if SettingsClass.GetLoraMode() == "SENDER":
                reqRepeater = subscriberAdapter.GetShouldRequestRepeater()
            loraStatusMsg.SetRepeater(reqRepeater)
            loraStatusMsg.GenerateRSCode()
            return {"Data": (loraStatusMsg.GetByteArray(),), "MessageID": loraStatusMsg.GetHash()}
        else:
            return None
