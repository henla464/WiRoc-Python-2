from chipGPIO.chipGPIO import *
import logging
import socket
import subprocess

class HardwareAbstraction(object):
    WiRocLogger = logging.getLogger('WiRoc')
    Instance = None

    def __init__(self, typeOfDisplay):
        HardwareAbstraction.WiRocLogger.info("HardwareAbstraction::Init start")
        self.typeOfDisplay = typeOfDisplay
        self.runningOnChip = socket.gethostname() == 'chip'
        self.runningOnNanoPi = socket.gethostname() == 'nanopiair'
        f = open("../WiRocHWVersion.txt", "r")
        wirocHWVersion = f.read()
        self.wirocHWVersion = wirocHWVersion.strip()
        f.close()

    def SetupPins(self):
        if self.runningOnNanoPi:
            if self.wirocHWVersion == 'v4Rev1':
                pinModeNonXIO(64, INPUT)  # lora aux pin (corresponds to pin 19)
                pinModeNonXIO(2, OUTPUT) #lora enable pin (corresponds to pin 13)
                digitalWriteNonXIO(2, 1)
                pinModeNonXIO(17, OUTPUT)  # lora M0 pin (corresponds to pin 7 (nanopi wiki) / pin 37 (PCB footprint))
                digitalWriteNonXIO(17, 0)
            else:
                pinModeNonXIO(0, INPUT)  # lora aux pin
                pinModeNonXIO(2, OUTPUT) #lora enable pin
                digitalWriteNonXIO(2, 1)
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
            else: #OLED
                pinModeNonXIO(134, INPUT)
                pinModeNonXIO(135, OUTPUT)
                digitalWriteNonXIO(135, 1)

    def GetSISerialPorts(self):
        if self.wirocHWVersion == 'v4Rev1':
            return ['/dev/ttyS2']
        return []

    def EnableLora(self):
        # enable radio module 139;
        # with new oled design: 135
        # pin 2 for nanopiair
        if self.runningOnNanoPi:
                digitalWriteNonXIO(2, 0) #lora enable pin (corresponds to pin 13)
        elif self.runningOnChip:
            if self.typeOfDisplay == '7SEG':
                digitalWriteNonXIO(139, 0)
            else:
                digitalWriteNonXIO(135, 0)


    def DisableLora(self):
        # disable radio module 139; #with new oled design: 135
        # pin 2 for nanopiair
        if self.runningOnNanoPi:
            digitalWriteNonXIO(2, 1) #lora enable pin (corresponds to pin 13)
        elif self.runningOnChip:
            if self.typeOfDisplay == '7SEG':
                digitalWriteNonXIO(139, 1)
            else:
                digitalWriteNonXIO(135, 1)

    def GetIsTransmittingReceiving(self):
        # aux 138, with new oled design: 134
        if self.runningOnChip:
            if self.typeOfDisplay == '7SEG':
                return digitalReadNonXIO(138) == 0
            else:
                return digitalReadNonXIO(134) == 0
        elif self.runningOnNanoPi:
            if self.wirocHWVersion == 'v4Rev1':
                return digitalReadNonXIO(64) == 0  # lora aux pin (corresponds to pin 19)
            else:
                return digitalReadNonXIO(0) == 0 # lora aux pin (corresponds to pin 11)
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
            statusReg = os.popen("/usr/sbin/i2cget -f -y 0 0x34 0x4a").read()
            shortKeyPress = int(statusReg, 16) & 0x02
            return shortKeyPress > 0
        return False

    def ClearShortKeyPress(self):
        if self.runningOnChip or self.runningOnNanoPi:
            HardwareAbstraction.WiRocLogger.debug("HardwareAbstraction::ClearShortKeyPress")
            os.system("sudo sh -c '/usr/sbin/i2cset -f -y 0 0x34 0x4a 0x02'")

    def GetRFCommsSerialPorts(self):
        if self.runningOnNanoPi:
            boundResult = subprocess.run(['rfcomm'], stdout=subprocess.PIPE, check=True)
            rfComms = boundResult.stdout.decode('utf-8').strip()
            if len(rfComms) == 0:
                return []
            rfCommsArray = rfComms.split('\n')

            rfCommsSerialPortArray = ['/dev/' + rfComm.split(' ')[0][:-1] for rfComm in rfCommsArray if rfComm.split(' ')[4] == "clean" or rfComm.split(' ')[4] == "connected"]
            return rfCommsSerialPortArray
        return []