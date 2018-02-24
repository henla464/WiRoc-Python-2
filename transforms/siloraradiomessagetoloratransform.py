from datamodel.datamodel import LoraRadioMessage
from datamodel.datamodel import SIMessage
from battery import Battery
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
        # Assume it is a LoraRadioMessage that is wrapped
        loraMessage = LoraRadioMessage()
        loraMessage.AddPayload(unwrappedMessage)
        if loraMessage.GetMessageType() == LoraRadioMessage.MessageTypeStatus:
            if messageBoxData.MessageSource == "WiRoc":
                return SettingsClass.GetLoraMessageTimeSendingTimeS(10+2) # ack 10 bytes + 2 extra
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
        loraMessage = LoraRadioMessage()
        loraMessage.AddPayload(unwrappedMessage)
        if loraMessage.GetMessageType() == LoraRadioMessage.MessageTypeStatus:
            # We received a status message wrapped in a WiRoc to WiRoc message
            # We want to send it on, but add information about this WiRoc
            loraMessage.AddThisWiRocToStatusMessage(SettingsClass.GetSIStationNumber(),
                                                    Battery.GetBatteryPercent4Bits())
            batteryLow = Battery.GetIsBatteryLow() or loraMessage.GetBatteryLowBit()
            loraMessage.SetBatteryLowBit(batteryLow)
            ackReq = SettingsClass.GetAcknowledgementRequested()
            loraMessage.SetAcknowledgementRequested(ackReq)
            loraMessage.SetMessageNumber(msgSub.MessageNumber)
            reqRepeater = subscriberAdapter.GetShouldRequestRepeater()
            loraMessage.SetRepeaterBit(reqRepeater)
            loraMessage.UpdateChecksum()
            return {"Data": loraMessage.GetByteArray(), "MessageID": loraMessage.GetMessageID()}
        else:
            return None
