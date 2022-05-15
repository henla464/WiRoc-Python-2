from battery import Battery
from loraradio.LoraRadioDataHandler import LoraRadioDataHandler
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from loraradio.LoraRadioMessageRS import LoraRadioMessageRS, LoraRadioMessagePunchReDCoSRS
from settings.settings import SettingsClass
import logging

class RepeaterSIMessageToLoraTransform(object):
    DeleteAfterSent = False
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType():
        return "REPEATER"

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
        return "RepeaterSIMessageToLoraTransform"

    @staticmethod
    def GetBatchSize():
        return 1

    @staticmethod
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter):
        if LoraRadioDataHandler.GetRepeater(messageBoxData.MessageData):
            # no ack expected from receiver, should be sent after repeater sent ack
            return 0
        else:
            # possible ack from receiver 10 + ack sent from repeater 10
            # add 2 extra loop
            return LoraRadioMessageRS.GetLoraMessageTimeSendingTimeSByMessageType(LoraRadioMessageRS.MessageTypeLoraAck)*2+0.1

    @staticmethod
    def GetDeleteAfterSent():
        # check setting for ack
        RepeaterSIMessageToLoraTransform.DeleteAfterSent = not SettingsClass.GetAcknowledgementRequested()
        return RepeaterSIMessageToLoraTransform.DeleteAfterSent

    @staticmethod
    def GetDeleteAfterSentChanged():
        return RepeaterSIMessageToLoraTransform.DeleteAfterSent != (not SettingsClass.GetAcknowledgementRequested())

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSubBatch, subscriberAdapter):
        RepeaterSIMessageToLoraTransform.WiRocLogger.debug("RepeaterSIMessageToLoraTransform::Transform()")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        loraPunchMsg = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(payloadData)
        batteryLow = Battery.GetIsBatteryLow() or loraPunchMsg.GetBatteryLow()
        ackReq = SettingsClass.GetAcknowledgementRequested()
        loraPunchMsg.SetAckRequested(ackReq)
        loraPunchMsg.SetBatteryLow(batteryLow)
        loraPunchMsg.SetRepeater(False)
        loraPunchMsg.GenerateAndAddRSCode()
        interleavedMessageData = LoraRadioMessagePunchReDCoSRS.InterleaveToAirOrder(
            loraPunchMsg.GetByteArray())
        return {"Data": (interleavedMessageData,), "MessageID": loraPunchMsg.GetHash()}
