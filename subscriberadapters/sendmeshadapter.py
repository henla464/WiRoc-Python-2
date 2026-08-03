from __future__ import annotations

from typing import Any
from chipGPIO.hardwareAbstraction import HardwareAbstraction
from settings.settings import SettingsClass
import logging
import subprocess
import re


# Virtual adapter that creates and configures a mesh network if a
# mesh capable
class SendMeshAdapter(object):
    WiRocLogger: logging.Logger = logging.getLogger('WiRoc.Output')
    Instances: list[SendMeshAdapter] = []
    _meshSecurityLocalSubnet: str | None = None
    _meshSecurityAllowedIPs: list | None = None

    @staticmethod
    def CreateInstances(hardwareAbstraction: HardwareAbstraction) -> bool:
        if HardwareAbstraction.Instance is None:
            HardwareAbstraction.Instance = HardwareAbstraction()
        # because we want to also tear down when we disable mesh, we always create an instance
        enabled = SettingsClass.GetWifiMeshEnabled()
        if len(SendMeshAdapter.Instances) == 0 and enabled:
            SendMeshAdapter.Instances.append(SendMeshAdapter('mesh1'))
            return True

        if len(SendMeshAdapter.Instances) > 0 and not enabled:
            # Teardown
            SendMeshAdapter.Instances[0].Init()
            SendMeshAdapter.Instances = []
            return True
        # check if enabled changed => let init/enabledisablesubscription run
        isInitialized = SendMeshAdapter.Instances[0].GetIsInitialized() if len(SendMeshAdapter.Instances) > 0 else False
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
        self.wifiMeshRouteToInterface = None
        self.wifiMeshRestrictEnabled = None
        self.wifiMeshAllowedIPs = None

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
        SendMeshAdapter.WiRocLogger.verbose(
            f"SendMeshAdapter::ShouldBeInitialized() self.wifiMeshEnabled {self.wifiMeshEnabled}")
        SendMeshAdapter.WiRocLogger.verbose(
            f"SendMeshAdapter::ShouldBeInitialized() self.wifiMeshNetworkNameNumber {self.wifiMeshNetworkNameNumber}")
        SendMeshAdapter.WiRocLogger.verbose(
            f"SendMeshAdapter::ShouldBeInitialized() self.wifiMeshGatewayEnabled {self.wifiMeshGatewayEnabled}")
        SendMeshAdapter.WiRocLogger.verbose(
            f"SendMeshAdapter::ShouldBeInitialized() self.wifiMeshIPNetworkNumber {self.wifiMeshIPNetworkNumber}")
        SendMeshAdapter.WiRocLogger.verbose(
            f"SendMeshAdapter::ShouldBeInitialized() self.wifiMeshNodeNumber {self.wifiMeshNodeNumber}")
        SendMeshAdapter.WiRocLogger.verbose(
            f"SendMeshAdapter::ShouldBeInitialized() self.isInitialized {self.isInitialized}")
        SendMeshAdapter.WiRocLogger.verbose(
            f"SendMeshAdapter::ShouldBeInitialized() self.wifiMeshRouteToInterface {self.wifiMeshRouteToInterface}")
        if ((SettingsClass.GetWifiMeshEnabled() is True and
             self.wifiMeshEnabled and
             self.isInitialized and
             SettingsClass.GetWifiMeshNetworkNameNumber() == self.wifiMeshNetworkNameNumber and
             SettingsClass.GetWifiMeshGatewayEnabled() == self.wifiMeshGatewayEnabled and
             SettingsClass.GetWifiMeshIPNetworkNumber() == self.wifiMeshIPNetworkNumber and
             SettingsClass.GetWifiMeshNodeNumber() == self.wifiMeshNodeNumber and
             SettingsClass.GetWifiMeshRouteToInterface() == self.wifiMeshRouteToInterface and
             SettingsClass.GetWifiMeshRestrictEnabled() == self.wifiMeshRestrictEnabled and
             SettingsClass.GetWifiMeshAllowedIPs() == self.wifiMeshAllowedIPs and
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
        # IP forwarding is enabled permanently via /etc/sysctl.d/99-wiroc-ipforward.conf (set by install.sh)
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
            # forward_delete1 = subprocess.run(['iptables', '-D', 'FORWARD', '1'], capture_output=True)
            # forward_delete2 = subprocess.run(['iptables', '-D', 'FORWARD', '1'], capture_output=True)

            # Mesh security: optionally restrict mesh access to local network
            restrictEnabled = SettingsClass.GetWifiMeshRestrictEnabled()
            if restrictEnabled:
                # Get local subnet from internet interface
                result = subprocess.run(['ip', '-4', '-o', 'addr', 'show', internet_interface],
                                       capture_output=True, text=True)
                match = re.search(r'inet (\d+\.\d+\.\d+\.\d+/\d+)', result.stdout)
                if match:
                    localSubnet = match.group(1)
                    SendMeshAdapter._meshSecurityLocalSubnet = localSubnet

                    # Get allowed IPs
                    allowedIPs = SettingsClass.GetWifiMeshAllowedIPs()
                    SendMeshAdapter._meshSecurityAllowedIPs = allowedIPs

                    # Insert DROP first at position 1 (blocks everything to local subnet)
                    subprocess.run(['iptables', '-I', 'FORWARD', '1',
                                   '-i', mesh_interface, '-o', internet_interface,
                                   '-d', localSubnet, '-j', 'DROP'], check=True)
                    SendMeshAdapter.WiRocLogger.info(
                        f"SendMeshAdapter::SetupInternetSharing() Added mesh DROP rule for subnet: {localSubnet}")

                    # Insert ACCEPT rules at position 1 (before DROP), so allowed IPs go through
                    for entry in allowedIPs:
                        cmd = ['iptables', '-I', 'FORWARD', '1', '-i', mesh_interface,
                               '-o', internet_interface, '-d', entry.get('ip', '')]
                        protocol = entry.get('protocol', '*')
                        if protocol != '*':
                            cmd.extend(['-p', protocol])
                        port = entry.get('port', '*')
                        if port != '*':
                            cmd.extend(['--dport', str(port)])
                        cmd.extend(['-j', 'ACCEPT'])
                        subprocess.run(cmd, check=True)
                        SendMeshAdapter.WiRocLogger.info(
                            f"SendMeshAdapter::SetupInternetSharing() Added mesh ACCEPT rule for {entry}")
                else:
                    SendMeshAdapter.WiRocLogger.warning(
                        "SendMeshAdapter::SetupInternetSharing() Could not determine local subnet, skipping mesh restriction")
                    SendMeshAdapter._meshSecurityLocalSubnet = None
                    SendMeshAdapter._meshSecurityAllowedIPs = []
            else:
                SendMeshAdapter._meshSecurityLocalSubnet = None
                SendMeshAdapter._meshSecurityAllowedIPs = []

            # Generic mesh -> internet ACCEPT (everything not matched by security rules above)
            subprocess.run(
                ['iptables', '-A', 'FORWARD', '-i', mesh_interface, '-o', internet_interface, '-j', 'ACCEPT'],
                check=True)

            # Reply traffic: internet -> mesh
            subprocess.run(['iptables', '-A', 'FORWARD',
                            '-i', internet_interface, '-o', mesh_interface,
                            '-m', 'state', '--state', 'RELATED,ESTABLISHED', '-j', 'ACCEPT'], check=True)

            # Normal network can initiate connections to mesh devices
            subprocess.run(['iptables', '-A', 'FORWARD',
                            '-i', internet_interface, '-o', mesh_interface, '-j', 'ACCEPT'], check=True)
            SendMeshAdapter.WiRocLogger.info(
                "SendMeshAdapter::SetupInternetSharing() Added normal->mesh ACCEPT rule")

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
            # First, remove normal->mesh ACCEPT rule (added last in Setup)
            try:
                subprocess.run(['iptables', '-D', 'FORWARD',
                                '-i', internet_interface, '-o', mesh_interface, '-j', 'ACCEPT'],
                               capture_output=True, check=False)
            except Exception as e:
                SendMeshAdapter.WiRocLogger.debug(
                    f"SendMeshAdapter::TearDownInternetSharing() normal->mesh ACCEPT rule may not exist: {e}")

            # Remove RELATED,ESTABLISHED rule
            try:
                subprocess.run(['iptables', '-D', 'FORWARD',
                                '-i', internet_interface, '-o', mesh_interface,
                                '-m', 'state', '--state', 'RELATED,ESTABLISHED', '-j', 'ACCEPT'],
                               capture_output=True, check=False)
            except Exception as e:
                SendMeshAdapter.WiRocLogger.debug(
                    f"SendMeshAdapter::TearDownInternetSharing() REL,EST rule may not exist: {e}")

            # Remove generic mesh->internet ACCEPT rule
            try:
                subprocess.run(['iptables', '-D', 'FORWARD',
                                '-i', mesh_interface, '-o', internet_interface, '-j', 'ACCEPT'],
                               capture_output=True, check=False)
            except Exception as e:
                SendMeshAdapter.WiRocLogger.debug(
                    f"SendMeshAdapter::TearDownInternetSharing() mesh->internet ACCEPT rule may not exist: {e}")

            # Remove mesh security rules (if any were added)
            localSubnet = SendMeshAdapter._meshSecurityLocalSubnet
            allowedIPs = SendMeshAdapter._meshSecurityAllowedIPs
            if localSubnet and allowedIPs is not None:
                # Remove DROP rule for mesh->local subnet
                try:
                    subprocess.run(['iptables', '-D', 'FORWARD',
                                    '-i', mesh_interface, '-o', internet_interface,
                                    '-d', localSubnet, '-j', 'DROP'],
                                   capture_output=True, check=False)
                except Exception as e:
                    SendMeshAdapter.WiRocLogger.debug(
                        f"SendMeshAdapter::TearDownInternetSharing() mesh DROP rule may not exist: {e}")

                # Remove ACCEPT rules for each allowed IP (reverse order)
                for entry in reversed(allowedIPs):
                    try:
                        cmd = ['iptables', '-D', 'FORWARD', '-i', mesh_interface,
                               '-o', internet_interface, '-d', entry.get('ip', '')]
                        protocol = entry.get('protocol', '*')
                        if protocol != '*':
                            cmd.extend(['-p', protocol])
                        port = entry.get('port', '*')
                        if port != '*':
                            cmd.extend(['--dport', str(port)])
                        cmd.extend(['-j', 'ACCEPT'])
                        subprocess.run(cmd, capture_output=True, check=False)
                    except Exception as e:
                        SendMeshAdapter.WiRocLogger.debug(
                            f"SendMeshAdapter::TearDownInternetSharing() allowed IP rule may not exist: {e}")

            # Clear security rules state
            SendMeshAdapter._meshSecurityLocalSubnet = None
            SendMeshAdapter._meshSecurityAllowedIPs = None

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
                f"SendMeshAdapter::PowerSaveOff() set power_save off failed: {result.stderr}")

            return False
        return True

    @staticmethod
    def SetMaxSyncOffset(mesh_interface: str):
        result = subprocess.run(
            f"iw dev {mesh_interface} set mesh_param mesh_sync_offset_max_neighor 90",
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            SendMeshAdapter.WiRocLogger.error(
                f"SendMeshAdapter::SetMaxSyncOffset() setting mesh_sync_offset_max_neighor failed: {result.stderr}")
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
                f"SendMeshAdapter::SetPLinkTimeout() setting mesh_plink_timeout failed: {result.stderr}")
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
    def FlushIPAddress(mesh_interface: str):
        result = subprocess.run(
            f"ip addr flush dev {mesh_interface}",
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            SendMeshAdapter.WiRocLogger.error(
                f"SendMeshAdapter::FlushIPAddress() flushing mesh IP address failed: {result.stderr}")
            return False
        return True

    @staticmethod
    def AddDefaultRoute(mesh_interface:str, gateway_ip_address: str):
        result = subprocess.run(
            f"ip route add default via {gateway_ip_address} dev {mesh_interface}",
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            SendMeshAdapter.WiRocLogger.error(
                f"SendMeshAdapter::Init() adding default route failed: {result.stderr}")
            return False
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
            SendMeshAdapter.WiRocLogger.info(f"SendMeshAdapter::Init() Wifi mesh should not be enabled")
            internetInterface = SettingsClass.GetWifiMeshRouteToInterface()
            self.TearDownInternetSharing(HardwareAbstraction.Instance.GetMeshInterfaceName(), internetInterface)
            self.DeleteDefaultRoute(theMeshDevice, wifiMeshGatewayIPAddress)
            self.FlushIPAddress(theMeshDevice)
            self.wifiMeshEnabled = False
            self.isInitialized = True
            return True

        if not HardwareAbstraction.Instance.DoesInterfaceExist(theMeshDevice):
            SendMeshAdapter.WiRocLogger.info(f"SendMeshAdapter::Init() mesh interface doesnt exist")
            internetInterface = SettingsClass.GetWifiMeshRouteToInterface()
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

        internetInterface = SettingsClass.GetWifiMeshRouteToInterface()
        wifiMeshIPAddress = None
        self.wifiMeshIPNetworkNumber = SettingsClass.GetWifiMeshIPNetworkNumber()
        self.wifiMeshNodeNumber = SettingsClass.GetWifiMeshNodeNumber()
        if SettingsClass.GetWifiMeshGatewayEnabled():
            wifiMeshIPAddress = wifiMeshGatewayIPAddress
        else:
            wifiMeshIPAddress = f"192.168.{self.wifiMeshIPNetworkNumber}.{self.wifiMeshNodeNumber}"

        # Set fixed IP address
        if self.ShouldIPAddressBeRemovedAndAdded(theMeshDevice, wifiMeshIPAddress):
            self.FlushIPAddress(theMeshDevice)

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
            SendMeshAdapter.WiRocLogger.info(f"SendMeshAdapter::Init() should not be gateway")
            self.DeleteDefaultRoute(theMeshDevice, wifiMeshGatewayIPAddress)
            if not self.AddDefaultRoute(theMeshDevice, wifiMeshGatewayIPAddress):
                self.isInitialized = False
                return False

            if not self.AddDNSOnInterface(theMeshDevice):
                self.isInitialized = False
                return False
        else:
            SendMeshAdapter.WiRocLogger.info(f"SendMeshAdapter::Init() should be gateway")
            self.DeleteDefaultRoute(theMeshDevice, wifiMeshGatewayIPAddress)

        self.PowerSaveOff(theMeshDevice)

        # Join mesh
        SendMeshAdapter.WiRocLogger.info(f"SendMeshAdapter::Init() before join mesh")
        self.wifiMeshNetworkNameNumber = SettingsClass.GetWifiMeshNetworkNameNumber()
        wifiMeshSSIDName = f"WiRocMesh{self.wifiMeshNetworkNameNumber}"
        wifiMeshFrequency = SettingsClass.GetWifiMeshFrequency()
        if self.JoinMesh(theMeshDevice, wifiMeshSSIDName, wifiMeshFrequency):
            self.SetMaxSyncOffset(theMeshDevice)
            self.SetPLinkTimeout(theMeshDevice)
            if SettingsClass.GetWifiMeshGatewayEnabled():
                # Tear down old rules first in case settings changed
                self.TearDownInternetSharing(theMeshDevice, internetInterface)
                self.SetupInternetSharing(theMeshDevice, internetInterface)
                self.wifiMeshRouteToInterface = internetInterface
                self.wifiMeshEnabled = True
                self.wifiMeshGatewayEnabled = True
                self.wifiMeshRestrictEnabled = SettingsClass.GetWifiMeshRestrictEnabled()
                self.wifiMeshAllowedIPs = SettingsClass.GetWifiMeshAllowedIPs()
                self.isInitialized = True
                return True
            else:
                # Enable IP forwarding
                self.SetupIPForwarding()
                self.TearDownInternetSharing(theMeshDevice, internetInterface)
                self.wifiMeshRouteToInterface = internetInterface
                self.wifiMeshEnabled = True
                self.wifiMeshGatewayEnabled = False
                self.wifiMeshRestrictEnabled = False
                self.wifiMeshAllowedIPs = []
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
        return 1000000  # 1 second in microseconds

    # messageData is tuple of bytearray
    def SendData(self, messageData: tuple[bytearray], successCB, failureCB, notSentCB,
                 settingsDictionary: dict[str, Any]) -> bool:
        return False
