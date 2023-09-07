from datamodel.datamodel import SIMessage, MessageSubscriptionBatch
from battery import Battery
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from loraradio.LoraRadioMessageRS import LoraRadioMessagePunchReDCoSRS, LoraRadioMessagePunchDoubleReDCoSRS
from settings.settings import SettingsClass
import logging


class SITestTestToLoraTransform(object):
    DeleteAfterSent = False
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType() -> str:
        return "SITEST"

    @staticmethod
    def GetInputMessageSubType() -> str:
        return "Test"

    @staticmethod
    def GetOutputMessageType() -> str:
        return "LORA"

    @staticmethod
    def GetName() -> str:
        return "SITestTestToLoraTransform"

    @staticmethod
    def GetOutputMessageSubType() -> str:
        return "Punch"

    @staticmethod
    def GetBatchSize() -> int:
        return 2

    @staticmethod
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter) -> float | None:
        return 0

    @staticmethod
    def GetDeleteAfterSent() -> bool:
        # check setting for ack
        SITestTestToLoraTransform.DeleteAfterSent = not SettingsClass.GetAcknowledgementRequested()
        return SITestTestToLoraTransform.DeleteAfterSent

    @staticmethod
    def GetDeleteAfterSentChanged() -> bool:
        return SITestTestToLoraTransform.DeleteAfterSent != (not SettingsClass.GetAcknowledgementRequested())

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSubBatch: MessageSubscriptionBatch, subscriberAdapter):
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
                loraPunchMsg = LoraRadioMessageCreator.GetPunchReDCoSMessage(batteryLow, ackReq, None)
                loraPunchMsg.SetSIMessageByteArray(payloadData)
                loraPunchMsg.SetRepeater(reqRepeater)
                loraPunchMsg.GenerateAndAddRSCode()
                loraPunchMsg.GenerateAndAddCRC()
                interleavedMessageData = LoraRadioMessagePunchReDCoSRS.InterleaveToAirOrder(
                    loraPunchMsg.GetByteArray())
                return {"Data": (interleavedMessageData,), "MessageID": loraPunchMsg.GetHash()}
            elif len(msgSubBatch.MessageSubscriptionBatchItems) == 2:
                loraPunchDoubleMsg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessage(batteryLow, ackReq, None)
                loraPunchDoubleMsg.SetSIMessageByteArrays(payloadData, msgSubBatch.MessageSubscriptionBatchItems[1].MessageData)
                loraPunchDoubleMsg.SetRepeater(reqRepeater)
                loraPunchDoubleMsg.GenerateAndAddRSCode()
                loraPunchDoubleMsg.GenerateAndAddCRC()
                interleavedMessageData = LoraRadioMessagePunchDoubleReDCoSRS.InterleaveToAirOrder(
                    loraPunchDoubleMsg.GetByteArray())
                return {"Data": (interleavedMessageData,), "MessageID": loraPunchDoubleMsg.GetHash()}

        return None