from datamodel.datamodel import SIMessage
from battery import Battery
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
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
    def GetBatchSize():
        return 2

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
            loraPunchMsg = LoraRadioMessageCreator.GetPunchMessageByFullMessageData(payloadData, rssiByte=None)
            batteryLow = Battery.GetIsBatteryLow()
            loraPunchMsg.SetBatteryLow(batteryLow)
            ackReq = SettingsClass.GetAcknowledgementRequested()
            loraPunchMsg.SetAckRequested(ackReq)
            reqRepeater = subscriberAdapter.GetShouldRequestRepeater()
            loraPunchMsg.SetRepeater(reqRepeater)
            loraPunchMsg.GenerateRS()
            return {"Data": loraPunchMsg.GetByteArray(), "MessageID": loraPunchMsg.GetHash()}
        return None