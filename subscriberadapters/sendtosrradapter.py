from __future__ import annotations

from chipGPIO.hardwareAbstraction import HardwareAbstraction
from settings.settings import SettingsClass
from datamodel.db_helper import DatabaseHelper
import logging
from smbus2 import SMBus
import time


class SendToSRRAdapter(object):
    WiRocLogger: logging.Logger = logging.getLogger('WiRoc.Output')
    Instances: list[SendToSRRAdapter] = []
    SubscriptionsEnabled: bool = False

    HARDWAREFEATURESENABLEDISABLEREGADDR = 0x06

    PUNCHREGADDR = 0x40

    SEND_MODE_BIT = 0x20

    @staticmethod
    def CreateInstances(hardwareAbstraction: HardwareAbstraction) -> bool:
        if hardwareAbstraction.HasSRR():
            if len(SendToSRRAdapter.Instances) == 0:
                bus = SMBus(0)  # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)
                addr = 0x20

                try:
                    if SettingsClass.GetSRRRedChannelEnabled() or SettingsClass.GetSRRBlueChannelEnabled():
                        # send messages on at least one of the two SRR channels.
                        SendToSRRAdapter.Instances.append(
                            SendToSRRAdapter("sndsrr1", bus, addr, hardwareAbstraction))
                        return True
                    else:
                        return False
                except Exception as err:
                    logging.getLogger('WiRoc.Output').error(
                        "SendToSRRAdapter::CreateInstances() Exception: " + str(err))
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
            enabled = SettingsClass.GetSendToSirapEnabled()
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
        return None

    def __init__(self, instanceName: str, i2cBus: SMBus, i2cAddress: int, hardwareAbstraction: HardwareAbstraction):
        self.instanceName: str = instanceName
        self.transforms: dict[str, any] = {}
        self.isInitialized: bool = False
        self.isDBInitialized: bool = False
        self.i2cBus: SMBus = i2cBus
        self.i2cAddress: int = i2cAddress

    def GetInstanceName(self) -> str:
        return self.instanceName

    @staticmethod
    def GetDeleteAfterSent() -> bool:
        return True

    @staticmethod
    def GetWaitUntilAckSent() -> bool:
        return False

    def GetIsInitialized(self) -> bool:
        return self.isInitialized

    def ShouldBeInitialized(self) -> bool:
        return not self.isInitialized

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

    def GetTransform(self, transformName: str) -> any:
        return self.transforms[transformName]

    def Init(self) -> bool:
        if self.GetIsInitialized():
            return True

        HardwareAbstraction.Instance.DisableSRR()
        time.sleep(0.01)
        HardwareAbstraction.Instance.EnableSRR()
        time.sleep(0.05)

        # Read current hardware features configuration
        current_features = self.i2cBus.read_byte_data(
            self.i2cAddress,
            SendToSRRAdapter.HARDWAREFEATURESENABLEDISABLEREGADDR
        )

        # Check if send mode is already enabled
        original_mode = current_features & SendToSRRAdapter.SEND_MODE_BIT

        # Switch to send mode if not already set
        if not original_mode:
            new_features = current_features | SendToSRRAdapter.SEND_MODE_BIT
            self.i2cBus.write_byte_data(
                self.i2cAddress,
                SendToSRRAdapter.HARDWAREFEATURESENABLEDISABLEREGADDR,
                new_features
            )

        self.isInitialized = True
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
                if len(data) > 30:
                    raise ValueError(f"Data length {len(data)} exceeds maximum allowed (30 bytes)")

                # Prepend message length (including the length byte)
                total_length = len(data) + 1  # +1 for the length byte
                full_message = bytearray([total_length]) + data

                # Write the entire message in one block
                self.i2cBus.write_i2c_block_data(
                    self.i2cAddress,
                    SendToSRRAdapter.PUNCHREGADDR,
                    list(full_message)
                )

                self.WiRocLogger.debug(f"SendData: Sent {len(full_message)} bytes")
            successCB()
            return True
        except Exception as e:
            self.WiRocLogger.error(f"SendData: Exception - {str(e)}")
            failureCB()
            return False
