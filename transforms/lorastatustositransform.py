from datamodel.datamodel import SIMessage, MessageSubscriptionBatch
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from settings.settings import SettingsClass
from battery import Battery
from utils.utils import Utils
import logging


class LoraStatusToSITransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType() -> str:
        return "LORA"

    @staticmethod
    def GetInputMessageSubType() -> str:
        return "Status"

    @staticmethod
    def GetOutputMessageType() -> str:
        return "SI"

    @staticmethod
    def GetOutputMessageSubType() -> str:
        return "Status"

    @staticmethod
    def GetName() -> str:
        return "LoraStatusToSITransform"

    @staticmethod
    def GetBatchSize() -> int:
        return 1

    @staticmethod
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter) -> float | None:
        if SettingsClass.GetConnectedComputerIsWiRocDevice():
            return 0
        else:
            return None

    @staticmethod
    def GetDeleteAfterSent() -> bool:
        return True

    @staticmethod
    def GetDeleteAfterSentChanged() -> bool:
        return False

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSubBatch: MessageSubscriptionBatch, subscriberAdapter):

        LoraStatusToSITransform.WiRocLogger.debug("LoraToSITransform::Transform() Message type status")
        if SettingsClass.GetConnectedComputerIsWiRocDevice():
            payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
            loraStatusMsg = LoraRadioMessageCreator.GetStatusMessageByFullMessageData(payloadData)
            siMsg = SIMessage()
            siMsg.AddHeader(SIMessage.Status)
            siMsg.AddPayload(loraStatusMsg.GetByteArray())
            siMsg.AddFooter()
            LoraStatusToSITransform.WiRocLogger.debug("LoraToSITransform::Transform() data: " +  + Utils.GetDataInHex(siMsg.GetByteArray(), logging.DEBUG))
            return {"Data": (siMsg.GetByteArray(),), "MessageID": None}
        else:
            LoraStatusToSITransform.WiRocLogger.debug("LoraToSITransform::Transform() return None, not connected to wiroc device")
            return None
