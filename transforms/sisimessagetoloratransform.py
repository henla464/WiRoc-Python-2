from battery import Battery
from datamodel.datamodel import SIMessage, MessageSubscriptionBatch
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from loraradio.LoraRadioMessageRS import LoraRadioMessageRS, LoraRadioMessagePunchReDCoSRS, \
    LoraRadioMessagePunchDoubleReDCoSRS
from settings.settings import SettingsClass
import logging

from utils.utils import Utils


class SISIMessageToLoraTransform(object):
    DeleteAfterSent = False
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType() -> str:
        return "SI"

    @staticmethod
    def GetInputMessageSubType() -> str:
        return "SIMessage"

    @staticmethod
    def GetOutputMessageType() -> str:
        return "LORA"

    @staticmethod
    def GetOutputMessageSubType() -> str:
        return "Punch"

    @staticmethod
    def GetName() -> str:
        return "SISIMessageToLoraTransform"

    @staticmethod
    def GetBatchSize() -> int:
        return 2

    @staticmethod
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter) -> float | None:
        return 0

    @staticmethod
    def GetDeleteAfterSent() -> bool:
        # check setting for ack
        SISIMessageToLoraTransform.DeleteAfterSent = not SettingsClass.GetAcknowledgementRequested()
        return SISIMessageToLoraTransform.DeleteAfterSent

    @staticmethod
    def GetDeleteAfterSentChanged() -> bool:
        return SISIMessageToLoraTransform.DeleteAfterSent != (not SettingsClass.GetAcknowledgementRequested())

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSubBatch: MessageSubscriptionBatch, subscriberAdapter):
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
                loraPunchDoubleMsg.SetSIMessageByteArrays(payloadData,
                                                          msgSubBatch.MessageSubscriptionBatchItems[1].MessageData)
                loraPunchDoubleMsg.SetRepeater(reqRepeater)
                loraPunchDoubleMsg.GenerateAndAddRSCode()
                loraPunchDoubleMsg.GenerateAndAddCRC()
                interleavedMessageData = LoraRadioMessagePunchDoubleReDCoSRS.InterleaveToAirOrder(
                    loraPunchDoubleMsg.GetByteArray())
                return {"Data": (interleavedMessageData,), "MessageID": loraPunchDoubleMsg.GetHash()}
