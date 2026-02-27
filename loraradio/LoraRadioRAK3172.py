__author__ = 'henla464'

import threading
import serial
import time
import logging
from datamodel.db_helper import DatabaseHelper, ErrorCodeData, ChannelData
from loraradio.LoraRadioMessageRS import (LoraRadioMessageAckRS, LoraRadioMessageStatusRS, LoraRadioMessageStatus2RS,
                                          LoraRadioMessagePunchReDCoSRS, LoraRadioMessagePunchDoubleReDCoSRS)
from loraradio.ReturnStatus import ReturnStatus
from utils.utils import Utils
from loraradio.LoraParametersRAK3172 import LoraParametersRAK3172
from loraradio.LoraRadioDataHandler import LoraRadioDataHandler
import errno
from chipGPIO.hardwareAbstraction import HardwareAbstraction


class LoraRadioRAK3172:
    Instances = []
    WiRocLogger = logging.getLogger('WiRoc')

    LoraModuleParameters: LoraParametersRAK3172 = None

    # Send Data
    SendLORADataCmd = "ATC+SEND={data}\r"
    SendLORADataCmd_ExpectedResponseStart1 = "OK"
    SendLORADataCmd_ExpectedResponseStart2 = "BU"

    # Receive Data
    ReceiveLORADataCmd = "ATC+REC=?\r"
    ReceiveLORADataCmd_ExpectedResponseStart1 = "OK"
    ReceiveLORADataCmd_ExpectedResponseNoDataStart1 = "EM"
    # OK<binary data>
    # EM

    # Get all LORA P2P parameters
    ViewLORAP2PParametersCmd = "ATC+P2P=?\r"
    ViewLORAP2PParametersCmd_ExpectedResponseStart = "ATC+P2P="
    # AT+P2P=<Frequency>:<Spreading Factor>:<Bandwidth>:<Code Rate>:<Preamble Length>:<TX Power>:<low data rate optimize>:<crc on>:<payload length>
    # Frequency in Hz ( 150000000 - 600000000 )
    # SF = {6, 7, 8, 9, 10, 11, 12}
    # Bandwidth {0=125, 1=250, 2=500, 3=7.8, 4=10.4, 5=15.63, 6=20.83, 7=31.25, 8=41.67, 9=62.5}
    # CR = {4/5=0, 4/6=1, 4/7=2, 4/8=3}
    # Preamble Length = {2-65535}
    # TX Power = {5-22}
    # Low data rate optimize {0=off, 1=on}
    # CRC on {0=off, 1=on}
    # RxGain {0=off, 1=on}
    # drf1268dsCompatMode {0=off, 1=on} will netid when sending ack (and disregard netid when calculating hash)
    # sendAck {0=off, 1=on}
    # payloadLength {0 = explicit header with length, 1-255 = no header, fixed length payload}

    # Set all LORA P2P parameters (same format as above)
    SetLORAP2PParametersCmd = "ATC+P2P={frequency}:{spreadingfactor}:{bandwidth}:{coderate}:{preamblelength}:{txpower}:{lowdatarateoptimize}:{crcon}:{rxgain}:{drf1268dscompatmode}:{sendack}:{payloadlength}\r"
    SetLORAP2PParametersCmd_ExpectedResponseStart = "OK"

    @staticmethod
    def GetInstance(portName: str, hardwareAbstraction: HardwareAbstraction):
        for loraRadio in LoraRadioRAK3172.Instances:
            if loraRadio.GetPortName() == portName:
                return loraRadio
        newInstance = LoraRadioRAK3172(portName, hardwareAbstraction)
        LoraRadioRAK3172.Instances.append(newInstance)
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
        self.CRCOn: bool | None = None
        self.rxGain: bool | None = None
        self.drf1268dsCompatMode: bool | None = None
        self.sendAck: bool | None = None

        self.totalNumberOfMessagesSent: int = 0
        self.totalNumberOfAcksReceived: int = 0
        self.acksReceivedSinceLastMessageSent: int = 0
        self.runningAveragePercentageAcked: float = 0.5
        self.hardwareAbstraction: HardwareAbstraction = hardwareAbstraction
        self.loraRadioDataHandler: LoraRadioDataHandler = LoraRadioDataHandler(2, 1, 1)
        self.ackReceivedMatchingLastSentMessage: bool = True
        self.serialLock: threading.Lock = threading.Lock()

    def GetIsInitialized(self, channel: str, loraRange: str, loraPower: int, codeRate: int, crcOn: bool, rxGain: bool,
                         drf1268dsCompatMode: bool, sendAck: bool, enabled: bool) -> bool:
        LoraRadioRAK3172.WiRocLogger.verbose(f"channel {channel} {self.channel}")
        LoraRadioRAK3172.WiRocLogger.verbose(f"loraRange {loraRange} {self.loraRange}")
        LoraRadioRAK3172.WiRocLogger.verbose(f"loraPower {loraPower} {self.loraPower}")
        LoraRadioRAK3172.WiRocLogger.verbose(f"CodeRate {codeRate} {self.codeRate}")
        LoraRadioRAK3172.WiRocLogger.verbose(f"CRCOn {crcOn} {self.CRCOn}")
        LoraRadioRAK3172.WiRocLogger.verbose(f"RxGain {rxGain} {self.rxGain}")
        LoraRadioRAK3172.WiRocLogger.verbose(f"drf1268dsCompatMode {drf1268dsCompatMode} {self.drf1268dsCompatMode}")
        LoraRadioRAK3172.WiRocLogger.verbose(f"sendAck {sendAck} {self.sendAck}")
        LoraRadioRAK3172.WiRocLogger.verbose(f"enabled {enabled} {self.enabled}")
        LoraRadioRAK3172.WiRocLogger.verbose(f"isInitialized {self.isInitialized}")

        return self.isInitialized and \
            channel == self.channel and \
            loraPower == self.loraPower and \
            loraRange == self.loraRange and \
            codeRate == self.codeRate and \
            rxGain == self.rxGain and \
            crcOn == self.CRCOn and \
            drf1268dsCompatMode == self.drf1268dsCompatMode and \
            sendAck == self.sendAck and \
            enabled == self.enabled

    def GetPortName(self) -> str:
        return self.portName

    @staticmethod
    def addCRC(commandBytes):
        crcSum = 0
        for item in commandBytes[2:-1]:
            crcSum += item
        commandBytes[-1] = crcSum % 256
        return commandBytes

    def getRadioReply(self, expectedLength: int) -> bytearray:
        LoraRadioRAK3172.WiRocLogger.debug("LoraRadioRAK3172::getRadioReply() Enter")
        time.sleep(0.01)
        data = bytearray([])
        while self.radioSerial.in_waiting > 0:
            b = self.radioSerial.read(1)
            if len(b) > 0:
                data.append(b[0])
            if self.radioSerial.in_waiting == 0 and len(data) < expectedLength:
                time.sleep(2 / 1000)
                if self.radioSerial.in_waiting == 0:
                    break
        LoraRadioRAK3172.WiRocLogger.debug(
            "LoraRadioRAK3172::getRadioReply() response: " + Utils.GetDataInHex(data, logging.DEBUG))
        return data

    def setParameters(self, channelData: ChannelData, channelNumber: int, loraPower: int, codeRate: int, CRCOn: bool,
                      rxGain: bool, drf1268dsCompatMode: bool, sendAck: bool, preambleLength: int) -> bool:
        # {frequency}:{spreadingfactor}:{bandwidth}:{coderate}:{preamblelength}:{txpower}:{lowdatarateoptimize}:{crcon}:{rxgain}:{drf1268dsCompatMode}:{sendAck}:{payloadlength}
        setParameters: str = LoraRadioRAK3172.SetLORAP2PParametersCmd.format(frequency=str(channelData.Frequency),
                                                                             spreadingfactor=str(channelData.RfFactor),
                                                                             bandwidth=str(channelData.RfBw),
                                                                             coderate=str(codeRate),
                                                                             preamblelength=str(preambleLength),
                                                                             txpower=str(loraPower),
                                                                             lowdatarateoptimize=("1" if channelData.LowDatarateOptimize else "0"),
                                                                             crcon=("1" if CRCOn else "0"),
                                                                             rxgain=("1" if rxGain else "0"),
                                                                             drf1268dscompatmode=("1" if drf1268dsCompatMode else "0"),
                                                                             sendack=("1" if sendAck else "0"),
                                                                             payloadlength="0"
                                                                             )

        LoraRadioRAK3172.WiRocLogger.debug(f"LoraRadioRAK3172::setParameters(): {setParameters}")
        self.radioSerial.write(setParameters.encode('ascii'))
        self.radioSerial.flush()
        self.WaitForSerialUpToTimeMS(200)
        expectedLengthAtLeast = 4
        readParameterResp = self.getRadioReply(expectedLengthAtLeast)
        return readParameterResp.startswith(
            LoraRadioRAK3172.SetLORAP2PParametersCmd_ExpectedResponseStart.encode('ascii'))

    def getParameters(self) -> LoraParametersRAK3172 | None:
        LoraRadioRAK3172.WiRocLogger.debug("LoraRadioRAK3172::getParameters(): Enter, read parameters")
        self.radioSerial.write(LoraRadioRAK3172.ViewLORAP2PParametersCmd.encode('ascii'))
        self.radioSerial.flush()
        self.WaitForSerialUpToTimeMS(200)
        expectedLengthAtLeast = 33
        readParameterResp = self.getRadioReply(expectedLengthAtLeast)
        readParameterRespStr = readParameterResp.decode('ascii').rstrip()
        LoraRadioRAK3172.WiRocLogger.debug("LoraRadioRAK3172::getParameters(): got: " + readParameterRespStr)
        if len(readParameterResp) >= expectedLengthAtLeast:
            loraModuleParameters = LoraParametersRAK3172()
            parameters = readParameterRespStr[8:].split(':')
            loraModuleParameters.Frequency = int(parameters[0])
            loraModuleParameters.SpreadingFactor = int(parameters[1])
            loraModuleParameters.Bandwidth = int(parameters[2])
            loraModuleParameters.CodeRate = int(parameters[3])
            loraModuleParameters.PreambleLength = int(parameters[4])
            loraModuleParameters.TransmitPower = int(parameters[5])
            loraModuleParameters.LowDataRateOptimize = (int(parameters[6]) > 0)
            loraModuleParameters.CRCOn = (int(parameters[7]) > 0)
            loraModuleParameters.RxGain = (int(parameters[8]) > 0)
            loraModuleParameters.Drf1268dsCompatMode = (int(parameters[9]) > 0)
            loraModuleParameters.SendAck = (int(parameters[10]) > 0)
            loraModuleParameters.PayloadLength = int(parameters[11])
            return loraModuleParameters
        else:
            LoraRadioRAK3172.WiRocLogger.debug(
                "LoraRadioRAK3172::getParameters(): got: " + readParameterRespStr + ", expected at least: " + str(
                    expectedLengthAtLeast) + " bytes")

        LoraRadioRAK3172.WiRocLogger.error("LoraRadioRAK3172::getParameters() return None")
        return None

    def GetIsEnabled(self) -> bool:
        return self.enabled

    def GetChannel(self) -> str:
        return self.channel

    def WaitForSerialUpToTimeMS(self, ms) -> None:
        for i in range(int(ms / 10)):
            if self.radioSerial.in_waiting > 0:
                time.sleep(0.01)
                break
            time.sleep(0.01)

    def SetErrorCode(self, code: str, message: str):
        errorCodeData = ErrorCodeData()
        errorCodeData.Code = code
        errorCodeData.Message = message
        DatabaseHelper.save_error_code(errorCodeData)

    def ClearErrorCode(self, code: str) -> None:
        # clear any lora config error code
        self.SetErrorCode(code, "")

    def enableListenMode(self) -> bool:
        listenWithoutTimeoutAndAllowTransmission = LoraRadioRAK3172.ReceiveLORADataCmd.format(timeout="65533").encode("ascii")
        self.radioSerial.write(listenWithoutTimeoutAndAllowTransmission)
        self.radioSerial.flush()
        self.WaitForSerialUpToTimeMS(200)
        expectedLengthAtLeast = 2
        readParameterResp = self.getRadioReply(expectedLengthAtLeast)
        return readParameterResp.startswith(
            LoraRadioRAK3172.ReceiveLORADataCmd_ExpectedResponseStart1.encode('ascii'))

    def cancelListenMode(self) -> bool:
        listenWithoutTimeoutAndAllowTransmission = LoraRadioRAK3172.ReceiveLORADataCmd.format(timeout="0").encode("ascii")
        self.radioSerial.write(listenWithoutTimeoutAndAllowTransmission)
        self.radioSerial.flush()
        self.WaitForSerialUpToTimeMS(200)
        expectedLengthAtLeast = 2
        readParameterResp = self.getRadioReply(expectedLengthAtLeast)
        return readParameterResp.startswith(
            LoraRadioRAK3172.ReceiveLORADataCmd_ExpectedResponseStart1.encode('ascii'))

    def Init(self, channel: str, loraRange: str, loraPower: int, codeRate: int, crcOn: bool, rxGain: bool,
             drf1268dsCompatMode: bool, sendAck: bool, enabled: bool):
        LoraRadioRAK3172.WiRocLogger.info(
            f"LoraRadioRAK3172::Init() Port name: {self.portName} Channel: {channel} "
            f"LoraRange {loraRange} LoraPower: {loraPower} CodeRate: {codeRate} "
            f"RxGain {rxGain} drf1268dsCompatMode {drf1268dsCompatMode} "
            f"sendAck {sendAck} Enabled: {enabled}")

        self.channel = channel
        self.loraPower = loraPower
        self.loraRange = loraRange
        self.codeRate = codeRate
        self.CRCOn = crcOn
        self.rxGain = rxGain
        self.drf1268dsCompatMode = drf1268dsCompatMode  # no change of radio config, adds netid to message in senddata
        self.sendAck = sendAck
        preambleLength: int = 8

        if enabled:
            self.hardwareAbstraction.EnableLora()
            self.enabled = enabled
        else:
            self.hardwareAbstraction.DisableLora()
            self.enabled = enabled
            self.isInitialized = True
            return True

        self.serialLock.acquire()
        try:

            self.hardwareAbstraction.EnableLora()
            time.sleep(0.1)

            self.radioSerial.baudrate = 115200
            self.radioSerial.bytesize = serial.EIGHTBITS
            self.radioSerial.parity = serial.PARITY_NONE
            self.radioSerial.stopbits = serial.STOPBITS_ONE
            self.radioSerial.port = self.portName
            if not self.radioSerial.is_open:
                self.radioSerial.open()
            if not self.radioSerial.is_open:
                self.isInitialized = False
                LoraRadioRAK3172.WiRocLogger.error("LoraRadioRAK3172::Init() Serial port not open")
                self.SetErrorCode(ErrorCodeData.ERR_LORA_MODULE_COM, "Lora mod. comm")
                return False

            newSettingsWritten = False
            try:
                LoraRadioRAK3172.LoraModuleParameters = self.getParameters()
                if LoraRadioRAK3172.LoraModuleParameters is None:
                    self.isInitialized = False
                    LoraRadioRAK3172.WiRocLogger.error("LoraRadioRAK3172::Init() Could not get parameters")
                    self.SetErrorCode(ErrorCodeData.ERR_LORA_CONF, "Lora config failed")
                    return False
                channelData = DatabaseHelper.get_channel(channel, loraRange, 'RAK3172')
                LoraRadioRAK3172.WiRocLogger.verbose(f"Freq {channelData.Frequency} {LoraRadioRAK3172.LoraModuleParameters.Frequency} {channelData.Frequency == LoraRadioRAK3172.LoraModuleParameters.Frequency}")
                LoraRadioRAK3172.WiRocLogger.verbose(f"RfFactor {channelData.RfFactor} {LoraRadioRAK3172.LoraModuleParameters.SpreadingFactor} {channelData.RfFactor == LoraRadioRAK3172.LoraModuleParameters.SpreadingFactor}")
                LoraRadioRAK3172.WiRocLogger.verbose(f"loraPower {loraPower} {LoraRadioRAK3172.LoraModuleParameters.TransmitPower} {loraPower == LoraRadioRAK3172.LoraModuleParameters.TransmitPower}")
                LoraRadioRAK3172.WiRocLogger.verbose(f"RfBw {channelData.RfBw} {LoraRadioRAK3172.LoraModuleParameters.Bandwidth} {channelData.RfBw == LoraRadioRAK3172.LoraModuleParameters.Bandwidth}")
                LoraRadioRAK3172.WiRocLogger.verbose(f"CodeRate {codeRate} {LoraRadioRAK3172.LoraModuleParameters.CodeRate} {codeRate == LoraRadioRAK3172.LoraModuleParameters.CodeRate}")
                LoraRadioRAK3172.WiRocLogger.verbose(f"LowDatarateOptimize {channelData.LowDatarateOptimize} {LoraRadioRAK3172.LoraModuleParameters.LowDataRateOptimize} {channelData.LowDatarateOptimize == LoraRadioRAK3172.LoraModuleParameters.LowDataRateOptimize}")
                LoraRadioRAK3172.WiRocLogger.verbose(f"CRCOn {crcOn} {LoraRadioRAK3172.LoraModuleParameters.CRCOn} {crcOn == LoraRadioRAK3172.LoraModuleParameters.CRCOn}")
                LoraRadioRAK3172.WiRocLogger.verbose(f"RxGain {rxGain} {LoraRadioRAK3172.LoraModuleParameters.RxGain} {rxGain == LoraRadioRAK3172.LoraModuleParameters.RxGain}")
                LoraRadioRAK3172.WiRocLogger.verbose(f"drf1268dsCompatMode {drf1268dsCompatMode} {LoraRadioRAK3172.LoraModuleParameters.Drf1268dsCompatMode} {drf1268dsCompatMode == LoraRadioRAK3172.LoraModuleParameters.Drf1268dsCompatMode}")
                LoraRadioRAK3172.WiRocLogger.verbose(f"sendAck {sendAck} {LoraRadioRAK3172.LoraModuleParameters.SendAck} {sendAck == LoraRadioRAK3172.LoraModuleParameters.SendAck}")

                if (channelData.Frequency == LoraRadioRAK3172.LoraModuleParameters.Frequency and
                        channelData.RfFactor == LoraRadioRAK3172.LoraModuleParameters.SpreadingFactor and
                        loraPower == LoraRadioRAK3172.LoraModuleParameters.TransmitPower and
                        channelData.RfBw == LoraRadioRAK3172.LoraModuleParameters.Bandwidth and
                        codeRate == LoraRadioRAK3172.LoraModuleParameters.CodeRate and
                        channelData.LowDatarateOptimize == LoraRadioRAK3172.LoraModuleParameters.LowDataRateOptimize and
                        crcOn == LoraRadioRAK3172.LoraModuleParameters.CRCOn and
                        rxGain == LoraRadioRAK3172.LoraModuleParameters.RxGain and
                        drf1268dsCompatMode == LoraRadioRAK3172.LoraModuleParameters.Drf1268dsCompatMode and
                        sendAck == LoraRadioRAK3172.LoraModuleParameters.SendAck and
                        preambleLength == LoraRadioRAK3172.LoraModuleParameters.PreambleLength):
                    LoraRadioRAK3172.WiRocLogger.info("LoraRadioRAK3172::Init() Already correct parameters")
                    self.isInitialized = True
                    return True
                else:
                    channelNumber = int(channel.lstrip("HAM"))
                    if self.setParameters(channelData, channelNumber, loraPower, codeRate, crcOn, rxGain, drf1268dsCompatMode, sendAck, preambleLength):
                        LoraRadioRAK3172.WiRocLogger.info("LoraRadioRAK3172::Init() Parameters set")
                        self.isInitialized = True
                        newSettingsWritten = True
                        return True
                    else:
                        LoraRadioRAK3172.WiRocLogger.error("LoraRadioRAK3172::Init() Setting parameters failed")
                        self.SetErrorCode(ErrorCodeData.ERR_LORA_CONF, "Lora config failed")
                        self.isInitialized = False
                        return False
            finally:
                if not newSettingsWritten:  # when new settings is written then a reset/restart is done automatically
                    self.hardwareAbstraction.DisableLora()
                    time.sleep(0.1)
                    self.hardwareAbstraction.EnableLora()
        finally:
            self.serialLock.release()

    def SetAckReceivedMatchingLastSentMessage(self, ackReceivedMatchingLastSentMsg: bool) -> None:
        # Keep track if received ack matched last sent message. If it didn't then it is likely another WiRoc
        # just sent on same channel and just received ack for a message.
        # If another WiRoc got an Ack then it is good to send now before the other WiRoc sends its next message.
        self.ackReceivedMatchingLastSentMessage = ackReceivedMatchingLastSentMsg

    def GetAckReceivedMatchingLastSentMessage(self) -> bool:
        return self.ackReceivedMatchingLastSentMessage

    def UpdateSentStats(self) -> None:
        self.totalNumberOfMessagesSent += 1
        self.runningAveragePercentageAcked = self.runningAveragePercentageAcked * 0.9 + 0.1 * self.acksReceivedSinceLastMessageSent
        self.acksReceivedSinceLastMessageSent = 0

    def UpdateAcksReceivedStats(self) -> None:
        self.totalNumberOfMessagesSent += 1
        self.acksReceivedSinceLastMessageSent += 1

    # delay sending next message if Lora module aux indicates transmit or receiving already
    def IsReadyToSend(self) -> bool:
        if self.hardwareAbstraction.GetIsTransmittingReceiving():
            return False
        return True

    def SendData(self, messageData: bytearray) -> ReturnStatus:
        self.serialLock.acquire()
        try:
            LoraRadioRAK3172.WiRocLogger.debug(
                "LoraRadioRAK3172::SendData() send data: " + Utils.GetDataInHex(messageData, logging.DEBUG))
            while True:
                try:
                    # Module will only send data when requested, so shouldn't have any data to read
                    while self.radioSerial.in_waiting > 0:
                        bytesRead = self.radioSerial.read(1)
                        LoraRadioRAK3172.WiRocLogger.error(
                            "LoraRadioRAK3172::SendData() Bytes received before send " + Utils.GetDataInHex(bytesRead,
                                                                                                            loggingLevel=logging.ERROR))

                    channelNumber = int(self.channel.lstrip("HAM"))

                    data = bytearray([channelNumber]) + messageData if self.drf1268dsCompatMode else messageData
                    messageDataWithNetID = Utils.GetDataInHexUpperCase(data)

                    messageString = LoraRadioRAK3172.SendLORADataCmd.format(data=messageDataWithNetID)
                    self.radioSerial.write(messageString.encode("ascii"))
                    self.radioSerial.flush()
                except IOError as ioe:
                    LoraRadioRAK3172.WiRocLogger.error("LoraRadioRAK3172::SendData() " + str(ioe))
                    if ioe.errno != errno.EINTR:
                        raise
                    continue
                break

            self.WaitForSerialUpToTimeMS(100)
            sendReply = self.getRadioReply(2)
            if sendReply.decode("ascii").startswith(LoraRadioRAK3172.SendLORADataCmd_ExpectedResponseStart1):  # ok
                LoraRadioRAK3172.WiRocLogger.debug("LoraRadioRAK3172::SendData() Module returned ok")
                if self.radioSerial.in_waiting >= 2:
                    self.radioSerial.read(2) # remove also 'CR LF'
                return ReturnStatus.SENT
            elif sendReply.decode("ascii") == "BU":  # busy
                LoraRadioRAK3172.WiRocLogger.debug("LoraRadioRAK3172::SendData() Module returned busy")
                if self.radioSerial.in_waiting >= 2:
                    self.radioSerial.read(2)  # remove also 'CR LF'
                return ReturnStatus.BUSY
            else:
                LoraRadioRAK3172.WiRocLogger.debug(
                    "LoraRadioRAK3172::SendData() Module returned: " + Utils.GetDataInHex(sendReply, logging.ERROR))
                # Module didn't return OK / Busy. Clear the receive buffer (although it should be empty)
                while self.radioSerial.in_waiting > 0:
                    bytesRead = self.radioSerial.read(1)
                    LoraRadioRAK3172.WiRocLogger.error(
                        "LoraRadioRAK3172::SendData() Module didn't return OK but has more bytes: " + Utils.GetDataInHex(
                            bytesRead,
                            loggingLevel=logging.ERROR))
                return ReturnStatus.OTHER
        finally:
            self.serialLock.release()

    def GetRadioData(
            self) -> LoraRadioMessageAckRS | LoraRadioMessageStatusRS | LoraRadioMessageStatus2RS | LoraRadioMessagePunchReDCoSRS | LoraRadioMessagePunchDoubleReDCoSRS | None:
        self.serialLock.acquire()
        try:
            if self.hardwareAbstraction.GetLORAIRQValue():
                allReceivedData = bytearray()
                # Let's wait a little so that the full message is available to be read from serial.
                self.radioSerial.write(LoraRadioRAK3172.ReceiveLORADataCmd.encode("ascii"))
                self.WaitForSerialUpToTimeMS(100)
                while self.radioSerial.in_waiting > 0:
                    bytesRead = self.radioSerial.read(1)
                    allReceivedData.append(bytesRead[0])

                returnStatus = allReceivedData[0:2]
                if returnStatus == "EM".encode("ascii"):
                    # No data to fetch
                    return None
                elif returnStatus == "OK".encode("ascii"):
                    if len(allReceivedData) < 6:
                        LoraRadioRAK3172.WiRocLogger.debug(
                            "LoraRadioRAK3172::GetRadioData() data fetched, too short: " + Utils.GetDataInHex(allReceivedData,
                                                                                                   loggingLevel=logging.DEBUG))
                        return None
                    # remove OK
                    receivedMsgData = allReceivedData[2:]
                    # remove CR LF
                    if receivedMsgData[-1] == 0x0A:
                        receivedMsgData = receivedMsgData[0:-1]
                    if receivedMsgData[-1] == 0x0D:
                        receivedMsgData = receivedMsgData[0:-1]
                    if self.drf1268dsCompatMode:
                        # remove NetID (drf1268ds sends a netid, set as the channelnumber)
                        receivedMsgData = receivedMsgData[1:]

                    # The Lora module adds two RSSI bytes, 1 SNR bytea and a Status byte
                    # They are handled in loraRadioDataHandler and added to the message
                    # Status. Bit 0-6: 0=Rx Done, 1=rx timeout 2=rx error ie crc error
                    # Status Bit 7 = 1 Ack sent

                    self.loraRadioDataHandler.AddData(receivedMsgData)
                    LoraRadioRAK3172.WiRocLogger.debug("LoraRadioRAK3172::GetRadioData() data fetched: " + Utils.GetDataInHex(receivedMsgData,loggingLevel=logging.DEBUG))

                msg = self.loraRadioDataHandler.GetMessage()

                if msg is None:
                    LoraRadioRAK3172.WiRocLogger.debug("LoraRadioRAK3172::GetRadioData() No message found")

                return msg
            return None
        finally:
            self.serialLock.release()
