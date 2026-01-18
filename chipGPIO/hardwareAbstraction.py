from __future__ import annotations
import logging
import socket
import subprocess
import gpiod
from smbus2 import SMBus
import yaml
from datetime import timedelta, datetime, timezone
from pathlib import Path
import inspect
try:
    from gpiod.line import Direction, Value
except ImportError:
    pass


class HardwareAbstraction(object):
    WiRocLogger = logging.getLogger('WiRoc')
    Instance: HardwareAbstraction = None
    i2cAddress: int = 0x34
    rtcAddress: int = 0x51

    def __init__(self):
        HardwareAbstraction.WiRocLogger.info("HardwareAbstraction::Init start")
        self.i2cBus = SMBus(0)  # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)
        self.LORAaux = None
        self.LORAenable = None
        self.LORAM0 = None
        self.SRRirq = None
        self.SRRnrst = None
        self.PMUIRQ = None
        self.StatusLed = None

        self.line_request = None
        self.PMUIRQLine = None
        self.LORAenableLine = None
        self.LORAM0Line = None
        self.LORAauxLine = None
        self.SRRirqLine = None
        self.SRRnrstLine = None
        self.StatusLedLine = None
        self.isNewGpiod = None

        with open("../settings.yaml", "r") as f:
            settings = yaml.load(f, Loader=yaml.BaseLoader)
        wirocHWVersion: str = settings['WiRocHWVersion']
        self.wirocHWVersion: str = wirocHWVersion.strip()
        self.wirocHWVersionNumber: int = int(self.wirocHWVersion.split("Rev")[0][1:])
        self.wirocHWRevisionNumber: int = int(self.wirocHWVersion.split("Rev")[1])

    def SetupPins(self):
        # gpioinfo give us gpiochip0 and gpiochip1. But gpiochip0 for the lines (pins) needed
        chip: gpiod.chip = None

        if inspect.ismodule(gpiod.chip):
            self.isNewGpiod = True
            chipPath = "/dev/gpiochip0"

            self.PMUIRQLine = 3
            self.LORAenableLine = 2

            if self.wirocHWVersion == 'v4Rev1' or self.wirocHWVersion == 'v5Rev1':
                self.LORAM0Line = 17
                self.LORAauxLine = 64

                self.line_request = gpiod.request_lines(chipPath, consumer="wirocpython", config={
                    self.LORAenableLine: gpiod.LineSettings(direction=Direction.OUTPUT),   # lora enable pin (corresponds to pin 13)
                    self.PMUIRQLine: gpiod.LineSettings(direction=Direction.INPUT), # IRQ pin GPIOA3 Pin 15
                    self.LORAM0Line: gpiod.LineSettings(direction=Direction.OUTPUT),  # lora M0 pin (corresponds to pin 7 (nanopi wiki) / pin 37 (PCB footprint))
                    self.LORAauxLine: gpiod.LineSettings(direction=Direction.INPUT)    # lora aux pin (corresponds to pin 19)
                })
                self.line_request.set_value(self.LORAenableLine, Value.ACTIVE)
                self.line_request.set_value(self.LORAM0Line, Value.INACTIVE)

            elif self.wirocHWVersionNumber >= 6 and self.wirocHWRevisionNumber <= 7:
                self.SRRirqLine = 6
                self.LORAM0Line = 17
                self.LORAauxLine = 64
                self.SRRnrstLine = 67
                self.line_request = gpiod.request_lines(chipPath, consumer="wirocpython", config={
                    self.LORAenableLine: gpiod.LineSettings(direction=Direction.OUTPUT),  # lora enable pin (corresponds to pin 13)
                    self.PMUIRQLine: gpiod.LineSettings(direction=Direction.INPUT),  # IRQ pin GPIOA3 Pin 15
                    self.SRRirqLine : gpiod.LineSettings(direction=Direction.INPUT),  # SRR_IRQ input interrupt message available (corresponds to pin 12 GPIOA6)
                    self.LORAM0Line: gpiod.LineSettings(direction=Direction.OUTPUT),      # lora M0 pin (corresponds to pin 7 (nanopi wiki) / pin 37 (PCB footprint))
                    self.LORAauxLine: gpiod.LineSettings(direction=Direction.INPUT),       # lora aux pin (corresponds to pin 19)
                    self.SRRnrstLine: gpiod.LineSettings(direction=Direction.OUTPUT)  # SRR_NRST reset SRR (corresponds to pin 24 GPIOC3)
                })
                self.line_request.set_value(self.LORAenableLine, Value.ACTIVE)
                self.line_request.set_value(self.LORAM0Line, Value.ACTIVE)
                self.line_request.set_value(self.SRRnrstLine, Value.ACTIVE)
            elif self.wirocHWVersionNumber >= 8:
                self.SRRirqLine = 6
                self.LORAM0Line = 17
                self.LORAauxLine = 64
                self.SRRnrstLine = 201
                self.line_request = gpiod.request_lines(chipPath, consumer="wirocpython", config={
                    self.LORAenableLine: gpiod.LineSettings(direction=Direction.OUTPUT),  # lora enable pin (corresponds to pin 13)
                    self.PMUIRQLine: gpiod.LineSettings(direction=Direction.INPUT),  # IRQ pin GPIOA3 Pin 15
                    self.SRRirqLine : gpiod.LineSettings(direction=Direction.INPUT),  # SRR_IRQ input interrupt message available (corresponds to pin 12 GPIOA6)
                    self.LORAM0Line: gpiod.LineSettings(direction=Direction.OUTPUT),      # lora M0 pin (corresponds to pin 7 (nanopi wiki) / pin 37 (PCB footprint))
                    self.LORAauxLine: gpiod.LineSettings(direction=Direction.INPUT),       # lora aux pin (corresponds to pin 19)
                    self.SRRnrstLine: gpiod.LineSettings(direction=Direction.OUTPUT)  # SRR_NRST reset SRR (GPIOG9)
                })
                self.line_request.set_value(self.LORAenableLine, Value.ACTIVE)
                self.line_request.set_value(self.LORAM0Line, Value.ACTIVE)
                self.line_request.set_value(self.SRRnrstLine, Value.ACTIVE)
            else:
                self.LORAauxLine = 0
                self.StatusLedLine = 6
                self.line_request = gpiod.request_lines(chipPath, consumer="wirocpython", config={
                    self.LORAenableLine: gpiod.LineSettings(direction=Direction.OUTPUT),  # lora enable pin (corresponds to pin 13)
                    self.PMUIRQLine: gpiod.LineSettings(direction=Direction.INPUT),  # IRQ pin GPIOA3 Pin 15
                    self.LORAauxLine: gpiod.LineSettings(direction=Direction.INPUT),      # lora aux pin
                    self.StatusLedLine: gpiod.LineSettings(direction=Direction.OUTPUT)    # status led pin GPIOA6 Pin 12, linux gpio 6
                })
                self.line_request.set_value(self.LORAenableLine, Value.ACTIVE)
                self.line_request.set_value(self.StatusLedLine, Value.ACTIVE)

        else:
            self.isNewGpiod = False
            chip = gpiod.chip('gpiochip0')

            configOutput = gpiod.line_request()
            configOutput.consumer = "wirocpython"
            configOutput.request_type = gpiod.line_request.DIRECTION_OUTPUT
            configInput = gpiod.line_request()
            configInput.consumer = "wirocpython"
            configInput.request_type = gpiod.line_request.DIRECTION_INPUT


            self.PMUIRQ = chip.get_line(3)  # IRQ pin GPIOA3 Pin 15
            self.PMUIRQ.request(configInput)

            if self.wirocHWVersion == 'v4Rev1' or self.wirocHWVersion == 'v5Rev1':
                self.LORAaux = chip.get_line(64) # lora aux pin (corresponds to pin 19)
                self.LORAaux.request(configInput)

                self.LORAenable = chip.get_line(2)  # lora enable pin (corresponds to pin 13)
                self.LORAenable.request(configOutput)
                self.LORAenable.set_value(1)

                self.LORAM0 = chip.get_line(17)  # lora M0 pin (corresponds to pin 7 (nanopi wiki) / pin 37 (PCB footprint))
                self.LORAM0.request(configOutput)
                self.LORAM0.set_value(0)
            elif self.wirocHWVersionNumber >= 6:
                self.LORAaux = chip.get_line(64)  # lora aux pin (corresponds to pin 19)
                self.LORAaux.request(configInput)

                self.LORAenable = chip.get_line(2) # lora enable pin (corresponds to pin 13)
                self.LORAenable.request(configOutput)
                self.LORAenable.set_value(1)

                self.LORAM0 = chip.get_line(17)  # lora M0 pin (corresponds to pin 7 (nanopi wiki) / pin 37 (PCB footprint))
                self.LORAM0.request(configOutput)
                self.LORAM0.set_value(0)

                self.SRRirq = chip.get_line(6) # SRR_IRQ input interrupt message available (corresponds to pin 12 GPIOA6)
                self.SRRirq.request(configInput)

                self.SRRnrst = chip.get_line(67) # SRR_NRST reset SRR (corresponds to pin 24 GPIOC3)
                self.SRRnrst.request(configOutput)
                self.SRRnrst.set_value(1)
            else:
                self.LORAaux = chip.get_line(0)  # lora aux pin
                self.LORAaux.request(configInput)

                self.LORAenable = chip.get_line(2)  # lora enable pin (corresponds to pin 13)
                self.LORAenable.request(configOutput)
                self.LORAenable.set_value(1)

                self.StatusLed = chip.get_line(6)  # status led pin GPIOA6 Pin 12, linux gpio 6
                self.StatusLed.request(configOutput)
                self.StatusLed.set_value(1)

    def GetSISerialPorts(self):
        if self.wirocHWVersionNumber >= 4:
            #== 'v4Rev1' or self.wirocHWVersion == 'v5Rev1' or self.wirocHWVersion == 'v6Rev1':
            return ['/dev/ttyS2']
        return []

    def EnableLora(self):
        if self.isNewGpiod:
            self.line_request.set_value(self.LORAenableLine, Value.INACTIVE)
            if self.LORAM0Line is not None:
                self.line_request.set_value(self.LORAM0Line, Value.INACTIVE)
        else:
            self.LORAenable.set_value(0)
            if self.LORAM0Line is not None:
                self.LORAM0Line.set_value(0)

    def DisableLora(self):
        if self.isNewGpiod:
            self.line_request.set_value(self.LORAenableLine, Value.ACTIVE)
            if self.LORAM0Line is not None:
                self.line_request.set_value(self.LORAM0Line, Value.ACTIVE)
        else:
            self.LORAenable.set_value(1)
            if self.LORAM0Line is not None:
                self.LORAM0Line.set_value(1)

    def EnableSRR(self):
        if self.isNewGpiod:
            if self.SRRnrstLine is not None:
                self.line_request.set_value(self.SRRnrstLine, Value.ACTIVE)
        else:
            if self.SRRnrst is not None:
                self.SRRnrst.set_value(1)

    def DisableSRR(self):
        if self.isNewGpiod:
            if self.SRRnrstLine is not None:
                self.line_request.set_value(self.SRRnrstLine, Value.INACTIVE)
        else:
            if self.SRRnrst is not None:
                self.SRRnrst.set_value(0)

    def GetSRRIRQValue(self):
        if self.isNewGpiod:
            if self.SRRirqLine is not None:
                return self.line_request.get_value(self.SRRirqLine) == Value.ACTIVE
        else:
            if self.SRRirq is not None:
                return self.SRRirq.get_value() == 1
            else:
                return False

    def GetIsPMUIRQ(self):
        if self.isNewGpiod:
            if self.PMUIRQLine is not None:
                irqValue = (self.line_request.get_value(self.PMUIRQLine) == Value.INACTIVE)
                if irqValue:
                    Path('/home/chip/PMUIRQ.txt').touch()
                return irqValue
        else:
            if self.PMUIRQ is not None:
                irqValue = self.PMUIRQ.get_value()
                if irqValue == 0:
                    Path('/home/chip/PMUIRQ.txt').touch()
                return self.PMUIRQ.get_value() == 0
            else:
                return False

    def GetIsTransmittingReceiving(self):
        if self.isNewGpiod:
            return self.line_request.get_value(self.LORAauxLine) == Value.INACTIVE
        else:
            return self.LORAaux.get_value() == 0  # lora aux pin (corresponds to pin 19)

    def GetWifiSignalStrength(self):
        wifiInUseSSIDSignal = str(subprocess.check_output(["nmcli", "-t", "-f", "in-use,ssid,signal", "device", "wifi"]))
        for row in wifiInUseSSIDSignal.split('\\n'):
            if row.startswith('*'):
                return int(row.split(':')[2])
        return None

    def GetBuiltinWifiInterfaceName(self) -> str:
        return "wlan0"

    def GetBuiltinEthernetInterfaceName(self) -> str:
        return ""

    def GetInternetInterfaceName(self) -> str:
        return "wlan0"

    def GetMeshInterfacePhy(self) -> str | None:
        mesh_phys = []
        current_phy = None

        # 1. Get mesh-capable PHYs
        try:
            for line in subprocess.check_output(["iw", "list"], text=True).splitlines():
                line = line.strip()
                if line.startswith("Wiphy"):
                    current_phy = line.split()[1]
                elif line == "* mesh point" and current_phy:
                    mesh_phys.append(current_phy)
                    break

            return mesh_phys[0] if len(mesh_phys) > 0 else None
        except Exception as e:
            HardwareAbstraction.WiRocLogger.error(
                f"HardwareAbstraction::GetMeshInterfaceName() listing wifi mesh phys failed {e}")
            return None

    def GetMeshInterfaceName(self) -> str | None:
        return "mesh0"

    def GetUSBEthernetInterfaces(self) -> list[str]:
        result = subprocess.run(['nmcli', '-m', 'multiline', '-f', 'device,type', 'device', 'status'], stdout=subprocess.PIPE, check=True)
        if result.returncode != 0:
            errStr = result.stderr.decode('utf-8')
            raise Exception("Error: " + errStr)
        devices = result.stdout.decode('utf-8').splitlines()[0: -1]  # remove last empty element
        devices = [dev[40:] for dev in devices]
        ifaces = devices[::2]
        ifaceNetworkTypes = devices[1::2]
        ethernetInterfaces: list[str] = []
        for iface, ifaceNetworkType in zip(ifaces, ifaceNetworkTypes):
            if ifaceNetworkType == 'ethernet':
                if iface != self.GetBuiltinEthernetInterfaceName():
                    ethernetInterfaces.append(iface)
        return ethernetInterfaces

    def GetAllIPAddressesOnInterface(self, interface: str):
        try:
            # Get all IPs on the interface
            result = subprocess.run(
                f"ip -4 addr show dev {interface}",
                shell=True,
                capture_output=True,
                text=True,
                check=True
            )

            # Extract current IPv4 addresses
            current_ips = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith("inet "):
                    ip_cidr = line.split()[1]  # e.g., "192.168.50.2/24"
                    ip = ip_cidr.split("/")[0]
                    current_ips.append(ip)

            return current_ips
        except Exception as e:
            HardwareAbstraction.WiRocLogger.error(
                f"HardwareAbstraction::GetAllIPAddressesOnInterface() getting IPAddresses of interface {interface} failed {e}")
            return []

    def GetInterfaceMAC(self, interface: str):
        try:
            result = subprocess.run(f"cat /sys/class/net/{interface}/address",
                                shell=True,
                                capture_output=True,
                                text=True,
                                check=True)

            mac = result.stdout
            return mac
        except Exception as e:
            HardwareAbstraction.WiRocLogger.error(
                f"HardwareAbstraction::GetInterfaceMAC() getting MAC of interface {interface} failed {e}")
            return ""


    def DoesInterfaceExist(self, interface:str) -> bool:
        result = subprocess.run(
            f"ip link show dev {interface}",
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        meshInterfaceCreated = '1'
        if result.returncode != 0:
            HardwareAbstraction.WiRocLogger.error(
                f"HardwareAbstraction::DoesInterfaceExist({interface}): {result.stderr}")
            return False
        return True

    def GetWiRocIPAddresses(self):
        ipAddresses = subprocess.check_output(["hostname", "-I"]).decode('ascii')
        ipAddressesArray = ipAddresses.split(" ")
        return ipAddressesArray

    def GetIsShortKeyPress(self):
        # HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::GetIsShortKeyPress")

        IRQ_STATUS_3_REGADDR = 0x4a
        statusReg = self.i2cBus.read_byte_data(self.i2cAddress, IRQ_STATUS_3_REGADDR)

        shortKeyPress = statusReg & 0x02
        return shortKeyPress > 0

    def ClearShortKeyPress(self):
        HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::ClearShortKeyPress")
        IRQ_STATUS_3_REGADDR = 0x4a
        self.i2cBus.write_byte_data(self.i2cAddress, IRQ_STATUS_3_REGADDR, 0x02)

    def GetIsLongKeyPress(self):
        # HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::GetIsLongKeyPress")

        IRQ_STATUS_3_REGADDR = 0x4a
        statusReg = self.i2cBus.read_byte_data(self.i2cAddress, IRQ_STATUS_3_REGADDR)

        longKeyPress = statusReg & 0x01
        return longKeyPress > 0

    def ClearLongKeyPress(self):
        HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::ClearLongKeyPress")
        IRQ_STATUS_3_REGADDR = 0x4a
        self.i2cBus.write_byte_data(self.i2cAddress, IRQ_STATUS_3_REGADDR, 0x01)

    def ClearPMUIRQStatus1(self):
        HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::ClearPMUIRQStatus1")
        IRQ_STATUS_1_REGADDR = 0x48
        self.i2cBus.write_byte_data(self.i2cAddress, IRQ_STATUS_1_REGADDR, 0xFF)

    def ClearPMUIRQStatus2(self):
        HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::ClearPMUIRQStatus2")
        IRQ_STATUS_2_REGADDR = 0x49
        self.i2cBus.write_byte_data(self.i2cAddress, IRQ_STATUS_2_REGADDR, 0xFF)

    def ClearPMUIRQStatus3(self):
        HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::ClearPMUIRQStatus3")
        IRQ_STATUS_3_REGADDR = 0x4a
        self.i2cBus.write_byte_data(self.i2cAddress, IRQ_STATUS_3_REGADDR, 0xFF)

    def ClearPMUIRQStatus4(self):
           HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::ClearPMUIRQStatus4")
           IRQ_STATUS_4_REGADDR = 0x4b
           self.i2cBus.write_byte_data(self.i2cAddress, IRQ_STATUS_4_REGADDR, 0xFF)

    def ClearPMUIRQStatus5(self):
        HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::ClearPMUIRQStatus5")
        IRQ_STATUS_5_REGADDR = 0x4c
        self.i2cBus.write_byte_data(self.i2cAddress, IRQ_STATUS_5_REGADDR, 0xFF)

    def DisablePMUIRQ1(self):
        HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::DisablePMUIRQ4")
        IRQ_1_REGADDR = 0x40
        self.i2cBus.write_byte_data(self.i2cAddress, IRQ_1_REGADDR, 0x00)

    def DisablePMUIRQ2(self):
        HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::DisablePMUIRQ4")
        IRQ_2_REGADDR = 0x41
        self.i2cBus.write_byte_data(self.i2cAddress, IRQ_2_REGADDR, 0x00)

    # IRQ3 Contains PEK short and long. Default is correct so no need to disable.
    def DisablePMUIRQ3(self):
        HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::DisablePMUIRQ4")
        IRQ_3_REGADDR = 0x42
        self.i2cBus.write_byte_data(self.i2cAddress, IRQ_3_REGADDR, 0x00)

    def DisablePMUIRQ4(self):
        HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::DisablePMUIRQ4")
        IRQ_4_REGADDR = 0x43
        self.i2cBus.write_byte_data(self.i2cAddress, IRQ_4_REGADDR, 0x00)

    def HasRTC(self):
        return self.wirocHWVersionNumber >= 7

    def HasSRR(self):
        # The version 6 had SRR but with flex cable that seem to only give problems.
        # So lets only enabled SRR when version >= 7
        return self.wirocHWVersionNumber >= 7

    def GetRTCDateTime(self) -> str:
        HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::GetRTCDateTime")
        SECOND_REGADDR = 0x02
        MINUTE_REGADDR = 0x03
        HOUR_REGADDR = 0x04
        DAY_REGADDR = 0x05
        MONTH_REGADDR = 0x07
        YEAR_REGADDR = 0x08

        seconds = self.i2cBus.read_byte_data(self.rtcAddress, SECOND_REGADDR, force=True)
        minutes = self.i2cBus.read_byte_data(self.rtcAddress, MINUTE_REGADDR, force=True)
        hours = self.i2cBus.read_byte_data(self.rtcAddress, HOUR_REGADDR, force=True)
        days = self.i2cBus.read_byte_data(self.rtcAddress, DAY_REGADDR, force=True)
        months = self.i2cBus.read_byte_data(self.rtcAddress, MONTH_REGADDR, force=True)
        years = self.i2cBus.read_byte_data(self.rtcAddress, YEAR_REGADDR, force=True)

        # Exclude the VL flag, and downshift
        seconds_HighCharacter = (seconds & 0x70) >> 4
        seconds_LowCharacter = (seconds & 0x0F)
        minutes_HighCharacter = (minutes & 0x70) >> 4
        minutes_LowCharacter = (minutes & 0x0F)
        hour_HighCharacter = (hours & 0x30) >> 4
        hour_LowCharacter = (hours & 0x0F)
        days_HighCharacter = (days & 0x30) >> 4
        days_LowCharacter = (days & 0x0F)
        months_HighCharacter = (months & 0x10) >> 4
        months_LowCharacter = (months & 0x0F)
        years_HighCharacter = (years & 0xF0) >> 4
        years_LowCharacter = (years & 0x0F)

        # Convert UTC to local time
        utcDateTimeStr = f"20{years_HighCharacter}{years_LowCharacter}-{months_HighCharacter}{months_LowCharacter}-{days_HighCharacter}{days_LowCharacter} {hour_HighCharacter}{hour_LowCharacter}:{minutes_HighCharacter}{minutes_LowCharacter}:{seconds_HighCharacter}{seconds_LowCharacter}"
        HardwareAbstraction.WiRocLogger.debug(f"HardwareAbstraction::GetRTCDateTime {utcDateTimeStr}")
        utcDateTime = datetime.strptime(utcDateTimeStr, "%Y-%m-%d %H:%M:%S")
        utcDateTime = utcDateTime.replace(tzinfo=timezone.utc)
        localDateTime = utcDateTime.astimezone(datetime.now().tzinfo)
        localDateTimeStr = localDateTime.strftime("%Y-%m-%d %H:%M:%S")

        return localDateTimeStr

    def SetRTCDateTime(self, dateAndTimeWithSeconds: str) -> None:
        HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::SetRTCDateTime")

        years_local = int(dateAndTimeWithSeconds[2:4])
        months_local = int(dateAndTimeWithSeconds[5:7])
        days_local = int(dateAndTimeWithSeconds[8:10])
        hours_local = int(dateAndTimeWithSeconds[11:13])
        minutes_local = int(dateAndTimeWithSeconds[14:16])
        seconds_local = int(dateAndTimeWithSeconds[17:19])
       # raise Exception(str(months_local))
        # Convert to UTC time
        localDateTime = datetime(2000 + years_local, months_local, days_local, hours_local, minutes_local, seconds_local)
        utcDateTime = localDateTime.astimezone(timezone.utc)
        utcDateTimeStr = utcDateTime.strftime("%Y-%m-%d %H:%M:%S")

        years_HighCharacter = int(utcDateTimeStr[2])
        years_LowCharacter = int(utcDateTimeStr[3])
        months_HighCharacter = int(utcDateTimeStr[5])
        months_LowCharacter = int(utcDateTimeStr[6])
        days_HighCharacter = int(utcDateTimeStr[8])
        days_LowCharacter = int(utcDateTimeStr[9])
        hour_HighCharacter = int(utcDateTimeStr[11])
        hour_LowCharacter = int(utcDateTimeStr[12])
        minutes_HighCharacter = int(utcDateTimeStr[14])
        minutes_LowCharacter = int(utcDateTimeStr[15])
        seconds_HighCharacter = int(utcDateTimeStr[17])
        seconds_LowCharacter = int(utcDateTimeStr[18])

        years = (years_HighCharacter << 4) | years_LowCharacter
        months = (months_HighCharacter << 4) | months_LowCharacter
        days = (days_HighCharacter << 4) | days_LowCharacter
        hours = (hour_HighCharacter << 4) | hour_LowCharacter
        minutes = (minutes_HighCharacter << 4) | minutes_LowCharacter
        seconds = (seconds_HighCharacter << 4) | seconds_LowCharacter

        SECOND_REGADDR = 0x02
        MINUTE_REGADDR = 0x03
        HOUR_REGADDR = 0x04
        DAY_REGADDR = 0x05
        MONTH_REGADDR = 0x07
        YEAR_REGADDR = 0x08

        self.i2cBus.write_byte_data(self.rtcAddress, YEAR_REGADDR, years, force=True)
        self.i2cBus.write_byte_data(self.rtcAddress, MONTH_REGADDR, months, force=True)
        self.i2cBus.write_byte_data(self.rtcAddress, DAY_REGADDR, days, force=True)
        self.i2cBus.write_byte_data(self.rtcAddress, HOUR_REGADDR, hours, force=True)
        self.i2cBus.write_byte_data(self.rtcAddress, MINUTE_REGADDR, minutes, force=True)
        self.i2cBus.write_byte_data(self.rtcAddress, SECOND_REGADDR, seconds, force=True)

    def GetRTCWakeUpTime(self) -> str:
        HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::GetRTCWakeUpTime")
        MINUTE_ALARM_REGADDR = 0x09
        HOUR_ALARM_REGADDR = 0x0a
        minutes = self.i2cBus.read_byte_data(self.rtcAddress, MINUTE_ALARM_REGADDR, force=True)
        hours = self.i2cBus.read_byte_data(self.rtcAddress, HOUR_ALARM_REGADDR, force=True)
        # Exclude AE_M minute alarm enable bit
        minutes_HighCharacter = (minutes & 0x70) >> 4
        minutes_LowCharacter = (minutes & 0x0F)
        hour_HighCharacter = (hours & 0x30) >> 4
        hour_LowCharacter = (hours & 0x0F)

        utcnow = datetime.utcnow()
        noOfSecondsSinceMidnightAlarm = (hour_HighCharacter*10 + hour_LowCharacter) * 3600 +  (minutes_HighCharacter*10 +minutes_LowCharacter) * 60
        noOfSecondsSinceMidnightCurrentTime = utcnow.hour * 3600 + utcnow.minute*60 + utcnow.second
        dateOfAlarm = utcnow
        if noOfSecondsSinceMidnightAlarm < noOfSecondsSinceMidnightCurrentTime:
            dateOfAlarm = datetime.utcnow() + timedelta(days=1)

        dateofAlarmStr = dateOfAlarm.strftime("%Y-%m-%d")

        utcDateTimeAlarmStr = f"{dateofAlarmStr} {hour_HighCharacter}{hour_LowCharacter}:{minutes_HighCharacter}{minutes_LowCharacter}:00"
        try:
            utcDateTimeAlarm = datetime.strptime(utcDateTimeAlarmStr, "%Y-%m-%d %H:%M:%S")
            utcDateTimeAlarm = utcDateTimeAlarm.replace(tzinfo=timezone.utc)
            localDateTimeAlarm = utcDateTimeAlarm.astimezone(datetime.now().tzinfo)
            localDateTimeAlarmStr = localDateTimeAlarm.strftime("%H:%M")

            return localDateTimeAlarmStr
        except:
            # rtc wakeup time not valid, set default value
            return "00:00"

    def SetWakeUpTime(self, time: str) -> None:
        HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::SetWakeUpTime")

        now = datetime.now()
        noOfSecondsSinceMidnightAlarm = int(time[0:2]) * 3600 + int(time[3:5]) * 60
        noOfSecondsSinceMidnightCurrentTime = now.hour * 3600 + now.minute * 60 + now.second
        dateOfAlarm = now
        if noOfSecondsSinceMidnightAlarm < noOfSecondsSinceMidnightCurrentTime:
            dateOfAlarm = now + timedelta(days=1)

        localDateTime = datetime(dateOfAlarm.year, dateOfAlarm.month, dateOfAlarm.day, int(time[0:2]), int(time[3:5]), 0)
        utcDateTime = localDateTime.astimezone(timezone.utc)
        alarmTimeUtcStr = utcDateTime.strftime("%H:%M")

        MINUTE_REGADDR = 0x09
        HOUR_REGADDR = 0x0a

        hour_HighCharacter = int(alarmTimeUtcStr[0])
        hour_LowCharacter = int(alarmTimeUtcStr[1])
        minutes_HighCharacter = int(alarmTimeUtcStr[3])
        minutes_LowCharacter = int(alarmTimeUtcStr[4])

        minutes = (minutes_HighCharacter << 4) | minutes_LowCharacter
        hours = (hour_HighCharacter << 4) | hour_LowCharacter
        self.i2cBus.write_byte_data(self.rtcAddress, MINUTE_REGADDR, minutes, force=True)
        self.i2cBus.write_byte_data(self.rtcAddress, HOUR_REGADDR, hours, force=True)

    def SetWakeUpToBeEnabledAtShutdown(self) -> None:
        HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::SetWakeUpToBeEnabledAtShutdown")
        DAY_REGADDR = 0x0b
        self.i2cBus.write_byte_data(self.rtcAddress, DAY_REGADDR, 0x02, force=True)

    def ClearWakeUpToBeEnabledAtShutdown(self) -> None:
        HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::ClearWakeUpToBeEnabledAtShutdown")
        DAY_REGADDR = 0x0b
        self.i2cBus.write_byte_data(self.rtcAddress, DAY_REGADDR, 0x00, force=True)

    def GetWakeUpToBeEnabledAtShutdown(self) -> bool:
        HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::GetWakeUpToBeEnabledAtShutdown")
        if self.HasRTC():
            DAY_REGADDR = 0x0b
            dayBCD = self.i2cBus.read_byte_data(self.rtcAddress, DAY_REGADDR, force=True)
            return (dayBCD & 0x3F) == 0x02
        else:
            return False
