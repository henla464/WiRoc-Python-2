from datamodel.datamodel import LoraRadioMessage
from datamodel.datamodel import SIMessage
from battery import Battery
from datamodel.db_helper import DatabaseHelper
from settings.settings import SettingsClass

class SITestTestToLoraTransform(object):
    DeleteAfterSent = False

    @staticmethod
    def GetInputMessageType():
        return "SITEST"

    @staticmethod
    def GetInputMessageSubType():
        return "Test"

    @staticmethod
    def GetOutputMessageType():
        return "LORA"

    @staticmethod
    def GetName():
        return "SITestTestToLoraTransform"

    @staticmethod
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter):
        return 0

    @staticmethod
    def GetDeleteAfterSent():
        # check setting for ack
        SITestTestToLoraTransform.DeleteAfterSent = not SettingsClass.GetAcknowledgementRequested()
        return SITestTestToLoraTransform.DeleteAfterSent

    @staticmethod
    def GetDeleteAfterSentChanged():
        return SITestTestToLoraTransform.DeleteAfterSent != (not SettingsClass.GetAcknowledgementRequested())

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSub, subscriberAdapter):
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
            loraMessage.SetMessageNumber(msgSub.MessageNumber)
            reqRepeater = subscriberAdapter.GetShouldRequestRepeater()
            loraMessage.SetRepeaterBit(reqRepeater)
            loraMessage.UpdateChecksum()
            return {"Data": loraMessage.GetByteArray(), "MessageID": loraMessage.GetMessageID()}
        return None