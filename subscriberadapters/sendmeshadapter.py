from __future__ import annotations

import tempfile

from chipGPIO.hardwareAbstraction import HardwareAbstraction
from settings.settings import SettingsClass
from datamodel.db_helper import DatabaseHelper
import socket
import logging
import subprocess

from utils.utils import Utils


class SendToSirapAdapter(object):
    WiRocLogger: logging.Logger = logging.getLogger('WiRoc.Output')
    Instances: list[SendToSirapAdapter] = []
    SubscriptionsEnabled: bool = False

    @staticmethod
    def CreateInstances(hardwareAbstraction: HardwareAbstraction) -> bool:
        if len(SendToSirapAdapter.Instances) == 0:
            SendToSirapAdapter.Instances.append(SendToSirapAdapter('sirap1'))
            return True
        # check if enabled changed => let init/enabledisablesubscription run
        isInitialized = SendToSirapAdapter.Instances[0].GetIsInitialized()
        enabled = SettingsClass.GetSendToSirapEnabled()
        subscriptionShouldBeEnabled = (isInitialized and enabled)
        if SendToSirapAdapter.SubscriptionsEnabled != subscriptionShouldBeEnabled:
            return True
        return False

    @staticmethod
    def GetTypeName() -> str:
        return "SIRAP"

    @staticmethod
    def EnableDisableSubscription():
        if len(SendToSirapAdapter.Instances) > 0:
            isInitialized = SendToSirapAdapter.Instances[0].GetIsInitialized()
            enabled = SettingsClass.GetSendToSirapEnabled()
            subscriptionShouldBeEnabled = (isInitialized and enabled)
            if SendToSirapAdapter.SubscriptionsEnabled != subscriptionShouldBeEnabled:
                SendToSirapAdapter.WiRocLogger.info(
                    "SendToSirapAdapter::EnableDisableSubscription() subscription set enabled: " + str(
                        subscriptionShouldBeEnabled))
                SendToSirapAdapter.SubscriptionsEnabled = subscriptionShouldBeEnabled
                DatabaseHelper.update_subscriptions(subscriptionShouldBeEnabled,
                                                    SendToSirapAdapter.GetDeleteAfterSent(),
                                                    SendToSirapAdapter.GetTypeName())

    @staticmethod
    def EnableDisableTransforms() -> None:
        return None

    def __init__(self, instanceName):
        self.instanceName: str = instanceName
        self.transforms: dict[str, any] = {}
        self.sock: socket.socket | None = None
        self.isInitialized: bool = False
        self.isDBInitialized: bool = False

        self.wpaSupplicantConfigurationFilePath = None
        self.wpaSupplicantLogFilePath = None

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
        if SettingsClass.wifiMeshEnabled != self.wifiMeshEnabled:
            return True
        return not self.isInitialized

    # has adapter, transforms, subscriptions etc been added to database?
    def GetIsDBInitialized(self) -> bool:
        return self.isDBInitialized

    def SetIsDBInitialized(self, val: bool = True) -> None:
        self.isDBInitialized = val

    def GetTransformNames(self) -> list[str]:
        return ["LoraSIMessageToSirapTransform", "SISIMessageToSirapTransform",
                "SITestTestToSirapTransform", "LoraSIMessageDoubleToSirapTransform",
                "SRRSRRMessageToSirapTransform"]

    def SetTransform(self, transformClass):
        self.transforms[transformClass.GetName()] = transformClass

    def GetTransform(self, transformName: str) -> any:
        return self.transforms[transformName]

    @staticmethod
    def GetWPASupplicantConfigurationContent(self, mesh_ssid, password, frequency) -> str:
        conf = f"""ctrl_interface=/var/run/wpa_supplicant
                ctrl_interface_group=0
                update_config=1
                pmf=1
                # Fast Transition (optional)
                ft_over_ds=1
                ft_psk_generate_local=1
            
                network={{
                    mode=5
                    ssid="{mesh_ssid}"
                    key_mgmt=SAE
                    psk="{password}"
                    pairwise=CCMP
                    group=CCMP
                    beacon_int=100
                    dtim_period=2
                    mesh_rssi_threshold=-80
                    mesh_basic_rates=60 120 240
                    # Optional: specify frequency
                    # freq_list={frequency}
                    mesh_fwding=1
                    # Enable intra-PAN communication
                    no_auto_peer=0
                }}"""
        return conf

    def StartWpaSupplicant(self, interface, mesh_ssid, password, frequency):
        """Start wpa_supplicant for mesh network"""
        try:
            # Generate configuration
            conf_content = self.GetWPASupplicantConfigurationContent(mesh_ssid, password, frequency)

            # Create temporary configuration file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
                f.write(conf_content)
                self.wpaSupplicantConfigurationFilePath = f.name

            # Create log file
            log_file = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
            log_file.close()
            self.wpaSupplicantLogFilePath = log_file.name

            print(f"Starting wpa_supplicant on {interface}...")
            print(f"Configuration file: {self.wpa_supplicant_conf}")
            print(f"Log file: {self.wpa_supplicant_log}")

            # Start wpa_supplicant in background
            cmd = [
                'wpa_supplicant',
                '-i', interface,
                '-c', self.wpa_supplicant_conf,
                '-d',  # Debug info
                '-f', self.wpa_supplicant_log,
                '-B'  # Run in background
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                print(f"Failed to start wpa_supplicant: {result.stderr}")
                return False

            # Try to get PID
            time.sleep(2)  # Give it time to start
            pid_result = subprocess.run(['pgrep', '-f', f'wpa_supplicant.*{interface}'],
                                        capture_output=True, text=True)

            if pid_result.stdout.strip():
                self.wpa_supplicant_pid = int(pid_result.stdout.strip().split('\n')[0])
                print(f"wpa_supplicant started with PID: {self.wpa_supplicant_pid}")
                return True
            else:
                print("Could not find wpa_supplicant PID")
                # Check log file for errors
                if os.path.exists(self.wpa_supplicant_log):
                    with open(self.wpa_supplicant_log, 'r') as f:
                        log_content = f.read()
                        if log_content:
                            print("wpa_supplicant log:")
                            print(log_content[-1000:])  # Last 1000 chars
                return False

        except Exception as e:
            print(f"Error starting wpa_supplicant: {e}")
            return False

    def stop_wpa_supplicant(self):
            """Stop wpa_supplicant if running"""
            if self.wpa_supplicant_pid:
                try:
                    print(f"Stopping wpa_supplicant (PID: {self.wpa_supplicant_pid})...")
                    subprocess.run(['kill', str(self.wpa_supplicant_pid)], check=False)
                    time.sleep(1)
                    self.wpa_supplicant_pid = None
                except Exception as e:
                    print(f"Error stopping wpa_supplicant: {e}")

            # Clean up temporary files
            if self.wpa_supplicant_conf and os.path.exists(self.wpa_supplicant_conf):
                os.unlink(self.wpa_supplicant_conf)
            if self.wpa_supplicant_log and os.path.exists(self.wpa_supplicant_log):
                os.unlink(self.wpa_supplicant_log)

    def SetupInternetSharing(self, mesh_interface, internet_interface):
        """Set up internet sharing via NAT"""
        try:
            if not internet_interface:
                print("No internet interface specified, skipping internet sharing")
                return True

            # Check if internet interface exists
            result = subprocess.run(['ip', 'link', 'show', internet_interface],
                                    capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Internet interface {internet_interface} not found")
                return False

            print(f"Setting up internet sharing from {internet_interface} to {mesh_interface}...")

            # Enable IP forwarding
            subprocess.run(['sysctl', '-w', 'net.ipv4.ip_forward=1'], check=True)

            # Configure iptables rules
            # Check if rules already exist
            nat_check = subprocess.run(['iptables', '-t', 'nat', '-C', 'POSTROUTING',
                                        '-o', internet_interface, '-j', 'MASQUERADE'],
                                       capture_output=True)

            if nat_check.returncode != 0:
                subprocess.run(['iptables', '-t', 'nat', '-A', 'POSTROUTING',
                                '-o', internet_interface, '-j', 'MASQUERADE'], check=True)
                print("Added NAT masquerade rule")

            # Forwarding rules
            forward_check1 = subprocess.run(['iptables', '-C', 'FORWARD',
                                             '-i', mesh_interface, '-o', internet_interface, '-j', 'ACCEPT'],
                                            capture_output=True)
            if forward_check1.returncode != 0:
                subprocess.run(['iptables', '-A', 'FORWARD',
                                '-i', mesh_interface, '-o', internet_interface, '-j', 'ACCEPT'], check=True)

            forward_check2 = subprocess.run(['iptables', '-C', 'FORWARD',
                                             '-i', internet_interface, '-o', mesh_interface,
                                             '-m', 'state', '--state', 'RELATED,ESTABLISHED', '-j', 'ACCEPT'],
                                            capture_output=True)
            if forward_check2.returncode != 0:
                subprocess.run(['iptables', '-A', 'FORWARD',
                                '-i', internet_interface, '-o', mesh_interface,
                                '-m', 'state', '--state', 'RELATED,ESTABLISHED', '-j', 'ACCEPT'], check=True)

            print("Internet sharing configured successfully")
            return True

        except subprocess.CalledProcessError as e:
            print(f"Error setting up internet sharing: {e}")
            return False

    def Init(self) -> bool:
        if SettingsClass.GetWifiMeshEnabled() != self.wifiMeshEnabled:
            if SettingsClass.GetWifiMeshEnabled():
                WifiMeshFrequency = SettingsClass.GetWifiMeshFrequency()
                wifiMeshNetworkNumber = SettingsClass.GetWifiMeshNetworkNumber()
                wifiMeshSSIDName = f"WiRocMesh{wifiMeshNetworkNumber}"
                wifiMeshPassword = SettingsClass.GetWifiMeshPassword()
                wifiMeshIPAddress = "192.168.25.1"
                internetInterface = "wlan0"
        #       self.wifiMeshEnabled = True

                result = subprocess.run(
                    "iw dev | grep -E 'Interface|type mesh' -A1 | grep Interface | awk '{print $2}' | sort",
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=False  # Set to True if you want to raise an error on failure
                )

                # Get the list of devices
                devices = result.stdout.strip().split('\n') if result.stdout else []
                if len(devices) > 0:
                    print(f"Devices: {devices}")
                    theMeshDevice: str = devices[0]

                    # Take the mesh device down to be able to configure it
                    result = subprocess.run(
                        f"ip link set {theMeshDevice} down",
                        shell=True,
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    if result.returncode != 0:
                        SendToSirapAdapter.WiRocLogger.error(f"SendToSirapAdapter::Init() taking wifi mesh device down failed: {result.stderr}")

                    # Set the channel / frequency to use
                    #result = subprocess.run(
                    #    f"iw dev {theMeshDevice} set freq {WifiMeshFrequency} HT20",
                    #    shell=True,
                    #    capture_output=True,
                    #    text=True,
                    #    check=False
                    #)
                    #if result.returncode != 0:
                    #    SendToSirapAdapter.WiRocLogger.error(f"SendToSirapAdapter::Init() setting wifi mesh frequency failed: {result.stderr}")

                    # Bring device up
                    result = subprocess.run(
                        f"ip link set {theMeshDevice} up",
                        shell=True,
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    if result.returncode != 0:
                        SendToSirapAdapter.WiRocLogger.error(
                            f"SendToSirapAdapter::Init() bringing the wifi mesh device up failed: {result.stderr}")

                    # iw dev $MESH_DEVICE mesh join $MESH_NETWORK freq $WifiMeshFrequency
                    # Join the mesh network
                    result = subprocess.run(
                        f"iw dev $MESH_DEVICE mesh join {wifiMeshSSIDName} freq {WifiMeshFrequency}",
                        shell=True,
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    if result.returncode != 0:
                        SendToSirapAdapter.WiRocLogger.error(
                            f"SendToSirapAdapter::Init() joining mesh network failed: {result.stderr}")

                    # set password: iw dev $MESH_DEVICE set meshid $MESH_NETWORK

                    # Configure IP address for mesh interface
                    result = subprocess.run(
                        f"ip addr add {wifiMeshIPAddress}/24 dev {theMeshDevice}",
                        shell=True,
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    if result.returncode != 0:
                        SendToSirapAdapter.WiRocLogger.error(
                            f"SendToSirapAdapter::Init() setting the wifi mesh IP address failed: {result.stderr}")

                    if True:
                        # Configure forwarding to wlan0

                        result = subprocess.run(
                            f"ip link show {internetInterface}",
                            shell=True,
                            capture_output=True,
                            text=True,
                            check=False
                        )
                        if result.returncode != 0:
                            SendToSirapAdapter.WiRocLogger.error(
                                f"SendToSirapAdapter::Init() check if internet interface exists failed: {result.stderr}")

                        # Enable IP forwarding
                        result = subprocess.run(
                            f"echo 1 > /proc/sys/net/ipv4/ip_forward",
                            shell=True,
                            capture_output=True,
                            text=True,
                            check=False
                        )
                        if result.returncode != 0:
                            SendToSirapAdapter.WiRocLogger.error(
                                f"SendToSirapAdapter::Init() enable ip forward failed: {result.stderr}")

                        # # Configure NAT/masquerading for internet sharing
                        #         if ! iptables -t nat -C POSTROUTING -o $InternetInterface -j MASQUERADE 2>/dev/null; then
                        #             iptables -t nat -A POSTROUTING -o $InternetInterface -j MASQUERADE
                        #             echo "Added NAT masquerade rule"
                        #         fi
                        #
                        #         # Add forwarding rules if not already present
                        #         if ! iptables -C FORWARD -i $MESH_DEVICE -o $InternetInterface -j ACCEPT 2>/dev/null; then
                        #             iptables -A FORWARD -i $MESH_DEVICE -o $InternetInterface -j ACCEPT
                        #         fi
                        #
                        #         if ! iptables -C FORWARD -i $InternetInterface -o $MESH_DEVICE -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null; then
                        #             iptables -A FORWARD -i $InternetInterface -o $MESH_DEVICE -m state --state RELATED,ESTABLISHED -j ACCEPT
                        #         fi

        #   else:
        #       sudo iw dev wlan0 mesh leave
        if self.GetIsInitialized():
            return True
        self.isInitialized = True
        return True

    def IsReadyToSend(self) -> bool:
        return True

    @staticmethod
    def GetDelayAfterMessageSent() -> float:
        return 0

    def GetRetryDelay(self, tryNo: int) -> float:
        return 1

    def OpenConnection(self, failureCB, callbackQueue, settingsDictionary: dict[str, any]) -> bool:
        if self.sock is None:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                SendToSirapAdapter.WiRocLogger.debug(
                    "SendToSirapAdapter::OpenConnection() Address: " + settingsDictionary["SendToSirapIP"] + " Port: " + str(
                        settingsDictionary["SendToSirapIPPort"]))
                server_address = (settingsDictionary["SendToSirapIP"], settingsDictionary["SendToSirapIPPort"])
                self.sock.settimeout(2)
                self.sock.connect(server_address)
                SendToSirapAdapter.WiRocLogger.debug("SendToSirapAdapter::OpenConnection() After connect")
                return True
            except socket.gaierror as msg:
                SendToSirapAdapter.WiRocLogger.error(
                    "SendToSirapAdapter::OpenConnection() Address-related error connecting to server: " + str(msg))
                if self.sock is not None:
                    self.sock.close()
                self.sock = None
                failureCB()
                #callbackQueue.put((failureCB,))
                return False
            except socket.error as msg:
                SendToSirapAdapter.WiRocLogger.error("SendToSirapAdapter::OpenConnection() Connection error: " + str(msg))
                if self.sock is not None:
                    self.sock.close()
                self.sock = None
                failureCB()
                #callbackQueue.put((failureCB,))
                return False
        return True

    # messageData is tuple of bytearray
    def SendData(self, messageData: tuple[bytearray], successCB, failureCB, notSentCB, settingsDictionary: dict[str, any]) -> bool:
        try:
            # Send data
            for data in messageData:
                if not self.OpenConnection(failureCB, None, settingsDictionary):
                    self.sock = None
                    return False

                self.sock.sendall(data)
                self.sock.close()
                self.sock = None
                SendToSirapAdapter.WiRocLogger.debug(
                    "SendToSirapAdapter::SendData() Sent to SIRAP: " + Utils.GetDataInHex(data, logging.DEBUG))

            DatabaseHelper.add_message_stat(self.GetInstanceName(), "SIMessage", "Sent", 1)
            successCB()
            return True
        except socket.error as msg:
            logging.error(msg)
            if self.sock is not None:
                self.sock.close()
            self.sock = None
            failureCB()
            return False
        except:
            SendToSirapAdapter.WiRocLogger.error("SendToSirapAdapter::SendData() Exception")
            if self.sock is not None:
                self.sock.close()
            self.sock = None
            failureCB()
            return False
