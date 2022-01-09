from battery import Battery
from loraradio.LoraRadioDataHandler import LoraRadioDataHandler
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from loraradio.LoraRadioMessageRS import LoraRadioMessageRS
from settings.settings import SettingsClass
import logging

class RepeaterStatusToLoraTransform(object):
    DeleteAfterSent = False
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType():
        return "REPEATER"

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
        return "RepeaterStatusToLoraTransform"

    @staticmethod
    def GetBatchSize():
        return 1

    @staticmethod
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter):
        repeater = LoraRadioDataHandler.GetRepeater(messageBoxData.MessageData)
        if repeater:
            # no ack expected from receiver, should be sent after repeater sent ack
            return 0
        else:
            # possible ack from receiver 10 + ack sent from repeater 10
            return SettingsClass.GetLoraMessageTimeSendingTimeSByMessageType(LoraRadioMessageRS.MessageTypeLoraAck)*2+0.1

    @staticmethod
    def GetDeleteAfterSent():
        # check setting for ack
        RepeaterStatusToLoraTransform.DeleteAfterSent = not SettingsClass.GetAcknowledgementRequested()
        return RepeaterStatusToLoraTransform.DeleteAfterSent

    @staticmethod
    def GetDeleteAfterSentChanged():
        return RepeaterStatusToLoraTransform.DeleteAfterSent != (not SettingsClass.GetAcknowledgementRequested())

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSubBatch, subscriberAdapter):
        RepeaterStatusToLoraTransform.WiRocLogger.debug("RepeaterStatusToLoraTransform::Transform()")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        loraStatusMsg = LoraRadioMessageCreator.GetStatusMessageByFullMessageData(payloadData)
        loraStatusMsg.SetRepeater(False)
        loraStatusMsg.GenerateRSCode()
        return {"Data": (loraStatusMsg.GetByteArray(),), "MessageID": loraStatusMsg.GetHash()}
