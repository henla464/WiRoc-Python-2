from battery import Battery
from datamodel.datamodel import MessageSubscriptionBatch
from loraradio.LoraRadioDataHandler import LoraRadioDataHandler
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from loraradio.LoraRadioMessageRS import LoraRadioMessageRS, LoraRadioMessagePunchDoubleReDCoSRS
from settings.settings import SettingsClass
import logging


class RepeaterSIMessageDoubleToLoraTransform(object):
    DeleteAfterSent = False
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType() -> str:
        return "REPEATER"

    @staticmethod
    def GetInputMessageSubType() -> str:
        return "SIMessageDouble"

    @staticmethod
    def GetOutputMessageType() -> str:
        return "LORA"

    @staticmethod
    def GetOutputMessageSubType() -> str:
        return "Punch"

    @staticmethod
    def GetName() -> str:
        return "RepeaterSIMessageDoubleToLoraTransform"

    @staticmethod
    def GetBatchSize() -> int:
        return 1

    @staticmethod
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter) -> float | None:
        if LoraRadioDataHandler.GetRepeater(messageBoxData.MessageData):
            # no ack expected from receiver, should be sent after repeater sent ack
            return 0
        else:
            # possible ack from receiver 10 + ack sent from repeater 10
            # add 2 extra loop
            return LoraRadioMessageRS.GetLoraMessageTimeSendingTimeSByMessageType(LoraRadioMessageRS.MessageTypeLoraAck)*2+0.1

    @staticmethod
    def GetDeleteAfterSent() -> bool:
        # check setting for ack
        RepeaterSIMessageDoubleToLoraTransform.DeleteAfterSent = not SettingsClass.GetAcknowledgementRequested()
        return RepeaterSIMessageDoubleToLoraTransform.DeleteAfterSent

    @staticmethod
    def GetDeleteAfterSentChanged() -> bool:
        return RepeaterSIMessageDoubleToLoraTransform.DeleteAfterSent != (not SettingsClass.GetAcknowledgementRequested())

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSubBatch: MessageSubscriptionBatch, subscriberAdapter):
        RepeaterSIMessageDoubleToLoraTransform.WiRocLogger.debug("RepeaterSIMessageDoubleToLoraTransform::Transform()")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        loraPunchDoubleMsg = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(payloadData)
        batteryLow = Battery.GetIsBatteryLow() or loraPunchDoubleMsg.GetBatteryLow()
        ackReq = SettingsClass.GetAcknowledgementRequested()
        loraPunchDoubleMsg.SetAckRequested(ackReq)
        loraPunchDoubleMsg.SetBatteryLow(batteryLow)
        loraPunchDoubleMsg.SetRepeater(False)
        loraPunchDoubleMsg.GenerateAndAddRSCode()
        interleavedMessageData = LoraRadioMessagePunchDoubleReDCoSRS.InterleaveToAirOrder(loraPunchDoubleMsg.GetByteArray())
        return {"Data": (interleavedMessageData,), "MessageID": loraPunchDoubleMsg.GetHash()}
