__author__ = 'henla464'

import threading
from typing import Self
import serial
import time
import logging
from datamodel.db_helper import DatabaseHelper, ErrorCodeData, ChannelData
from loraradio.LoraRadioMessageRS import LoraRadioMessageAckRS, LoraRadioMessageStatusRS, LoraRadioMessagePunchReDCoSRS, LoraRadioMessagePunchDoubleReDCoSRS
from utils.utils import Utils
from loraradio.loraparameters import LoraParameters
from loraradio.LoraRadioDataHandler import LoraRadioDataHandler
import struct
import errno
from chipGPIO.hardwareAbstraction import HardwareAbstraction


class LoraRadioDRF1268DS_RS:
    Instances = []
    WiRocLogger = logging.getLogger('WiRoc')

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
                              0x1D,  # cmd code: Exit AT
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
    def GetInstance(portName: str,hardwareAbstraction: HardwareAbstraction):
        for loraRadio in LoraRadioDRF1268DS_RS.Instances:
            if loraRadio.GetPortName() == portName:
                return loraRadio
        newInstance = LoraRadioDRF1268DS_RS(portName, hardwareAbstraction)
        LoraRadioDRF1268DS_RS.Instances.append(newInstance)
        return newInstance

    def __init__(self, portName, hardwareAbstraction: HardwareAbstraction):
        self.radioSerial = serial.Serial()
        self.portName = portName
        self.isInitialized = False
        self.enabled: bool | None = None
        self.channel: str | None = None
        self.loraRange: str | None = None
        self.loraPower: int | None = None
        self.codeRate: int | None = None
        self.rxGain: bool | None = None
        self.totalNumberOfMessagesSent: int = 0
        self.totalNumberOfAcksReceived: int = 0
        self.acksReceivedSinceLastMessageSent: int = 0
        self.runningAveragePercentageAcked: float = 0.5
        self.hardwareAbstraction: HardwareAbstraction = hardwareAbstraction
        self.loraRadioDataHandler: LoraRadioDataHandler = LoraRadioDataHandler(True)
        self.ackReceivedMatchingLastSentMessage: bool = True
        self.serialLock: threading.Lock = threading.Lock()

    def GetIsInitialized(self, channel: str, loraRange: str, loraPower: int, codeRate: int, rxGain: bool, enabled: bool) -> bool:
        return self.isInitialized and \
                channel == self.channel and \
                loraPower == self.loraPower and \
                loraRange == self.loraRange and \
                codeRate == self.codeRate and \
                rxGain == self.rxGain and \
                enabled == self.enabled

    def GetPortName(self) -> str:
        return self.portName

    @staticmethod
    def addCRC(commandBytes):
        sum = 0
        for item in commandBytes[2:-1]:
            sum += item
        commandBytes[-1] = sum % 256
        return commandBytes

    def getRadioReply(self, expectedLength: int) -> bytearray:
        LoraRadioDRF1268DS_RS.WiRocLogger.debug("LoraRadioDRF1268DS_RS::getRadioReply() Enter")
        data = bytearray([])
        while self.radioSerial.in_waiting > 0:
            b = self.radioSerial.read(1)
            if len(data) < expectedLength and len(b) > 0:
                data.append(b[0])
            if len(data) == expectedLength:
                break
            if self.radioSerial.in_waiting == 0 and len(data) < expectedLength:
                time.sleep(2 / 1000)
        LoraRadioDRF1268DS_RS.WiRocLogger.debug("LoraRadioDRF1268DS_RS::getRadioReply() response: " + Utils.GetDataInHex(data, logging.DEBUG))
        return data

    def getRadioSettingsReply(self, expectedLength: int) -> bytearray:
        #LoraRadioDRF1268DS_RS.WiRocLogger.debug("LoraRadioDRF1268DS_RS::getRadioSettingsReply() Enter")
        data = bytearray([])
        while self.radioSerial.in_waiting > 0:

            bytesRead = self.radioSerial.read(1)
            #LoraRadioDRF1268DS_RS.WiRocLogger.debug("LoraRadioDRF1268DS_RS::getRadioSettingsReply() Byte: " + Utils.GetDataInHex(bytesRead, logging.DEBUG))
            if len(bytesRead) > 0 and bytesRead[0] == 0xFF:
                data.append(bytesRead[0])
                while self.radioSerial.in_waiting > 0:
                    b = self.radioSerial.read(1)
                    #LoraRadioDRF1268DS_RS.WiRocLogger.debug(
                    #    "LoraRadioDRF1268DS_RS::getRadioSettingsReply() Byte: " + Utils.GetDataInHex(b, logging.DEBUG))
                    if len(data) < expectedLength and len(b) > 0:
                        data.append(b[0])
                    if self.radioSerial.in_waiting == 0 and len(data) < expectedLength:
                        time.sleep(2 / 1000)
                break
        LoraRadioDRF1268DS_RS.WiRocLogger.debug(
            "LoraRadioDRF1268DS_RS::getRadioSettingsReply() response: " + Utils.GetDataInHex(data, logging.DEBUG))
        return data

    def enterATMode(self) -> bool:
        #LoraRadioDRF1268DS_RS.WiRocLogger.debug("LoraRadioDRF1268DS_RS::enterATMode() Enter")
        self.radioSerial.write(LoraRadioDRF1268DS_RS.EnterATMode)
        self.radioSerial.flush()
        time.sleep(0.3)
        correctEnterATModeResp = LoraRadioDRF1268DS_RS.EnterATModeResponse
        enterATModeResp = self.getRadioSettingsReply(len(correctEnterATModeResp))
        if enterATModeResp == correctEnterATModeResp:
            LoraRadioDRF1268DS_RS.WiRocLogger.debug(
                "LoraRadioDRF1268DS_RS::enterATMode() Success, received " + Utils.GetDataInHex(enterATModeResp,
                                                                                              logging.DEBUG))
            return True
        else:
            LoraRadioDRF1268DS_RS.WiRocLogger.debug(
                "LoraRadioDRF1268DS_RS::enterATMode() Wrong response, expected : " + Utils.GetDataInHex(
                    correctEnterATModeResp, logging.DEBUG) + " got: " + Utils.GetDataInHex(enterATModeResp, logging.DEBUG))
            return False

    def exitATMode(self) -> bool:
        #LoraRadioDRF1268DS_RS.WiRocLogger.debug("LoraRadioDRF1268DS_RS::exitATMode() Enter")
        self.radioSerial.write(LoraRadioDRF1268DS_RS.Quit)
        self.radioSerial.flush()
        time.sleep(0.3)
        correctExitATModeResp = LoraRadioDRF1268DS_RS.QuitResponse
        exitATModeResp = self.getRadioSettingsReply(len(correctExitATModeResp))
        if exitATModeResp == correctExitATModeResp:
            LoraRadioDRF1268DS_RS.WiRocLogger.debug("LoraRadioDRF1268DS_RS::exitATMode() Success, received " + Utils.GetDataInHex(exitATModeResp, logging.DEBUG))
            return True
        else:
            LoraRadioDRF1268DS_RS.WiRocLogger.debug(
                "LoraRadioDRF1268DS_RS::exitATMode() Wrong response, expected : " + Utils.GetDataInHex(correctExitATModeResp, logging.DEBUG) + " got: " + Utils.GetDataInHex(exitATModeResp, logging.DEBUG))
            return False

    def enterATModeAndChangeBaudRateIfRequired(self) -> bool:
        LoraRadioDRF1268DS_RS.WiRocLogger.debug("LoraRadioDRF1268DS_RS::changeTo57600BaudRate(): Enter")
        if self.enterATMode():
            LoraRadioDRF1268DS_RS.WiRocLogger.debug("LoraRadioDRF1268DS_RS::changeTo57600BaudRate(): Already correct UART")
            return True
        else:
            # Must be 9600 so change to that for the UART link, then change module to 57600 and reset
            self.radioSerial.baudrate = 9600
            self.radioSerial.write(LoraRadioDRF1268DS_RS.SetUART)
            self.radioSerial.flush()
            setUartResp = self.getRadioSettingsReply(len(LoraRadioDRF1268DS_RS.SetUARTResp))
            if setUartResp == LoraRadioDRF1268DS_RS.SetUARTResp:
                LoraRadioDRF1268DS_RS.WiRocLogger.debug("LoraRadioDRF1268DS::changeTo57600BaudRate(): UART parameters changed")
                self.radioSerial.write(LoraRadioDRF1268DS_RS.Reset)
                self.radioSerial.flush()
                resetResp = self.getRadioSettingsReply(len(LoraRadioDRF1268DS_RS.ResetResp))
                if resetResp == LoraRadioDRF1268DS_RS.ResetResp:
                    self.radioSerial.baudrate = 57600
                    time.sleep(0.5)
                    if self.enterATMode():
                        return True

            self.radioSerial.baudrate = 57600
            return False

    def setParameters(self, channelData: ChannelData, channelNumber: int, loraPower: int, codeRate: int, rxGain: bool) -> bool:
        LoraRadioDRF1268DS_RS.WiRocLogger.debug("LoraRadioDRF1268DS_RS::setParameters(): Enter, read parameters")
        self.radioSerial.write(LoraRadioDRF1268DS_RS.ReadParameter)
        self.radioSerial.flush()
        time.sleep(0.2)
        expectedLength = 0x26
        readParameterResp = self.getRadioSettingsReply(expectedLength)
        readParameterResp[3] = 0x03  # write
        readParameterResp[6] = channelNumber
        readParameterResp[11] = channelData.RfFactor
        readParameterResp[12] = 0x05  # Bandwidth 31,25kHz
        readParameterResp[13] = codeRate
        readParameterResp[14] = loraPower
        if rxGain:
            readParameterResp[23] = 0x81  # ID / Rx Gain enable
        else:
            readParameterResp[23] = 0x01  # ID / Rx Gain disabled
        readParameterResp[24] = 0x01  # LBT enable
        readParameterResp[25] = 0x01  # RSSI enable
        struct.pack_into('>II', readParameterResp, 15, channelData.Frequency, channelData.Frequency)
        readParameterResp = self.addCRC(readParameterResp)
        LoraRadioDRF1268DS_RS.WiRocLogger.debug("LoraRadioDRF1268DS_RS::setParameters(): Write new parameters: " + Utils.GetDataInHex(readParameterResp, logging.DEBUG))
        self.radioSerial.write(readParameterResp)
        self.radioSerial.flush()
        time.sleep(0.5)
        correctWriteResp = LoraRadioDRF1268DS_RS.WriteResp
        writeResp = self.getRadioSettingsReply(len(correctWriteResp))
        return writeResp == correctWriteResp

    def getParameters(self) -> LoraParameters | None:
        LoraRadioDRF1268DS_RS.WiRocLogger.debug("LoraRadioDRF1268DS_RS::getParameters(): Enter, read parameters")
        self.radioSerial.write(LoraRadioDRF1268DS_RS.ReadParameter)
        self.radioSerial.flush()
        time.sleep(0.3)
        expectedLength = 0x26
        readParameterResp = self.getRadioSettingsReply(expectedLength)
        LoraRadioDRF1268DS_RS.WiRocLogger.debug("LoraRadioDRF1268DS_RS::getParameters(): got: " + str(len(readParameterResp)) + " bytes, expected: " + str(expectedLength))
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
            loraModuleParameters.TransmitFrequency = struct.unpack_from(">I", bytes(readParameterResp[15:]))[0]
            loraModuleParameters.ReceiveFrequency = struct.unpack_from(">I", bytes(readParameterResp[19:]))[0]
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
        LoraRadioDRF1268DS_RS.WiRocLogger.error("LoraRadioDRF1268DS_RS::getParameters() return None")
        return None

    #def Disable(self) -> None:
    #    self.isInitialized = False
    #    self.radioSerial.close()
    #    self.hardwareAbstraction.DisableLora()

    def GetIsEnabled(self) -> bool:
        return self.enabled

    def GetChannel(self) -> str:
        return self.channel

    def WaitForSerialUpToTimeMS(self, ms) -> None:
        for i in range(int(ms/10)):
            if self.radioSerial.in_waiting > 0:
                time.sleep(0.01)
                break
            time.sleep(0.01)

    def SetErrorCode(self, message: str):
        errorCodeData = ErrorCodeData()
        errorCodeData.Code = ErrorCodeData.ERR_LORA_CONF
        errorCodeData.Message = message
        DatabaseHelper.save_error_code(errorCodeData)

    def ClearErrorCode(self) -> None:
        # clear any lora config error code
        self.SetErrorCode("")

    def Init(self, channel: str, loraRange: str, loraPower: int, codeRate: int, rxGain: bool, enabled: bool):
        LoraRadioDRF1268DS_RS.WiRocLogger.info(
            f"LoraRadioDRF1268DS_RS::Init() Port name: {self.portName} Channel: {channel} "
            f"LoraRange {loraRange} LoraPower: {loraPower} CodeRate: {codeRate} "
            f"RxGain: {rxGain} Enabled: {enabled}")

        if enabled:
            self.hardwareAbstraction.EnableLora()
            self.enabled = enabled
        else:
            self.hardwareAbstraction.DisableLora()
            self.enabled = enabled
            return True

        self.serialLock.acquire()
        try:

            self.hardwareAbstraction.EnableLora()
            time.sleep(0.1)

            self.channel = channel
            self.loraPower = loraPower
            self.loraRange = loraRange
            self.codeRate = codeRate
            self.rxGain = rxGain

            self.radioSerial.baudrate = 9600
            self.radioSerial.port = self.portName
            if not self.radioSerial.is_open:
                self.radioSerial.open()
            if not self.radioSerial.is_open:
                LoraRadioDRF1268DS_RS.WiRocLogger.error("LoraRadioDRF1268DS_RS::Init() Serial port not open")
                return False

            newSettingsWritten = False
            try:
                if self.enterATMode():
                    LoraRadioDRF1268DS_RS.LoraModuleParameters = self.getParameters()
                    if LoraRadioDRF1268DS_RS.LoraModuleParameters is None:
                        LoraRadioDRF1268DS_RS.WiRocLogger.error("LoraRadioDRF1268DS_RS::Init() Could not get parameters")
                        self.SetErrorCode("Lora config failed")
                        return False
                    channelData = DatabaseHelper.get_channel(channel, loraRange, 'DRF1268DS')
                    if channelData.Frequency ==  LoraRadioDRF1268DS_RS.LoraModuleParameters.TransmitFrequency and \
                        channelData.Frequency == LoraRadioDRF1268DS_RS.LoraModuleParameters.ReceiveFrequency and \
                        channelData.RfFactor == LoraRadioDRF1268DS_RS.LoraModuleParameters.SpreadingFactor and \
                        loraPower == LoraRadioDRF1268DS_RS.LoraModuleParameters.TransmitPower and \
                        channelData.RfBw == LoraRadioDRF1268DS_RS.LoraModuleParameters.Bandwidth and \
                        channel == LoraRadioDRF1268DS_RS.LoraModuleParameters.NetID and \
                        codeRate == LoraRadioDRF1268DS_RS.LoraModuleParameters.CodeRate and \
                        ((rxGain and 0x81 == LoraRadioDRF1268DS_RS.LoraModuleParameters.IDRxGainEnable) or
                        (not rxGain and 0x01 == LoraRadioDRF1268DS_RS.LoraModuleParameters.IDRxGainEnable)):
                        self.isInitialized = True
                        LoraRadioDRF1268DS_RS.WiRocLogger.info("LoraRadioDRF1268DS_RS::Init() Already correct parameters")
                        self.ClearErrorCode()
                        return True
                    else:
                        LoraRadioDRF1268DS_RS.WiRocLogger.info("LoraRadioDRF1268DS_RS::Init() frequency" + str(channelData.Frequency))
                        channelNumber = int(channel.lstrip("HAM"))
                        if self.setParameters(channelData, channelNumber, loraPower, codeRate, rxGain):
                            LoraRadioDRF1268DS_RS.WiRocLogger.info("LoraRadioDRF1268DS_RS::Init() Parameters set")
                            self.isInitialized = True
                            newSettingsWritten = True
                            self.ClearErrorCode()
                            return True
                        else:
                            LoraRadioDRF1268DS_RS.WiRocLogger.error("LoraRadioDRF1268DS_RS::Init() Setting parameters failed")
                            self.SetErrorCode("Lora config failed")
                            self.isInitialized = False
                            return False
                else:
                    LoraRadioDRF1268DS_RS.WiRocLogger.error("LoraRadioDRF1268DS_RS::Init() enterATMode failed")
                    self.SetErrorCode("Lora config failed")
                    self.isInitialized = False
                    return False

            finally:
                if not newSettingsWritten: # when new settings is written then a reset/restart is done automatically
                    if not self.exitATMode():
                        LoraRadioDRF1268DS_RS.WiRocLogger.error("LoraRadioDRF1268DS_RS::Init() Could not exit ATMode")
                    self.hardwareAbstraction.DisableLora()
                    time.sleep(0.1)
                    self.hardwareAbstraction.EnableLora()
        finally:
            self.serialLock.release()

    def SetAckReceivedMatchingLastSentMessage(self, ackReceivedMatchingLastSentMsg :bool) -> None:
        # Keep track if received ack matched last sent message. If it didn't then it is likely another WiRoc
        # just sent on same channel and just received ack for a message.
        # If another WiRoc got an Ack then it is good to send now before the other WiRoc sends its next message.
        self.ackReceivedMatchingLastSentMessage = ackReceivedMatchingLastSentMsg

    def GetAckReceivedMatchingLastSentMessage(self) -> bool:
        return self.ackReceivedMatchingLastSentMessage

    def UpdateSentStats(self) -> None:
        self.totalNumberOfMessagesSent += 1
        self.runningAveragePercentageAcked = self.runningAveragePercentageAcked*0.9 + 0.1*self.acksReceivedSinceLastMessageSent
        self.acksReceivedSinceLastMessageSent = 0

    def UpdateAcksReceivedStats(self) -> None:
        self.totalNumberOfMessagesSent += 1
        self.acksReceivedSinceLastMessageSent += 1

    # delay sending next message if Lora module aux indicates transmit or receiving already
    def IsReadyToSend(self) -> bool:
        if self.hardwareAbstraction.GetIsTransmittingReceiving():
            return False
        return True

    def SendData(self, messageData: bytearray) -> bool:
        self.serialLock.acquire()
        try:
            LoraRadioDRF1268DS_RS.WiRocLogger.debug("LoraRadioDRF1268DS_RS::SendData() send data: " + Utils.GetDataInHex(messageData, logging.DEBUG))
            while True:
                try:
                    allReceivedData = bytearray()
                    while self.radioSerial.in_waiting > 0:
                        bytesRead = self.radioSerial.read(1)
                        allReceivedData.append(bytesRead[0])
                        self.loraRadioDataHandler.AddData(bytesRead[0])
                    if len(allReceivedData) > 0:
                        LoraRadioDRF1268DS_RS.WiRocLogger.info(
                            "LoraRadioDRF1268DS_RS::SendData() read this data before send: " + Utils.GetDataInHex(
                                allReceivedData,
                                logging.INFO))

                    self.radioSerial.write(messageData)
                    self.radioSerial.flush()
                except IOError as ioe:
                    LoraRadioDRF1268DS_RS.WiRocLogger.error("LoraRadioDRF1268DS_RS::SendData() " + str(ioe))
                    if ioe.errno != errno.EINTR:
                        raise
                    continue
                break

            self.WaitForSerialUpToTimeMS(1500)
            sendReply = self.getRadioReply(4)
            if sendReply == bytearray([0x6F, 0x6B, 0x0D, 0x0A]):  # ok
                LoraRadioDRF1268DS_RS.WiRocLogger.debug(
                    "LoraRadioDRF1268DS_RS::SendData() Module returned ok")
                return True
            elif sendReply == bytearray([0x62, 0x75, 0x73, 0x79]):  # busy
                LoraRadioDRF1268DS_RS.WiRocLogger.debug(
                    "LoraRadioDRF1268DS_RS::SendData() Module returned busy")
                self.radioSerial.read(2)  # remove also 'CR LF'
                return False
            else:
                LoraRadioDRF1268DS_RS.WiRocLogger.debug("LoraRadioDRF1268DS_RS::SendData() Module returned: " + Utils.GetDataInHex(sendReply, logging.ERROR))
                # Module didn't return OK / Busy, or maybe it did and another message was received first
                allReceivedData = bytearray()
                for dataByte in sendReply:
                    allReceivedData.append(dataByte)

                while self.radioSerial.in_waiting > 0:
                    bytesRead = self.radioSerial.read(1)
                    allReceivedData.append(bytesRead[0])
                # if another message was received above then we may need to wait a bit for the ok/busy to be received. (noticed in logs)
                self.WaitForSerialUpToTimeMS(10)
                while self.radioSerial.in_waiting > 0:
                    bytesRead = self.radioSerial.read(1)
                    allReceivedData.append(bytesRead[0])

                if allReceivedData[-4:] == bytearray([0x6F, 0x6B, 0x0D, 0x0A]): # ok
                    LoraRadioDRF1268DS_RS.WiRocLogger.debug(
                        "LoraRadioDRF1268DS_RS::SendData() 2 Module returned ok")
                    for dataByte in allReceivedData[:-4]:
                        self.loraRadioDataHandler.AddData(dataByte)
                    return True
                elif allReceivedData[-6:] == bytearray([0x62, 0x75, 0x73, 0x79, 0x0d, 0x0a]):  # busy
                    LoraRadioDRF1268DS_RS.WiRocLogger.debug(
                        "LoraRadioDRF1268DS_RS::SendData() 2 Module returned busy")
                    for dataByte in allReceivedData[:-6]:
                        self.loraRadioDataHandler.AddData(dataByte)
                    return False
                # todo: check if the message matches a message type, a punch or ack
                # an real example: 857fc37fc37fc3
                else:
                    # could not make sens of data so let's ignore it
                    LoraRadioDRF1268DS_RS.WiRocLogger.error(
                        "LoraRadioDRF1268DS_RS::SendData() Module returned allReceivedData: " + Utils.GetDataInHex(allReceivedData,
                                                                                                                   logging.ERROR))
                    return False
        finally:
            self.serialLock.release()

    def GetRadioData(self) -> LoraRadioMessageAckRS | LoraRadioMessageStatusRS | LoraRadioMessagePunchReDCoSRS | LoraRadioMessagePunchDoubleReDCoSRS | None:
        self.serialLock.acquire()
        try:
            if self.radioSerial.in_waiting == 0 and len(self.loraRadioDataHandler.DataReceived) == 0:
                return None
            LoraRadioDRF1268DS_RS.WiRocLogger.debug("LoraRadioDRF1268DS_RS::GetRadioData() data to fetch")
            allReceivedData = bytearray()
            # Let's wait a little so that the full message is available to be read from serial.
            time.sleep(2 / 100)
            while self.radioSerial.in_waiting > 0:
                bytesRead = self.radioSerial.read(1)
                allReceivedData.append(bytesRead[0])
                self.loraRadioDataHandler.AddData(bytesRead[0])

            LoraRadioDRF1268DS_RS.WiRocLogger.debug("LoraRadioDRF1268DS_RS::GetRadioData() data fetched: " + Utils.GetDataInHex(allReceivedData, logging.DEBUG))

            msg = self.loraRadioDataHandler.GetMessage()

            if msg is None:
                LoraRadioDRF1268DS_RS.WiRocLogger.debug("LoraRadioDRF1268DS_RS::GetRadioData() No message found")

            return msg
        finally:
            self.serialLock.release()