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
            if serialDevice.GetPortName() == portName:
                return serialDevice
        newInstance = SerialComputer(portName)
        SerialComputer.Instances.append(newInstance)
        return newInstance

    def __init__(self, portName):
        self.compSerial = serial.Serial()
        self.portName = portName
        self.isInitialized = False
        self.channel = None
        self.loraDataRate = None

    def GetIsInitialized(self):
        return self.isInitialized

    def GetPortName(self):
        return self.portName

    def TestConnection(self):
        wasOpened = False
        try:
            if not self.compSerial.is_open:
                logging.debug("TestConnection 1")
                self.compSerial.open()
                wasOpened = True
                logging.debug("TestConnection 2")

            if self.compSerial.is_open:
                logging.debug("TestConnection 3")
                noOfBytes = self.compSerial.in_waiting()
                logging.debug("TestConnection 4") # + str(noOfBytes)
            else:
                return False

        except Exception as ex:
            logging.error("TestConnection SI Computer, serial exception:")
            logging.error(ex)
            self.compSerial.close()
            return False

        if wasOpened:
            logging.debug("TestConnection 5")
            self.compSerial.close()
            logging.debug("TestConnection 6")

        logging.debug("TestConnection 7")
        return True

    def Init(self):
        if self.GetIsInitialized():
            return True
        logging.info("SI computer port name: " + self.portName)
        baudRate = 38400
        self.compSerial.baudrate = baudRate
        self.compSerial.port = self.portName
        if not self.compSerial.is_open:
            try:
                self.compSerial.open()
                self.isInitialized = True
            except Exception as ex:
                logging.error("SI Computer, opening serial exception:")
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
        logging.info("Sent to SI computer")
        return True

    def GetData(self):
        if self.compSerial.inWaiting() == 0:
            return None
        logging.debug("Serial computer, data to fetch")
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
                if len(receivedData) < expectedLength and self.compSerial.inWaiting() == 0:
                    logging.debug("Serial computer, sleep and wait for more bytes")
                    sleep(0.05)

        if len(receivedData) != expectedLength:
            # throw away the data, isn't correct
            logging.error("Serial computer, data not of expected length (thrown away)")
            return None

        logging.info("Serial computer message received!")
        return {"MessageType": "DATA", "Data": receivedData, "ChecksumOK": self.IsChecksumOK(receivedData)}
