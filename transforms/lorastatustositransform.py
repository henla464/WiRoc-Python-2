from datamodel.datamodel import SIMessage
from datamodel.datamodel import LoraRadioMessage
from settings.settings import SettingsClass
from battery import Battery
import logging

class LoraStatusToSITransform(object):
    @staticmethod
    def GetInputMessageType():
        return "LORA"

    @staticmethod
    def GetInputMessageSubType():
        return "Status"

    @staticmethod
    def GetOutputMessageType():
        return "SI"

    @staticmethod
    def GetName():
        return "LoraStatusToSITransform"

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
        payloadData = msgSub.MessageData
        loraMessage = LoraRadioMessage()
        loraMessage.AddPayload(payloadData)
        logging.debug("LoraToSITransform::Transform() Message type status")
        if SettingsClass.GetConnectedComputerIsWiRocDevice():
            loraMessage.AddThisWiRocToStatusMessage(SettingsClass.GetSIStationNumber(), Battery.GetBatteryPercent4Bits())
            siMsg = SIMessage()
            siMsg.AddHeader(SIMessage.WiRocToWiRoc)
            siMsg.AddPayload(loraMessage.GetByteArray())
            siMsg.AddFooter()
            dataInHex = ''.join(format(x, '02x') for x in siMsg.GetByteArray())
            logging.debug("LoraToSITransform::Transform() data: " + dataInHex)
            return {"Data": siMsg.GetByteArray(), "MessageID": None}
        else:
            logging.debug("LoraToSITransform::Transform() return None, not connected to wiroc device")
            return None
