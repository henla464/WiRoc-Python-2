from datamodel.datamodel import SIMessage
from datamodel.datamodel import LoraRadioMessage
from settings.settings import SettingsClass
from battery import Battery
import logging

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
        loraMessage = LoraRadioMessage()
        loraMessage.AddPayload(payloadData)
        if loraMessage.GetMessageType() == LoraRadioMessage.MessageTypeStatus:
            logging.debug("LoraToSITransform::Transform() Message type status")
            if SettingsClass.GetConnectedComputerIsWiRocDevice():
                loraMessage.AddThisWiRocToStatusMessage(SettingsClass.GetSIStationNumber(), Battery.GetBatteryPercent4Bits())
                siMsg = SIMessage()
                siMsg.AddHeader(SIMessage.WiRocToWiRoc)
                siMsg.AddPayload(loraMessage.GetByteArray())
                siMsg.AddFooter()
                dataInHex = ''.join(format(x, '02x') for x in siMsg.GetByteArray())
                logging.debug("LoraToSITransform::Transform() data: " + dataInHex)
                return {"Data": siMsg.GetByteArray(), "CustomData": None}
            else:
                logging.debug("LoraToSITransform::Transform() return None, not connected to wiroc device")
                return None
        elif loraMessage.GetMessageType() == LoraRadioMessage.MessageTypeSIPunch:
            logging.debug("LoraToSITransform::Transform() MessageTypeSIPunch")
            return {"Data":payloadData[LoraRadioMessage.GetHeaderSize():], "CustomData": None}
        else:
            logging.error("LoraToSITransform::Transform() return None, unknown lora message type")
            return None
