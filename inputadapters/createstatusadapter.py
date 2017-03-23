from settings.settings import SettingsClass
import logging
from datetime import datetime, timedelta

class CreateStatusAdapter(object):
    Instances = []
    @staticmethod
    def CreateInstances():
        if SettingsClass.GetSendStatusMessages():
            if len(CreateStatusAdapter.Instances) == 0:
                CreateStatusAdapter.Instances.append(CreateStatusAdapter("status1"))
        else:
            CreateStatusAdapter.Instances = []
        return CreateStatusAdapter.Instances

    @staticmethod
    def GetTypeName():
        return "SI"

    def __init__(self, instanceName):
        self.instanceName = instanceName
        self.isInitialized = False
        self.statusMsgData = bytearray(bytes([0x02, 0xD3, 0x0D, 0x00, 0x1A, 0x00, 0x1F, 0x15, 0x8E,
                                              0x3D, 0x35, 0x0D, 0xBA, 0x00, 0x0C, 0x78, 0xAE, 0x25, 0x03]))

    def GetInstanceName(self):
        return self.instanceName

    def GetIsInitialized(self):
        return self.isInitialized

    def Init(self):
        if self.GetIsInitialized():
            return True
        self.isInitialized = True
        return True

    def GetData(self):
        if datetime.now() - SettingsClass.GetTimeOfLastMessageAdded() > timedelta(seconds=SettingsClass.GetStatusMessageInterval()):
            logging.debug("CreateStatusAdapter::GetData() Data to fetch")
            return {"MessageType": "DATA", "Data": self.statusMsgData, "ChecksumOK": True}