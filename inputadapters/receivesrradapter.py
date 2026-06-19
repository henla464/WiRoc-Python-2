from chipGPIO.hardwareAbstraction import HardwareAbstraction
from datamodel.datamodel import SRRMessage
from settings.settings import SettingsClass
import logging
from datamodel.db_helper import DatabaseHelper
from utils.utils import Utils
from srrradio import SRRRadio
from .inputdatadict import InputDataDict


class ReceiveSRRAdapter(object):
    Instances = []

    @staticmethod
    def CreateInstances(hardwareAbstraction: HardwareAbstraction) -> bool:
        if hardwareAbstraction.HasSRR():

            if len(ReceiveSRRAdapter.Instances) == 0:

                srrEnabled: bool = SettingsClass.GetSRREnabled()
                if not srrEnabled:
                    HardwareAbstraction.Instance.DisableSRR()
                    ReceiveSRRAdapter.Instances = []
                    return False
                srrMode: str = SettingsClass.GetSRRMode()
                if srrMode == "SEND":
                    ReceiveSRRAdapter.Instances = []
                    return False

                if SettingsClass.GetSRRRedChannelEnabled() or SettingsClass.GetSRRBlueChannelEnabled():
                    srrRadio = SRRRadio.GetInstance(hardwareAbstraction)
                    if srrRadio is not None:
                        ReceiveSRRAdapter.Instances.append(
                            ReceiveSRRAdapter("SRR1", srrRadio, hardwareAbstraction))
                        return True
                return False
            else:

                srrEnabled: bool = SettingsClass.GetSRREnabled()
                if not srrEnabled:
                    HardwareAbstraction.Instance.DisableSRR()
                    ReceiveSRRAdapter.Instances = []
                    return True
                srrMode: str = SettingsClass.GetSRRMode()
                if srrMode == "SEND":
                    ReceiveSRRAdapter.Instances = []
                    return True

                if SettingsClass.GetSRRRedChannelEnabled() or SettingsClass.GetSRRBlueChannelEnabled():
                    return False
                else:
                    ReceiveSRRAdapter.Instances = []
                    return True
        return False

    @staticmethod
    def GetTypeName() -> str:
        return "SRR"

    def __init__(self, instanceName: str, srrRadio: SRRRadio, hardwareAbstraction: HardwareAbstraction):
        self.WiRocLogger = logging.getLogger('WiRoc.Input')
        self.instanceName: str = instanceName
        self.srrRadio: SRRRadio = srrRadio
        self.hardwareAbstraction = hardwareAbstraction

    def GetInstanceName(self) -> str:
        return self.instanceName

    def GetIsInitialized(self) -> bool:
        return self.srrRadio.GetIsInitialized(
            SettingsClass.GetSRREnabled(), SettingsClass.GetSRRMode(),
            SettingsClass.GetSRRRedChannelEnabled(), SettingsClass.GetSRRRedChannelListenOnly(),
            SettingsClass.GetSRRBlueChannelEnabled(), SettingsClass.GetSRRBlueChannelListenOnly())

    def ShouldBeInitialized(self) -> bool:
        return not self.GetIsInitialized()

    def Init(self) -> bool:
        return self.srrRadio.Init(
            SettingsClass.GetSRREnabled(), SettingsClass.GetSRRMode(),
            SettingsClass.GetSRRRedChannelEnabled(), SettingsClass.GetSRRRedChannelListenOnly(),
            SettingsClass.GetSRRBlueChannelEnabled(), SettingsClass.GetSRRBlueChannelListenOnly())

    def UpdateInfrequently(self) -> bool:
        return True

    def GetErrorMsg(self) -> int:
        statusReg, _ = self.srrRadio.GetErrorData()
        return statusReg

    def GetData(self) -> InputDataDict | None:
        if self.hardwareAbstraction.GetSRRIRQValue():

            msgLength = self.srrRadio.GetPunchLength()
            if msgLength == 0:
                self.srrRadio.GetErrorData()
                return None

            if msgLength not in SRRMessage.MessageTypeLengths.values():
                self.WiRocLogger.error(
                    f"ReceiveSRRAdapter::GetData() Message of incorrect length received. Length: {msgLength}")
                if msgLength > 0:
                    dataToDiscard = self.srrRadio.ReadDataBlock(msgLength)
                    self.WiRocLogger.error(
                        f"ReceiveSRRAdapter::GetData() The SRR Message of incorrect length received: "
                        + Utils.GetDataInHex(dataToDiscard, logging.ERROR))
                return None

            punchMessageData = self.srrRadio.ReadDataBlock(msgLength)

            self.WiRocLogger.debug("ReceiveSRRAdapter::GetData() Data to fetch")
            self.WiRocLogger.debug(
                "ReceiveSRRAdapter::GetData() Data: " + Utils.GetDataInHex(punchMessageData, logging.DEBUG))
            try:
                DatabaseHelper.add_message_stat(self.GetInstanceName(), "SRRMessage", "Received", 1)
            except Exception as ex:
                self.WiRocLogger.error("ReceiveSRRAdapter::GetData() Error saving statistics: " + str(ex))

            return {"MessageType": "DATA", "MessageSubTypeName": "SRRMessage",
                    "MessageSource": "SRR", "Data": punchMessageData,
                    "ChecksumOK": True, "MessageID": None,
                    "SIStationSerialNumber": None, "LoraRadioMessage": None}
        return None

    def AddedToMessageBox(self, mbid: int) -> None:
        return None
