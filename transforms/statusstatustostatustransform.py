from datamodel.datamodel import LoraRadioMessage
from settings.settings import SettingsClass
from battery import Battery
import logging

class StatusStatusToStatusTransform(object):

    @staticmethod
    def GetInputMessageType():
        return "STATUS"

    @staticmethod
    def GetInputMessageSubType():
        return "Status"

    @staticmethod
    def GetOutputMessageType():
        return "STATUS"

    @staticmethod
    def GetName():
        return "StatusStatusToStatusTransform"

    @staticmethod
    def GetWaitThisNumberOfBytes(messageBoxData, msgSub, subAdapter):
        return 0

    @staticmethod
    def GetDeleteAfterSent():
        return True

    @staticmethod
    def GetDeleteAfterSentChanged():
        return False

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSub, subscriberAdapter):
        loraMessage = LoraRadioMessage()
        loraMessage.AddPayload(msgSub.MessageData)
        loraMessage.AddThisWiRocToStatusMessage(SettingsClass.GetSIStationNumber(), Battery.GetBatteryPercent4Bits())
        return {"Data": loraMessage.GetByteArray(), "MessageID": None}
