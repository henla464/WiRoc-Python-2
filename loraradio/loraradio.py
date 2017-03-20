__author__ = 'henla464'

import serial
import time
import logging
from constants import *
from datamodel.datamodel import LoraRadioMessage
from datamodel.db_helper import DatabaseHelper
from chipGPIO.chipGPIO import *
import socket

class LoraRadio:
    Instances = []

    @staticmethod
    def GetInstance(portName):
        for loraRadio in LoraRadio.Instances:
            if loraRadio.GetPortName() == portName:
                return loraRadio
        newInstance = LoraRadio(portName)
        LoraRadio.Instances.append(newInstance)
        return newInstance

    def __init__(self, portName):
        self.radioSerial = serial.Serial()
        self.receivedMessage = LoraRadioMessage()
        self.portName = portName
        self.isInitialized = False
        self.channel = None
        self.loraDataRate = None

    def GetIsInitialized(self, channel, dataRate):
        return self.isInitialized and \
               channel == self.channel and \
               dataRate == self.loraDataRate

    def GetPortName(self):
        return self.portName

    @staticmethod
    def calculateCS(dataBytes):
        sum = 0
        for item in dataBytes:
            sum += item
        return sum % 256

    @staticmethod
    def getSettingsArray(channel, loraDataRate):
        channelData = DatabaseHelper.mainDatabaseHelper.get_channel(channel, loraDataRate)
        frequency = int(channelData.Frequency / 61.035)
        frequencyOne = ((frequency & 0xFF0000)>>16)
        frequencyTwo = ((frequency & 0xFF00)>>8)
        frequencyThree = (frequency & 0xFF)


        logging.debug("LoraRadio::getSettingsArray() channel: " + str(channel))
        logging.debug("LoraRadio::getSettingsArray() loradatarate: " + str(loraDataRate))
        logging.debug("LoraRadio::getSettingsArray() rffactor: " + str(channelData.RfFactor))
        logging.debug("LoraRadio::getSettingsArray() rfBw: " + str(channelData.RfBw))

        settingsArray = bytearray([0xAF, 0xAF,    # sync word
                                   0x00, 0x00,  # id code
                                   0xAF,        # header
                                   0x80,        # command (sending)
                                   0x01,        # command type (write)
                                   0x0C,        # length (data section, from here to CS)
                                   0x04,        # baud rate (1=1200, 2=2400, 3=4800, 4=9600, 5=19200,6=38400, 7=57600)
                                   0x00,        # parity (0=no parity check, 1=odd parity, 2=even parity)
                                   frequencyOne, frequencyTwo, frequencyThree,  # frequency (The value=Frequency/61.035)
                                   channelData.RfFactor,   # rf factor (7=128, 8=256, 9=512, 10=1024, 11=2048, 12=4096)
                                   0x00,        # Mode (0=standard, 1=central, 2=node)
                                   channelData.RfBw,       # rf_bw (6=62.5k, 7=125k, 8=250k, 9=500k)
                                   0x00, 0x00,   # ID
                                   0x00,        # NetID
                                   0x07,        # RF power
                                   0x00,        # CS (calculate and set)
                                   0x0D, 0x0A   # end code
                                   ])
        settingsArray[20] = LoraRadio.calculateCS(settingsArray[:-2])
        return settingsArray

    def getRadioSettingsReply(self):
        data = bytearray([])
        logging.debug("LoraRadio::getSettingsArray() LoraRadio settings reply response: ")
        while self.radioSerial.inWaiting() > 0:
            bytesRead = self.radioSerial.read(1)
            if len(bytesRead) > 0 and bytesRead[0] == 0xAF:
                data.append(bytesRead[0])
                while self.radioSerial.inWaiting() > 0:
                    if len(data) < 23:
                        b = self.radioSerial.read(1)
                        data.append(b[0])
                    else:
                        self.radioSerial.read(1)

                    time.sleep(2 / 1000)
                break
        logging.debug("LoraRadio::getSettingsArray() " + str(data))
        return data

    def Disable(self):
        self.isInitialized = False
        self.radioSerial.close()
        digitalWriteNonXIO(139, 1)  # disable radio module

    def GetChannel(self):
        return self.channel

    def GetDataRate(self):
        return self.loraDataRate

    def Init(self, channel, loraDataRate):
        logging.info("LoraRadio::Init() Port name: " + self.portName + " Channel: " + str(channel) + " LoraDataRate: " + str(loraDataRate))
        if socket.gethostname() == 'chip':
            digitalWriteNonXIO(139, 0) #enable radio module
        self.channel = channel
        self.loraDataRate = loraDataRate

        readSettingArray = bytes([0xAF, 0xAF, # sync word
                                  0x00, 0x00, # id code
                                  0xAF,       # header
                                  0x80,       # command (sending)
                                  0x02,       # command type (read)
                                  0x0C,       # length (data section, from here to CS)
                                  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                                  0x9B,       # CS (calculate and set)
                                  0x0D, 0x0A  # end code
                                  ])

        baudRate = 9600
        self.radioSerial.baudrate = baudRate
        self.radioSerial.port = self.portName
        if not self.radioSerial.is_open:
            self.radioSerial.open()
        if self.radioSerial.is_open:
            self.radioSerial.write(readSettingArray)

        time.sleep(0.5)
        data = self.getRadioSettingsReply()

        settingsArray = LoraRadio.getSettingsArray(channel, loraDataRate)

        if data[8:16] == settingsArray[8:16]:
            self.isInitialized = True
            logging.info("LoraRadio::Init() Lora radio already configured correctly")
            return True
        else:
            self.radioSerial.write(settingsArray)
            time.sleep(0.1)
            setResponse = self.getRadioSettingsReply()
            if setResponse[8:15] == settingsArray[8:15]:
                self.isInitialized = True
                digitalWriteNonXIO(139, 1) # disable/enable to make the setting stick
                time.sleep(0.2)
                digitalWriteNonXIO(139, 0)
                logging.info("LoraRadio::Init() Now configured correctly")
                return True
            else:
                self.isInitialized = False
                logging.error("LoraRadio::Init() Error configuring")
                return False

    def SendData(self, messageData):
        #print(binascii.hexlify(messageData))
        self.radioSerial.write(messageData)
        return True

    def GetRadioData(self):
        if self.radioSerial.inWaiting() == 0:
            return None
        logging.debug("LoraRadio::GetRadioData() data to fetch")
        startFound = False
        while self.radioSerial.inWaiting() > 0:
            # print("looking for stx: ", end="")
            bytesRead = self.radioSerial.read(1)
            if bytesRead[0] == STX:
                startFound = True
            if startFound:
                self.receivedMessage.AddByte(bytesRead[0])
                if not self.receivedMessage.IsFilled() and self.radioSerial.inWaiting() == 0:
                    logging.info("LoraRadio::GetRadioData() Sleep, wait for more bytes")
                    time.sleep(0.05)

        if not self.receivedMessage.IsFilled():
            # throw away the data, isn't correct
            self.receivedMessage = LoraRadioMessage()
            logging.error("LoraRadio::GetRadioData() received incorrect data")
            return None
        else:
            message = self.receivedMessage
            self.receivedMessage = LoraRadioMessage()
            logging.info("LoraRadio::GetRadioData() received message!")
            return message
