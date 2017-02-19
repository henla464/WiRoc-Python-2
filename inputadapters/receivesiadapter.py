from settings.settings import SettingsClass
import serial
import pyudev
import logging
from constants import *
from time import sleep
from utils.utils import Utils

class ReceiveSIAdapter(object):
    Instances = []
    @staticmethod
    def CreateInstances():
        serialPorts = []
        #https://github.com/dhylands/usb-ser-mon/blob/master/find_port.py
        uDevContext = pyudev.Context()
        for device in uDevContext.list_devices(subsystem='tty'):
            if 'ID_VENDOR_ID' in device:
                if device['ID_VENDOR_ID'].lower() == '10c4' and \
                                device['ID_MODEL_ID'].lower() == '800a':
                    serialPorts.append(device.device_node)
                elif device['ID_VENDOR_ID'].lower() == '0525' and \
                                device['ID_MODEL_ID'].lower() == 'a4aa':
                    serialPorts.append(device.device_node)

        newInstances = []
        for serialDev in serialPorts:
            alreadyCreated = False
            for instance in ReceiveSIAdapter.Instances:
                if instance.GetSerialDevicePath() == serialDev:
                    alreadyCreated = True
                    newInstances.append(instance)

            if not alreadyCreated:
                newInstances.append(
                    ReceiveSIAdapter('si' + str(1+len(newInstances)), serialDev))

        ReceiveSIAdapter.Instances = newInstances
        if len(ReceiveSIAdapter.Instances) > 0:
            SettingsClass.SetReceiveSIAdapterActive(True)
        else:
            SettingsClass.SetReceiveSIAdapterActive(False)
        return ReceiveSIAdapter.Instances

    @staticmethod
    def GetTypeName():
        return "SI"

    def __init__(self, instanceName, portName):
        self.instanceName = instanceName
        self.portName = portName
        self.siSerial = serial.Serial()
        self.isInitialized = False

    def GetInstanceName(self):
        return self.instanceName

    def GetSerialDevicePath(self):
        return self.portName

    def GetIsInitialized(self):
        return self.isInitialized

    def IsChecksumOK(self, receivedData):
        calculatedCRC = Utils.CalculateCRC(receivedData[1:-3])
        crcInMessage = receivedData[-3:-1]
        return calculatedCRC == crcInMessage

    def isCorrectMSModeDirectResponse(self, data):
        return len(data) == 9 and data[0] == STX and data[5] == 0x4D

    def Init(self):
        if self.GetIsInitialized() and self.siSerial.is_open:
            return True
        logging.info("SI Station port name: " + self.portName)
        baudRate = 38400
        self.siSerial.baudrate = baudRate
        self.siSerial.port = self.portName
        if not self.siSerial.is_open:
            try:
                self.siSerial.open()
            except Exception as ex:
                logging.error("SI Station, opening serial exception:")
                logging.error(ex)
                return False

        if self.siSerial.is_open:
            #set master - mode to direct

            msdMode = bytes([0xFF, 0x02, 0xF0, 0x01, 0x4D, 0x6D, 0x0A, 0x03])
            self.siSerial.write(msdMode)
            sleep(0.1)
            response = bytearray()
            while self.siSerial.inWaiting() > 0:
                bytesRead = self.siSerial.read(1)
                response.append(bytesRead[0])

            startIndex = response.find(bytearray(bytes([STX])))
            if startIndex >= 0 and self.isCorrectMSModeDirectResponse(response[startIndex:]):
                logging.info("SI Station 38400 kbit/s works")
                self.isInitialized = True
                return True


            # something wrong, try other baudrate
            self.siSerial.close()
            baudRate = 4800
            self.siSerial.port = self.portName
            self.siSerial.baudrate = baudRate
            self.siSerial.open()
            self.siSerial.write(msdMode)
            sleep(0.1)
            response = bytearray()
            while self.siSerial.inWaiting() > 0:
                bytesRead = self.siSerial.read(1)
                response.append(bytesRead[0])

            startIndex = response.find(bytearray(bytes([STX])))
            if startIndex >= 0 and self.isCorrectMSModeDirectResponse(response[startIndex:]):
                logging.info("SI Station 4800 kbit/s works")
                self.isInitialized = True
                return True

        logging.error("SI Station, could not communicate with master station")
        return False

    # messageData is a bytearray
    def GetData(self):
        if self.siSerial.inWaiting() == 0:
            return None
        logging.debug("SI Station, data to fetch")
        expectedLength = 3
        receivedData = bytearray()
        startFound = False
        while self.siSerial.inWaiting() > 0:
            # print("looking for stx: ", end="")
            bytesRead = self.siSerial.read(1)
            if bytesRead[0] == STX:
                startFound = True
            if startFound:
                receivedData.append(bytesRead[0])
                if len(receivedData) == 3:
                    expectedLength = receivedData[2]+6
                if len(receivedData) < expectedLength and self.siSerial.inWaiting() == 0:
                    logging.debug("SI Station, sleep and wait for more bytes")
                    sleep(0.05)

        if len(receivedData) != expectedLength:
            # throw away the data, isn't correct
            dataInHex = ''.join(format(x, '02x') for x in receivedData)
            logging.error("SI Station, data not of expected length (thrown away), expected: " + str(expectedLength) + " got: " + str(len(receivedData)) + " data: " + dataInHex)
            return None

        logging.info("SI message received!")
        return {"MessageType": "DATA", "Data": receivedData, "ChecksumOK": self.IsChecksumOK(receivedData)}