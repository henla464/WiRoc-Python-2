from __future__ import annotations

from typing import Any
from chipGPIO.hardwareAbstraction import HardwareAbstraction
from settings.settings import SettingsClass
import logging
import subprocess


# Virtual adapter that creates and configures a mesh network if a
# mesh capable
class SendMeshAdapter(object):
    WiRocLogger: logging.Logger = logging.getLogger('WiRoc.Output')
    Instances: list[SendMeshAdapter] = []

    @staticmethod
    def CreateInstances(hardwareAbstraction: HardwareAbstraction) -> bool:
        if HardwareAbstraction.Instance is None:
            HardwareAbstraction.Instance = HardwareAbstraction()
        # because we want to also tear down when we disable mesh, we always create an instance
        if len(SendMeshAdapter.Instances) == 0:
            SendMeshAdapter.Instances.append(SendMeshAdapter('mesh1'))
            return True
        # check if enabled changed => let init/enabledisablesubscription run
        isInitialized = SendMeshAdapter.Instances[0].GetIsInitialized()
        enabled = SettingsClass.GetWifiMeshEnabled()
        allInitializedAsItShould = ((isInitialized and enabled) or (not enabled and not isInitialized))
        if allInitializedAsItShould:
            return False
        return True

    @staticmethod
    def GetTypeName() -> str:
        return "MESH"

    @staticmethod
    def EnableDisableSubscription() -> None:
        return None

    @staticmethod
    def EnableDisableTransforms() -> None:
        return None

    def __init__(self, instanceName):
        self.instanceName: str = instanceName
        self.transforms: dict[str, Any] = {}
        self.isInitialized: bool = False
        self.isDBInitialized: bool = False

        self.wifiMeshEnabled = False
        self.wifiMeshNetworkNameNumber = None
        self.wifiMeshIPNetworkNumber = None
        self.wifiMeshNodeNumber = None
        self.wifiMeshGatewayEnabled = None

    def GetInstanceName(self) -> str:
        return self.instanceName

    @staticmethod
    def GetDeleteAfterSent() -> bool:
        return True

    # when receiving from other WiRoc device, should we wait until the other
    # WiRoc device sent an ack to aviod sending at same time
    @staticmethod
    def GetWaitUntilAckSent() -> bool:
        return False

    def GetIsInitialized(self) -> bool:
        return self.isInitialized

    def ShouldBeInitialized(self) -> bool:
        SendMeshAdapter.WiRocLogger.info(
            f"SendMeshAdapter::ShouldBeInitialized() self.wifiMeshEnabled {self.wifiMeshEnabled}")
        SendMeshAdapter.WiRocLogger.info(
            f"SendMeshAdapter::ShouldBeInitialized() self.wifiMeshNetworkNameNumber {self.wifiMeshNetworkNameNumber}")
        SendMeshAdapter.WiRocLogger.info(
            f"SendMeshAdapter::ShouldBeInitialized() self.wifiMeshGatewayEnabled {self.wifiMeshGatewayEnabled}")
        SendMeshAdapter.WiRocLogger.info(
            f"SendMeshAdapter::ShouldBeInitialized() self.wifiMeshIPNetworkNumber {self.wifiMeshIPNetworkNumber}")
        SendMeshAdapter.WiRocLogger.info(
            f"SendMeshAdapter::ShouldBeInitialized() self.wifiMeshNodeNumber {self.wifiMeshNodeNumber}")
        SendMeshAdapter.WiRocLogger.info(
            f"SendMeshAdapter::ShouldBeInitialized() self.isInitialized {self.isInitialized}")
        if ((SettingsClass.GetWifiMeshEnabled() is True and
             self.wifiMeshEnabled and
             self.isInitialized and
             SettingsClass.GetWifiMeshNetworkNameNumber() == self.wifiMeshNetworkNameNumber and
             SettingsClass.GetWifiMeshGatewayEnabled() == self.wifiMeshGatewayEnabled and
             SettingsClass.GetWifiMeshIPNetworkNumber() == self.wifiMeshIPNetworkNumber and
             SettingsClass.GetWifiMeshNodeNumber() == self.wifiMeshNodeNumber and
             HardwareAbstraction.Instance.DoesInterfaceExist(HardwareAbstraction.Instance.GetMeshInterfaceName()) and
             self.IsMeshPoint(HardwareAbstraction.Instance.GetMeshInterfaceName()))
                or
                (SettingsClass.GetWifiMeshEnabled() is False and
                 self.wifiMeshEnabled is False)):
            return False
        return True

    # has adapter, transforms, subscriptions etc been added to database?
    def GetIsDBInitialized(self) -> bool:
        return self.isDBInitialized

    def SetIsDBInitialized(self, val: bool = True) -> None:
        self.isDBInitialized = val

    def GetTransformNames(self) -> list[str]:
        return []

    def SetTransform(self, transformClass) -> None:
        return None

    def GetTransform(self, transformName: str) -> Any:
        return self.transforms[transformName]

    @staticmethod
    def BringMeshInterfaceUp(mesh_interface: str):
        result = subprocess.run(
            f"ip link set {mesh_interface} up",
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            SendMeshAdapter.WiRocLogger.error(
                f"SendMeshAdapter::BringMeshInterfaceUp() bring {mesh_interface} up failed: {result.stderr}")
            return False
        return True

    def HasExpectedIP(self):
        ipAddresses = HardwareAbstraction.Instance.GetWiRocIPAddresses()
        wifiMeshIPNetworkNumber = SettingsClass.GetWifiMeshIPNetworkNumber()
        startExpectedIPNumber = f"192.168.{wifiMeshIPNetworkNumber}."
        for ipAddr in ipAddresses:
            SendMeshAdapter.WiRocLogger.debug(
                f"SendMeshAdapter::HasExpectedIP() {ipAddr} expected start: {startExpectedIPNumber}")
            if ipAddr.startswith(startExpectedIPNumber):
                return True

        return False

    @staticmethod
    def SetupIPForwarding():
        # Enable IP forwarding
        result = subprocess.run(
            f"sysctl -w net.ipv4.ip_forward=1",
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            SendMeshAdapter.WiRocLogger.error(
                f"SendMeshAdapter::SetupIPForwarding() setup ip forwarding failed: {result.stderr}")
            return False
        return True

    @staticmethod
    def SetupInternetSharing(mesh_interface: str, internet_interface: str):
        """Set up internet sharing via NAT"""
        try:
            if not internet_interface:
                SendMeshAdapter.WiRocLogger.error(
                    "SendMeshAdapter::SetupInternetSharing() No internet interface specified, skipping internet sharing")
                return True

            # Check if internet interface exists
            result = subprocess.run(['ip', 'link', 'show', internet_interface],
                                    capture_output=True, text=True)
            if result.returncode != 0:
                SendMeshAdapter.WiRocLogger.error(
                    f"SendMeshAdapter::SetupInternetSharing() Internet interface {internet_interface} not found")
                return False

            SendMeshAdapter.WiRocLogger.info(
                f"SendMeshAdapter::SetupInternetSharing() Setting up internet sharing from {internet_interface} to {mesh_interface}...")

            # Enable IP forwarding
            SendMeshAdapter.SetupIPForwarding()

            # Configure iptables rules
            # Check if rules already exist
            nat_delete = subprocess.run(['iptables', '-t', 'nat', '-D', 'POSTROUTING',
                                         '-o', internet_interface, '-j', 'MASQUERADE'],
                                        capture_output=True)

            subprocess.run(['iptables', '-t', 'nat', '-A', 'POSTROUTING',
                            '-o', internet_interface, '-j', 'MASQUERADE'], check=True)
            SendMeshAdapter.WiRocLogger.info("SendMeshAdapter::SetupInternetSharing() Added NAT masquerade rule")

            # Forwarding rules
            # Tried to delete specific rules but can't get it to work. So now just deleting the two first
            forward_delete1 = subprocess.run(['iptables', '-D', 'FORWARD', '1'], capture_output=True)
            forward_delete2 = subprocess.run(['iptables', '-D', 'FORWARD', '1'], capture_output=True)

            subprocess.run(
                ['iptables', '-A', 'FORWARD', '-i', mesh_interface, '-o', internet_interface, '-j', 'ACCEPT'],
                check=True)

            subprocess.run(['iptables', '-A', 'FORWARD',
                            '-i', internet_interface, '-o', mesh_interface,
                            '-m', 'state', '--state', 'RELATED,ESTABLISHED', '-j', 'ACCEPT'], check=True)

            # Set this as the root node and announce
            subprocess.run(
                ['iw', 'dev', mesh_interface, 'set', 'mesh_param', 'mesh_hwmp_rootmode', '2'],
                check=True)

            subprocess.run(
                ['iw', 'dev', mesh_interface, 'set', 'mesh_param', 'mesh_gate_announcements', '1'],
                check=True)

            SendMeshAdapter.WiRocLogger.info(
                "SendMeshAdapter::SetupInternetSharing() Internet sharing configured successfully")
            return True

        except subprocess.CalledProcessError as e:
            SendMeshAdapter.WiRocLogger.error(
                f"SendMeshAdapter::SetupInternetSharing() Error setting up internet sharing: {e}")
            return False

    @staticmethod
    def TearDownInternetSharing(mesh_interface: str, internet_interface: str):
        """Tear down internet sharing via NAT"""
        try:
            if not internet_interface:
                SendMeshAdapter.WiRocLogger.info(
                    "SendMeshAdapter::TearDownInternetSharing() No internet interface specified, nothing to tear down")
                return True

            SendMeshAdapter.WiRocLogger.info(
                f"SendMeshAdapter::TearDownInternetSharing() Removing internet sharing from {internet_interface} to {mesh_interface}...")

            # Remove iptables rules in reverse order
            # First, remove FORWARD rules
            try:
                subprocess.run(['iptables', '-D', 'FORWARD',
                                '-i', internet_interface, '-o', mesh_interface,
                                '-m', 'state', '--state', 'RELATED,ESTABLISHED', '-j', 'ACCEPT'],
                               capture_output=True, check=False)
            except Exception as e:
                SendMeshAdapter.WiRocLogger.debug(
                    f"SendMeshAdapter::TearDownInternetSharing() Rule 1 may not exist: {e}")

            try:
                subprocess.run(['iptables', '-D', 'FORWARD',
                                '-i', mesh_interface, '-o', internet_interface, '-j', 'ACCEPT'],
                               capture_output=True, check=False)
            except Exception as e:
                SendMeshAdapter.WiRocLogger.debug(
                    f"SendMeshAdapter::TearDownInternetSharing() Rule 2 may not exist: {e}")

            # Remove NAT masquerade rule
            try:
                subprocess.run(['iptables', '-t', 'nat', '-D', 'POSTROUTING',
                                '-o', internet_interface, '-j', 'MASQUERADE'],
                               capture_output=True, check=False)
            except Exception as e:
                SendMeshAdapter.WiRocLogger.debug(
                    f"SendMeshAdapter::TearDownInternetSharing() NAT rule may not exist: {e}")


            # remove this as the root node
            try:
                subprocess.run(
                    ['iw', 'dev', mesh_interface, 'set', 'mesh_param', 'mesh_hwmp_rootmode', '0'],
                    check=False)
            except Exception as e:
                SendMeshAdapter.WiRocLogger.error(
                    f"SendMeshAdapter::TearDownInternetSharing() mesh_hwmp_rootmode: {e}")

            # stop root announcements
            try:
                subprocess.run(
                    ['iw', 'dev', mesh_interface, 'set', 'mesh_param', 'mesh_gate_announcements', '0'],
                    check=False)
            except Exception as e:
                SendMeshAdapter.WiRocLogger.error(
                    f"SendMeshAdapter::TearDownInternetSharing() mesh_gate_announcements: {e}")

            SendMeshAdapter.WiRocLogger.info(
                "SendMeshAdapter::TearDownInternetSharing() Internet sharing torn down successfully")
            return True

        except Exception as e:
            SendMeshAdapter.WiRocLogger.error(
                f"SendMeshAdapter::TearDownInternetSharing() Error tearing down internet sharing: {e}")
            return False

    @staticmethod
    def IsMeshPoint(mesh_interface: str) -> bool:
        result = subprocess.run(
            f"iw dev {mesh_interface} info",
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            SendMeshAdapter.WiRocLogger.error(
                f"SendMeshAdapter::IsMeshPoint() check if device is set to mesh point: {result.stderr}")
            return False
        if "type mesh point" in result.stdout:
            return True
        return False

    def ChangeDeviceToMeshPoint(self, mesh_interface: str):
        result = subprocess.run(
            f"ip link set {mesh_interface} down",
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            SendMeshAdapter.WiRocLogger.error(
                f"SendMeshAdapter::ChangeDeviceToMeshPoint() taking wifi mesh device down failed: {result.stderr}")
            self.isInitialized = False
            return False

        result = subprocess.run(
            f"iw dev {mesh_interface} set type mesh",
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            SendMeshAdapter.WiRocLogger.error(
                f"SendMeshAdapter::ChangeDeviceToMeshPoint() changing to mesh point failed: {result.stderr}")
            self.isInitialized = False
            return False

        result = subprocess.run(
            f"ip link set {mesh_interface} up",
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            SendMeshAdapter.WiRocLogger.error(
                f"SendMeshAdapter::ChangeDeviceToMeshPoint() taking wifi mesh device up failed: {result.stderr}")
            self.isInitialized = False
            return False

        return True

    @staticmethod
    def JoinMesh(mesh_interface: str, mesh_name: str, frequency: int):
        result = subprocess.run(
            f"iw dev {mesh_interface} mesh join {mesh_name} freq {frequency}",
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            SendMeshAdapter.WiRocLogger.error(
                f"SendMeshAdapter::JoinMesh() join mesh failed: {result.stderr}")
            result = subprocess.run(
                f"iw dev {mesh_interface} mesh leave",
                shell=True,
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode != 0:
                SendMeshAdapter.WiRocLogger.error(
                    f"SendMeshAdapter::JoinMesh() leave mesh failed: {result.stderr}")

            return False
        return True

    @staticmethod
    def AddDNSOnInterface(mesh_interface: str):
        result = subprocess.run(
            f"resolvectl dns {mesh_interface} 1.1.1.1 8.8.8.8",
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            SendMeshAdapter.WiRocLogger.error(
                f"SendMeshAdapter::AddDNSOnInterface() add DNS failed: {result.stderr}")
            return False
        return True

    @staticmethod
    def PowerSaveOff(mesh_interface: str):
        result = subprocess.run(
            f"iw dev {mesh_interface} set power_save off",
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            SendMeshAdapter.WiRocLogger.error(
                f"SendMeshAdapter::JoinMesh() join mesh failed: {result.stderr}")

            return False
        return True

    @staticmethod
    def SetMaxSyncOffset(mesh_interface: str):
        result = subprocess.run(
            f"iw dev {mesh_interface} set mesh_param mesh_sync_offset_max_neighbor 5000",
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            SendMeshAdapter.WiRocLogger.error(
                f"SendMeshAdapter::SetMaxSyncOffset() setting mesh_sync_offset_max_neighbor failed: {result.stderr}")
            return False
        return True

    @staticmethod
    def SetPLinkTimeout(mesh_interface: str):
        result = subprocess.run(
            f"iw dev {mesh_interface} set mesh_param mesh_plink_timeout 60",
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            SendMeshAdapter.WiRocLogger.error(
                f"SendMeshAdapter::SetMaxSyncOffset() setting mesh_plink_timeout failed: {result.stderr}")
            return False
        return True

    @staticmethod
    def ShouldIPAddressBeRemovedAndAdded(mesh_interface: str, new_ip_address: str):
        ipAddresses = HardwareAbstraction.Instance.GetAllIPAddressesOnInterface(mesh_interface)
        if len(ipAddresses) > 1:
            return True
        else:
            if new_ip_address in ipAddresses:
                return False
            else:
                return True

    @staticmethod
    def DeleteDefaultRoute(mesh_interface: str, gateway_ip_address: str) -> None:
        subprocess.run(
            f"ip route del default via {gateway_ip_address} dev {mesh_interface}",
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        # ignore errors from delete

    def Init(self) -> bool:
        if not self.ShouldBeInitialized():
            return True

        theMeshDevice: str = HardwareAbstraction.Instance.GetMeshInterfaceName()
        wifiMeshGatewayIPAddress: str = f"192.168.{SettingsClass.GetWifiMeshIPNetworkNumber()}.1"

        if not SettingsClass.GetWifiMeshEnabled():
            internetInterface = HardwareAbstraction.Instance.GetInternetInterfaceName()
            self.TearDownInternetSharing(HardwareAbstraction.Instance.GetMeshInterfaceName(), internetInterface)
            self.DeleteDefaultRoute(theMeshDevice, wifiMeshGatewayIPAddress)
            self.wifiMeshEnabled = False
            self.isInitialized = True
            return True

        if not HardwareAbstraction.Instance.DoesInterfaceExist(theMeshDevice):
            internetInterface = HardwareAbstraction.Instance.GetInternetInterfaceName()
            self.TearDownInternetSharing(HardwareAbstraction.Instance.GetMeshInterfaceName(), internetInterface)
            self.DeleteDefaultRoute(theMeshDevice, wifiMeshGatewayIPAddress)
            self.wifiMeshEnabled = False
            self.isInitialized = False
            return False

        if not self.IsMeshPoint(theMeshDevice):
            self.ChangeDeviceToMeshPoint(theMeshDevice)

        if self.IsMeshPoint(theMeshDevice):
            SendMeshAdapter.WiRocLogger.info(f"SendMeshAdapter::Init() mesh0 is Mesh Point")
        else:
            SendMeshAdapter.WiRocLogger.error(f"SendMeshAdapter::Init() mesh0 is not a Mesh Point")
            self.isInitialized = False
            return False

        internetInterface = HardwareAbstraction.Instance.GetInternetInterfaceName()
        wifiMeshIPAddress = None
        self.wifiMeshIPNetworkNumber = SettingsClass.GetWifiMeshIPNetworkNumber()
        self.wifiMeshNodeNumber = SettingsClass.GetWifiMeshNodeNumber()
        if SettingsClass.GetWifiMeshGatewayEnabled():
            wifiMeshIPAddress = wifiMeshGatewayIPAddress
        else:
            wifiMeshIPAddress = f"192.168.{self.wifiMeshIPNetworkNumber}.{self.wifiMeshNodeNumber}"

        # Set fixed IP address
        if self.ShouldIPAddressBeRemovedAndAdded(theMeshDevice, wifiMeshIPAddress):
            result = subprocess.run(
                f"ip addr flush dev {theMeshDevice}",
                shell=True,
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode != 0:
                SendMeshAdapter.WiRocLogger.error(
                    f"SendMeshAdapter::Init() flushing mesh IP address failed: {result.stderr}")
                return False

        result = subprocess.run(
            f"ip addr replace {wifiMeshIPAddress}/24 dev {theMeshDevice}",
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            SendMeshAdapter.WiRocLogger.error(
                f"SendMeshAdapter::Init() setting the wifi mesh IP address failed: {result.stderr}")
            self.isInitialized = False
            return False

        if not SettingsClass.GetWifiMeshGatewayEnabled():
            self.DeleteDefaultRoute(theMeshDevice, wifiMeshGatewayIPAddress)

            result = subprocess.run(
                f"ip route add default via {wifiMeshGatewayIPAddress} dev {theMeshDevice}",
                shell=True,
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode != 0:
                SendMeshAdapter.WiRocLogger.error(
                    f"SendMeshAdapter::Init() adding default route failed: {result.stderr}")
                self.isInitialized = False
                return False

            if not self.AddDNSOnInterface(theMeshDevice):
                self.isInitialized = False
                return False

        self.SetMaxSyncOffset(theMeshDevice)
        self.SetPLinkTimeout(theMeshDevice)
        self.PowerSaveOff(theMeshDevice)

        # Join mesh
        self.wifiMeshNetworkNameNumber = SettingsClass.GetWifiMeshNetworkNameNumber()
        wifiMeshSSIDName = f"WiRocMesh{self.wifiMeshNetworkNameNumber}"
        wifiMeshFrequency = SettingsClass.GetWifiMeshFrequency()
        if self.JoinMesh(theMeshDevice, wifiMeshSSIDName, wifiMeshFrequency):
            if SettingsClass.GetWifiMeshGatewayEnabled():
                self.SetupInternetSharing(theMeshDevice, internetInterface)
                self.wifiMeshEnabled = True
                self.wifiMeshGatewayEnabled = True
                self.isInitialized = True
                return True
            else:
                # Enable IP forwarding
                self.SetupIPForwarding()
                self.TearDownInternetSharing(theMeshDevice, internetInterface)
                self.wifiMeshEnabled = True
                self.wifiMeshGatewayEnabled = False
                self.isInitialized = True
                return True
        else:
            self.wifiMeshEnabled = True
            self.wifiMeshGatewayEnabled = False
            self.isInitialized = False
            return False

    def IsReadyToSend(self) -> bool:
        return False

    @staticmethod
    def GetDelayAfterMessageSent() -> float:
        return 0

    def GetRetryDelay(self, tryNo: int) -> float:
        return 1

    # messageData is tuple of bytearray
    def SendData(self, messageData: tuple[bytearray], successCB, failureCB, notSentCB,
                 settingsDictionary: dict[str, Any]) -> bool:
        return False
