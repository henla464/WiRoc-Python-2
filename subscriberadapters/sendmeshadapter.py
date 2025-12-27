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

    def ShouldBeInitialized(self) -> bool:
        if ((SettingsClass.GetWifiMeshEnabled() == True and
                self.wifiMeshEnabled == True and
                SettingsClass.GetWifiMeshNetworkNameNumber() == self.wifiMeshNetworkNameNumber and
                SettingsClass.GetWifiMeshGatewayEnabled() == self.wifiMeshGatewayEnabled and
                SettingsClass.GetWifiMeshPassword() == self.wifiMeshPassword) or
                (SettingsClass.GetWifiMeshEnabled() == False and
                self.wifiMeshEnabled == False)):
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

    #@staticmethod
    #def GetWPASupplicantConfigurationContent(mesh_ssid, password, frequency) -> str:
    #    conf = f"""ctrl_interface=/var/run/wpa_supplicant
    #            ctrl_interface_group=0
    #            update_config=1
    #            pmf=1
    #            # Fast Transition (optional)
    #            ft_over_ds=1
    #            ft_psk_generate_local=1
    #
    #            network={{
    #                mode=5
    #                ssid="{mesh_ssid}"
    #                key_mgmt=SAE
    #                psk="{password}"
    #                pairwise=CCMP
    #                group=CCMP
    #                beacon_int=100
    #                dtim_period=2
    #                mesh_rssi_threshold=-80
    #                mesh_basic_rates=60 120 240
    #                freq_list={frequency}
    #                mesh_fwding=1
    #                # Enable intra-PAN communication
    #                no_auto_peer=0
    #            }}"""
    #    return conf

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

    def ReconfigureWpa(self, theMeshDeviceInterfaceName, mesh_ssid, password, frequency) -> bool:
        controlPath = f"/run/wpa_supplicant/{theMeshDeviceInterfaceName}"
        # Example: check status
        response = self.SendWPACommand(controlPath, "STATUS")
        SendMeshAdapter.WiRocLogger.info(f"SendMeshAdapter::ReconfigureWpa() {response}")

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
        result = self.SendWPACommand(controlPath, f'SET_NETWORK {network_id} ssid "{mesh_ssid}"')
        if result != "OK":
            SendMeshAdapter.WiRocLogger.error(
                f"SendMeshAdapter::ReconfigureWpa() Failed to set ssid {mesh_ssid}: {result}")
            return False
        result = self.SendWPACommand(controlPath, f"SET_NETWORK {network_id} frequency {frequency}")
        if result != "OK":
            SendMeshAdapter.WiRocLogger.error(
                f"SendMeshAdapter::ReconfigureWpa() Failed to set frequency {frequency} {result}")
            return False
        result = self.SendWPACommand(controlPath, f"SET_NETWORK {network_id} key_mgmt SAE")
        if result != "OK":
            SendMeshAdapter.WiRocLogger.error(
                f"SendMeshAdapter::ReconfigureWpa() Failed to set key_mgmt SAE: {result}")
            return False
        result = self.SendWPACommand(controlPath, f'SET_NETWORK {network_id} psk "{password}"')
        if result != "OK":
            SendMeshAdapter.WiRocLogger.error(
                f"SendMeshAdapter::ReconfigureWpa() Failed to set password: {result}")
            return False
        result = self.SendWPACommand(controlPath, f"ENABLE_NETWORK {network_id}")
        if result != "OK":
            SendMeshAdapter.WiRocLogger.error(
                f"SendMeshAdapter::ReconfigureWpa() Failed to ENABLE_NETWORK: {result}")
            return False

        return True

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

        if SettingsClass.GetWifiMeshEnabled() != self.wifiMeshEnabled:
            if SettingsClass.GetWifiMeshEnabled():
                theMeshDevice: str = HardwareAbstraction.Instance.GetMeshInterfaceName()
                if theMeshDevice is None:
                    SendMeshAdapter.WiRocLogger.error(
                        f"SendMeshAdapter::Init() listing wifi mesh device failed")
                    self.isInitialized = False
                    return False

                self.theMeshDeviceInterfaceName = theMeshDevice
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

                # iw dev $MESH_DEVICE mesh join $MESH_NETWORK freq $WifiMeshFrequency
                # Join the mesh network
                #result = subprocess.run(
                #    f"iw dev $MESH_DEVICE mesh join {wifiMeshSSIDName} freq {WifiMeshFrequency}",
                #    shell=True,
                #    capture_output=True,
                #    text=True,
                #    check=False
                #)
                #if result.returncode != 0:
                #    SendMeshAdapter.WiRocLogger.error(
                #        f"SendMeshAdapter::Init() joining mesh network failed: {result.stderr}")

                wifiMeshGatewayEnabled = SettingsClass.GetWifiMeshGatewayEnabled()
                internetInterface = HardwareAbstraction.Instance.GetInternetInterfaceName()
                if wifiMeshGatewayEnabled:
                    wifiMeshIPNetworkNumber = SettingsClass.GetWifiMeshIPNetworkNumber()
                    self.wifiMeshGatewayEnabled = wifiMeshIPNetworkNumber
                    wifiMeshIPAddress = f"192.168.{wifiMeshIPNetworkNumber}.1"

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
                    self.wifiMeshEnabled = True
                    self.isInitialized = True
            else:
                self.StopWpaSupplicant()
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
