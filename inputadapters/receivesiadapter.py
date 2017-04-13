from settings.settings import SettingsClass
import serial
import logging
from constants import *
from time import sleep
from utils.utils import Utils
import serial.tools.list_ports

class ReceiveSIAdapter(object):
    Instances = []
    @staticmethod
    def CreateInstances():
        portInfoList = serial.tools.list_ports.grep('10c4:800a|0525:a4aa')
        serialPorts = [portInfo.device for portInfo in portInfoList]
        newInstancesFoundOrRemoved = False
        newInstances = []
        for serialDev in serialPorts:
            alreadyCreated = False
            for instance in ReceiveSIAdapter.Instances:
                if instance.GetSerialDevicePath() == serialDev:
                    alreadyCreated = True
                    newInstances.append(instance)

            if not alreadyCreated:
                newInstancesFoundOrRemoved = True
                newInstances.append(
                    ReceiveSIAdapter('si' + str(1+len(newInstances)), serialDev))

        if len(newInstances) != len(ReceiveSIAdapter.Instances):
            newInstancesFoundOrRemoved = True

        if newInstancesFoundOrRemoved:
            ReceiveSIAdapter.Instances = newInstances
            if len(ReceiveSIAdapter.Instances) > 0:
                SettingsClass.SetReceiveSIAdapterActive(True)
            else:
                SettingsClass.SetReceiveSIAdapterActive(False)
            return True
        else:
            return False

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
        logging.debug("ReceiveSIAdapter::Init() SI Station port name: " + self.portName)
        self.siSerial.baudrate = 38400
        self.siSerial.port = self.portName
        if not self.siSerial.is_open:
            try:
                self.siSerial.open()
                logging.debug("ReceiveSIAdapter::Init() opened serial")
            except Exception as ex:
                logging.error("ReceiveSIAdapter::Init() opening serial exception:")
                logging.error(ex)
                return False

        if self.siSerial.is_open:
            #set master - mode to direct
            logging.debug("ReceiveSIAdapter::Init() serial port open")
            msdMode = bytes([0xFF, 0x02, 0x02, 0xF0, 0x01, 0x4D, 0x6D, 0x0A, 0x03])
            self.siSerial.write(msdMode)
            sleep(0.2)
            expectedLength = 3
            response = bytearray()
            startFound = False
            while self.siSerial.in_waiting > 0:
                # print("looking for stx: ", end="")
                bytesRead = self.siSerial.read(1)
                #print(bytesRead)
                if bytesRead[0] == STX:
                    startFound = True
                    if len(response) == 1:
                        # second STX found, discard
                        continue
                if startFound:
                    response.append(bytesRead[0])
                    if len(response) == 3:
                        expectedLength = response[2] + 6
                    if len(response) == expectedLength:
                        break
                    if len(response) < expectedLength and self.siSerial.in_waiting == 0:
                        logging.debug("ReceiveSIAdapter::Init() sleep and wait for more bytes")
                        sleep(0.05)
                        if self.siSerial.in_waiting == 0:
                            break

            if self.isCorrectMSModeDirectResponse(response):
                logging.info("ReceiveSIAdapter::Init() SI Station 38400 kbit/s works")
                self.isInitialized = True
                return True
            else:
                logging.info("ReceiveSIAdapter::Init() received: " + str(response))

            # something wrong, try other baudrate
            self.siSerial.close()
            self.siSerial.port = self.portName
            self.siSerial.baudrate = 4800
            self.siSerial.open()
            self.siSerial.write(msdMode)
            sleep(0.2)
            expectedLength = 3
            response = bytearray()
            startFound = False
            while self.siSerial.in_waiting > 0:
                # print("looking for stx: ", end="")
                bytesRead = self.siSerial.read(1)

                if bytesRead[0] == STX:
                    startFound = True
                    if len(response)==1:
                        #second STX found, discard
                        continue
                if startFound:
                    response.append(bytesRead[0])
                    if len(response) == 3:
                        expectedLength = response[2] + 6
                    if len(response) == expectedLength:
                        break
                    if len(response) < expectedLength and self.siSerial.in_waiting == 0:
                        logging.debug("ReceiveSIAdapter::Init() sleep and wait for more bytes")
                        sleep(0.05)
                        if self.radioSerial.in_waiting == 0:
                            break

            if self.isCorrectMSModeDirectResponse(response):
                logging.info("ReceiveSIAdapter::Init() SI Station 4800 kbit/s works")
                self.isInitialized = True
                return True
            else:
                logging.info("ReceiveSIAdapter::Init() received: " + str(response))

        logging.error("ReceiveSIAdapter::Init() could not communicate with master station")
        return False

    def UpdateInfreqently(self):
        return True

    # messageData is a bytearray
    def GetData(self):
        if self.siSerial.in_waiting == 0:
            return None
        logging.debug("ReceiveSIAdapter::GetData() Data to fetch")
        expectedLength = 3
        receivedData = bytearray()
        startFound = False
        while self.siSerial.in_waiting > 0:
            # print("looking for stx: ", end="")
            bytesRead = self.siSerial.read(1)
            if bytesRead[0] == STX:
                startFound = True
                if len(receivedData) == 1:
                    # second STX found, discard
                    continue
            if startFound:
                receivedData.append(bytesRead[0])
                if len(receivedData) == 3:
                    expectedLength = receivedData[2]+6
                if len(receivedData) == expectedLength:
                    break
                if len(receivedData) < expectedLength and self.siSerial.in_waiting == 0:
                    logging.debug("ReceiveSIAdapter::GetData() sleep and wait for more bytes")
                    sleep(0.05)

        if len(receivedData) != expectedLength:
            # throw away the data, isn't correct
            dataInHex = ''.join(format(x, '02x') for x in receivedData)
            logging.error("ReceiveSIAdapter::GetData() data not of expected length (thrown away), expected: " + str(expectedLength) + " got: " + str(len(receivedData)) + " data: " + dataInHex)
            return None

        if receivedData[1] == 0xD3:
            logging.debug("ReceiveSIAdapter::GetData() SI message received!")
            return {"MessageType": "DATA", "Data": receivedData, "ChecksumOK": self.IsChecksumOK(receivedData)}
        else:
            logging.debug("ReceiveSIAdapter::GetData() Unknown SI message received!")
            return None