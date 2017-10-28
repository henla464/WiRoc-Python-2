from datamodel.datamodel import LoraRadioMessage
from datamodel.datamodel import SIMessage
from battery import Battery
from settings.settings import SettingsClass

class RepeaterStatusToLoraTransform(object):
    DeleteAfterSent = False

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
    def GetName():
        return "RepeaterStatusToLoraTransform"

    @staticmethod
    def GetWaitThisNumberOfBytes(messageBoxData, msgSub, subAdapter):
        return 22 #possible ack from destination 10 + ack sent from repeater 10 + 2 extra

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
    def Transform(msgSub, subscriberAdapter):
        payloadData = msgSub.MessageData
        loraMsg = LoraRadioMessage()
        loraMsg.AddPayload(payloadData)
        loraMsg.AddThisWiRocToStatusMessage(SettingsClass.GetSIStationNumber(),
                                                Battery.GetBatteryPercent4Bits())
        batteryLow = Battery.GetIsBatteryLow() or loraMsg.GetBatteryLowBit()
        loraMsg.SetBatteryLowBit(batteryLow)
        ackReq = SettingsClass.GetAcknowledgementRequested()
        loraMsg.SetAcknowledgementRequested(ackReq)
        loraMsg.SetMessageNumber(msgSub.MessageNumber)
        loraMsg.SetRepeaterBit(False)
        loraMsg.UpdateChecksum()
        return {"Data": loraMsg.GetByteArray(), "MessageID": loraMsg.GetMessageID()}
