from battery import Battery
from datamodel.datamodel import SIMessage, MessageSubscriptionBatch, SRRMessage, SRRBoardPunch, AirPlusPunch, \
    AirPlusPunchOneOfMultiple
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

    @staticmethod
    def GetSIMsg(srrPayloadData: bytearray, subscriberAdapter) -> SIMessage:
        siMsg: SIMessage | None = None
        headerSize: int = SRRMessage.GetHeaderSize()

        if srrPayloadData[0] >= headerSize:
            srrMessage = SRRMessage()
            srrMessage.AddPayload(srrPayloadData[0:headerSize])
            messageType: int = srrMessage.GetMessageType()
            if messageType == SRRMessage.SRRBoardPunch:
                srrBoardPunch = SRRBoardPunch()
                srrBoardPunch.AddPayload(srrPayloadData)
                siMsg = srrBoardPunch.GetSIMessage()
            elif messageType == SRRMessage.AirPlusPunch:
                airPlusPunch = AirPlusPunch()
                airPlusPunch.AddPayload(srrPayloadData)
                siMsg = airPlusPunch.GetSIMessage()
            elif messageType == SRRMessage.AirPlusPunchOneOfMultiple:
                airPlusPunchOneOfMultiple = AirPlusPunchOneOfMultiple()
                airPlusPunchOneOfMultiple.AddPayload(srrPayloadData)
                siMsg = airPlusPunchOneOfMultiple.GetSIMessage()

        return siMsg

    @staticmethod
    def Transform(msgSubBatch: MessageSubscriptionBatch, subscriberAdapter):
        SRRSRRMessageToLoraTransform.WiRocLogger.debug("SRRSRRMessageToLoraTransform::Transform()")

        ackReq = SettingsClass.GetAcknowledgementRequested()
        reqRepeater = subscriberAdapter.GetShouldRequestRepeater()
        batteryLow = Battery.GetIsBatteryLow()

        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        siMsg: SIMessage = SRRSRRMessageToLoraTransform.GetSIMsg(payloadData, subscriberAdapter)
        siMsgPayload = siMsg.GetByteArray()

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
            payloadData2 = msgSubBatch.MessageSubscriptionBatchItems[1].MessageData
            siMsg2: SIMessage = SRRSRRMessageToLoraTransform.GetSIMsg(payloadData2, subscriberAdapter)

            loraPunchDoubleMsg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessage(batteryLow, ackReq, None)
            siMsgPayload2 = siMsg2.GetByteArray()
            loraPunchDoubleMsg.SetSIMessageByteArrays(siMsgPayload, siMsgPayload2)
            loraPunchDoubleMsg.SetRepeater(reqRepeater)
            loraPunchDoubleMsg.GenerateAndAddRSCode()
            loraPunchDoubleMsg.GenerateAndAddCRC()
            interleavedMessageData = LoraRadioMessagePunchDoubleReDCoSRS.InterleaveToAirOrder(
                loraPunchDoubleMsg.GetByteArray())
            return {"Data": (interleavedMessageData,), "MessageID": loraPunchDoubleMsg.GetHash()}
