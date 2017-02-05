import serial
from serialcomputer.serialcomputer import SerialComputer
import socket, os
import logging
from constants import *
from time import sleep
from utils.utils import Utils

class ReceiveSerialComputerAdapter(object):

    Instances = []
    @staticmethod
    def CreateInstances():
        serialPorts = []

        if socket.gethostname() == 'chip':
            if os.path.exists('/dev/ttyGS0'):
                serialPorts.append('/dev/ttyGS0')

        newInstances = []
        for serialDev in serialPorts:
            alreadyCreated = False
            for instance in ReceiveSerialComputerAdapter.Instances:
                if instance.GetSerialDevicePath() == serialDev:
                    alreadyCreated = True
                    newInstances.append(instance)

            if not alreadyCreated:
                newInstances.append(
                    ReceiveSerialComputerAdapter('rcvSer' + str(1 + len(newInstances)), serialDev))

                ReceiveSerialComputerAdapter.Instances = newInstances
        return ReceiveSerialComputerAdapter.Instances

    @staticmethod
    def GetTypeName():
        return "SERIAL"

    def __init__(self, instanceName, portName):
        self.instanceName = instanceName
        self.portName = portName
        self.serialComputer = SerialComputer.GetInstance(portName)

    def GetInstanceName(self):
        return self.instanceName

    def GetSerialDevicePath(self):
        return self.portName

    def GetIsInitialized(self):
        return self.serialComputer.GetIsInitialized()

    def IsChecksumOK(self, receivedData):
        calculatedCRC = Utils.CalculateCRC(receivedData[1:-3])
        crcInMessage = receivedData[-3:-1]
        return calculatedCRC == crcInMessage

    def Init(self):
        self.serialComputer.Init()

    # messageData is a bytearray
    def GetData(self):
        data = self.serialComputer.GetData()
        if data is not None:
            if not data["ChecksumOK"]:
                logging.debug("Checksum not ok, message thrown away")
                return None

            replyMessage = bytearray()
            commandCode = data["Data"][1];
            replyMessage.append(STX)  # STX
            replyMessage.append(commandCode)
            if commandCode == 0x83:
                # Get system value
                address = data["Data"][3]
                numberOfBytesRequested = data["Data"][4]
                replyMessage.append(numberOfBytesRequested+3)  # length
                replyMessage.append(0x03) #station number 3E7 == 999
                replyMessage.append(0xE7)
                replyMessage.append(address) #index 5
                for addr in range(address,address+numberOfBytesRequested):
                    if addr == 0x71: #index 7
                        logging.info("Addr: " + str(addr) + " val 0x02")
                        replyMessage.append(0x02) # control 0x02 (dec 2)
                    elif addr == 0x74: #index 10
                        logging.info("Addr: " + str(addr) + " val 0x03")
                        replyMessage.append(0x03) # 00000011, autosend and extended protocol
                    else: #index 6, 8, 9, 11
                        logging.info("Addr: " + str(addr) + " val 0x00")
                        replyMessage.append(0x00)
            elif commandCode == 0xF0:
                #set transfer mode
                replyMessage.append(0x03)  # length
                replyMessage.append(0x03) #station number 3E7 == 999
                replyMessage.append(0xE7)
                replyMessage.append(0x4D) #direct communication

            crc = Utils.CalculateCRC(replyMessage[1:])
            replyMessage.append(crc[0])  # crc1
            replyMessage.append(crc[1])  # crc0
            replyMessage.append(ETX)
            self.serialComputer.SendData(replyMessage)

        return None