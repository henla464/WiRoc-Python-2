from datamodel.datamodel import SIMessage
from datamodel.db_helper import DatabaseHelper
from utils.utils import Utils
from struct import *
import logging

class ReceiveRepeaterMessagesAdapter(object):
    Instances = []
    @staticmethod
    def CreateInstances():
        if len(ReceiveRepeaterMessagesAdapter.Instances) == 0:
            ReceiveRepeaterMessagesAdapter.Instances.append(ReceiveRepeaterMessagesAdapter("rcvRepeater1"))
            return True
        return False

    @staticmethod
    def GetTypeName():
        return "REPEATER"

    def __init__(self, instanceName):
        self.instanceName = instanceName
        self.isInitialized = False
        self.lastRepeaterMessageBoxIdAdded = None

    def GetInstanceName(self):
        return self.instanceName

    def GetIsInitialized(self):
        return self.isInitialized

    def ShouldBeInitialized(self):
        return not self.isInitialized

    def Init(self):
        if self.GetIsInitialized():
            return True
        self.isInitialized = True
        return True

    def UpdateInfreqently(self):
        return True

    def GetData(self):
        messageToAdd = DatabaseHelper.get_repeater_message_to_add()
        if messageToAdd is not None:
            self.lastRepeaterMessageBoxIdAdded = messageToAdd.id

            logging.debug("ReceiveRepeaterMessagesAdapter::GetData() Data to fetch")
            dataInHex = ''.join(format(x, '02x') for x in messageToAdd.MessageData)
            logging.debug(dataInHex)
            return {"MessageType": "DATA", "MessageSource":"Repeater", "MessageSubTypeName": "SIMessage", "Data": messageToAdd.MessageData, "ChecksumOK": True}
        return None

    def AddedToMessageBox(self, mbid):
        DatabaseHelper.set_relay_message_added_to_message_box(self.lastRepeaterMessageBoxIdAdded, mbid)
        return None