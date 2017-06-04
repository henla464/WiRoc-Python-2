from datamodel.datamodel import LoraRadioMessage
from datamodel.datamodel import SIMessage
from battery import Battery
from datamodel.db_helper import DatabaseHelper

class SITestToLoraTransform(object):

    @staticmethod
    def GetInputMessageType():
        return "SITEST"

    @staticmethod
    def GetOutputMessageType():
        return "LORA"

    @staticmethod
    def GetName():
        return "SITestToLoraTransform"

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSub):
        payloadData = msgSub.MessageData
        siMsg = SIMessage()
        siMsg.AddPayload(payloadData)
        if siMsg.GetMessageType() == SIMessage.SIPunch:
            payloadDataLength = len(payloadData)
            messageType = LoraRadioMessage.MessageTypeSIPunch
            batteryLow = Battery.GetIsBatteryLow()
            ackReq = DatabaseHelper.get_test_punch_ack_req(msgSub.MessageBoxId)
            loraMessage = LoraRadioMessage(payloadDataLength, messageType, batteryLow, ackReq)
            loraMessage.AddPayload(payloadData)
            return {"Data": loraMessage.GetByteArray(), "CustomData": loraMessage.GetMessageNumber()}
        return None