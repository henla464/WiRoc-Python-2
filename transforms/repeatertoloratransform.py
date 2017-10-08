from datamodel.datamodel import LoraRadioMessage
from datamodel.datamodel import SIMessage
from battery import Battery
from settings.settings import SettingsClass

class RepeaterToLoraTransform(object):
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
        RepeaterToLoraTransform.DeleteAfterSent = not SettingsClass.GetAcknowledgementRequested()
        return RepeaterToLoraTransform.DeleteAfterSent

    @staticmethod
    def GetDeleteAfterSentChanged():
        return RepeaterToLoraTransform.DeleteAfterSent != (not SettingsClass.GetAcknowledgementRequested())

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
            loraMsg.SetMessageNumber(msgSub.MessageNumber)
            loraMsg.UpdateChecksum()
            return {"Data": loraMsg.GetByteArray(), "CustomData": loraMsg.GetMessageID()}
        elif loraMsg.GetMessageType() == loraMsg.MessageTypeStatus:
            loraMsg.AddThisWiRocToStatusMessage(SettingsClass.GetSIStationNumber(),
                                                    Battery.GetBatteryPercent4Bits())
            batteryLow = Battery.GetIsBatteryLow() or loraMsg.GetBatteryLowBit()
            loraMsg.SetBatteryLowBit(batteryLow)
            ackReq = SettingsClass.GetAcknowledgementRequested()
            loraMsg.SetAcknowledgementRequested(ackReq)
            loraMsg.SetMessageNumber(msgSub.MessageNumber)
            loraMsg.UpdateChecksum()
            return {"Data": loraMsg.GetByteArray(), "CustomData": loraMsg.GetMessageID()}
        return None