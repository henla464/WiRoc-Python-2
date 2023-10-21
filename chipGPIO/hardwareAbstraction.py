from chipGPIO.chipGPIO import *
import logging
import socket
import subprocess
import gpiod
from smbus2 import SMBus
import yaml
from datetime import timedelta
from pathlib import Path


class HardwareAbstraction(object):
    WiRocLogger = logging.getLogger('WiRoc')
    Instance = None
    i2cAddress = 0x34

    def __init__(self):
        HardwareAbstraction.WiRocLogger.info("HardwareAbstraction::Init start")
        self.i2cBus = SMBus(0)  # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)
        self.LORAaux = None
        self.LORAenable = None
        self.LORAM0 = None
        self.SRRirq = None
        self.SRRnrst = None
        self.PMUIRQ = None
        with open("../settings.yaml", "r") as f:
            settings = yaml.load(f, Loader=yaml.BaseLoader)
        wirocHWVersion: str = settings['WiRocHWVersion']
        self.wirocHWVersion: str = wirocHWVersion.strip()
        self.wirocHWVersionNumber: int = int(self.wirocHWVersion.split("Rev")[0][1:])
        self.wirocHWRevisionNumber:int  = int(self.wirocHWVersion.split("Rev")[1])

    def SetupPins(self):
        # gpioinfo give us gpiochip0 and gpiochip1. But gpiochip0 for the lines (pins) needed
        chip: gpiod.chip = gpiod.chip('gpiochip0')
        configOutput = gpiod.line_request()
        configOutput.consumer = "wirocpython"
        configOutput.request_type = gpiod.line_request.DIRECTION_OUTPUT
        configInput = gpiod.line_request()
        configInput.consumer = "wirocpython"
        configInput.request_type = gpiod.line_request.DIRECTION_INPUT

        configIrq = gpiod.line_request()
        configIrq.consumer = "wirocpython"
        configIrq.request_type = gpiod.line_request.EVENT_RISING_EDGE

        self.PMUIRQ = chip.get_line(3)  # IRQ pin GPIOA3 Pin 15
        self.PMUIRQ.request(configInput)

        if self.wirocHWVersion == 'v4Rev1' or self.wirocHWVersion == 'v5Rev1':
            self.LORAaux = chip.get_line(64) # lora aux pin (corresponds to pin 19)
            self.LORAaux.request(configInput)

            self.LORAenable = chip.get_line(2) # lora enable pin (corresponds to pin 13)
            self.LORAenable.request(configOutput)
            self.LORAenable.set_value(1)

            self.LORAM0 = chip.get_line(17)  # lora M0 pin (corresponds to pin 7 (nanopi wiki) / pin 37 (PCB footprint))
            self.LORAM0.request(configOutput)
            self.LORAM0.set_value(0)
        elif self.wirocHWVersionNumber >= 6:
            self.LORAaux = chip.get_line(64) # lora aux pin (corresponds to pin 19)
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

    def GetSISerialPorts(self):
        if self.wirocHWVersionNumber >= 4:
            #== 'v4Rev1' or self.wirocHWVersion == 'v5Rev1' or self.wirocHWVersion == 'v6Rev1':
            return ['/dev/ttyS2']
        return []

    def EnableLora(self):
        self.LORAenable.set_value(0)

    def DisableLora(self):
        self.LORAenable.set_value(1)

    def EnableSRR(self):
        if self.SRRnrst is not None:
            self.SRRnrst.set_value(1)

    def DisableSRR(self):
        if self.SRRnrst is not None:
            self.SRRnrst.set_value(0)

    def GetSRRIRQValue(self):
        if self.SRRirq is not None:
            return self.SRRirq.get_value() == 1
        else:
            return False

    def GetIsPMUIRQ(self):
        if self.PMUIRQ is not None:
            irqValue = self.PMUIRQ.get_value()
            if irqValue == 0:
                Path('/home/chip/PMUIRQ.txt').touch()
            return self.PMUIRQ.get_value() == 0
        else:
            return False

    def GetIsTransmittingReceiving(self):
        return self.LORAaux.get_value() == 0  # lora aux pin (corresponds to pin 19)

    def GetWifiSignalStrength(self):
        wifiInUseSSIDSignal = str(subprocess.check_output(["nmcli", "-t", "-f", "in-use,ssid,signal", "device", "wifi"]))
        for row in wifiInUseSSIDSignal.split('\\n'):
            if row.startswith('*'):
                return int(row.split(':')[2])
        return None

    def GetWiRocIPAddresses(self):
        ipAddresses = subprocess.check_output(["hostname", "-I"]).decode('ascii')
        ipAddressesArray = ipAddresses.split(" ")
        return ipAddressesArray

    def GetIsShortKeyPress(self):
        HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::GetIsShortKeyPress")

        IRQ_STATUS_3_REGADDR = 0x4a
        statusReg = self.i2cBus.read_byte_data(self.i2cAddress, IRQ_STATUS_3_REGADDR)

        shortKeyPress = statusReg & 0x02
        return shortKeyPress > 0

    def ClearShortKeyPress(self):
        HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::ClearShortKeyPress")
        IRQ_STATUS_3_REGADDR = 0x4a
        self.i2cBus.write_byte_data(self.i2cAddress, IRQ_STATUS_3_REGADDR, 0x02)

    def GetIsLongKeyPress(self):
        HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::GetIsLongKeyPress")

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