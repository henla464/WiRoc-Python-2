__author__ = 'henla464'

import serial
import time
import logging
from constants import *
from datamodel.datamodel import LoraRadioMessage
from datamodel.db_helper import DatabaseHelper
from utils.utils import Utils
from settings.settings import SettingsClass
import socket
import binascii
from datetime import datetime
import errno

class LoraRadio:
    Instances = []

    ReadSettingCmd = bytes([0xAF, 0xAF,  # sync word
                              0x00, 0x00,  # id code
                              0xAF,  # header
                              0x80,  # command (sending)
                              0x02,  # command type (read)
                              0x0C,  # length (data section, from here to CS)
                              0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                              0x9B,  # CS (calculate and set)
                              0x0D, 0x0A  # end code
                              ])

    DetectAirSignalCmd = bytes([0xAF, 0xAF,  # sync word
                                0x00, 0x00,  # id code
                                0xAF,  # start code
                                0x80,  # command (sending)
                                0x23,  # command detect air signal
                                0x02,  # len
                                0x00,  # data
                                0x00,  # data
                                0xB2,  # CRC
                                0x0D, 0x0A])  # end code

    SignalDetected = bytes([0xAF, 0xAF,  # sync word
                                0x00, 0x00,  # id code
                                0xAF,  # start code
                                0x00,  # command rec
                                0x23,  # command detect air signal
                                0x02,  # len
                                0x00,  # data
                                0x00,  # data
                                0x32,  # CRC
                                0x0D, 0x0A])  # end code

    SignalNotDetected = bytes([0xAF, 0xAF,  # sync word
                            0x00, 0x00,  # id code
                            0xAF,  # start code
                            0x00,  # command rec
                            0x23,  # command detect air signal
                            0x02,  # len
                            0x01,  # data
                            0x00,  # data
                            0x33,  # CRC
                            0x0D, 0x0A])  # end code

    WriteSerialBaudRateCmd = bytes([0xAF, 0xAF,  # sync word
                                0x00, 0x00,  # id code
                                0xAF,  # start code
                                0x80,  # command (sending)
                                0x09,  # command detect air signal
                                0x02,  # len
                                0x07,  # data rate 57600
                                0x00,  # data no parity
                                0x9F,  # CRC
                                0x0D, 0x0A])  # end code

    ReadSerialBaudRateCmd = bytes([0xAF, 0xAF,  # sync word
                                    0x00, 0x00,  # id code
                                    0xAF,  # start code
                                    0x80,  # command (sending)
                                    0x0A,  # command detect air signal
                                    0x02,  # len
                                    0x00,  # data rate
                                    0x00,  # data parity
                                    0x99,  # CRC
                                    0x0D, 0x0A])  # end code

    RestartModuleCmd = bytes([0xAF, 0xAF,  # sync word
                               0x00, 0x00,  # id code
                               0xAF,  # start code
                               0x80,  # command (sending)
                               0x20,  # restart
                               0x02,  # len
                               0x00,  # data
                               0x00,  # data
                               0xAF,  # CRC
                               0x0D, 0x0A])  # end code

    RestartModuleResp = bytes([0xAF, 0xAF,  # sync word
                              0x00, 0x00,  # id code
                              0xAF,  # start code
                              0x00,  # command (sending)
                              0x20,  # restart
                              0x02,  # len
                              0x00,  # data
                              0x00,  # data
                              0x2F,  # CRC
                              0x0D, 0x0A])  # end code

    @staticmethod
    def GetInstance(portName,hardwareAbstraction):
        for loraRadio in LoraRadio.Instances:
            if loraRadio.GetPortName() == portName:
                return loraRadio
        newInstance = LoraRadio(portName, hardwareAbstraction)
        LoraRadio.Instances.append(newInstance)
        return newInstance

    def __init__(self, portName, hardwareAbstraction):
        self.radioSerial = serial.Serial()
        self.receivedMessage = LoraRadioMessage()
        self.receivedMessage2 = None
        self.portName = portName
        self.isInitialized = False
        self.channel = None
        self.loraDataRate = None
        self.loraPower = None
        self.lastMessageSentDate = None
        self.totalNumberOfMessagesSent = 0
        self.totalNumberOfAcksReceived = 0
        self.acksReceivedSinceLastMessageSent = 0
        self.runningAveragePercentageAcked = 0.5
        self.chip = False
        self.hardwareAbstraction = hardwareAbstraction

    def GetIsInitialized(self, channel, dataRate, loraPower):
        return self.isInitialized and \
               channel == self.channel and \
               loraPower == self.loraPower and \
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
    def getSettingsArray(channel, loraDataRate, loraPower):
        channelData = DatabaseHelper.get_channel(channel, loraDataRate)
        frequency = int(channelData.Frequency / 61.035)
        frequencyOne = ((frequency & 0xFF0000)>>16)
        frequencyTwo = ((frequency & 0xFF00)>>8)
        frequencyThree = (frequency & 0xFF)


        logging.debug("LoraRadio::getSettingsArray() channel: " + str(channel))
        logging.debug("LoraRadio::getSettingsArray() loradatarate: " + str(loraDataRate))
        logging.debug("LoraRadio::getSettingsArray() loraPower: " + str(loraPower))
        logging.debug("LoraRadio::getSettingsArray() rffactor: " + str(channelData.RfFactor))
        logging.debug("LoraRadio::getSettingsArray() rfBw: " + str(channelData.RfBw))
        logging.debug("LoraRadio::getSettingsArray() frequency: " + str(channelData.Frequency))

        settingsArray = bytearray([0xAF, 0xAF,    # sync word
                                   0x00, 0x00,  # id code
                                   0xAF,        # header
                                   0x80,        # command (sending)
                                   0x01,        # command type (write)
                                   0x0C,        # length (data section, from here to CS)
                                   0x07,        # baud rate (1=1200, 2=2400, 3=4800, 4=9600, 5=19200,6=38400, 7=57600)
                                   0x00,        # parity (0=no parity check, 1=odd parity, 2=even parity)
                                   frequencyOne, frequencyTwo, frequencyThree,  # frequency (The value=Frequency/61.035)
                                   channelData.RfFactor,   # rf factor (7=128, 8=256, 9=512, 10=1024, 11=2048, 12=4096)
                                   0x00,        # Mode (0=standard, 1=central, 2=node)
                                   channelData.RfBw,       # rf_bw (6=62.5k, 7=125k, 8=250k, 9=500k)
                                   0x00, 0x00,   # ID
                                   channel,        # NetID
                                   loraPower,        # RF power (0x07)
                                   0x00,        # CS (calculate and set)
                                   0x0D, 0x0A   # end code
                                   ])
        settingsArray[20] = LoraRadio.calculateCS(settingsArray[:-2])
        return settingsArray

    def getRadioSettingsReply(self):
        data = bytearray([])
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
        logging.debug("LoraRadio::getSettingsReply() response: " +  Utils.GetDataInHex(data, logging.DEBUG))
        return data

    def Disable(self):
        self.isInitialized = False
        self.radioSerial.close()
        self.hardwareAbstraction.DisableLora()

    def GetChannel(self):
        return self.channel

    def GetDataRate(self):
        return self.loraDataRate

    def WaitForSerialUpToTimeMS(self, ms):
        for i in range(int(ms/10)):
            if self.radioSerial.in_waiting > 0:
                time.sleep(0.01)
                break
            time.sleep(0.01)

    def Init(self, channel, loraDataRate, loraPower):
        logging.info("LoraRadio::Init() Port name: " + self.portName + " Channel: " + str(channel) + " LoraDataRate: " + str(loraDataRate) + " LoraPower: " + str(loraPower))
        self.hardwareAbstraction.EnableLora()
        time.sleep(0.1)

        self.channel = channel
        self.loraDataRate = loraDataRate
        self.loraPower = loraPower

        self.radioSerial.baudrate = 9600
        self.radioSerial.port = self.portName
        if not self.radioSerial.is_open:
            self.radioSerial.open()
        if self.radioSerial.is_open:
            self.radioSerial.write(LoraRadio.ReadSettingCmd)
            self.radioSerial.flush()

        self.WaitForSerialUpToTimeMS(500)
        data = self.getRadioSettingsReply()

        if len(data) == 0:
            # switch to 57600
            logging.debug("LoraRadio::Init() 9600 didn't work, change to 57600")
            self.radioSerial.close()
            self.radioSerial.baudrate = 57600
            #self.hardwareAbstraction.DisableLora()
            #time.sleep(0.2)
            #self.hardwareAbstraction.EnableLora()
            #time.sleep(0.2)
            self.radioSerial.open()
            time.sleep(2)

        if len(data) == 0:
            if self.radioSerial.is_open:
                self.radioSerial.write(LoraRadio.ReadSettingCmd)
                self.radioSerial.flush()
                self.WaitForSerialUpToTimeMS(500)
                data = self.getRadioSettingsReply()

        settingsArray = LoraRadio.getSettingsArray(channel, loraDataRate, loraPower)

        if data[8:16] == settingsArray[8:16]:
            self.isInitialized = True
            logging.info("LoraRadio::Init() Lora radio already configured correctly")
            # restart the module, regardless if we changed baud rate or not because we want the firmware version number
            self.firmwareVersion = self.RestartModule(57600)
            return True
        else:
            self.radioSerial.write(settingsArray)
            self.radioSerial.flush()
            time.sleep(0.5)
            setResponse = self.getRadioSettingsReply()
            if setResponse[8:15] == settingsArray[8:15]:
                self.isInitialized = True
                #self.hardwareAbstraction.DisableLora()
                #time.sleep(0.2)
                #self.hardwareAbstraction.EnableLora()
                logging.info("LoraRadio::Init() Now configured correctly")
                self.firmwareVersion = self.RestartModule(57600)
                return True
            else:
                self.isInitialized = False
                logging.error("LoraRadio::Init() Error configuring")
                return False

    def isSliceInList(self, listSlice, fullList):
        len_s = len(listSlice)  # so we don't recompute length of listSlice on every iteration
        return any(listSlice == fullList[i:len_s + i] for i in range(len(fullList) - len_s + 1))

    def removeSliceFromList(self, listSlice, fullList):
        len_s = len(listSlice)
        for i in range(len(fullList) - len_s + 1):
            if listSlice == fullList[i:len_s + i]:
                return fullList[0:i]+fullList[i+len_s:]
        return fullList

    def ChangeToHigherBaudRate(self):
        logging.debug("LoraRadio::ChangeToHigherBaudRate() enter: " +  Utils.GetDataInHex(LoraRadio.WriteSerialBaudRateCmd, logging.DEBUG))
        self.radioSerial.write(LoraRadio.WriteSerialBaudRateCmd)
        self.radioSerial.flush()
        self.WaitForSerialUpToTimeMS(250)
        allReceivedData = bytearray()
        while self.radioSerial.in_waiting > 0 and len(allReceivedData) < 13:
            # print("looking for stx: ", end="")
            bytesRead = self.radioSerial.read(1)
            allReceivedData.append(bytesRead[0])
            if len(allReceivedData) < 13 and self.radioSerial.in_waiting == 0:
                    logging.info("LoraRadio::ChangeToHigherBaudRate() Sleep, wait for more bytes")
                    time.sleep(0.05)
                    if self.radioSerial.in_waiting == 0:
                        break

        if len(allReceivedData) != 13:
            logging.error("LoraRadio::ChangeToHigherBaudRate() incorrect response: " + Utils.GetDataInHex(allReceivedData, logging.DEBUG))
        else:

            logging.info("LoraRadio::ChangeToHigherBaudRate() Changed to 57600 baudrate: " +  + Utils.GetDataInHex(allReceivedData, logging.DEBUG))

    def RestartModule(self, baudRateAfter):
        logging.debug("LoraRadio::RestartModule() enter: " +  Utils.GetDataInHex(LoraRadio.RestartModuleCmd, logging.DEBUG))
        self.radioSerial.write(LoraRadio.RestartModuleCmd)
        self.radioSerial.flush()
        self.WaitForSerialUpToTimeMS(200)
        allReceivedData = bytearray()
        while self.radioSerial.in_waiting > 0 and len(allReceivedData) < 13:
            # print("looking for stx: ", end="")
            bytesRead = self.radioSerial.read(1)
            allReceivedData.append(bytesRead[0])
            if len(allReceivedData) < 13 and self.radioSerial.in_waiting == 0:
                    logging.info("LoraRadio::RestartModule() Sleep, wait for more bytes")
                    time.sleep(0.05)
                    if self.radioSerial.in_waiting == 0:
                        break

        if len(allReceivedData) != 13:
            logging.error("LoraRadio::RestartModule() incorrect response: " + Utils.GetDataInHex(allReceivedData, logging.ERROR))

        self.radioSerial.baudrate = 9600
        self.WaitForSerialUpToTimeMS(2000)
        version = None
        allReceivedData = bytearray()
        try:
            while self.radioSerial.in_waiting > 0:
                bytesRead = self.radioSerial.read(1)
                allReceivedData.append(bytesRead[0])
            logging.debug("Startup output: " +  Utils.GetDataInHex(allReceivedData, logging.DEBUG))

            startUpString = allReceivedData.decode("utf-8")
            logging.info("LoraRadio Firmware: " + startUpString)
            startUpStringArr = startUpString.split(" ")
            if len(startUpStringArr) > 5:
                version = startUpStringArr[5].rstrip()
        except:
            logging.debug("Could not interpret startup string")
        self.radioSerial.baudrate = baudRateAfter
        return version


    def GetDetectAirSignal(self):
        logging.debug("LoraRadio::GetDetectAirSignal() enter")
        self.radioSerial.write(LoraRadio.DetectAirSignalCmd)
        self.radioSerial.flush()
        logging.debug("LoraRadio::GetDetectAirSignal() after flush")

        allReceivedData = bytearray()
        # wait up to 0.2 seconds for serial response to arrive
        for i in range(20):
            if self.radioSerial.in_waiting > 0:
                break
            time.sleep(0.01)
        logging.debug("LoraRadio::GetDetectAirSignal() after resp")
        while self.radioSerial.in_waiting > 0 and len(allReceivedData) < 13:
            # print("looking for stx: ", end="")
            bytesRead = self.radioSerial.read(1)
            allReceivedData.append(bytesRead[0])
            if len(allReceivedData) < 13 and self.radioSerial.in_waiting == 0:
                    logging.info("LoraRadio::GetDetectAirSignal() Sleep, wait for more bytes")
                    time.sleep(0.05)
                    if self.radioSerial.in_waiting == 0:
                        break

        # check if command reply is as expected
        if allReceivedData == LoraRadio.SignalDetected:
            logging.debug("LoraRadio::GetDetectAirSignal() Signal detected")
            return True
        if allReceivedData == LoraRadio.SignalNotDetected:
            logging.debug("LoraRadio::GetDetectAirSignal() Signal not detected")
            return False

        #If not read until no more bytes to read.
        time.sleep(0.01)
        while self.radioSerial.in_waiting > 0:
            # print("looking for stx: ", end="")
            bytesRead = self.radioSerial.read(1)
            allReceivedData.append(bytesRead[0])

        #Find and remove reply if it is within the data received. See if the remaining bytes matches a message.
        allReceivedDataMinusSignalNotDetectedReply = self.removeSliceFromList(LoraRadio.SignalNotDetected, allReceivedData)
        if (len(allReceivedDataMinusSignalNotDetectedReply) != len(allReceivedData)):
            self.receivedMessage2 = LoraRadioMessage()
            for theByte in allReceivedDataMinusSignalNotDetectedReply:
                self.receivedMessage2.AddByte(theByte)
            if not self.receivedMessage2.IsFilled() or not self.receivedMessage2.GetIsChecksumOK():
                self.receivedMessage2 = None
                if len(allReceivedDataMinusSignalNotDetectedReply) > 0:
                    logging.error("LoraRadio::GetDetectAirSignal() Signal not detected, extra bytes found but doesn't seem to be correct message")
                    logging.error("All data received: " + Utils.GetDataInHex(allReceivedData, logging.ERROR))
                else:
                    logging.error("LoraRadio::GetDetectAirSignal() Signal not detected 2")
            else:
                logging.debug("LoraRadio::GetDetectAirSignal() Signal not detected, message found also")
            return False

        allReceivedDataMinusSignalDetectedReply = self.removeSliceFromList(LoraRadio.SignalDetected, allReceivedData)
        if (len(allReceivedDataMinusSignalDetectedReply) != len(allReceivedData)):
            self.receivedMessage2 = LoraRadioMessage()
            for theByte in allReceivedDataMinusSignalDetectedReply:
                self.receivedMessage2.AddByte(theByte)
            if not self.receivedMessage2.IsFilled() or not self.receivedMessage2.GetIsChecksumOK():
                self.receivedMessage2 = None
                logging.error("LoraRadio::GetDetectAirSignal() Signal detected, extra bytes found but doesn't seem to be correct message")
                logging.error("All data received: " + Utils.GetDataInHex(allReceivedData, logging.ERROR))
            else:
                logging.debug("LoraRadio::GetDetectAirSignal() Signal detected, message found also")
            return True
        return False

    def UpdateSentStats(self):
        self.totalNumberOfMessagesSent += 1
        self.runningAveragePercentageAcked = self.runningAveragePercentageAcked*0.9 + 0.1*self.acksReceivedSinceLastMessageSent
        self.acksReceivedSinceLastMessageSent = 0

    def UpdateAcksReceivedStats(self):
        self.totalNumberOfMessagesSent += 1
        self.acksReceivedSinceLastMessageSent += 1

    # delay sending next message if we Lora module aux indicates transmit or receiving already
    def IsReadyToSend(self):
        if self.hardwareAbstraction.GetIsTransmittingReceiving():
            return False
        return True

    def IsAirSignalDetected(self):
        return False

        # read all data before sending new messages, especially important to avoid receiving mixed data when detecting air signal
        if self.radioSerial.in_waiting > 0:
            return False
        if self.firmwareVersion == "V3.6":
            return self.GetDetectAirSignal()

    def SendData(self, messageData):
        logging.debug("LoraRadio::SendData() send data: " + Utils.GetDataInHex(messageData, logging.DEBUG))
        #self.UpdateSentStats() of use?
        self.lastMessageSentDate =  time.monotonic()
        while True:
            try:
                self.radioSerial.write(messageData)
                logging.debug("after write")
                self.radioSerial.flush()
            except IOError as ioe:
                logging.error("LoraRadio::SendData() " + str(ioe))
                if ioe.errno != errno.EINTR:
                    raise
                continue
            return True

    def GetRadioData(self):
        if self.receivedMessage2 != None:
            message = self.receivedMessage2
            self.receivedMessage2 = None
            logging.info("LoraRadio::GetRadioData() received message 2!")
            return message
        if self.radioSerial.in_waiting == 0:
            return None
        logging.debug("LoraRadio::GetRadioData() data to fetch")
        startFound = False
        allReceivedData = bytearray()
        while self.radioSerial.in_waiting > 0:
            # print("looking for stx: ", end="")
            bytesRead = self.radioSerial.read(1)
            allReceivedData.append(bytesRead[0])
            if bytesRead[0] == STX:
                startFound = True
            if startFound:
                self.receivedMessage.AddByte(bytesRead[0])
                if self.receivedMessage.IsFilled():
                    break
                if not self.receivedMessage.IsFilled() and self.radioSerial.in_waiting == 0:
                    logging.info("LoraRadio::GetRadioData() Sleep, wait for more bytes")
                    time.sleep(0.05)
                    if self.radioSerial.in_waiting == 0:
                        break
            else:
                logging.debug("LoraRadio::GetRadioData() start not found")

        # reset so that a messages can be sent. The received message could be an ack that we were waiting for
        self.lastMessageSentDate = None
        logging.debug("LoraRadio::GetRadioData() received data, got: " + Utils.GetDataInHex(allReceivedData, logging.DEBUG))
        if not self.receivedMessage.IsFilled():
            # throw away the data, isn't correct
            logging.error("LoraRadio::GetRadioData() received incorrect data")
            self.receivedMessage = LoraRadioMessage()
            return None
        else:
            message = self.receivedMessage
            self.receivedMessage = LoraRadioMessage()
            #if message.GetMessageType() == LoraRadioMessage.MessageTypeLoraAck:
            #    self.UpdateAcksReceivedStats() of use?
            logging.info("LoraRadio::GetRadioData() received message!")
            return message
