from battery import Battery
from datamodel.datamodel import SIMessage, MessageSubscriptionBatch
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from loraradio.LoraRadioMessageRS import LoraRadioMessageRS, LoraRadioMessagePunchReDCoSRS, \
    LoraRadioMessagePunchDoubleReDCoSRS
from settings.settings import SettingsClass
import logging

from utils.utils import Utils


class SRRSRRMessageToLoraTransform(object):
    DeleteAfterSent = False
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType() -> str:
        return "SRR"

    @staticmethod
    def GetInputMessageSubType() -> str:
        return "SRRMessage"

    @staticmethod
    def GetOutputMessageType() -> str:
        return "LORA"

    @staticmethod
    def GetOutputMessageSubType() -> str:
        return "Punch"

    @staticmethod
    def GetName() -> str:
        return "SRRSRRMessageToLoraTransform"

    @staticmethod
    def GetBatchSize() -> int:
        return 2

    @staticmethod
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter) -> float | None:
        return 0

    @staticmethod
    def GetDeleteAfterSent() -> bool:
        # check setting for ack
        SRRSRRMessageToLoraTransform.DeleteAfterSent = not SettingsClass.GetAcknowledgementRequested()
        return SRRSRRMessageToLoraTransform.DeleteAfterSent

    @staticmethod
    def GetDeleteAfterSentChanged() -> bool:
        return SRRSRRMessageToLoraTransform.DeleteAfterSent != (not SettingsClass.GetAcknowledgementRequested())

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSubBatch: MessageSubscriptionBatch, subscriberAdapter):
        SRRSRRMessageToLoraTransform.WiRocLogger.debug("SRRSRRMessageToLoraTransform::Transform()")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        siMsg = SIMessage()
        siMsg.AddHeader(SIMessage.SIPunch)
        siMsg.AddPayload(payloadData[18:31])
        siMsg.AddFooter()
        siMsgPayload = siMsg.GetByteArray()
        if siMsg.GetMessageType() == SIMessage.SIPunch:
            # all MessageSubscriptionBatchItems will be SIPunch because only SIPunch is sent from SRR SRRMessage
            ackReq = SettingsClass.GetAcknowledgementRequested()
            reqRepeater = subscriberAdapter.GetShouldRequestRepeater()
            batteryLow = Battery.GetIsBatteryLow()
            if len(msgSubBatch.MessageSubscriptionBatchItems) == 1:
                loraPunchMsg = LoraRadioMessageCreator.GetPunchReDCoSMessage(batteryLow, ackReq, None)
                loraPunchMsg.SetSIMessageByteArray(siMsgPayload)
                loraPunchMsg.SetRepeater(reqRepeater)
                loraPunchMsg.GenerateAndAddRSCode()
                loraPunchMsg.GenerateAndAddCRC()
                interleavedMessageData = LoraRadioMessagePunchReDCoSRS.InterleaveToAirOrder(
                    loraPunchMsg.GetByteArray())
                return {"Data": (interleavedMessageData,), "MessageID": loraPunchMsg.GetHash()}
            elif len(msgSubBatch.MessageSubscriptionBatchItems) == 2:
                loraPunchDoubleMsg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessage(batteryLow, ackReq, None)
                payloadData2 = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
                siMsg2 = SIMessage()
                siMsg2.AddHeader(SIMessage.SIPunch)
                siMsg2.AddPayload(payloadData2[18:31])
                siMsg2.AddFooter()
                siMsgPayload2 = siMsg2.GetByteArray()
                loraPunchDoubleMsg.SetSIMessageByteArrays(siMsgPayload, siMsgPayload2)
                loraPunchDoubleMsg.SetRepeater(reqRepeater)
                loraPunchDoubleMsg.GenerateAndAddRSCode()
                loraPunchDoubleMsg.GenerateAndAddCRC()
                interleavedMessageData = LoraRadioMessagePunchDoubleReDCoSRS.InterleaveToAirOrder(
                    loraPunchDoubleMsg.GetByteArray())
                return {"Data": (interleavedMessageData,), "MessageID": loraPunchDoubleMsg.GetHash()}
