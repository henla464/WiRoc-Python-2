from chipGPIO.hardwareAbstraction import HardwareAbstraction
from datamodel.db_helper import DatabaseHelper
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from settings.settings import SettingsClass
from utils.utils import Utils
import logging


class ReceiveRepeaterMessagesAdapter(object):
    Instances = []
    WiRocLogger = logging.getLogger('WiRoc.Input')

    @staticmethod
    def CreateInstances(hardwareAbstraction: HardwareAbstraction) -> bool:
        if SettingsClass.GetLoraMode() == "REPEATER":
            if len(ReceiveRepeaterMessagesAdapter.Instances) == 0:
                ReceiveRepeaterMessagesAdapter.Instances.append(ReceiveRepeaterMessagesAdapter("rcvRepeater1"))
                return True
        else:
            if len(ReceiveRepeaterMessagesAdapter.Instances) > 0:
                ReceiveRepeaterMessagesAdapter.Instances.clear()
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

    def UpdateInfrequently(self):
        return True

    def GetData(self):
        messageToAdd = DatabaseHelper.get_repeater_message_to_add()
        if messageToAdd is not None:
            self.lastRepeaterMessageBoxIdAdded = messageToAdd.id

            ReceiveRepeaterMessagesAdapter.WiRocLogger.debug("ReceiveRepeaterMessagesAdapter::GetData() Data to fetch: " + Utils.GetDataInHex(messageToAdd.MessageData, logging.DEBUG))
            loraMessage = None
            if messageToAdd.MessageSubTypeName == "SIMessage":
                loraMessage = LoraRadioMessageCreator.GetPunchReDCoSMessageByFullMessageData(messageToAdd.MessageData, messageToAdd.RSSIValue)
            elif messageToAdd.MessageSubTypeName == "SIMessageDouble":
                loraMessage = LoraRadioMessageCreator.GetPunchDoubleReDCoSMessageByFullMessageData(messageToAdd.MessageData, messageToAdd.RSSIValue)
            elif messageToAdd.MessageSubTypeName == "Status":
                loraMessage = LoraRadioMessageCreator.GetStatusMessageByFullMessageData(messageToAdd.MessageData, messageToAdd.RSSIValue)
            return {"MessageType": "DATA", "MessageSource":"Repeater", "MessageSubTypeName": messageToAdd.MessageSubTypeName, "Data": messageToAdd.MessageData, "MessageID": messageToAdd.MessageID, "LoraRadioMessage": loraMessage, "ChecksumOK": True}
        return None

    def AddedToMessageBox(self, mbid: int) -> None:
        DatabaseHelper.archive_repeater_message_after_added_to_message_box(self.lastRepeaterMessageBoxIdAdded)
        return None