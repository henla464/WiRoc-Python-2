from utils.utils import Utils
from datamodel.datamodel import SIMessage
import logging


class SRRSRRMessageToSirapTransform(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')

    @staticmethod
    def GetInputMessageType():
        return "SRR"

    @staticmethod
    def GetInputMessageSubType():
        return "SRRMessage"

    @staticmethod
    def GetOutputMessageType():
        return "SIRAP"

    @staticmethod
    def GetOutputMessageSubType():
        return "Punch"

    @staticmethod
    def GetName():
        return "SRRSRRMessageToSirapTransform"

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
        SRRSRRMessageToSirapTransform.WiRocLogger.debug("SRRSRRMessageToSirapTransform::Transform()")
        payloadData = msgSubBatch.MessageSubscriptionBatchItems[0].MessageData
        siMsg = SIMessage()
        siMsg.AddHeader(SIMessage.SIPunch)
        siMsg.AddPayload(payloadData[18:31])
        siMsg.AddFooter()
        return {"Data": (Utils.GetSirapDataFromSIData(siMsg),), "MessageID": None}
