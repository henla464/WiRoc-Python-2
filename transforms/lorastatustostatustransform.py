from datamodel.datamodel import SIMessage
from datamodel.datamodel import LoraRadioMessage
from settings.settings import SettingsClass
from battery import Battery
import logging

class LoraStatusToStatusTransform(object):
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
        logging.debug("LoraStatusToStatusTransform::Transform() Message type status")
        loraMessage = LoraRadioMessage()
        loraMessage.AddPayload(msgSub.MessageData)
        loraMessage.AddThisWiRocToStatusMessage(SettingsClass.GetSIStationNumber(), Battery.GetBatteryPercent4Bits())
        return {"Data": loraMessage.GetByteArray(), "MessageID": None}
