from datamodel.datamodel import MessageSubscriptionBatch
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from settings.settings import SettingsClass
import logging
from utils.utils import Utils


class StatusStatusToLoraTransform(object):
    DeleteAfterSent = False
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType() -> str:
        return "STATUS"

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
        return "StatusStatusToLoraTransform"

    @staticmethod
    def GetBatchSize() -> int:
        return 1

    @staticmethod
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter) -> float | None:
        return 0

    @staticmethod
    def GetDeleteAfterSent() -> bool:
        StatusStatusToLoraTransform.DeleteAfterSent = not SettingsClass.GetStatusAcknowledgementRequested()
        return StatusStatusToLoraTransform.DeleteAfterSent

    @staticmethod
    def GetDeleteAfterSentChanged() -> bool:
        return StatusStatusToLoraTransform.DeleteAfterSent != (not SettingsClass.GetStatusAcknowledgementRequested())

    @staticmethod
    def Transform(msgSubBatch: MessageSubscriptionBatch, subscriberAdapter):
        StatusStatusToLoraTransform.WiRocLogger.debug("StatusStatusToLoraTransform::Transform()")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        StatusStatusToLoraTransform.WiRocLogger.debug("StatusStatusToLoraTransform::Transform() MessageData: " + Utils.GetDataInHex(payloadData, logging.DEBUG))
        loraStatusMsg = LoraRadioMessageCreator.GetStatusMessageByFullMessageData(payloadData)
        StatusStatusToLoraTransform.WiRocLogger.debug(
            "StatusStatusToLoraTransform::Transform() Before generate RSCode: " + Utils.GetDataInHex(loraStatusMsg.GetByteArray(), logging.DEBUG))
        reqRepeater = False
        if SettingsClass.GetLoraMode() == "SENDER":
            reqRepeater = subscriberAdapter.GetShouldRequestRepeater()
        loraStatusMsg.SetRepeater(reqRepeater)
        loraStatusMsg.GenerateAndAddRSCode()
        return {"Data": (loraStatusMsg.GetByteArray(),), "MessageID": loraStatusMsg.GetHash()}
