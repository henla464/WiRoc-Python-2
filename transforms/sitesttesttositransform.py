from datamodel.datamodel import SIMessage
import logging


class SITestTestMessageToSITransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType():
        return "SITEST"

    @staticmethod
    def GetInputMessageSubType():
        return "Test"

    @staticmethod
    def GetOutputMessageType():
        return "SI"

    @staticmethod
    def GetOutputMessageSubType():
        return "Punch"

    @staticmethod
    def GetName():
        return "SISIMessageToSITransform"

    @staticmethod
    def GetBatchSize():
        return 1

    @staticmethod
    def GetWaitThisNumberOfSeconds(messageBoxData, msgSub, subAdapter):
        return 0

    @staticmethod
    def GetDeleteAfterSent():
        return True

    @staticmethod
    def GetDeleteAfterSentChanged():
        return False

    #payloadData is a bytearray
    @staticmethod
    def Transform(msgSubBatch, subscriberAdapter):
        SITestTestMessageToSITransform.WiRocLogger.debug("SITestTestMessageToSITransform::Transform()")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        siMsg = SIMessage()
        siMsg.AddPayload(payloadData)
        return {"Data": (payloadData,), "MessageID": None}
