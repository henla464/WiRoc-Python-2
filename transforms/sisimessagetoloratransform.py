from battery import Battery
from datamodel.datamodel import SIMessage
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from loraradio.LoraRadioMessageRS import LoraRadioMessageRS
from settings.settings import SettingsClass
import logging

class SISIMessageToLoraTransform(object):
    DeleteAfterSent = False
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType():
        return "SI"

    @staticmethod
    def GetInputMessageSubType():
        return "SIMessage"

    @staticmethod
    def GetOutputMessageType():
        return "LORA"

    @staticmethod
    def GetOutputMessageSubType():
        return "Punch"

    @staticmethod
    def GetName():
        return "SISIMessageToLoraTransform"

    @staticmethod
    def GetBatchSize():
        return 2

    @staticmethod
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter):
        if messageBoxData.MessageSource == "WiRoc":
            return SettingsClass.GetLoraMessageTimeSendingTimeSByMessageType(LoraRadioMessageRS.MessageTypeLoraAck)+0.1 # ack 10 bytes + 2 loop
        return 0

    @staticmethod
    def GetDeleteAfterSent():
        # check setting for ack
        SISIMessageToLoraTransform.DeleteAfterSent = not SettingsClass.GetAcknowledgementRequested()
        return SISIMessageToLoraTransform.DeleteAfterSent

    @staticmethod
    def GetDeleteAfterSentChanged():
        return SISIMessageToLoraTransform.DeleteAfterSent != (not SettingsClass.GetAcknowledgementRequested())

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSubBatch, subscriberAdapter):
        SISIMessageToLoraTransform.WiRocLogger.debug("SISIMessageToLoraTransform::Transform()")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        siMsg = SIMessage()
        siMsg.AddPayload(payloadData)
        if siMsg.GetMessageType() == SIMessage.SIPunch:
            # all MessageSubscriptionBatchItems will be SIPunch because only SIPunch is sent from SI SIMessage
            ackReq = SettingsClass.GetAcknowledgementRequested()
            reqRepeater = subscriberAdapter.GetShouldRequestRepeater()
            batteryLow = Battery.GetIsBatteryLow()
            if len(msgSubBatch.MessageSubscriptionBatchItems) == 1:
                loraPunchMsg = LoraRadioMessageCreator.GetPunchMessage(batteryLow, ackReq, None)
                loraPunchMsg.SetSIMessageByteArray(payloadData)
                loraPunchMsg.SetRepeater(reqRepeater)
                loraPunchMsg.GenerateRSCode()
                return {"Data": (loraPunchMsg.GetByteArray(),), "MessageID": loraPunchMsg.GetHash()}
            elif len(msgSubBatch.MessageSubscriptionBatchItems) == 2:
                loraPunchDoubleMsg = LoraRadioMessageCreator.GetPunchDoubleMessage(batteryLow, ackReq, None)
                loraPunchDoubleMsg.SetSIMessageByteArrays(payloadData,
                                                          msgSubBatch.MessageSubscriptionBatchItems[1].MessageData)
                loraPunchDoubleMsg.SetRepeater(reqRepeater)
                loraPunchDoubleMsg.GenerateRSCode()
                return {"Data": (loraPunchDoubleMsg.GetByteArray(),), "MessageID": loraPunchDoubleMsg.GetHash()}
