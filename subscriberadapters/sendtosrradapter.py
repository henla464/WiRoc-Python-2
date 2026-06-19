from __future__ import annotations
from typing import Any

from chipGPIO.hardwareAbstraction import HardwareAbstraction
from settings.settings import SettingsClass
from datamodel.db_helper import DatabaseHelper
import logging
from smbus2 import SMBus
import time
from utils.utils import Utils

class SendToSRRAdapter(object):
    WiRocLogger: logging.Logger = logging.getLogger('WiRoc.Output')
    Instances: list[SendToSRRAdapter] = []
    SubscriptionsEnabled: bool = False

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
            if len(SendToSRRAdapter.Instances) == 0:
                bus = SMBus(0)  # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)
                addr = 0x20

                if SettingsClass.GetSRRMode() == "SEND" and (
                        SettingsClass.GetSRRRedChannelEnabled() or SettingsClass.GetSRRBlueChannelEnabled()):
                    
                    try:
                        # firmware version
                        firmwareVersion = bus.read_byte_data(addr, SendToSRRAdapter.FIRMWAREVERSIONREGADDR)

                        # hardware features
                        hardwareFeatures = bus.read_byte_data(addr, SendToSRRAdapter.HARDWAREFEATURESREGADDR)

                        # send messages on at least one of the two SRR channels.
                        SendToSRRAdapter.Instances.append(
                            SendToSRRAdapter("sndsrr1", bus, addr, firmwareVersion, hardwareFeatures, hardwareAbstraction))
                        return True
                    except Exception as err:
                        logging.getLogger('WiRoc.Output').error("SendToSRRAdapter::CreateInstances() Exception: " + str(err))
                        return False
                else:
                    # Shouldn't have a instance
                    SendToSRRAdapter.Instances = []
                    return False
            else:
                if SettingsClass.GetSRRMode() == "SEND" and (
                        SettingsClass.GetSRRRedChannelEnabled() or SettingsClass.GetSRRBlueChannelEnabled()):
                    # Instance already exists
                    return False
                else:
                    # Shouldn't have a instance
                    SendToSRRAdapter.Instances = []
                    return True
        return False

    @staticmethod
    def GetTypeName() -> str:
        return "SRR"

    @staticmethod
    def EnableDisableSubscription():
        if len(SendToSRRAdapter.Instances) > 0:
            isInitialized = SendToSRRAdapter.Instances[0].GetIsInitialized()
            enabled = (SettingsClass.GetSRREnabled() and SettingsClass.GetSRRMode() == "SEND")
            subscriptionShouldBeEnabled = (isInitialized and enabled)
            if SendToSRRAdapter.SubscriptionsEnabled != subscriptionShouldBeEnabled:
                SendToSRRAdapter.WiRocLogger.info(
                    "SendToSRRAdapter::EnableDisableSubscription() subscription set enabled: " + str(
                        subscriptionShouldBeEnabled))
                SendToSRRAdapter.SubscriptionsEnabled = subscriptionShouldBeEnabled
                DatabaseHelper.update_subscriptions(subscriptionShouldBeEnabled,
                                                    SendToSRRAdapter.GetDeleteAfterSent(),
                                                    SendToSRRAdapter.GetTypeName())

    @staticmethod
    def EnableDisableTransforms() -> None:
        if len(SendToSRRAdapter.Instances) > 0:
            enableSendTransforms = (SettingsClass.GetSRREnabled() and SettingsClass.GetSRRMode() == "SEND")
            DatabaseHelper.set_transform_enabled(enableSendTransforms, "LoraSIMessageToSRRTransform")
            DatabaseHelper.set_transform_enabled(enableSendTransforms, "SISIMessageToSRRTransform")
            DatabaseHelper.set_transform_enabled(enableSendTransforms, "SITestTestToSRRTransform")
            DatabaseHelper.set_transform_enabled(enableSendTransforms, "LoraSIMessageDoubleToSRRTransform")

    def __init__(self, instanceName: str, i2cBus: SMBus, i2cAddress: int, firmwareVersion: int, hardwareFeatures: int, hardwareAbstraction: HardwareAbstraction):
        self.instanceName: str = instanceName
        self.transforms: dict[str, any] = {}
        self.isInitialized: bool = False
        self.isDBInitialized: bool = False
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

    @staticmethod
    def GetDeleteAfterSent() -> bool:
        return True

    @staticmethod
    def GetWaitUntilAckSent() -> bool:
        return False

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

    # has adapter, transforms, subscriptions etc been added to database?
    def GetIsDBInitialized(self) -> bool:
        return self.isDBInitialized

    def SetIsDBInitialized(self, val: bool = True) -> None:
        self.isDBInitialized = val

    def GetTransformNames(self) -> list[str]:
        return ["LoraSIMessageToSRRTransform", "SISIMessageToSRRTransform",
                "SITestTestToSRRTransform", "LoraSIMessageDoubleToSRRTransform"]

    def SetTransform(self, transformClass):
        self.transforms[transformClass.GetName()] = transformClass

    def GetTransform(self, transformName: str) -> Any:
        return self.transforms[transformName]

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
            if btAddress == "NoBTAddress":
                # random one should be fine here
                btAddress = self.GetRandomBluetoothAddress()
            srrSerialNoByte0 = int(btAddress[15:17], 16)
            srrSerialNoByte1 = int(btAddress[12:14], 16)
            srrSerialNoByte2 = int(btAddress[9:11], 16)
            srrSerialNoByte3 = int(btAddress[6:8], 16)
            srrSerialNo: list[int] = [srrSerialNoByte3, srrSerialNoByte2, srrSerialNoByte1, srrSerialNoByte0]

            self.i2cBus.write_block_data(self.i2cAddress, SendToSRRAdapter.SERIALNOREGADDR, srrSerialNo)

            # Enable/Disable features
            featuresEnabledDisabled: int = self.i2cBus.read_byte_data(self.i2cAddress,
                                                                      SendToSRRAdapter.HARDWAREFEATURESENABLEDISABLEREGADDR)
            newFeaturesEnabledDisabled: int = featuresEnabledDisabled
            # we don't create an instance when srrEnabled is false so srrEnabled should always be true here
            srrEnabled: bool = SettingsClass.GetSRREnabled()
            # we don't create an instance when srrMode is RECEIVE so srrMode should always be SEND here
            srrMode: str = SettingsClass.GetSRRMode()
            sendMode: bool = srrMode == "SEND"
            redChannelEnabled: bool = SettingsClass.GetSRRRedChannelEnabled()
            redChannelListenOnly: bool = SettingsClass.GetSRRRedChannelListenOnly()
            blueChannelEnabled: bool = SettingsClass.GetSRRBlueChannelEnabled()
            blueChannelListenOnly: bool = SettingsClass.GetSRRBlueChannelListenOnly()

            shouldRedChannelBeEnabled = redChannelEnabled and srrEnabled
            shouldBlueChannelBeEnabled = blueChannelEnabled and srrEnabled
            if ((featuresEnabledDisabled & SendToSRRAdapter.RED_CHANNEL_BIT) > 0) != shouldRedChannelBeEnabled:
                if shouldRedChannelBeEnabled:
                    newFeaturesEnabledDisabled = newFeaturesEnabledDisabled | SendToSRRAdapter.RED_CHANNEL_BIT
                else:
                    newFeaturesEnabledDisabled = newFeaturesEnabledDisabled & ~SendToSRRAdapter.RED_CHANNEL_BIT

            if ((featuresEnabledDisabled & SendToSRRAdapter.BLUE_CHANNEL_BIT) > 0) != shouldBlueChannelBeEnabled:
                if shouldBlueChannelBeEnabled:
                    newFeaturesEnabledDisabled = newFeaturesEnabledDisabled | SendToSRRAdapter.BLUE_CHANNEL_BIT
                else:
                    newFeaturesEnabledDisabled = newFeaturesEnabledDisabled & ~SendToSRRAdapter.BLUE_CHANNEL_BIT

            if ((featuresEnabledDisabled & SendToSRRAdapter.RED_CHANNEL_LISTENONLY_BIT) > 0) != redChannelListenOnly:
                if redChannelListenOnly:
                    newFeaturesEnabledDisabled = newFeaturesEnabledDisabled | SendToSRRAdapter.RED_CHANNEL_LISTENONLY_BIT
                else:
                    newFeaturesEnabledDisabled = newFeaturesEnabledDisabled & ~SendToSRRAdapter.RED_CHANNEL_LISTENONLY_BIT

            if ((featuresEnabledDisabled & SendToSRRAdapter.BLUE_CHANNEL_LISTENONLY_BIT) > 0) != blueChannelListenOnly:
                if blueChannelListenOnly:
                    newFeaturesEnabledDisabled = newFeaturesEnabledDisabled | SendToSRRAdapter.BLUE_CHANNEL_LISTENONLY_BIT
                else:
                    newFeaturesEnabledDisabled = newFeaturesEnabledDisabled & ~SendToSRRAdapter.BLUE_CHANNEL_LISTENONLY_BIT

            if ((featuresEnabledDisabled & SendToSRRAdapter.SEND_MODE_BIT) > 0) != sendMode:
                if sendMode:
                    newFeaturesEnabledDisabled = newFeaturesEnabledDisabled | SendToSRRAdapter.SEND_MODE_BIT
                else:
                    newFeaturesEnabledDisabled = newFeaturesEnabledDisabled & ~SendToSRRAdapter.SEND_MODE_BIT

            self.WiRocLogger.info(
                f"SendToSRRAdapter::Init() srrEnabled: {srrEnabled} redChannelEnabled: {redChannelEnabled} redChannelListenOnly: {redChannelListenOnly} blueChannelEnabled: {blueChannelEnabled} blueChannelListenOnly: {blueChannelListenOnly} srrMode: {srrMode}")
            self.WiRocLogger.info(
                f"SendToSRRAdapter::Init() newFeaturesEnabledDisabled {newFeaturesEnabledDisabled:>08b}")

            self.i2cBus.write_byte_data(self.i2cAddress, SendToSRRAdapter.HARDWAREFEATURESENABLEDISABLEREGADDR,
                                        newFeaturesEnabledDisabled)

            featuresEnabledDisabled2: int = self.i2cBus.read_byte_data(self.i2cAddress,
                                                                      SendToSRRAdapter.HARDWAREFEATURESENABLEDISABLEREGADDR)
            self.WiRocLogger.info(
                f"SendToSRRAdapter::Init() newFeaturesEnabledDisabled2 read back {featuresEnabledDisabled2:>08b}")

            self.srrEnabled = srrEnabled
            self.redChannelEnabled = redChannelEnabled
            self.redChannelListenOnly = redChannelListenOnly
            self.blueChannelEnabled = blueChannelEnabled
            self.blueChannelListenOnly = blueChannelListenOnly
            self.srrMode = srrMode
            self.isInitialized = True
        except Exception as ex:
            self.WiRocLogger.error(f"SendToSRRAdapter::Init() Exception {ex}")
            return False

        return True

    def IsReadyToSend(self) -> bool:
        return True

    @staticmethod
    def GetDelayAfterMessageSent() -> float:
        return 0

    def GetRetryDelay(self, tryNo: int) -> float:
        return 1

    # messageData is tuple of bytearray
    def SendData(self, messageData: tuple[bytearray], successCB, failureCB, notSentCB,
                 settingsDictionary: dict[str, any]) -> bool:
        # Send data
        try:
            for data in messageData:
                if len(data) > 15:
                    raise ValueError(f"Data length {len(data)} exceeds maximum allowed (15 bytes)")

                # Prepend message length (including the length byte)
                total_length = len(data) + 1  # +1 for the length byte
                full_message = bytearray([total_length]) + data

                # Write the entire message in one block
                self.i2cBus.write_i2c_block_data(
                    self.i2cAddress,
                    SendToSRRAdapter.PUNCHREGADDR,
                    list(full_message)
                )

                self.WiRocLogger.debug(f"SendToSRRAdapter::SendData: Sent {len(full_message)} bytes: " + Utils.GetDataInHex(full_message, logging.DEBUG))
            successCB()
            return True
        except Exception as e:
            self.WiRocLogger.error(f"SendData: Exception - {str(e)}")
            failureCB()
            return False
