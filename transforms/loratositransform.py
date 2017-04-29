from datamodel.datamodel import SIMessage
from datamodel.datamodel import LoraRadioMessage
from settings.settings import SettingsClass
from battery import Battery

class LoraToSITransform(object):
    @staticmethod
    def GetInputMessageType():
        return "LORA"

    @staticmethod
    def GetOutputMessageType():
        return "SI"

    @staticmethod
    def GetName():
        return "LoraToSITransform"

    #payloadData is a bytearray
    @staticmethod
    def Transform(payloadData):
        loraMessage = LoraRadioMessage(payloadData)
        if loraMessage.GetMessageType() == LoraRadioMessage.MessageTypeStatus:
            if SettingsClass.GetConnectedComputerIsWiRocDevice():
                loraMessage.AddThisWiRocToStatusMessage(SettingsClass.GetSIStationNumber(), Battery.GetBatteryPercent4Bits())
                siMsg = SIMessage()
                siMsg.AddHeader(SIMessage.WiRocToWiRoc)
                siMsg.AddPayload(loraMessage.GetByteArray())
                siMsg.AddFooter()
                return {"Data": siMsg.GetByteArray(), "CustomData": None}
            else:
                return None
        elif loraMessage.GetMessageType() == LoraRadioMessage.MessageTypeSIPunch:
            return {"Data":payloadData[LoraRadioMessage.GetHeaderSize():], "CustomData": None}
