__author__ = 'henla464'

import serial
import time
import logging
from constants import *
from datamodel.datamodel import LoraRadioMessage
from datamodel.db_helper import DatabaseHelper
from utils.utils import Utils
from loraradio.loraparameters import LoraParameters
import struct
from settings.settings import SettingsClass
import socket
import binascii
from datetime import datetime
import errno

class LoraRadioDRF1268DS:
    Instances = []

    EnterATMode = bytes([0xFF, 0xFF,  # sync word
                              0x02,  # length
                              0x1B,  # cmd code: Enter AT
                              0x1D])  # CRC

    EnterATModeResponse = bytes([0xFF, 0xFF,  # sync word
                              0x02,  # length
                              0x1C,  # cmd code: Enter AT resp
                              0x1E])  # CRC

    Quit = bytes([0xFF, 0xFF,  # sync word
                              0x02,  # length
                              0x1D,  # cmd code: Enter AT
                              0x1F])  # CRC

    QuitResponse = bytes([0xFF, 0xFF,  # sync word
                              0x02,  # length
                              0x1E,  # cmd code: Enter AT resp
                              0x20])  # CRC

    ReadParameter = bytes([0xFF, 0xFF,  # sync word
                              0x02,  # length
                              0x01,  # cmd code: Enter AT
                              0x03])  # CRC

    Write = bytes([0xFF, 0xFF,  # sync word
                              0x23,  # length
                              0x03,  # cmd code: Write
                              0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
                              0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                              0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                              0x00, 0x00, 0x00,
                              0x20])  # CRC

    WriteResp = bytes([0xFF, 0xFF,  # sync word
                       0x02,  # length
                       0x04,  # cmd code: write resp
                       0x06])  # CRC

    ReadDataRSSI = bytes([0xFF, 0xFF,  # sync word
                                0x02, # length
                                0x0F,  # cmd code: read data RSSI
                                0x11])  # CRC

    ReadChannelRSSI = bytes([0xFF, 0xFF,  # sync word
                          0x02,  # length
                          0x11,  # cmd code: read channel RSSI
                          0x13])  # CRC

    SetID = bytes([0xFF, 0xFF,  # sync word
                          0x05,  # length
                          0x09,  # cmd code: read channel RSSI
                          0x00, 0x00, # Device ID
                          0x00,  # Net ID (WiRoc Channel)
                          0x00])  # CRC

    SetIDResp = bytes([0xFF, 0xFF,  # sync word
                       0x02,  # length
                       0x0A,  # cmd code: write resp
                       0x0C])  # CRC

    SetUART = bytes([0xFF, 0xFF,  # sync word
                          0x06,  # length
                          0x05,  # cmd code: set UART
                          0x06,  # baud rate, 0x03=9600, 0x06=57600
                          0x00,  # data bit, 0x00=8-bit
                          0x00,  # parity, 0x00=no parity
                          0x00,  # stop bit, 0x00=1 stop bit
                          0x00])  # CRC

    SetUARTResp = bytes([0xFF, 0xFF,  # sync word
                       0x02,  # length
                       0x06,  # cmd code: set uart resp
                       0x08])  # CRC

    SetRF = bytes([0xFF, 0xFF,  # sync word
                     0x0E,  # length
                     0x07,  # cmd code: set RF
                     0x00,  # spreading factor
                     0x05,  # bandwidth 0x05->31.25kHz
                     0x16,  # tx power 0x16=22dBm
                     0x00,  # code rate, 0x00->4/5
                     0x00,  # tx rate 1
                     0x00,  # tx rate 2
                     0x00,  # tx rate 3
                     0x00,  # tx rate 4
                     0x00,  # rx rate 1
                     0x00,  # rx rate 2
                     0x00,  # rx rate 3
                     0x00,  # rx rate 4
                     0x00])  # CRC

    SetRFResp = bytes([0xFF, 0xFF,  # sync word
                   0x02,  # length
                   0x08,  # cmd code: set RF resp
                   0x0A])  # CRC

    SetMode = bytes([0xFF, 0xFF,  # sync word
                   0x06,  # length
                   0x0B,  # cmd code: set Mode
                   0x00,  # work mode 0x00 NORMAL
                   0x00,  # star mode 0x00 NORMAL
                   0x00,  # wake up time ??
                   0x01,  # sleep time 0x01 1s
                   0x00])  # CRC

    SetModeResp = bytes([0xFF, 0xFF,  # sync word
                   0x02,  # length
                   0x0C,  # cmd code: set Mode resp
                   0x0E])  # CRC

    Reset = bytes([0xFF, 0xFF,  # sync word
                               0x02, # length
                               0x15,  # reset
                               0x17])  # CRC

    ResetResp = bytes([0xFF, 0xFF,  # sync word
                   0x02,  # length
                   0x16,  # reset
                   0x18])  # CRC

    @staticmethod
    def GetInstance(portName,hardwareAbstraction):
        for loraRadio in LoraRadioDRF1268DS.Instances:
            if loraRadio.GetPortName() == portName:
                return loraRadio
        newInstance = LoraRadioDRF1268DS(portName, hardwareAbstraction)
        LoraRadioDRF1268DS.Instances.append(newInstance)
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
    def addCRC(commandBytes):
        sum = 0
        for item in commandBytes[2:-1]:
            sum += item
        commandBytes[-1] = sum % 256
        return commandBytes

    def getRadioSettingsReply(self, expextedLength):
        data = bytearray([])
        while self.radioSerial.in_waiting > 0:
            bytesRead = self.radioSerial.read(1)
            if len(bytesRead) > 0 and bytesRead[0] == 0xFF:
                data.append(bytesRead[0])
                while self.radioSerial.in_waiting > 0:
                    b = self.radioSerial.read(1)
                    if len(data) < expextedLength and len(b) > 0:
                        data.append(b[0])
                    if self.radioSerial.in_waiting == 0 and len(data) < expextedLength:
                        time.sleep(2 / 1000)
                break
        logging.debug(
            "LoraRadioDRF1268DS::getRadioSettingsReply() response: " + Utils.GetDataInHex(data, logging.DEBUG))
        return data

    def enterATMode(self):
        self.radioSerial.write(LoraRadioDRF1268DS.EnterATMode)
        self.radioSerial.flush()
        correctEnterATModeResp = LoraRadioDRF1268DS.EnterATModeResponse
        enterATModeResp = self.getRadioSettingsReply(len(correctEnterATModeResp))
        return enterATModeResp == correctEnterATModeResp

    def exitATMode(self):
        self.radioSerial.write(LoraRadioDRF1268DS.Quit)
        self.radioSerial.flush()
        correctExitATModeResp = LoraRadioDRF1268DS.QuitResponse
        exitATModeResp = self.getRadioSettingsReply(len(correctExitATModeResp))
        return exitATModeResp == correctExitATModeResp

    def enterATModeAndChangeBaudRateIfRequired(self):
        logging.debug("LoraRadioDRF1268DS::changeTo57600BaudRate(): Enter")
        if self.enterATMode():
            logging.debug("LoraRadioDRF1268DS::changeTo57600BaudRate(): Already correct UART")
            return True
        else:
            # Must be 9600 so change to that for the UART link, then change module to 57600 and reset
            self.radioSerial.baudrate = 9600
            self.radioSerial.write(LoraRadioDRF1268DS.SetUART)
            self.radioSerial.flush()
            setUartResp = self.getRadioSettingsReply(len(LoraRadioDRF1268DS.SetUARTResp))
            if setUartResp == LoraRadioDRF1268DS.SetUARTResp:
                logging.debug("LoraRadioDRF1268DS::changeTo57600BaudRate(): UART parameters changed")
                self.radioSerial.write(LoraRadioDRF1268DS.Reset)
                self.radioSerial.flush()
                resetResp = self.getRadioSettingsReply(len(LoraRadioDRF1268DS.ResetResp))
                if resetResp == LoraRadioDRF1268DS.ResetResp:
                    self.radioSerial.baudrate = 57600
                    time.sleep(0.5)
                    if self.enterATMode():
                        return True

            self.radioSerial.baudrate = 57600
            return False

    def setParameters(self, channelData, channel, loraPower):
        self.radioSerial.write(LoraRadioDRF1268DS.ReadParameter)
        self.radioSerial.flush()
        expectedLength = 0x25
        readParameterResp = self.getRadioSettingsReply(expectedLength)
        readParameterResp[3] = 0x03 # write
        readParameterResp[6] = channel
        readParameterResp[11] = channelData.RfFactor
        readParameterResp[14] = loraPower
        struct.pack_into('ii', readParameterResp, 15, channelData.Frequency, channelData.Frequency)
        readParameterResp = self.addCRC(readParameterResp)
        self.radioSerial.write(readParameterResp)
        self.radioSerial.flush()
        correctWriteResp = LoraRadioDRF1268DS.WriteResp
        writeResp = self.getRadioSettingsReply(len(correctWriteResp))
        return writeResp == correctWriteResp

    def getParameters(self):
        self.radioSerial.write(LoraRadioDRF1268DS.ReadParameter)
        self.radioSerial.flush()
        expectedLength = 0x26
        readParameterResp = self.getRadioSettingsReply(expectedLength)
        if len(readParameterResp) == expectedLength:
            loraModuleParameters = LoraParameters()
            loraModuleParameters.DeviceID = struct.unpack_from("H", bytes(readParameterResp[4:]))[0]
            loraModuleParameters.NetID = readParameterResp[6]
            loraModuleParameters.BaudRate = readParameterResp[7]
            loraModuleParameters.DataBit = readParameterResp[8]
            loraModuleParameters.ParityCheck = readParameterResp[9]
            loraModuleParameters.StopBit = readParameterResp[10]
            loraModuleParameters.SpreadingFactor = readParameterResp[11]
            loraModuleParameters.Bandwidth = readParameterResp[12]
            loraModuleParameters.CodeRate = readParameterResp[13]
            loraModuleParameters.TransmitPower = readParameterResp[14]
            loraModuleParameters.TransmitFrequency = struct.unpack_from("I", bytes(readParameterResp[15:]))[0]
            loraModuleParameters.ReceiveFrequency = struct.unpack_from("I", bytes(readParameterResp[19:]))[0]
            loraModuleParameters.IDRxGainEnable = readParameterResp[23]
            loraModuleParameters.LBTEnable = readParameterResp[24]
            loraModuleParameters.RSSIEnable = readParameterResp[25]
            loraModuleParameters.SensorType = readParameterResp[26]
            loraModuleParameters.PreWakeUp = readParameterResp[27]
            loraModuleParameters.WorkMode = readParameterResp[28]
            loraModuleParameters.StarMode = readParameterResp[29]
            loraModuleParameters.CADPeak = readParameterResp[30]
            loraModuleParameters.SleepTime = readParameterResp[31]
            loraModuleParameters.StartID = struct.unpack_from("H", bytes(readParameterResp[32:]))[0]
            loraModuleParameters.EndID = struct.unpack_from("H", bytes(readParameterResp[34:]))[0]
            loraModuleParameters.TimeSlot = readParameterResp[36]
            return loraModuleParameters
        return None

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
        logging.info("LoraRadioDRF1268DS::Init() Port name: " + self.portName + " Channel: " + str(channel) + " LoraDataRate: " + str(loraDataRate) + " LoraPower: " + str(loraPower))
        self.hardwareAbstraction.EnableLora()
        time.sleep(0.1)

        self.channel = channel
        self.loraDataRate = loraDataRate
        self.loraPower = loraPower

        self.radioSerial.baudrate = 9600
        self.radioSerial.port = self.portName
        if not self.radioSerial.is_open:
            self.radioSerial.open()
        if not self.radioSerial.is_open:
            logging.error("LoraRadioDRF1268DS::Init() Serial port not open")
            return False

        try:
            #if self.enterATModeAndChangeBaudRateIfRequired():
            if self.enterATMode():
                LoraRadioDRF1268DS.LoraModuleParameters = self.getParameters()
                channelData = DatabaseHelper.get_channel(channel, loraDataRate, 'DRF1268DS')
                if channelData.Frequency ==  LoraRadioDRF1268DS.LoraModuleParameters.TransmitFrequency and \
                    channelData.Frequency == LoraRadioDRF1268DS.LoraModuleParameters.ReceiveFrequency and \
                    channelData.RfFactor == LoraRadioDRF1268DS.LoraModuleParameters.SpreadingFactor and \
                    loraPower == LoraRadioDRF1268DS.LoraModuleParameters.TransmitPower and \
                    channelData.RfBw == LoraRadioDRF1268DS.LoraModuleParameters.Bandwidth and \
                    channel == LoraRadioDRF1268DS.LoraModuleParameters.NetID:
                    self.isInitialized = True
                    logging.info("LoraRadioDRF1268DS::Init() Already correct parameters")
                    SettingsClass.SetLoraModule("DRF1268DS")
                    return True
                else:
                    if self.setParameters(channelData, channel, loraPower):
                        logging.info("LoraRadioDRF1268DS::Init() Parameters set")
                        SettingsClass.SetLoraModule("DRF1268DS")
                        self.isInitialized = True
                        return True
                    else:
                        logging.error("LoraRadioDRF1268DS::Init() Setting parameters failed")
                        self.isInitialized = False
                        return False
            else:
                logging.error("LoraRadioDRF1268DS::Init() enterATMode failed")
                return False

        finally:
            if not self.exitATMode():
                logging.error("LoraRadioDRF1268DS::Init() Could not exit ATMode")

#    def isSliceInList(self, listSlice, fullList):
#        len_s = len(listSlice)  # so we don't recompute length of listSlice on every iteration
#        return any(listSlice == fullList[i:len_s + i] for i in range(len(fullList) - len_s + 1))

#    def removeSliceFromList(self, listSlice, fullList):
#        len_s = len(listSlice)
#        for i in range(len(fullList) - len_s + 1):
#            if listSlice == fullList[i:len_s + i]:
#                return fullList[0:i]+fullList[i+len_s:]
#        return fullList

    def UpdateSentStats(self):
        self.totalNumberOfMessagesSent += 1
        self.runningAveragePercentageAcked = self.runningAveragePercentageAcked*0.9 + 0.1*self.acksReceivedSinceLastMessageSent
        self.acksReceivedSinceLastMessageSent = 0

    def UpdateAcksReceivedStats(self):
        self.totalNumberOfMessagesSent += 1
        self.acksReceivedSinceLastMessageSent += 1

    # delay sending next message if Lora module aux indicates transmit or receiving already
    def IsReadyToSend(self):
        if self.hardwareAbstraction.GetIsTransmittingReceiving():
            return False
        return True

    def IsAirSignalDetected(self): #drf1268ds returns ok or busy when sending data instead of having separate command
        return False

    def SendData(self, messageData):
        logging.debug("LoraRadioDRF1268DS::SendData() send data: " + Utils.GetDataInHex(messageData, logging.DEBUG))
        while True:
            try:
                self.radioSerial.write(messageData)
                self.radioSerial.flush()
            except IOError as ioe:
                logging.error("LoraRadioDRF1268DS::SendData() " + str(ioe))
                if ioe.errno != errno.EINTR:
                    raise
                continue
            break

        self.WaitForSerialUpToTimeMS(10)
        sendReply = self.getRadioSettingsReply(2)
        if sendReply == bytearray([0x6F, 0x6B]): #ok
            logging.debug(
                "LoraRadioDRF1268DS::SendData() Module returned ok")
            return True
        elif sendReply == bytearray([0x62, 0x75]): #bu
            logging.debug(
                "LoraRadioDRF1268DS::SendData() Module returned busy")
            self.radioSerial.read(2) #remove also 'sy'
            return False
        else:
            logging.error("LoraRadioDRF1268DS::SendData() Module returned: " + Utils.GetDataInHex(sendReply, logging.ERROR))
            return False

    def GetRadioData(self):
        if self.receivedMessage2 != None:
            message = self.receivedMessage2
            self.receivedMessage2 = None
            logging.info("LoraRadioDRF1268DS::GetRadioData() received message 2!")
            return message
        if self.radioSerial.in_waiting == 0:
            return None
        logging.debug("LoraRadioDRF1268DS::GetRadioData() data to fetch")
        startFound = False
        allReceivedData = bytearray()
        while self.radioSerial.in_waiting > 0:
            bytesRead = self.radioSerial.read(1)
            allReceivedData.append(bytesRead[0])
            if bytesRead[0] == STX:
                startFound = True
            if startFound:
                self.receivedMessage.AddByte(bytesRead[0])
                if self.receivedMessage.IsFilled():
                    break
                if not self.receivedMessage.IsFilled() and self.radioSerial.in_waiting == 0:
                    logging.info("LoraRadioDRF1268DS::GetRadioData() Sleep, wait for more bytes")
                    time.sleep(0.05)
                    if self.radioSerial.in_waiting == 0:
                        break
            else:
                logging.debug("LoraRadioDRF1268DS::GetRadioData() start not found")

        logging.debug("LoraRadioDRF1268DS::GetRadioData() received data, got: " + Utils.GetDataInHex(allReceivedData, logging.DEBUG))
        if not self.receivedMessage.IsFilled():
            # throw away the data, isn't correct
            logging.error("LoraRadioDRF1268DS::GetRadioData() received incorrect data")
            self.receivedMessage = LoraRadioMessage()
            return None
        else:
            message = self.receivedMessage
            self.receivedMessage = LoraRadioMessage()
            logging.info("LoraRadioDRF1268DS::GetRadioData() received message!")
            return message
