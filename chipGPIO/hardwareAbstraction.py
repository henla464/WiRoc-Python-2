from chipGPIO.chipGPIO import *
import logging
import socket
import subprocess
import gpiod
import smbus

class HardwareAbstraction(object):
    WiRocLogger = logging.getLogger('WiRoc')
    Instance = None
    i2cAddress = 0x34

    def __init__(self, typeOfDisplay):
        HardwareAbstraction.WiRocLogger.info("HardwareAbstraction::Init start")
        self.typeOfDisplay = typeOfDisplay
        self.runningOnChip = socket.gethostname() == 'chip'
        self.runningOnNanoPi = socket.gethostname() == 'nanopiair'
        self.i2cBus = smbus.SMBus(0)  # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)
        self.LORAaux = None
        self.LORAenable = None
        self.LORAM0 = None
        self.SRRirq = None
        self.SRRnrst = None
        self.PMUIRQ = None
        f = open("../WiRocHWVersion.txt", "r")
        wirocHWVersion = f.read()
        self.wirocHWVersion = wirocHWVersion.strip()
        f.close()

    def SetupPins(self):
        if self.runningOnNanoPi:
            # gpioinfo give us gpiochip0 and gpiochip1. But gpiochip0 for the lines (pins) needed
            chip = gpiod.Chip('gpiochip0')
            configOutput = gpiod.line_request()
            configOutput.consumer = "wirocpython"
            configOutput.request_type = gpiod.line_request.DIRECTION_OUTPUT
            configInput = gpiod.line_request()
            configInput.consumer = "wirocpython"
            configInput.request_type = gpiod.line_request.DIRECTION_INPUT

            configIrq = gpiod.line_request()
            configIrq.consumer = "wirocpython"
            configIrq.request_type = gpiod.line_request.EVENT_RISING_EDGE

            if self.wirocHWVersion == 'v4Rev1' or self.wirocHWVersion == 'v5Rev1':
                self.LORAaux = chip.get_line(64) # lora aux pin (corresponds to pin 19)
                self.LORAaux.request(consumer="wirocpython", type=gpiod.LINE_REQ_DIR_IN)

                self.LORAenable = chip.get_line(2) # lora enable pin (corresponds to pin 13)
                self.LORAenable.request(consumer="wirocpython", type=gpiod.LINE_REQ_DIR_OUT)
                self.LORAenable.set_value(1)

                self.LORAM0 = chip.get_line(17)  # lora M0 pin (corresponds to pin 7 (nanopi wiki) / pin 37 (PCB footprint))
                self.LORAM0.request(consumer="wirocpython", type=gpiod.LINE_REQ_DIR_OUT)
                self.LORAM0.set_value(0)
            elif self.wirocHWVersion == 'v6Rev1':
                self.LORAaux = chip.get_line(64) # lora aux pin (corresponds to pin 19)
                self.LORAaux.request(consumer="wirocpython", type=gpiod.LINE_REQ_DIR_IN)

                self.LORAenable = chip.get_line(2) # lora enable pin (corresponds to pin 13)
                self.LORAenable.request(consumer="wirocpython", type=gpiod.LINE_REQ_DIR_OUT)
                self.LORAenable.set_value(1)

                self.LORAM0 = chip.get_line(17)  # lora M0 pin (corresponds to pin 7 (nanopi wiki) / pin 37 (PCB footprint))
                self.LORAM0.request(consumer="wirocpython", type=gpiod.LINE_REQ_DIR_OUT)
                self.LORAM0.set_value(0)

                self.SRRirq = chip.get_line(6) # SRR_IRQ input interrupt message available (corresponds to pin 12 GPIOA6)
                self.SRRirq.request(consumer="wirocpython", type=gpiod.LINE_REQ_DIR_IN)

                self.SRRnrst = chip.get_line(67) # SRR_NRST reset SRR (corresponds to pin 24 GPIOC3)
                self.SRRnrst.request(consumer="wirocpython", type=gpiod.LINE_REQ_DIR_OUT)
                self.SRRnrst.set_value(1)

                self.PMUIRQ = chip.get_line(3) # IRQ pin GPIOA3 Pin 15
                self.PMUIRQ.request(consumer="wirocpython", type=gpiod.LINE_REQ_EV_RISING_EDGE)
            else:
                self.LORAaux = chip.get_line(0)  # lora aux pin
                self.LORAaux.request(consumer="wirocpython", type=gpiod.LINE_REQ_DIR_IN)

                self.LORAenable = chip.get_line(2)  # lora enable pin (corresponds to pin 13)
                self.LORAenable.request(consumer="wirocpython", type=gpiod.LINE_REQ_DIR_OUT)
                self.LORAenable.set_value(1)
        elif self.runningOnChip:
            pinMode(0, OUTPUT)
            pinMode(1, OUTPUT)
            pinMode(2, OUTPUT)
            pinMode(3, OUTPUT)
            pinMode(4, OUTPUT)
            pinMode(5, OUTPUT)
            pinMode(6, OUTPUT)
            pinMode(7, OUTPUT)
            if self.typeOfDisplay == '7SEG':
                pinModeNonXIO(138, INPUT)
                pinModeNonXIO(139, OUTPUT)
                digitalWriteNonXIO(139, 1)
            else:  # OLED
                pinModeNonXIO(134, INPUT)
                pinModeNonXIO(135, OUTPUT)
                digitalWriteNonXIO(135, 1)

    def GetSISerialPorts(self):
        if self.wirocHWVersion == 'v4Rev1' or self.wirocHWVersion == 'v5Rev1' or self.wirocHWVersion == 'v6Rev1':
            return ['/dev/ttyS2']
        return []

    def GetDefaultValueForSendStatusMessage(self):
        if self.runningOnChip:
            return "0"
        else:
            return "1"

    def EnableLora(self):
        # enable radio module 139;
        # with new oled design: 135
        # pin 2 for nanopiair
        if self.runningOnNanoPi:
            self.LORAenable.set_value(0)
        elif self.runningOnChip:
            if self.typeOfDisplay == '7SEG':
                digitalWriteNonXIO(139, 0)
            else:
                digitalWriteNonXIO(135, 0)

    def DisableLora(self):
        # disable radio module 139; #with new oled design: 135
        # pin 2 for nanopiair
        if self.runningOnNanoPi:
            self.LORAenable.set_value(1)
        elif self.runningOnChip:
            if self.typeOfDisplay == '7SEG':
                digitalWriteNonXIO(139, 1)
            else:
                digitalWriteNonXIO(135, 1)

    def EnableSRR(self):
        if self.SRRnrst is not None:
            self.SRRnrst.set_value(0)

    def DisableSRR(self):
        if self.SRRirq is not None:
            self.SRRirq.get_value()

    def GetSRRIRQValue(self):
        if self.SRRnrst is not None:
            self.SRRnrst.get_value()
        else:
            return 0

    def GetIsPMUIRQ(self):
        if self.Button is not None:
            if self.Button.event_wait():  # todo: if needed add bounce time
                ev = self.Button.event_read()
                return True
            else:
                return False
        else:
            return False

    def GetIsTransmittingReceiving(self):
        # aux 138, with new oled design: 134
        if self.runningOnChip:
            if self.typeOfDisplay == '7SEG':
                return digitalReadNonXIO(138) == 0
            else:
                return digitalReadNonXIO(134) == 0
        elif self.runningOnNanoPi:
            return self.LORAaux.get_value() == 0  # lora aux pin (corresponds to pin 19)
        return False

    def GetWifiSignalStrength(self):
        if self.runningOnNanoPi:
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
        if self.runningOnChip or self.runningOnNanoPi:
            HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::GetIsShortKeyPress")

            IRQ_STATUS_3_REGADDR = 0x4a
            statusReg = self.i2cBus.read_byte_data(self.i2cAddress, IRQ_STATUS_3_REGADDR)

            #statusReg = os.popen("/usr/sbin/i2cget -f -y 0 0x34 0x4a").read()
            #shortKeyPress = int(statusReg, 16) & 0x02
            shortKeyPress = statusReg & 0x02
            return shortKeyPress > 0
        return False

    def ClearShortKeyPress(self):
        if self.runningOnChip or self.runningOnNanoPi:
            HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::ClearShortKeyPress")
            IRQ_STATUS_3_REGADDR = 0x4a
            self.i2cBus.write_byte_data(self.i2cAddress, IRQ_STATUS_3_REGADDR, 0x02)
            #os.system("sudo sh -c '/usr/sbin/i2cset -f -y 0 0x34 0x4a 0x02'")

    def ClearIRQStatus1(self):
        if self.runningOnChip or self.runningOnNanoPi:
            HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::ClearShortKeyPress")
            IRQ_STATUS_1_REGADDR = 0x48
            self.i2cBus.write_byte_data(self.i2cAddress, IRQ_STATUS_1_REGADDR, 0xFF)

    def ClearIRQStatus2(self):
        if self.runningOnChip or self.runningOnNanoPi:
            HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::ClearShortKeyPress")
            IRQ_STATUS_2_REGADDR = 0x49
            self.i2cBus.write_byte_data(self.i2cAddress, IRQ_STATUS_2_REGADDR, 0xFF)

    def ClearIRQStatus3(self):
        if self.runningOnChip or self.runningOnNanoPi:
            HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::ClearShortKeyPress")
            IRQ_STATUS_3_REGADDR = 0x4a
            self.i2cBus.write_byte_data(self.i2cAddress, IRQ_STATUS_3_REGADDR, 0xFF)
