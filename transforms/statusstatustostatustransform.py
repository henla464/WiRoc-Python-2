from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from settings.settings import SettingsClass
from battery import Battery

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
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter):
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
        loraStatusMsg = LoraRadioMessageCreator.GetStatusMessageByFullMessageData(msgSub.MessageData)
        loraStatusMsg.AddThisWiRocToStatusMessage(SettingsClass.GetSIStationNumber(), Battery.GetBatteryPercent4Bits())
        return {"Data": loraStatusMsg.GetByteArray(), "MessageID": None}
