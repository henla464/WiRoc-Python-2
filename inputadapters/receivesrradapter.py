from chipGPIO.hardwareAbstraction import HardwareAbstraction
from datamodel.datamodel import SRRMessage
from settings.settings import SettingsClass
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
import logging
from smbus2 import SMBus
import time
from datamodel.db_helper import DatabaseHelper
from utils.utils import Utils
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
                    firmwareVersion = 1 #bus.read_byte_data(addr, ReceiveSRRAdapter.FIRMWAREVERSIONREGADDR)

                    # hardware features
                    hardwareFeatures = 0x1f #bus.read_byte_data(addr, ReceiveSRRAdapter.HARDWAREFEATURESREGADDR)

                    if SettingsClass.GetSRRRedChannelEnabled() or SettingsClass.GetSRRBlueChannelEnabled():
                        # Listens for messages on at least one of the two SRR channels.
                        ReceiveSRRAdapter.Instances.append(
                            ReceiveSRRAdapter("SRR1", bus, addr, firmwareVersion, hardwareFeatures,
                                              hardwareAbstraction))
                        return True
                    else:
                        return False
                except Exception as err:
                    logging.getLogger('WiRoc.Input').error(
                        "ReceiveSRRAdapter::CreateInstances() Exception: " + str(err))
            else:
                if SettingsClass.GetSRRRedChannelEnabled() or SettingsClass.GetSRRBlueChannelEnabled():
                    # Instance already exists
                    return False
                else:
                    # Shouldn't have a instance
                    ReceiveSRRAdapter.Instances = []
                    return True
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

        HardwareAbstraction.Instance.DisableSRR()
        time.sleep(0.01)
        HardwareAbstraction.Instance.EnableSRR()
        time.sleep(0.05)

        try:
            # The SRR receiver/sender should have a unique serialno. This is used as the sender id in messages.
            # The lower four bytes of the BT Address should be unique enough.
            btAddress: str = SettingsClass.GetBTAddress()
            srrSerialNoByte0 = int(btAddress[15:17], 16)
            srrSerialNoByte1 = int(btAddress[12:14], 16)
            srrSerialNoByte2 = int(btAddress[9:11], 16)
            srrSerialNoByte3 = int(btAddress[6:8], 16)
            srrSerialNo: list[int] = [srrSerialNoByte3, srrSerialNoByte2, srrSerialNoByte1, srrSerialNoByte0]

            self.i2cBus.write_block_data(self.i2cAddress, ReceiveSRRAdapter.SERIALNOREGADDR, srrSerialNo)

            # Enable/Disable features
            featuresEnabledDisabled: int = self.i2cBus.read_byte_data(self.i2cAddress,
                                                                      ReceiveSRRAdapter.HARDWAREFEATURESENABLEDISABLEREGADDR)
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

            self.WiRocLogger.info(
                f"ReceiveSRRAdapter::Init() srrEnabled: {srrEnabled} redChannelEnabled: {redChannelEnabled} redChannelListenOnly: {redChannelListenOnly} blueChannelEnabled: {blueChannelEnabled} blueChannelListenOnly: {blueChannelListenOnly} srrMode: {srrMode}")
            self.WiRocLogger.info(
                f"ReceiveSRRAdapter::Init() newFeaturesEnabledDisabled {newFeaturesEnabledDisabled:>08b}")

            self.i2cBus.write_byte_data(self.i2cAddress, ReceiveSRRAdapter.HARDWAREFEATURESENABLEDISABLEREGADDR,
                                        newFeaturesEnabledDisabled)

            featuresEnabledDisabled2: int = self.i2cBus.read_byte_data(self.i2cAddress,
                                                                      ReceiveSRRAdapter.HARDWAREFEATURESENABLEDISABLEREGADDR)
            self.WiRocLogger.info(
                f"ReceiveSRRAdapter::Init() newFeaturesEnabledDisabled2 read back {featuresEnabledDisabled2:>08b}")

            self.srrEnabled = srrEnabled
            self.redChannelEnabled = redChannelEnabled
            self.redChannelListenOnly = redChannelListenOnly
            self.blueChannelEnabled = blueChannelEnabled
            self.blueChannelListenOnly = blueChannelListenOnly
            self.srrMode = srrMode
            self.isInitialized = True
        except Exception as ex:
            self.WiRocLogger.error(f"ReceiveSRRAdapter::Init() Exception {ex}")
            return False

        return True

    def UpdateInfrequently(self) -> bool:
        return True

    def GetErrorMsg(self) -> int:
        statusReg = self.i2cBus.read_byte_data(self.i2cAddress, ReceiveSRRAdapter.STATUSREGADDR)
        errorBit = 0x80
        if statusReg & errorBit:
            self.WiRocLogger.error(
                f"ReceiveSRRAdapter::GetErrorMsg() statusReg: {statusReg}")

            # msg length
            msgLength = self.i2cBus.read_byte_data(self.i2cAddress, ReceiveSRRAdapter.ERRORLENGTHREGADDR)

            errorMessage = bytearray()
            index = 0
            if msgLength > 0:
                remaining = msgLength
                while index < msgLength:
                    self.i2cBus.write_byte_data(self.i2cAddress, ReceiveSRRAdapter.SETDATAINDEXREGADDR, index)
                    noToRead = remaining
                    if remaining > 31:
                        noToRead = 31
                    data = self.i2cBus.read_i2c_block_data(self.i2cAddress, ReceiveSRRAdapter.ERRORMSGREGADDR, noToRead)
                    errorMessage.extend(data)
                    remaining -= noToRead
                    index += noToRead

            errorMsgString: str = errorMessage.decode("utf-8")
            self.WiRocLogger.error(
                f"ReceiveSRRAdapter::GetErrorMsg() error message: {errorMsgString}")

        else:
            self.WiRocLogger.debug(
                f"ReceiveSRRAdapter::GetErrorMsg() statusReg: {statusReg}")
        return statusReg

    def GetData(self) -> InputDataDict | None:
        if self.hardwareAbstraction.GetSRRIRQValue():

            # msg length
            msgLength = self.i2cBus.read_byte_data(self.i2cAddress, ReceiveSRRAdapter.PUNCHLENGTHREGADDR)
            if msgLength == 0:
                # no message to fetch, so should be an error message
                self.GetErrorMsg()
                return None

            if msgLength not in SRRMessage.MessageTypeLengths.values():
                self.WiRocLogger.error(
                    f"ReceiveSRRAdapter::GetData() Message of incorrect length received. Length: {msgLength}")
                # read the message so that it is popped from the queue on the SRR receiver board
                if msgLength > 0:
                    dataToDiscard = bytearray()
                    remainingDataToDiscard:int = msgLength
                    indexIntoDataToDiscard:int = 0
                    while indexIntoDataToDiscard < msgLength:
                        self.i2cBus.write_byte_data(self.i2cAddress, ReceiveSRRAdapter.SETDATAINDEXREGADDR, indexIntoDataToDiscard)
                        noToReadOfDataToDiscard = remainingDataToDiscard
                        if remainingDataToDiscard > 31:
                            noToReadOfDataToDiscard = 31
                        data: list[int] = self.i2cBus.read_i2c_block_data(self.i2cAddress, ReceiveSRRAdapter.PUNCHREGADDR,
                                                               noToReadOfDataToDiscard)
                        dataToDiscard.extend(data)
                        remainingDataToDiscard -= noToReadOfDataToDiscard
                        indexIntoDataToDiscard += noToReadOfDataToDiscard
                    self.WiRocLogger.error(f"ReceiveSRRAdapter::GetData() The SRR Message of incorrect length received: " + Utils.GetDataInHex(dataToDiscard, logging.ERROR))
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
