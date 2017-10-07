from datamodel.datamodel import LoraRadioMessage
from datamodel.datamodel import SIMessage
from battery import Battery
from settings.settings import SettingsClass

class SIToLoraTransform(object):
    DeleteAfterSent = False

    @staticmethod
    def GetInputMessageType():
        return "REPEATER"

    @staticmethod
    def GetOutputMessageType():
        return "LORA"

    @staticmethod
    def GetName():
        return "RepeaterToLoraTransform"

    @staticmethod
    def GetWaitThisNumberOfBytes():
        return 22 #possible ack from destination 10 + ack sent from repeater 10 + 2 extra

    @staticmethod
    def GetDeleteAfterSent():
        # check setting for ack
        SIToLoraTransform.DeleteAfterSent = not SettingsClass.GetAcknowledgementRequested()
        return SIToLoraTransform.DeleteAfterSent

    @staticmethod
    def GetDeleteAfterSentChanged():
        return SIToLoraTransform.DeleteAfterSent != (not SettingsClass.GetAcknowledgementRequested())

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSub):
        payloadData = msgSub.MessageData
        loraMsg = LoraRadioMessage()
        loraMsg.AddPayload(payloadData)
        if loraMsg.GetMessageType() == loraMsg.MessageTypeSIPunch:
            batteryLow = Battery.GetIsBatteryLow() or loraMsg.GetBatteryLowBit()
            ackReq = SettingsClass.GetAcknowledgementRequested()
            loraMsg.SetAcknowledgementRequested(ackReq)
            loraMsg.SetBatteryLowBit(batteryLow)
            loraMsg.UpdateMessageNumber()
            loraMsg.UpdateChecksum()
            return {"Data": loraMsg.GetByteArray(), "CustomData": loraMsg.GetMessageID()}
        elif loraMsg.GetMessageType() == loraMsg.MessageTypeStatus:
            loraMsg.AddThisWiRocToStatusMessage(SettingsClass.GetSIStationNumber(),
                                                    Battery.GetBatteryPercent4Bits())
            batteryLow = Battery.GetIsBatteryLow() or loraMsg.GetBatteryLowBit()
            loraMsg.SetBatteryLowBit(batteryLow)
            ackReq = SettingsClass.GetAcknowledgementRequested()
            loraMsg.SetAcknowledgementRequested(ackReq)
            loraMsg.UpdateMessageNumber()
            loraMsg.UpdateChecksum()
            return {"Data": loraMsg.GetByteArray(), "CustomData": loraMsg.GetMessageID()}
        return None