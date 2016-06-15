__author__ = 'henla464'

import serial
import time
import binascii
from constants import *
from datamodel.datamodel import RadioMessageData
from datamodel.datamodel import RadioMessageSimpleAckData
from datamodel.datamodel import PunchData


class Radio:
    channels = ["A1", "B1", "C1", "D1", "E2", "F2", "G2", "H2", "I3", "J3", "K3", "L3", "A4", "B4", "C4", "D4",
                "E5", "F5", "G5", "H5", "I6", "J6", "K6", "L6"]
    slopeCoefficient = [77332.743718593, 52590.391959799, 26331.9798994975, 7132.2211055276,
                        2301.4874371859, 964.7236180905]
    m = [22, 16, 16, 15, 15, 26]

    def __init__(self, portName, radioNumber):
        self.radioSerial = serial.Serial()
        self.channel = None
        self.receivedMessage = RadioMessageData()
        self.portName = portName
        self.radioNumber = radioNumber
        self.isInitialized = False
        self.timeOfLastTestMessageSent = 0
        self.testMessageNumber = 0

    def GetRadioNumber(self):
        return self.radioNumber

    def GetIsInitialized(self):
        return self.isInitialized

    @staticmethod
    def calculateCS(dataBytes):

        sum = 0
        for item in dataBytes:
            sum += item

        return sum % 256

    @staticmethod
    def getSettingsArray(channel):
        lowest_frequency = 7204063
        frequency_diff = [ 0, 1229, 2458, 3687, 410, 1639, 2867, 4096, 819, 2048, 3277, 4506 ]
        frequency = lowest_frequency + frequency_diff[ord(channel[0])-ord('A')]
        frequencyOne = ((frequency & 0xFF0000)>>16)
        frequencyTwo = ((frequency & 0xFF00)>>8)
        frequencyThree = (frequency & 0xFF)
        speed_number = (ord(channel[1])-ord('0'))
        if speed_number == 1:
            rf_factor = 12
            rf_bw = 6
        elif speed_number == 2:
            rf_factor = 12
            rf_bw = 7
        elif speed_number == 3:
            rf_factor = 12
            rf_bw = 8
        elif speed_number == 4:
            rf_factor = 11
            rf_bw = 9
        elif speed_number == 5:
            rf_factor = 9
            rf_bw = 9
        else:  #6
            rf_factor = 7
            rf_bw = 9

        settingsArray = bytearray([0xAF, 0xAF,    # sync word
                                   0x00, 0x00,  # id code
                                   0xAF,        # header
                                   0x80,        # command (sending)
                                   0x01,        # command type (write)
                                   0x0C,        # length (data section, from here to CS)
                                   0x04,        # baud rate (1=1200, 2=2400, 3=4800, 4=9600, 5=19200,6=38400, 7=57600)
                                   0x00,        # parity (0=no parity check, 1=odd parity, 2=even parity)
                                   frequencyOne, frequencyTwo, frequencyThree,  # frequency (The value=Frequency/61.035)
                                   rf_factor,   # rf factor (7=128, 8=256, 9=512, 10=1024, 11=2048, 12=4096)
                                   0x00,        # Mode (0=standard, 1=central, 2=node)
                                   rf_bw,       # rf_bw (6=62.5k, 7=125k, 8=250k, 9=500k)
                                   0x00, 0x00,   # ID
                                   0x00,        # NetID
                                   0x07,        # RF power
                                   0x00,        # CS (calculate and set)
                                   0x0D, 0x0A   # end code
                                   ])
        settingsArray[20] = Radio.calculateCS(settingsArray[:-2])
        return settingsArray

    def getRadioSettingsReply(self):
        data = bytearray([])
        print("Radio read response: ")
        while self.radioSerial.inWaiting() > 0:
            bytesRead = self.radioSerial.read(1)
            if len(bytesRead) > 0 and bytesRead[0] == 0xAF:
                data.append(bytesRead[0])
                print(" AF")
                while self.radioSerial.inWaiting() > 0:
                    if len(data) < 23:
                        b = self.radioSerial.read(1)
                        data.append(b[0])
                        print(" ", end="")
                        print(b, end="")
                    else:
                        self.radioSerial.read(1)

                    time.sleep(2 / 1000)
                print("")
                break
        return data

    def Disable(self):
        self.isInitialized = False
        self.radioSerial.close()

    def Init(self, channel):
        print("Channel: ", end="")
        print(channel)
        self.channel = channel

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

        baudrate = 9600
        print("Baud rate: ", end="")
        print(baudrate)
        self.radioSerial.baudrate = baudrate
        self.radioSerial.port = self.portName
        if not self.radioSerial.is_open:
            self.radioSerial.open()
        if self.radioSerial.is_open:
            self.radioSerial.write(readSettingArray)

        time.sleep(1)
        data = self.getRadioSettingsReply()

        settingsArray = self.getSettingsArray(channel)

        if data[8:15] == settingsArray[8:15]:
            self.isInitialized = True
            print("Already configured correctly")
        else:
            self.radioSerial.write(settingsArray)
            time.sleep(1)
            setResponse = self.getRadioSettingsReply()
            if setResponse[8:15] == settingsArray[8:15]:
                self.isInitialized = True
                print("Now configured correctly")
            else:
                self.isInitialized = False
                print("Error configuring")

    def GetSlopeCoefficient(self):
        return self.slopeCoefficient[ord(self.channel[1])-ord('1')]

    def GetM(self):
        return self.m[ord(self.channel[1])-ord('1')]

    def SendData(self, radioMessage):
        radioMessage.UpdateChecksum()
        byteArr = radioMessage.GetByteArray()
        print(binascii.hexlify(byteArr))
        self.radioSerial.write(byteArr)


    def GetRadioData(self):
        # read until STX
        while self.receivedMessage.IsUnInitialized() and self.radioSerial.inWaiting() > 0:
            #print("looking for stx: ", end="")
            bytesRead = self.radioSerial.read(1)
            print(bytesRead)
            if bytesRead[0] == STX:
                self.receivedMessage.AddByte(bytesRead[0]) #initializes
                break

        if self.receivedMessage.IsUnInitialized():
            #print("return, still uninitialized")
            return None

        while self.radioSerial.inWaiting() > 0 and self.receivedMessage.ShouldAddMoreBytes():
            bytesRead = self.radioSerial.read(1)
            #print("read byte: ", end="")
            #print(bytesRead[0])
            self.receivedMessage.AddByte(bytesRead[0])

        if not self.receivedMessage.ShouldAddMoreBytes():
            message = self.receivedMessage
            message.radioNumber = self.radioNumber
            self.receivedMessage = RadioMessageData()
            return message

        return None

    def GetRadioDataSimpleAck(self):
        # read until STX
        while self.receivedSimpleAckMessage.IsUnInitialized() and self.radioSerial.inWaiting() > 0:
            byteRead = self.radioSerial.read(1)
            if byteRead == STX:
                self.receivedSimpleAckMessage.AddByte(byteRead) #initializes

        if self.receivedSimpleAckMessage.IsUnInitialized():
            return None

        while self.radioSerial.inWaiting() > 0 and self.receivedSimpleAckMessage.ShouldAddMoreBytes():
            byteRead = self.radioSerial.read(1)
            self.receivedSimpleAckMessage.AddByte(byteRead)

        if not self.receivedSimpleAckMessage.ShouldAddMoreBytes():
            message = self.receivedSimpleAckMessage
            self.receivedSimpleAckMessage = RadioMessageSimpleAckData()
            return message

        return None

    def SendSimpleAckMessage(self, messageNumberToAck):
        simpleAckMessage = RadioMessageSimpleAckData()
        simpleAckMessage.messageNumberToAck = messageNumberToAck
        self.SendData(simpleAckMessage)

    def GetTimeOfLastTestMessageSent(self):
        return self.timeOfLastTestMessageSent

    def SendTestMessage(self, fromNode):
        dataRecord = PunchData()
        dataRecord.siCardNumber = self.testMessageNumber
        tstMessage = RadioMessageData(PUNCH)
        tstMessage.stx = STX
        tstMessage.dataLength = dataRecord.GetSize()
        tstMessage.fromNode = fromNode
        tstMessage.messageVersion = 1
        tstMessage.dataRecordArray = [dataRecord]
        tstMessage.UpdateChecksum()
        tstMessage.dataRecordArray = [dataRecord]

        self.SendData(tstMessage)
        self.timeOfLastTestMessageSent = time.time()
        self.testMessageNumber += 1
