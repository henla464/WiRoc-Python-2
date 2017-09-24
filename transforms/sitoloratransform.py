from datamodel.datamodel import LoraRadioMessage
from datamodel.datamodel import SIMessage
from battery import Battery
from settings.settings import SettingsClass

class SIToLoraTransform(object):

    @staticmethod
    def GetInputMessageType():
        return "SI"

    @staticmethod
    def GetOutputMessageType():
        return "LORA"

    @staticmethod
    def GetName():
        return "SIToLoraTransform"

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSub):
        payloadData = msgSub.MessageData
        siMsg = SIMessage()
        siMsg.AddPayload(payloadData)
        if siMsg.GetMessageType() == SIMessage.SIPunch:
            payloadDataLength = len(payloadData)
            messageType = LoraRadioMessage.MessageTypeSIPunch
            batteryLow = Battery.GetIsBatteryLow()
            ackReq = SettingsClass.GetAcknowledgementRequested()
            loraMessage = LoraRadioMessage(payloadDataLength, messageType, batteryLow, ackReq)
            loraMessage.AddPayload(payloadData)
            return {"Data": loraMessage.GetByteArray(), "CustomData": loraMessage.GetMessageID()}
        elif siMsg.GetMessageType() == SIMessage.WiRocToWiRoc:
            unwrappedMessage = payloadData[3:-3]
            # Assume it is a LoraRadioMessage that is wrapped
            loraMessage = LoraRadioMessage()
            loraMessage.AddPayload(unwrappedMessage)
            if loraMessage.GetMessageType() == LoraRadioMessage.MessageTypeStatus:
                # We received a status message wrapped in a WiRoc to WiRoc message
                # We want to send it on, but add information about this WiRoc
                loraMessage.AddThisWiRocToStatusMessage(SettingsClass.GetSIStationNumber(),
                                                        Battery.GetBatteryPercent4Bits())
                batteryLow = Battery.GetIsBatteryLow() or loraMessage.GetBatteryLowBit()
                loraMessage.SetBatteryLowBit(batteryLow)
                ackReq = SettingsClass.GetAcknowledgementRequested()
                loraMessage.SetAcknowledgementRequested(ackReq)
                loraMessage.UpdateMessageNumber()
                loraMessage.UpdateChecksum()
                return {"Data": loraMessage.GetByteArray(), "CustomData": loraMessage.GetMessageID()}
            else:
                return None
        return None