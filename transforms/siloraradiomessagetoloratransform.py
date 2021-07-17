from datamodel.datamodel import SIMessage
from battery import Battery
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from loraradio.LoraRadioMessageRS import LoraRadioMessageRS
from settings.settings import SettingsClass

class SILoraRadioMessageToLoraTransform(object):
    DeleteAfterSent = False

    @staticmethod
    def GetInputMessageType():
        return "SI"

    @staticmethod
    def GetInputMessageSubType():
        return "LoraRadioMessage"

    @staticmethod
    def GetOutputMessageType():
        return "LORA"

    @staticmethod
    def GetName():
        return "SILoraRadioMessageToLoraTransform"

    @staticmethod
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter):
        payloadData = messageBoxData.MessageData
        siMsg = SIMessage()
        siMsg.AddPayload(payloadData)
        # WiRoc to WiRoc message
        unwrappedMessage = payloadData[3:-3]
        # Assume it is a LoraRadioMessageRS that is wrapped
        headerMessageType = unwrappedMessage[1] & 0x1F
        if headerMessageType == LoraRadioMessageRS.MessageTypeStatus:
            if messageBoxData.MessageSource == "WiRoc":
                return SettingsClass.GetLoraMessageTimeSendingTimeSByMessageType(LoraRadioMessageRS.MessageTypeLoraAck)+0.1 # ack 10 bytes + 2 loop extra
        return None

    @staticmethod
    def GetDeleteAfterSent():
        # check setting for ack
        SILoraRadioMessageToLoraTransform.DeleteAfterSent = not SettingsClass.GetAcknowledgementRequested()
        return SILoraRadioMessageToLoraTransform.DeleteAfterSent

    @staticmethod
    def GetDeleteAfterSentChanged():
        return SILoraRadioMessageToLoraTransform.DeleteAfterSent != (not SettingsClass.GetAcknowledgementRequested())

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSub, subscriberAdapter):
        payloadData = msgSub.MessageData
        siMsg = SIMessage()
        siMsg.AddPayload(payloadData)
        #WiRoc to WiRoc message
        unwrappedMessage = payloadData[3:-3]
        # Assume it is a LoraRadioMessage that is wrapped
        headerMessageType = unwrappedMessage[1] & 0x1F
        if headerMessageType == LoraRadioMessageRS.MessageTypeStatus:
            # We received a status message wrapped in a WiRoc to WiRoc message
            # We want to send it on, but add information about this WiRoc
            loraStatusMsg = LoraRadioMessageCreator.GetStatusMessageByFullMessageData(unwrappedMessage)
            loraStatusMsg.AddThisWiRocToStatusMessage(SettingsClass.GetSIStationNumber(),
                                                    Battery.GetBatteryPercent4Bits())
            batteryLow = Battery.GetIsBatteryLow() or loraStatusMsg.GetBatteryLow()
            loraStatusMsg.SetBatteryLowBit(batteryLow)
            ackReq = SettingsClass.GetAcknowledgementRequested()
            loraStatusMsg.SetAckRequested(ackReq)
            reqRepeater = subscriberAdapter.GetShouldRequestRepeater()
            loraStatusMsg.SetRepeater(reqRepeater)
            loraStatusMsg.GenerateRSCode()
            return {"Data": loraStatusMsg.GetByteArray(), "MessageID": loraStatusMsg.GetHash()}
        else:
            return None
