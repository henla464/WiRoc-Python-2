from battery import Battery
from datamodel.datamodel import MessageSubscriptionBatch
from loraradio.LoraRadioDataHandler import LoraRadioDataHandler
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from loraradio.LoraRadioMessageRS import LoraRadioMessageRS
from settings.settings import SettingsClass
import logging


class RepeaterStatusToLoraTransform(object):
    DeleteAfterSent = False
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType() -> str:
        return "REPEATER"

    @staticmethod
    def GetInputMessageSubType() -> str:
        return "Status"

    @staticmethod
    def GetOutputMessageType() -> str:
        return "LORA"

    @staticmethod
    def GetOutputMessageSubType() -> str:
        return "Status"

    @staticmethod
    def GetName() -> str:
        return "RepeaterStatusToLoraTransform"

    @staticmethod
    def GetBatchSize() -> int:
        return 1

    @staticmethod
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter) -> float | None:
        repeater = LoraRadioDataHandler.GetRepeater(messageBoxData.MessageData)
        if repeater:
            # no ack expected from receiver, should be sent after repeater sent ack
            return 0
        else:
            # possible ack from receiver 10 + ack sent from repeater 10
            return LoraRadioMessageRS.GetLoraMessageTimeSendingTimeSByMessageType(LoraRadioMessageRS.MessageTypeLoraAck)*2+0.1

    @staticmethod
    def GetDeleteAfterSent() -> bool:
        # check setting for ack
        RepeaterStatusToLoraTransform.DeleteAfterSent = not SettingsClass.GetAcknowledgementRequested()
        return RepeaterStatusToLoraTransform.DeleteAfterSent

    @staticmethod
    def GetDeleteAfterSentChanged() -> bool:
        return RepeaterStatusToLoraTransform.DeleteAfterSent != (not SettingsClass.GetAcknowledgementRequested())

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSubBatch: MessageSubscriptionBatch, subscriberAdapter):
        RepeaterStatusToLoraTransform.WiRocLogger.debug("RepeaterStatusToLoraTransform::Transform()")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        loraStatusMsg = LoraRadioMessageCreator.GetStatusMessageByFullMessageData(payloadData)
        loraStatusMsg.SetRepeater(False)
        loraStatusMsg.GenerateAndAddRSCode()
        return {"Data": (loraStatusMsg.GetByteArray(),), "MessageID": loraStatusMsg.GetHash()}
