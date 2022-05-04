from battery import Battery
from loraradio.LoraRadioDataHandler import LoraRadioDataHandler
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from loraradio.LoraRadioMessageRS import LoraRadioMessageRS
from settings.settings import SettingsClass
import logging


class RepeaterSIMessageDoubleToLoraTransform(object):
    DeleteAfterSent = False
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType():
        return "REPEATER"

    @staticmethod
    def GetInputMessageSubType():
        return "SIMessageDouble"

    @staticmethod
    def GetOutputMessageType():
        return "LORA"

    @staticmethod
    def GetOutputMessageSubType():
        return "Punch"

    @staticmethod
    def GetName():
        return "RepeaterSIMessageDoubleToLoraTransform"

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
        RepeaterSIMessageDoubleToLoraTransform.DeleteAfterSent = not SettingsClass.GetAcknowledgementRequested()
        return RepeaterSIMessageDoubleToLoraTransform.DeleteAfterSent

    @staticmethod
    def GetDeleteAfterSentChanged():
        return RepeaterSIMessageDoubleToLoraTransform.DeleteAfterSent != (not SettingsClass.GetAcknowledgementRequested())

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSubBatch, subscriberAdapter):
        RepeaterSIMessageDoubleToLoraTransform.WiRocLogger.debug("RepeaterSIMessageDoubleToLoraTransform::Transform()")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        loraPunchDoubleMsg = LoraRadioMessageCreator.GetPunchDoubleMessageByFullMessageData(payloadData)
        batteryLow = Battery.GetIsBatteryLow() or loraPunchDoubleMsg.GetBatteryLow()
        ackReq = SettingsClass.GetAcknowledgementRequested()
        loraPunchDoubleMsg.SetAckRequested(ackReq)
        loraPunchDoubleMsg.SetBatteryLow(batteryLow)
        loraPunchDoubleMsg.SetRepeater(False)
        loraPunchDoubleMsg.GenerateAndAddRSCode()
        return {"Data": (loraPunchDoubleMsg.GetByteArray(),), "MessageID": loraPunchDoubleMsg.GetHash()}
