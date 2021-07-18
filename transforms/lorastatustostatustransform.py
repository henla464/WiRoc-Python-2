from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from settings.settings import SettingsClass
from battery import Battery
import logging

class LoraStatusToStatusTransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType():
        return "LORA"

    @staticmethod
    def GetInputMessageSubType():
        return "Status"

    @staticmethod
    def GetOutputMessageType():
        return "STATUS"

    @staticmethod
    def GetName():
        return "LoraStatusToStatusTransform"

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

    #msgSub.MessageData is a bytearray
    @staticmethod
    def Transform(msgSub, subscriberAdapter):
        LoraStatusToStatusTransform.WiRocLogger.debug("LoraStatusToStatusTransform::Transform() Message type status")
        loraStatusMsg = LoraRadioMessageCreator.GetStatusMessageByFullMessageData(msgSub.MessageData)
        loraStatusMsg.AddThisWiRocToStatusMessage(SettingsClass.GetSIStationNumber(), Battery.GetBatteryPercent4Bits())
        return {"Data": loraStatusMsg.GetByteArray(), "MessageID": None}
