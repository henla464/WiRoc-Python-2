from __future__ import annotations

import os
import socket
import tempfile
import time
from typing import Any
from chipGPIO.hardwareAbstraction import HardwareAbstraction
from settings.settings import SettingsClass
import logging
import subprocess

import subprocess
import tempfile
import os
import time

# Virtual adapter that creates and configures a mesh network if a
# mesh capable
class SendMeshAdapter(object):
    WiRocLogger: logging.Logger = logging.getLogger('WiRoc.Output')
    Instances: list[SendMeshAdapter] = []

    @staticmethod
    def CreateInstances(hardwareAbstraction: HardwareAbstraction) -> bool:
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

        self.wpaSupplicantConfigurationFilePath = None
        self.wpaSupplicantLogFilePath = None
        self.wpaSupplicantPID = None
        self.wifiMeshEnabled = False
        self.wifiMeshNetworkNameNumber = None
        self.wifiMeshIPNetworkNumber = None
        self.wifiMeshGatewayEnabled = None
        self.theMeshDeviceInterfaceName = None
        self.wifiMeshPassword = None
        self.dnsmasqConfPath = None
        self.dnsmasqPID = None

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

    def HasExpectedIP(self):
        ipAddresses = HardwareAbstraction.Instance.GetWiRocIPAddresses()
        wifiMeshIPNetworkNumber = SettingsClass.GetWifiMeshIPNetworkNumber()
        startExpectedIPNumber = f"192.168.{wifiMeshIPNetworkNumber}."
        for ipAddr in ipAddresses:
            SendMeshAdapter.WiRocLogger.debug(f"SendMeshAdapter::HasExpectedIP() {ipAddr} expected start: {startExpectedIPNumber}")
            if ipAddr.startswith(startExpectedIPNumber):
                return True

        return False

    def ShouldBeInitialized(self) -> bool:
        if ((SettingsClass.GetWifiMeshEnabled() is True and
                self.wifiMeshEnabled is True and
                SettingsClass.GetWifiMeshNetworkNameNumber() == self.wifiMeshNetworkNameNumber and
                SettingsClass.GetWifiMeshGatewayEnabled() == self.wifiMeshGatewayEnabled and
                SettingsClass.GetWifiMeshPassword() == self.wifiMeshPassword and
                self.HasExpectedIP() and
                not self.IsStuckInAvoidJoin(self.theMeshDeviceInterfaceName))
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
    def SendWPACommand(controlPath: str, cmd: str):
        client = None
        try:
            # Generate a unique temp path (file must NOT exist)
            with tempfile.TemporaryDirectory() as tmpdir:
                temp_path = os.path.join(tmpdir, "wpa_ctrl_socket")

                # Create datagram UNIX socket
                client = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
                client.bind(temp_path)  # bind to temporary local socket
                client.connect(controlPath)

                # Send null-terminated command
                client.send(cmd.encode() + b'\0')

                # Receive response
                resp = client.recv(4096)
                return resp.decode().strip()
        finally:
            if client:
                client.close()

    def RestartWPASupplicant(self):
        # sudo systemctl restart wpa_supplicant
        result = subprocess.run(
            f"systemctl restart wpa_supplicant",
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            SendMeshAdapter.WiRocLogger.error(
                f"SendMeshAdapter::RestartWPASupplicant() restarting wpa_supplicant service failed: {result.stderr}")
            self.isInitialized = False
            return False
        return True

    @staticmethod
    def IsStuckInAvoidJoin(interface_name, lookback_seconds=60) -> bool:
        if interface_name is None:
            return False

        try:
            # Calculate timestamp for log filtering
            since_time = time.strftime('%Y-%m-%d %H:%M:%S',
                                       time.localtime(time.time() - lookback_seconds))

            # Get logs for the interface from journalctl
            cmd = [
                'journalctl',
                '-u', 'wpa_supplicant',
                '--since', since_time,
                '-o', 'cat',  # Plain output without metadata
                '-n', '5'  # Last 50 lines
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            if result.returncode != 0:
                SendMeshAdapter.WiRocLogger.error(f"Failed to get logs: {result.stderr}")
                return False

            # Filter logs for this specific interface
            lines = result.stdout.strip().split('\n')
            interface_logs = [line for line in lines if interface_name in line]

            # Check the most recent log line for this interface
            if interface_logs:
                last_line = interface_logs[-1]
                if "Avoiding join because we already joined a mesh group" in last_line:
                    SendMeshAdapter.WiRocLogger.warning(
                        f"Found 'Avoiding join' error for {interface_name}: {last_line}"
                    )
                    return True

            return False

        except subprocess.TimeoutExpired:
            SendMeshAdapter.WiRocLogger.error("Timeout checking logs")
            return False
        except Exception as e:
            SendMeshAdapter.WiRocLogger.error(f"Error checking logs: {e}")
            return False

    def ReconfigureWpa(self, theMeshDeviceInterfaceName, mesh_ssid, password, frequency) -> bool:
        try:
            controlPath = f"/run/wpa_supplicant/{theMeshDeviceInterfaceName}"

            # Example: check status
            response = self.SendWPACommand(controlPath, "STATUS")
            SendMeshAdapter.WiRocLogger.info(f"SendMeshAdapter::ReconfigureWpa() STATUS: {response}")

            # Example: remove all networks (reconfigure)
            result = self.SendWPACommand(controlPath, "REMOVE_NETWORK all")
            if result != "OK":
                SendMeshAdapter.WiRocLogger.error(f"SendMeshAdapter::ReconfigureWpa() Failed to REMOVE_NETWORK all: {result}")
                return False

            # Example: add a mesh network
            network_id = self.SendWPACommand(controlPath, "ADD_NETWORK")

            # Configure mesh network
            result = self.SendWPACommand(controlPath, f"SET_NETWORK {network_id} mode 5")
            if result != "OK":
                SendMeshAdapter.WiRocLogger.error(
                    f"SendMeshAdapter::ReconfigureWpa() Failed to set mode 5: {result}")
                return False
            SendMeshAdapter.WiRocLogger.info(f"SendMeshAdapter::ReconfigureWpa() Set mode 5")
            result = self.SendWPACommand(controlPath, f'SET_NETWORK {network_id} ssid "{mesh_ssid}"')
            if result != "OK":
                SendMeshAdapter.WiRocLogger.error(
                    f"SendMeshAdapter::ReconfigureWpa() Failed to set ssid {mesh_ssid}: {result}")
                return False
            SendMeshAdapter.WiRocLogger.info(f"SendMeshAdapter::ReconfigureWpa() Set ssid {mesh_ssid}")
            result = self.SendWPACommand(controlPath, f"SET_NETWORK {network_id} frequency {frequency}")
            if result != "OK":
                SendMeshAdapter.WiRocLogger.error(
                    f"SendMeshAdapter::ReconfigureWpa() Failed to set frequency {frequency} {result}")
                return False
            SendMeshAdapter.WiRocLogger.info(f"SendMeshAdapter::ReconfigureWpa() set frequency {frequency}")

            result = self.SendWPACommand(controlPath, f"SET_NETWORK {network_id} key_mgmt SAE")
            if result != "OK":
                SendMeshAdapter.WiRocLogger.error(
                    f"SendMeshAdapter::ReconfigureWpa() Failed to set key_mgmt SAE: {result}")
                return False
            SendMeshAdapter.WiRocLogger.info(f"SendMeshAdapter::ReconfigureWpa() Set key_mgmt SAE")
            result = self.SendWPACommand(controlPath, f'SET_NETWORK {network_id} psk "{password}"')
            if result != "OK":
                SendMeshAdapter.WiRocLogger.error(
                    f"SendMeshAdapter::ReconfigureWpa() Failed to set password: {result}")
                return False
            SendMeshAdapter.WiRocLogger.error(f"SendMeshAdapter::ReconfigureWpa() Set password: {password}")
            result = self.SendWPACommand(controlPath, f"ENABLE_NETWORK {network_id}")
            if result != "OK":
                SendMeshAdapter.WiRocLogger.error(
                    f"SendMeshAdapter::ReconfigureWpa() Failed to ENABLE_NETWORK: {result}")
                return False
            SendMeshAdapter.WiRocLogger.error(f"SendMeshAdapter::ReconfigureWpa() Set ENABLE_NETWORK")

            result = self.SendWPACommand(controlPath, f"SET mesh_max_inactivity 300")
            if result != "OK":
                SendMeshAdapter.WiRocLogger.error(
                    f"SendMeshAdapter::ReconfigureWpa() Failed to set mesh_max_Inactivity 300: {result}")
                return False
            SendMeshAdapter.WiRocLogger.error(f"SendMeshAdapter::ReconfigureWpa() set mesh_max_Inactivity 300")

            result = self.SendWPACommand(controlPath, f"SET mesh_fwding 1")
            if result != "OK":
                SendMeshAdapter.WiRocLogger.error(
                    f"SendMeshAdapter::ReconfigureWpa() Failed to set SET mesh_fwding 1: {result}")
                return False
            SendMeshAdapter.WiRocLogger.error(f"SendMeshAdapter::ReconfigureWpa() set SET mesh_fwding 1")

            response = self.SendWPACommand(controlPath, "STATUS")
            SendMeshAdapter.WiRocLogger.info(f"SendMeshAdapter::ReconfigureWpa() STATUS: {response}")

            return True
        except Exception as e:
            SendMeshAdapter.WiRocLogger.error(
                f"SendMeshAdapter::ReconfigureWpa() reconfiguring wpa supplicant: {e}")
            return False

    @staticmethod
    def SetupInternetSharing(mesh_interface: str, internet_interface: str):
        """Set up internet sharing via NAT"""
        try:
            if not internet_interface:
                SendMeshAdapter.WiRocLogger.error("SendMeshAdapter::SetupInternetSharing() No internet interface specified, skipping internet sharing")
                return True

            # Check if internet interface exists
            result = subprocess.run(['ip', 'link', 'show', internet_interface],
                                    capture_output=True, text=True)
            if result.returncode != 0:
                SendMeshAdapter.WiRocLogger.error(f"SendMeshAdapter::SetupInternetSharing() Internet interface {internet_interface} not found")
                return False

            SendMeshAdapter.WiRocLogger.info(f"SendMeshAdapter::SetupInternetSharing() Setting up internet sharing from {internet_interface} to {mesh_interface}...")

            # Enable IP forwarding
            subprocess.run(['sysctl', '-w', 'net.ipv4.ip_forward=1'], check=True)

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
            forward_delete1 = subprocess.run(['iptables', '-D', 'FORWARD','1'],capture_output=True)
            forward_delete2 = subprocess.run(['iptables', '-D', 'FORWARD', '1'], capture_output=True)

            subprocess.run(['iptables', '-A', 'FORWARD', '-i', mesh_interface, '-o', internet_interface, '-j', 'ACCEPT'], check=True)

            subprocess.run(['iptables', '-A', 'FORWARD',
                                '-i', internet_interface, '-o', mesh_interface,
                                '-m', 'state', '--state', 'RELATED,ESTABLISHED', '-j', 'ACCEPT'], check=True)

            SendMeshAdapter.WiRocLogger.info("SendMeshAdapter::SetupInternetSharing() Internet sharing configured successfully")
            return True

        except subprocess.CalledProcessError as e:
            SendMeshAdapter.WiRocLogger.error(f"SendMeshAdapter::SetupInternetSharing() Error setting up internet sharing: {e}")
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

            # Optionally disable IP forwarding (careful with this - might affect other services)
            subprocess.run(['sysctl', '-w', 'net.ipv4.ip_forward=0'], capture_output=True, check=False)

            SendMeshAdapter.WiRocLogger.info(
                "SendMeshAdapter::TearDownInternetSharing() Internet sharing torn down successfully")
            return True

        except Exception as e:
            SendMeshAdapter.WiRocLogger.error(
                f"SendMeshAdapter::TearDownInternetSharing() Error tearing down internet sharing: {e}")
            return False

    def StartMeshDHCPServer(self, mesh_interface: str, gateway_ip: str):
        try:
            conf = f"""
                    interface={mesh_interface}
                    bind-interfaces
                    dhcp-range=192.168.25.50,192.168.25.200,255.255.255.0,24h
                    dhcp-option=3,{gateway_ip}
                    dhcp-option=6,8.8.8.8,1.1.1.1
                    log-dhcp
                    """
            with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
                f.write(conf)
                self.dnsmasqConfPath = f.name

            cmd = [
                'dnsmasq',
                '--conf-file=' + self.dnsmasqConfPath,
                '--no-daemon'
            ]

            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.dnsmasqPID = proc.pid

            SendMeshAdapter.WiRocLogger.info(
                f"SendMeshAdapter::StartMeshDHCPServer() Mesh DHCP server started (PID {self.dnsmasqPID})"
            )
            return True

        except Exception as e:
            SendMeshAdapter.WiRocLogger.error(f"SendMeshAdapter::StartMeshDHCPServer() Failed to start mesh DHCP server: {e}")
            return False

    def StopMeshDHCPServer(self):
        if self.dnsmasqPID:
            subprocess.run(['kill', str(self.dnsmasqPID)], check=False)
            self.dnsmasqPID = None

        if self.dnsmasqConfPath and os.path.exists(self.dnsmasqConfPath):
            os.remove(self.dnsmasqConfPath)

    def StartDHCPClient(self, mesh_interface: str):
        result = subprocess.run(
            f"dhcpcd {mesh_interface}",
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            SendMeshAdapter.WiRocLogger.error(
                f"SendMeshAdapter::StartDHCPClient() starting dhcpcd on interface {mesh_interface} failed: {result.stderr}")
            self.isInitialized = False
            return False
        SendMeshAdapter.WiRocLogger.info(
            f"SendMeshAdapter::StartDHCPClient() started dhcpcd on interface {mesh_interface}")

        return True

    def Init(self) -> bool:
        if not self.ShouldBeInitialized():
            return True

        SendMeshAdapter.WiRocLogger.info(f"SendMeshAdapter::Init() GetWifiMeshEnabled {SettingsClass.GetWifiMeshEnabled()}")
        SendMeshAdapter.WiRocLogger.info(
            f"SendMeshAdapter::Init() GetWifiMeshNetworkNameNumber {SettingsClass.GetWifiMeshNetworkNameNumber()}")
        SendMeshAdapter.WiRocLogger.info(
            f"SendMeshAdapter::Init() GetWifiMeshGatewayEnabled {SettingsClass.GetWifiMeshGatewayEnabled()}")
        SendMeshAdapter.WiRocLogger.info(
            f"SendMeshAdapter::Init() GetWifiMeshPassword {SettingsClass.GetWifiMeshPassword()}")

        theMeshDevice: str = HardwareAbstraction.Instance.GetMeshInterfaceName()
        self.theMeshDeviceInterfaceName = theMeshDevice

        if self.IsStuckInAvoidJoin(theMeshDevice):
            self.RestartWPASupplicant()
            self.wifiMeshEnabled = False
            return False

        wifiMeshGatewayEnabled = SettingsClass.GetWifiMeshGatewayEnabled()
        if not wifiMeshGatewayEnabled and self.wifiMeshEnabled and not self.HasExpectedIP():
            self.StartDHCPClient(theMeshDevice)

        if SettingsClass.GetWifiMeshEnabled() != self.wifiMeshEnabled:
            if SettingsClass.GetWifiMeshEnabled():
                if theMeshDevice is None:
                    SendMeshAdapter.WiRocLogger.error(
                        f"SendMeshAdapter::Init() listing wifi mesh device failed")
                    self.isInitialized = False
                    return False

                # Take the mesh device down to be able to configure it
                result = subprocess.run(
                    f"ip link set {theMeshDevice} down",
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=False
                )
                if result.returncode != 0:
                    SendMeshAdapter.WiRocLogger.error(
                        f"SendMeshAdapter::Init() taking wifi mesh device down failed: {result.stderr}")
                    self.isInitialized = False
                    return False

                wifiMeshPassword = SettingsClass.GetWifiMeshPassword()
                self.wifiMeshPassword = wifiMeshPassword
                wifiMeshNetworkNameNumber = SettingsClass.GetWifiMeshNetworkNameNumber()
                wifiMeshSSIDName = f"WiRocMesh{wifiMeshNetworkNameNumber}"
                wifiMeshFrequency = SettingsClass.GetWifiMeshFrequency()
                if not self.ReconfigureWpa(theMeshDeviceInterfaceName=theMeshDevice, mesh_ssid=wifiMeshSSIDName, password=wifiMeshPassword, frequency=wifiMeshFrequency):
                    SendMeshAdapter.WiRocLogger.error(
                        f"SendMeshAdapter::Init() ReconfigureWpa failed")
                    self.isInitialized = False
                    return False

                # Bring device up
                result = subprocess.run(
                    f"ip link set {theMeshDevice} up",
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=False
                )
                if result.returncode != 0:
                    SendMeshAdapter.WiRocLogger.error(
                        f"SendMeshAdapter::Init() bringing the wifi mesh device up failed: {result.stderr}")

                internetInterface = HardwareAbstraction.Instance.GetInternetInterfaceName()
                if wifiMeshGatewayEnabled:
                    self.wifiMeshIPNetworkNumber = SettingsClass.GetWifiMeshIPNetworkNumber()
                    wifiMeshIPAddress = f"192.168.{self.wifiMeshIPNetworkNumber}.1"

                    # Set fixed IP address for mesh interface on the gateway
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

                    # Configure forwarding to wlan0
                    self.SetupInternetSharing(theMeshDevice, internetInterface)
                    self.StartMeshDHCPServer(theMeshDevice, wifiMeshIPAddress)
                    self.wifiMeshEnabled = True
                    self.isInitialized = True
                else:
                    self.TearDownInternetSharing(theMeshDevice, internetInterface)
                    self.StartDHCPClient(theMeshDevice)
                    self.wifiMeshEnabled = True
                    self.isInitialized = True
            else:
                internetInterface = HardwareAbstraction.Instance.GetInternetInterfaceName()
                self.TearDownInternetSharing(self.theMeshDeviceInterfaceName, internetInterface)
                self.theMeshDeviceInterfaceName = None
                self.wifiMeshEnabled = False
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
                 settingsDictionary: dict[str, Any]) -> bool:
        return False
