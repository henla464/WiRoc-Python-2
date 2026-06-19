from __future__ import annotations

import logging
import random
import time
from smbus2 import SMBus

from chipGPIO.hardwareAbstraction import HardwareAbstraction
from settings.settings import SettingsClass
from utils.utils import Utils


class SRRRadio(object):
    """Shared I2C communication with the SRR radio module."""

    Instances: list[SRRRadio] = []
    WiRocLogger = logging.getLogger('WiRoc')

    # Register addresses
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

    # Message data registers
    PUNCHREGADDR = 0x40
    ERRORMSGREGADDR = 0x47

    # Hardware feature bits
    RED_CHANNEL_BIT = 0x01
    BLUE_CHANNEL_BIT = 0x02
    ERROR_ON_UART_BIT = 0x04
    RED_CHANNEL_LISTENONLY_BIT = 0x08
    BLUE_CHANNEL_LISTENONLY_BIT = 0x10
    SEND_MODE_BIT = 0x20

    # Status register bits
    STATUS_PUNCH_MESSAGE_BIT = 0x01
    STATUS_ERROR_MESSAGE_BIT = 0x80

    # Maximum bytes to read in a single I2C block transfer
    MAX_I2C_BLOCK_READ = 31

    I2C_BUS = 0
    I2C_ADDRESS = 0x20

    @staticmethod
    def GetInstance(hardwareAbstraction: HardwareAbstraction) -> SRRRadio | None:
        """Return the existing SRRRadio instance, or create a new one by probing I2C."""
        if len(SRRRadio.Instances) > 0:
            return SRRRadio.Instances[0]

        try:
            bus = SMBus(SRRRadio.I2C_BUS)
            addr = SRRRadio.I2C_ADDRESS

            firmwareVersion = bus.read_byte_data(addr, SRRRadio.FIRMWAREVERSIONREGADDR)
            hardwareFeatures = bus.read_byte_data(addr, SRRRadio.HARDWAREFEATURESREGADDR)

            instance = SRRRadio(bus, addr, firmwareVersion, hardwareFeatures, hardwareAbstraction)
            SRRRadio.Instances.append(instance)
            return instance
        except Exception as err:
            SRRRadio.WiRocLogger.error(f"SRRRadio::GetInstance() Exception: {err}")
            return None

    def __init__(self, i2cBus: SMBus, i2cAddress: int, firmwareVersion: int, hardwareFeatures: int,
                 hardwareAbstraction: HardwareAbstraction):
        self.i2cBus: SMBus = i2cBus
        self.i2cAddress: int = i2cAddress
        self.firmwareVersion: int = firmwareVersion
        self.hardwareFeatures: int = hardwareFeatures
        self.hardwareAbstraction: HardwareAbstraction = hardwareAbstraction

        self.isInitialized: bool = False
        self.srrEnabled: bool | None = None
        self.srrMode: str | None = None
        self.redChannelEnabled: bool | None = None
        self.redChannelListenOnly: bool | None = None
        self.blueChannelEnabled: bool | None = None
        self.blueChannelListenOnly: bool | None = None

    def GetIsInitialized(self, srrEnabled: bool, srrMode: str,
                         redChannelEnabled: bool, redChannelListenOnly: bool,
                         blueChannelEnabled: bool, blueChannelListenOnly: bool) -> bool:
        return self.isInitialized and srrEnabled == self.srrEnabled \
            and srrMode == self.srrMode and redChannelEnabled == self.redChannelEnabled \
            and redChannelListenOnly == self.redChannelListenOnly and blueChannelEnabled == self.blueChannelEnabled \
            and blueChannelListenOnly == self.blueChannelListenOnly

    def Init(self, srrEnabled: bool, srrMode: str,
             redChannelEnabled: bool, redChannelListenOnly: bool,
             blueChannelEnabled: bool, blueChannelListenOnly: bool) -> bool:
        """Initialize the SRR radio with the given settings."""

        if self.GetIsInitialized(srrEnabled, srrMode,
                                  redChannelEnabled, redChannelListenOnly,
                                  blueChannelEnabled, blueChannelListenOnly):
            return True

        self.hardwareAbstraction.DisableSRR()
        time.sleep(0.01)
        self.hardwareAbstraction.EnableSRR()
        time.sleep(0.05)

        try:
            # Set serial number from BT address (lower four bytes)
            btAddress: str = SettingsClass.GetBTAddress()
            if btAddress == "NoBTAddress":
                btAddress = SRRRadio.GetRandomBluetoothAddress()
            srrSerialNoByte0 = int(btAddress[15:17], 16)
            srrSerialNoByte1 = int(btAddress[12:14], 16)
            srrSerialNoByte2 = int(btAddress[9:11], 16)
            srrSerialNoByte3 = int(btAddress[6:8], 16)
            srrSerialNo: list[int] = [srrSerialNoByte3, srrSerialNoByte2, srrSerialNoByte1, srrSerialNoByte0]

            self.i2cBus.write_block_data(self.i2cAddress, SRRRadio.SERIALNOREGADDR, srrSerialNo)

            # Enable/Disable features
            featuresEnabledDisabled: int = self.i2cBus.read_byte_data(
                self.i2cAddress, SRRRadio.HARDWAREFEATURESENABLEDISABLEREGADDR)
            newFeaturesEnabledDisabled: int = featuresEnabledDisabled

            sendMode: bool = srrMode == "SEND"

            shouldRedChannelBeEnabled = redChannelEnabled and srrEnabled
            shouldBlueChannelBeEnabled = blueChannelEnabled and srrEnabled

            if ((featuresEnabledDisabled & SRRRadio.RED_CHANNEL_BIT) > 0) != shouldRedChannelBeEnabled:
                if shouldRedChannelBeEnabled:
                    newFeaturesEnabledDisabled = newFeaturesEnabledDisabled | SRRRadio.RED_CHANNEL_BIT
                else:
                    newFeaturesEnabledDisabled = newFeaturesEnabledDisabled & ~SRRRadio.RED_CHANNEL_BIT

            if ((featuresEnabledDisabled & SRRRadio.BLUE_CHANNEL_BIT) > 0) != shouldBlueChannelBeEnabled:
                if shouldBlueChannelBeEnabled:
                    newFeaturesEnabledDisabled = newFeaturesEnabledDisabled | SRRRadio.BLUE_CHANNEL_BIT
                else:
                    newFeaturesEnabledDisabled = newFeaturesEnabledDisabled & ~SRRRadio.BLUE_CHANNEL_BIT

            if ((featuresEnabledDisabled & SRRRadio.RED_CHANNEL_LISTENONLY_BIT) > 0) != redChannelListenOnly:
                if redChannelListenOnly:
                    newFeaturesEnabledDisabled = newFeaturesEnabledDisabled | SRRRadio.RED_CHANNEL_LISTENONLY_BIT
                else:
                    newFeaturesEnabledDisabled = newFeaturesEnabledDisabled & ~SRRRadio.RED_CHANNEL_LISTENONLY_BIT

            if ((featuresEnabledDisabled & SRRRadio.BLUE_CHANNEL_LISTENONLY_BIT) > 0) != blueChannelListenOnly:
                if blueChannelListenOnly:
                    newFeaturesEnabledDisabled = newFeaturesEnabledDisabled | SRRRadio.BLUE_CHANNEL_LISTENONLY_BIT
                else:
                    newFeaturesEnabledDisabled = newFeaturesEnabledDisabled & ~SRRRadio.BLUE_CHANNEL_LISTENONLY_BIT

            if ((featuresEnabledDisabled & SRRRadio.SEND_MODE_BIT) > 0) != sendMode:
                if sendMode:
                    newFeaturesEnabledDisabled = newFeaturesEnabledDisabled | SRRRadio.SEND_MODE_BIT
                else:
                    newFeaturesEnabledDisabled = newFeaturesEnabledDisabled & ~SRRRadio.SEND_MODE_BIT

            SRRRadio.WiRocLogger.info(
                f"SRRRadio::Init() srrEnabled: {srrEnabled} redChannelEnabled: {redChannelEnabled} "
                f"redChannelListenOnly: {redChannelListenOnly} blueChannelEnabled: {blueChannelEnabled} "
                f"blueChannelListenOnly: {blueChannelListenOnly} srrMode: {srrMode}")
            SRRRadio.WiRocLogger.info(
                f"SRRRadio::Init() newFeaturesEnabledDisabled {newFeaturesEnabledDisabled:>08b}")

            self.i2cBus.write_byte_data(self.i2cAddress, SRRRadio.HARDWAREFEATURESENABLEDISABLEREGADDR,
                                        newFeaturesEnabledDisabled)

            featuresEnabledDisabled2: int = self.i2cBus.read_byte_data(
                self.i2cAddress, SRRRadio.HARDWAREFEATURESENABLEDISABLEREGADDR)
            SRRRadio.WiRocLogger.info(
                f"SRRRadio::Init() newFeaturesEnabledDisabled2 read back {featuresEnabledDisabled2:>08b}")

            self.srrEnabled = srrEnabled
            self.redChannelEnabled = redChannelEnabled
            self.redChannelListenOnly = redChannelListenOnly
            self.blueChannelEnabled = blueChannelEnabled
            self.blueChannelListenOnly = blueChannelListenOnly
            self.srrMode = srrMode
            self.isInitialized = True
        except Exception as ex:
            SRRRadio.WiRocLogger.error(f"SRRRadio::Init() Exception {ex}")
            return False

        return True

    @staticmethod
    def GetRandomBluetoothAddress() -> str:
        return ":".join(f"{random.randint(0, 255):02X}" for _ in range(6))

    def GetStatus(self) -> int:
        """Read the STATUS register."""
        return self.i2cBus.read_byte_data(self.i2cAddress, SRRRadio.STATUSREGADDR)

    def GetPunchLength(self) -> int:
        """Read the PUNCHLENGTH register."""
        return self.i2cBus.read_byte_data(self.i2cAddress, SRRRadio.PUNCHLENGTHREGADDR)

    def ReadDataBlock(self, length: int, dataRegisterAddr: int = PUNCHREGADDR) -> bytearray:
        """Read a block of data from the given register in chunks, using SETDATAINDEXREGADDR."""
        data = bytearray()
        index = 0
        while index < length:
            self.i2cBus.write_byte_data(self.i2cAddress, SRRRadio.SETDATAINDEXREGADDR, index)
            remaining = length - index
            noToRead = min(remaining, SRRRadio.MAX_I2C_BLOCK_READ)
            chunk = self.i2cBus.read_i2c_block_data(self.i2cAddress, dataRegisterAddr, noToRead)
            data.extend(chunk)
            index += noToRead
        return data

    def GetErrorData(self) -> tuple[int, str | None]:
        """Read error message from the SRR. Returns (statusReg, errorMsgString or None)."""
        statusReg = self.GetStatus()
        if statusReg & SRRRadio.STATUS_ERROR_MESSAGE_BIT:
            SRRRadio.WiRocLogger.error(f"SRRRadio::GetErrorData() statusReg: {statusReg}")

            msgLength = self.i2cBus.read_byte_data(self.i2cAddress, SRRRadio.ERRORLENGTHREGADDR)

            if msgLength > 0:
                errorData = self.ReadDataBlock(msgLength, SRRRadio.ERRORMSGREGADDR)
                errorMsgString: str = errorData.decode("utf-8")
                SRRRadio.WiRocLogger.error(f"SRRRadio::GetErrorData() error message: {errorMsgString}")
                return statusReg, errorMsgString
        else:
            SRRRadio.WiRocLogger.debug(f"SRRRadio::GetErrorData() statusReg: {statusReg}")
        return statusReg, None

    def SendData(self, data: bytearray) -> None:
        """Write a punch (up to 15 payload bytes) to the SRR for CC2500 transmission.
        Prepends a length byte (payload length + 1 for the length byte itself)."""
        if len(data) > 15:
            raise ValueError(f"Data length {len(data)} exceeds maximum allowed (15 bytes)")

        total_length = len(data) + 1
        full_message = bytearray([total_length]) + data
        self.i2cBus.write_i2c_block_data(self.i2cAddress, SRRRadio.PUNCHREGADDR, list(full_message))
        SRRRadio.WiRocLogger.debug(
            f"SRRRadio::SendData: Sent {len(full_message)} bytes: "
            + Utils.GetDataInHex(full_message, logging.DEBUG))
