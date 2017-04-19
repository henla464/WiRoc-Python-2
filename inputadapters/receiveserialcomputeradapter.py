from serialcomputer.serialcomputer import SerialComputer
import socket, os
import logging
from constants import *
from utils.utils import Utils

class ReceiveSerialComputerAdapter(object):

    Instances = []
    @staticmethod
    def CreateInstances():
        serialPort = None

        if socket.gethostname() == 'chip':
            if os.path.exists('/dev/ttyGS0'):
                serialPort = '/dev/ttyGS0'

        if serialPort is None:
            if len(ReceiveSerialComputerAdapter.Instances) == 0:
                return False
            else:
                ReceiveSerialComputerAdapter.Instances = []
                return True
        else:
            if len(ReceiveSerialComputerAdapter.Instances) == 0:
                ReceiveSerialComputerAdapter.Instances.append(
                    ReceiveSerialComputerAdapter('rcvSer1', serialPort))
                return True
            elif (ReceiveSerialComputerAdapter.Instances[0].GetSerialDevicePath() == serialPort):
                return False
            else:
                ReceiveSerialComputerAdapter.Instances[0] = ReceiveSerialComputerAdapter('rcvSer1', serialPort)
                return True

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
        return self.serialComputer.Init()

    def UpdateInfreqently(self):
        return True

    # messageData is a bytearray
    def GetData(self):
        data = self.serialComputer.GetData()
        if data is not None:
            if not data["ChecksumOK"]:
                logging.debug("ReceiveSerialComputerAdapter::GetData() Checksum not ok, message thrown away")
                return None

            replyMessage = bytearray()
            commandCode = data["Data"][1]
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
                        logging.debug("Addr: " + str(addr) + " val 0x02")
                        replyMessage.append(0x02) # control 0x02 (dec 2)
                    elif addr == 0x74: #index 10
                        logging.debug("Addr: " + str(addr) + " val 0x03")
                        replyMessage.append(0x03) # 00000011, autosend and extended protocol
                    else: #index 6, 8, 9, 11
                        logging.debug("Addr: " + str(addr) + " val 0x00")
                        replyMessage.append(0x00)
            elif commandCode == 0xF0:
                #set transfer mode
                replyMessage.append(0x03)  # length
                replyMessage.append(0x03) #station number 3E7 == 999
                replyMessage.append(0xE7)
                replyMessage.append(0x4D) #direct communication
            elif commandCode == 0x01:
                # other WiRoc replied to the I'm a WiRoc device message
                # disable charging to avoid draining the other WiRocs battery
                # remember time when charging disabled, in settings. restore in reconfigure
                logging.debug("ReceiveSerialComputerAdapter::GetData() Disable charging...")
                abc = 1
                return None
            else:
                logging.debug("ReceiveSerialComputerAdapter::GetData() Unknown command received")
                return None

            crc = Utils.CalculateCRC(replyMessage[1:])
            replyMessage.append(crc[0])  # crc1
            replyMessage.append(crc[1])  # crc0
            replyMessage.append(ETX)
            logging.debug("ReceiveSerialComputerAdapter::GetData() Received: " + str(data["Data"]) + " Sending reply message: " + str(replyMessage))
            try:
                self.serialComputer.SendData(replyMessage)
            except:
                logging.error("ReceiveSerialComputerAdapter::GetData() Error sending reply message")
        return None