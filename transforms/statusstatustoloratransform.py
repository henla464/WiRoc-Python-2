from datamodel.datamodel import LoraRadioMessage
from settings.settings import SettingsClass
from battery import Battery
import logging

class StatusStatusToLoraTransform(object):
    DeleteAfterSent = False

    @staticmethod
    def GetInputMessageType():
        return "STATUS"

    @staticmethod
    def GetInputMessageSubType():
        return "Status"

    @staticmethod
    def GetOutputMessageType():
        return "LORA"

    @staticmethod
    def GetName():
        return "StatusStatusToLoraTransform"

    @staticmethod
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter):
        return 0

    @staticmethod
    def GetDeleteAfterSent():
        StatusStatusToLoraTransform.DeleteAfterSent = not SettingsClass.GetStatusAcknowledgementRequested()
        return StatusStatusToLoraTransform.DeleteAfterSent

    @staticmethod
    def GetDeleteAfterSentChanged():
        return StatusStatusToLoraTransform.DeleteAfterSent != (not SettingsClass.GetStatusAcknowledgementRequested())

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSub, subscriberAdapter):
        payloadData = msgSub.MessageData
        loraMessage = LoraRadioMessage()
        loraMessage.AddPayload(payloadData)
        loraMessage.AddThisWiRocToStatusMessage(SettingsClass.GetSIStationNumber(), Battery.GetBatteryPercent4Bits())
        loraMessage.SetMessageNumber(msgSub.MessageNumber)
        ackReq = SettingsClass.GetStatusAcknowledgementRequested()
        loraMessage.SetAcknowledgementRequested(ackReq)
        reqRepeater = False
        if SettingsClass.GetWiRocMode() == "SENDER":
            reqRepeater = subscriberAdapter.GetShouldRequestRepeater()
        loraMessage.SetRepeaterBit(reqRepeater)
        loraMessage.UpdateChecksum()
        return {"Data": loraMessage.GetByteArray(), "MessageID": loraMessage.GetMessageID()}
