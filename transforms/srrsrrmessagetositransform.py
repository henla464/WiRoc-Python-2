from datamodel.datamodel import SIMessage
import logging


class SRRSRRMessageToSITransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType():
        return "SRR"

    @staticmethod
    def GetInputMessageSubType():
        return "SRRMessage"

    @staticmethod
    def GetOutputMessageType():
        return "SI"

    @staticmethod
    def GetOutputMessageSubType():
        return "Punch"

    @staticmethod
    def GetName():
        return "SRRSRRMessageToSITransform"

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
        SRRSRRMessageToSITransform.WiRocLogger.debug("SRRSRRMessageToSITransform::Transform()")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        siMsg = SIMessage()
        siMsg.AddHeader(SIMessage.SIPunch)
        siMsg.AddPayload(payloadData[18:31])
        siMsg.AddFooter()
        return {"Data": (payloadData,), "MessageID": None}
