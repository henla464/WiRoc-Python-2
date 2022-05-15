from datamodel.datamodel import SIMessage
from battery import Battery
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from loraradio.LoraRadioMessageRS import LoraRadioMessagePunchReDCoSRS, LoraRadioMessagePunchDoubleReDCoSRS
from settings.settings import SettingsClass
import logging


class SITestTestToLoraTransform(object):
    DeleteAfterSent = False
    WiRocLogger = logging.getLogger('WiRoc.Output')

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
    def GetOutputMessageSubType():
        return "Punch"

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
    def Transform(msgSubBatch, subscriberAdapter):
        SITestTestToLoraTransform.WiRocLogger.debug("SITestTestToLoraTransform::Transform()")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        siMsg = SIMessage()
        siMsg.AddPayload(payloadData)
        if siMsg.GetMessageType() == SIMessage.SIPunch:
            # all MessageSubscriptionBatchItems will be SIPunch because only SIPunch is sent from SITest
            ackReq = SettingsClass.GetAcknowledgementRequested()
            reqRepeater = subscriberAdapter.GetShouldRequestRepeater()
            batteryLow = Battery.GetIsBatteryLow()
            if len(msgSubBatch.MessageSubscriptionBatchItems) == 1:
                loraPunchMsg = LoraRadioMessageCreator.GetPunchMessage(batteryLow, ackReq, None)
                loraPunchMsg.SetSIMessageByteArray(payloadData)
                loraPunchMsg.SetRepeater(reqRepeater)
                loraPunchMsg.GenerateAndAddRSCode()
                interleavedMessageData = LoraRadioMessagePunchReDCoSRS.InterleaveToAirOrder(
                    loraPunchMsg.GetByteArray())
                return {"Data": (interleavedMessageData,), "MessageID": loraPunchMsg.GetHash()}
            elif len(msgSubBatch.MessageSubscriptionBatchItems) == 2:
                loraPunchDoubleMsg = LoraRadioMessageCreator.GetPunchDoubleMessage(batteryLow, ackReq, None)
                loraPunchDoubleMsg.SetSIMessageByteArrays(payloadData, msgSubBatch.MessageSubscriptionBatchItems[1].MessageData)
                loraPunchDoubleMsg.SetRepeater(reqRepeater)
                loraPunchDoubleMsg.GenerateAndAddRSCode()
                interleavedMessageData = LoraRadioMessagePunchDoubleReDCoSRS.InterleaveToAirOrder(
                    loraPunchDoubleMsg.GetByteArray())
                return {"Data": (interleavedMessageData,), "MessageID": loraPunchDoubleMsg.GetHash()}

        return None