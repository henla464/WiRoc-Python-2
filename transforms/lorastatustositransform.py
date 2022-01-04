from datamodel.datamodel import SIMessage
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from settings.settings import SettingsClass
from battery import Battery
from utils.utils import Utils
import logging

class LoraStatusToSITransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType():
        return "LORA"

    @staticmethod
    def GetInputMessageSubType():
        return "Status"

    @staticmethod
    def GetOutputMessageType():
        return "SI"

    @staticmethod
    def GetOutputMessageSubType():
        return "Status"

    @staticmethod
    def GetName():
        return "LoraStatusToSITransform"

    @staticmethod
    def GetBatchSize():
        return 1

    @staticmethod
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter):
        if SettingsClass.GetConnectedComputerIsWiRocDevice():
            return 0
        else:
            return None

    @staticmethod
    def GetDeleteAfterSent():
        return True

    @staticmethod
    def GetDeleteAfterSentChanged():
        return False

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSubBatch, subscriberAdapter):

        LoraStatusToSITransform.WiRocLogger.debug("LoraToSITransform::Transform() Message type status")
        if SettingsClass.GetConnectedComputerIsWiRocDevice():
            payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
            loraStatusMsg = LoraRadioMessageCreator.GetStatusMessageByFullMessageData(payloadData)
            loraStatusMsg.AddThisWiRocToStatusMessage(SettingsClass.GetSIStationNumber(), Battery.GetBatteryPercent4Bits())
            siMsg = SIMessage()
            siMsg.AddHeader(SIMessage.WiRocToWiRoc)
            siMsg.AddPayload(loraStatusMsg.GetByteArray())
            siMsg.AddFooter()
            LoraStatusToSITransform.WiRocLogger.debug("LoraToSITransform::Transform() data: " +  + Utils.GetDataInHex(siMsg.GetByteArray(), logging.DEBUG))
            return {"Data": (siMsg.GetByteArray(),), "MessageID": None}
        else:
            LoraStatusToSITransform.WiRocLogger.debug("LoraToSITransform::Transform() return None, not connected to wiroc device")
            return None
