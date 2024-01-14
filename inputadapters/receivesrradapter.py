from chipGPIO.hardwareAbstraction import HardwareAbstraction
from datamodel.datamodel import SRRMessage
from settings.settings import SettingsClass
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
import logging
from smbus2 import SMBus
from datamodel.db_helper import DatabaseHelper
from .inputdatadict import InputDataDict


class ReceiveSRRAdapter(object):
    Instances = []
    FIRMWAREVERSIONREGADDR = 0x00
    HARDWAREFEATURESREGADDR = 0x01
    SERIALNOREGADDR = 0x02
    ERRORCOUNTREGADDR = 0x03
    STATUSREGADDR = 0x04
    SETDATAINDEXREGADDR = 0x05
    HARDWAREFEATURESENABLEDISABLEREGADDR = 0x06

    # Length registers
    PUNCHLENGTHREGADDR = 0x20
    ERRORLENGTHREGADDR = 0x27
    PUNCHREGADDR = 0x40
    ERRORMSGREGADDR = 0x47

    RED_CHANNEL_BIT = 0x01
    BLUE_CHANNEL_BIT = 0x02
    ERROR_ON_UART_BIT = 0x04
    RED_CHANNEL_LISTENONLY_BIT = 0x08
    BLUE_CHANNEL_LISTENONLY_BIT = 0x10
    SEND_MODE_BIT = 0x20

    @staticmethod
    def CreateInstances(hardwareAbstraction: HardwareAbstraction) -> bool:
        if hardwareAbstraction.HasSRR():
            if len(ReceiveSRRAdapter.Instances) == 0:
                bus = SMBus(0)  # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)
                addr = 0x20

                try:
                    # firmware version
                    firmwareVersion = bus.read_byte_data(addr, ReceiveSRRAdapter.FIRMWAREVERSIONREGADDR)

                    # hardware features
                    hardwareFeatures = bus.read_byte_data(addr, ReceiveSRRAdapter.HARDWAREFEATURESREGADDR)

                    if hardwareFeatures & ReceiveSRRAdapter.RED_CHANNEL_BIT or hardwareFeatures & ReceiveSRRAdapter.BLUE_CHANNEL_BIT:
                        # Listens for messages on at least one of the two SRR channels.
                        ReceiveSRRAdapter.Instances.append(
                            ReceiveSRRAdapter("SRR1", bus, addr, firmwareVersion, hardwareFeatures,
                                              hardwareAbstraction))
                    return True
                except Exception as err:
                    logging.getLogger('WiRoc.Input').error(
                        "ReceiveSRRAdapter::CreateInstances() Exception: " + str(err))
        return False

    @staticmethod
    def GetTypeName() -> str:
        return "SRR"

    def __init__(self, instanceName: str, i2cBus: SMBus, i2cAddress: int, firmwareVersion: int, hardwareFeatures: int,
                 hardwareAbstraction: HardwareAbstraction):
        self.WiRocLogger = logging.getLogger('WiRoc.Input')
        self.instanceName: str = instanceName
        self.isInitialized: bool = False
        self.i2cBus: SMBus = i2cBus
        self.i2cAddress: int = i2cAddress
        self.firmwareVersion: int = firmwareVersion
        self.hardwareFeatures: int = hardwareFeatures
        self.hardwareAbstraction = hardwareAbstraction
        self.srrEnabled: bool | None = None
        self.srrMode: str | None = None
        self.redChannelEnabled: bool | None = None
        self.redChannelListenOnly: bool | None = None
        self.blueChannelEnabled: bool | None = None
        self.blueChannelListenOnly: bool | None = None

    def GetInstanceName(self) -> str:
        return self.instanceName

    def GetIsInitialized(self) -> bool:
        srrEnabled: bool = SettingsClass.GetSRREnabled()
        srrMode: str = SettingsClass.GetSRRMode()
        redChannelEnabled: bool = SettingsClass.GetSRRRedChannelEnabled()
        redChannelListenOnly: bool = SettingsClass.GetSRRRedChannelListenOnly()
        blueChannelEnabled: bool = SettingsClass.GetSRRBlueChannelEnabled()
        blueChannelListenOnly: bool = SettingsClass.GetSRRBlueChannelListenOnly()
        return self.isInitialized and srrEnabled == self.srrEnabled \
            and srrMode == self.srrMode and redChannelEnabled == self.redChannelEnabled \
            and redChannelListenOnly == self.redChannelListenOnly and blueChannelEnabled == self.blueChannelEnabled \
            and blueChannelListenOnly == self.blueChannelListenOnly

    def ShouldBeInitialized(self) -> bool:
        return not self.GetIsInitialized()

    def Init(self) -> bool:
        if self.GetIsInitialized():
            return True

        featuresEnabledDisabled: int = self.i2cBus.read_byte_data(self.i2cAddress, ReceiveSRRAdapter.HARDWAREFEATURESENABLEDISABLEREGADDR)
        newFeaturesEnabledDisabled: int = featuresEnabledDisabled
        srrEnabled: bool = SettingsClass.GetSRREnabled()
        srrMode: str = SettingsClass.GetSRRMode()
        sendMode: bool = srrMode == "SEND"
        redChannelEnabled: bool = SettingsClass.GetSRRRedChannelEnabled()
        redChannelListenOnly: bool = SettingsClass.GetSRRRedChannelListenOnly()
        blueChannelEnabled: bool = SettingsClass.GetSRRBlueChannelEnabled()
        blueChannelListenOnly: bool = SettingsClass.GetSRRBlueChannelListenOnly()

        shouldRedChannelBeEnabled = redChannelEnabled and srrEnabled
        shouldBlueChannelBeEnabled = blueChannelEnabled and srrEnabled
        if ((featuresEnabledDisabled & ReceiveSRRAdapter.RED_CHANNEL_BIT) > 0) != shouldRedChannelBeEnabled:
            if shouldRedChannelBeEnabled:
                newFeaturesEnabledDisabled = newFeaturesEnabledDisabled | ReceiveSRRAdapter.RED_CHANNEL_BIT
            else:
                newFeaturesEnabledDisabled = newFeaturesEnabledDisabled & ~ReceiveSRRAdapter.RED_CHANNEL_BIT

        if ((featuresEnabledDisabled & ReceiveSRRAdapter.BLUE_CHANNEL_BIT) > 0) != shouldBlueChannelBeEnabled:
            if shouldBlueChannelBeEnabled:
                newFeaturesEnabledDisabled = newFeaturesEnabledDisabled | ReceiveSRRAdapter.BLUE_CHANNEL_BIT
            else:
                newFeaturesEnabledDisabled = newFeaturesEnabledDisabled & ~ReceiveSRRAdapter.BLUE_CHANNEL_BIT

        if ((featuresEnabledDisabled & ReceiveSRRAdapter.RED_CHANNEL_LISTENONLY_BIT) > 0) != redChannelListenOnly:
            if redChannelListenOnly:
                newFeaturesEnabledDisabled = newFeaturesEnabledDisabled | ReceiveSRRAdapter.RED_CHANNEL_LISTENONLY_BIT
            else:
                newFeaturesEnabledDisabled = newFeaturesEnabledDisabled & ~ReceiveSRRAdapter.RED_CHANNEL_LISTENONLY_BIT

        if ((featuresEnabledDisabled & ReceiveSRRAdapter.BLUE_CHANNEL_LISTENONLY_BIT) > 0) != blueChannelListenOnly:
            if blueChannelListenOnly:
                newFeaturesEnabledDisabled = newFeaturesEnabledDisabled | ReceiveSRRAdapter.BLUE_CHANNEL_LISTENONLY_BIT
            else:
                newFeaturesEnabledDisabled = newFeaturesEnabledDisabled & ~ReceiveSRRAdapter.BLUE_CHANNEL_LISTENONLY_BIT

        if ((featuresEnabledDisabled & ReceiveSRRAdapter.SEND_MODE_BIT) > 0) != sendMode:
            if sendMode:
                newFeaturesEnabledDisabled = newFeaturesEnabledDisabled | ReceiveSRRAdapter.SEND_MODE_BIT
            else:
                newFeaturesEnabledDisabled = newFeaturesEnabledDisabled & ~ReceiveSRRAdapter.SEND_MODE_BIT

        self.i2cBus.write_byte_data(self.i2cAddress, ReceiveSRRAdapter.HARDWAREFEATURESENABLEDISABLEREGADDR, newFeaturesEnabledDisabled)

        self.srrEnabled = srrEnabled
        self.redChannelEnabled = redChannelEnabled
        self.redChannelListenOnly = redChannelListenOnly
        self.blueChannelEnabled = blueChannelEnabled
        self.blueChannelListenOnly = blueChannelListenOnly
        self.srrMode = srrMode
        self.isInitialized = True
        return True

    def UpdateInfrequently(self) -> bool:
        return True

    def GetData(self) -> InputDataDict | None:
        if self.hardwareAbstraction.GetSRRIRQValue():
            # msg length
            msgLength = self.i2cBus.read_byte_data(self.i2cAddress, ReceiveSRRAdapter.PUNCHLENGTHREGADDR)

            if msgLength not in SRRMessage.MessageTypeLengths.values():
                self.WiRocLogger.error(
                    f"ReceiveSRRAdapter::GetData() Message of incorrect length received. Length: {msgLength}")
                return None

            # read punch
            punchMessageData = bytearray()
            index = 0
            if msgLength > 0:
                remaining = msgLength
                while index < msgLength:
                    self.i2cBus.write_byte_data(self.i2cAddress, ReceiveSRRAdapter.SETDATAINDEXREGADDR, index)
                    noToRead = remaining
                    if remaining > 31:
                        noToRead = 31
                    data = self.i2cBus.read_i2c_block_data(self.i2cAddress, ReceiveSRRAdapter.PUNCHREGADDR, noToRead)
                    punchMessageData.extend(data)
                    remaining -= noToRead
                    index += noToRead

                self.WiRocLogger.debug("ReceiveSRRAdapter::GetData() Data to fetch")

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
