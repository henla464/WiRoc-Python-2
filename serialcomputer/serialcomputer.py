__author__ = 'henla464'

import serial
from time import sleep
from utils.utils import Utils
import logging
from constants import *

class SerialComputer:
    Instances = []

    @staticmethod
    def GetInstance(portName):
        for serialDevice in SerialComputer.Instances:
            logging.debug(serialDevice.GetPortName() + "==" + portName)
            if serialDevice.GetPortName() == portName:
                return serialDevice
        newInstance = SerialComputer(portName)
        SerialComputer.Instances.append(newInstance)
        return newInstance

    def __init__(self, portName):
        self.compSerial = serial.Serial()
        self.portName = portName
        self.isInitialized = False

    def GetIsInitialized(self):
        return self.isInitialized

    def GetPortName(self):
        return self.portName

    def TestConnection(self):
        wasOpened = False
        if not self.compSerial.is_open:
            self.compSerial.baudrate = 38400
            self.compSerial.port = self.portName
            self.compSerial.writeTimeout = 0.01
            self.compSerial.open()
            wasOpened = True

        try:
            if self.compSerial.is_open:
                logging.debug("SerialComputer::TestConnection() before write byte: " + self.portName)
                self.compSerial.write(bytes([0x41]))
                logging.debug("SerialComputer::TestConnection() after write byte: " + self.portName) # + str(noOfBytes)
                if wasOpened:
                    self.compSerial.close()
                return True
        except serial.serialutil.SerialTimeoutException as timeOutEx:
            logging.error("SerialComputer::TestConnection() serial exception 1:")
            logging.error(timeOutEx)
        except Exception as ex:
            logging.error("SerialComputer::TestConnection() serial exception 2:")
            logging.error(ex)

        if wasOpened:
            self.compSerial.close()

        self.isInitialized = False
        return False

    def Init(self):
        if self.GetIsInitialized():
            return True
        logging.info("SerialComputer::Init() Computer port name: " + self.portName)
        baudRate = 38400
        if not self.compSerial.is_open:
            try:
                self.compSerial.baudrate = baudRate
                self.compSerial.port = self.portName
                self.compSerial.writeTimeout = 0.01
                self.compSerial.open()
                self.isInitialized = True
            except Exception as ex:
                logging.error("SerialComputer::Init(), opening serial exception:")
                logging.error(ex)
                return False
        return True

    def IsChecksumOK(self, receivedData):
        calculatedCRC = Utils.CalculateCRC(receivedData[1:-3])
        crcInMessage = receivedData[-3:-1]
        return calculatedCRC == crcInMessage

    def SendData(self, messageData):
        #print(binascii.hexlify(messageData))
        self.compSerial.write(messageData)
        try:
            if self.compSerial.is_open:
                self.compSerial.write(messageData)
                return True
            else:
                logging.error("SerialComputer::SendData() Serial port not open")
                return False
        except serial.serialutil.SerialTimeoutException as timeOutEx:
            logging.error("SerialComputer::SendData() serial exception 1:")
            logging.error(timeOutEx)
            return False
        except Exception as ex:
            logging.error("SerialComputer::SendData() serial exception 2:")
            logging.error(ex)
            return False

    def GetData(self):
        if not self.GetIsInitialized():
            return None
        if self.compSerial.inWaiting() == 0:
            return None
        logging.debug("SerialComputer::GetData() data to fetch")
        expectedLength = 3
        receivedData = bytearray()
        startFound = False
        while self.compSerial.inWaiting() > 0:
            # print("looking for stx: ", end="")
            bytesRead = self.compSerial.read(1)
            if bytesRead[0] == STX:
                startFound = True
            if startFound:
                receivedData.append(bytesRead[0])
                if len(receivedData) == 2:
                    if receivedData[0] == receivedData[1]:
                        # Double STX sent, remove first
                        receivedData = receivedData[1:]
                if len(receivedData) == 3:
                    expectedLength = receivedData[2] + 6
                if len(receivedData) == expectedLength:
                    break
                if len(receivedData) < expectedLength and self.compSerial.inWaiting() == 0:
                    logging.debug("SerialComputer::GetData() sleep and wait for more bytes")
                    sleep(0.05)
                    if self.compSerial.inWaiting() == 0:
                        break

        if len(receivedData) != expectedLength:
            # throw away the data, isn't correct
            dataInHex = ''.join(format(x, '02x') for x in receivedData)
            logging.error("SerialComputer::GetData() Data not of expected length (thrown away), expected: " + str(expectedLength) + " got: " + str(len(receivedData)) + " data: " + dataInHex)
            return None

        logging.info("SerialComputer::GetData() Message received!")
        return {"MessageType": "DATA", "Data": receivedData, "ChecksumOK": self.IsChecksumOK(receivedData)}
