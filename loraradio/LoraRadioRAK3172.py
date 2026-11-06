__author__ = 'henla464'

import threading
import serial
import time
import logging
from datamodel.db_helper import DatabaseHelper, ErrorCodeData, ChannelData
from datamodel.datamodel import SettingData
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

    # Above the worst-case RAK3172 airtime in TimeOnAirData (8950 ms, SF12/bw7/cr4 double punch)
    # so a real transmission is never cut short.
    StaleBusyTimeoutS: float = 12.0

    # Send Data
    SendLORADataCmd = "ATC+SEND={data}\r"
    # Mesh: destination prefix, 0 = toward root/default, 2..15 = downlink to that node (root only)
    SendLORADataCmdWithDest = "ATC+SEND={dest}:{data}\r"
    SendLORADataCmd_ExpectedResponseStart1 = "OK"
    SendLORADataCmd_ExpectedResponseStart2 = "BU"

    # Mesh state: enabled:isroot:ownaddr:txq:state:alloc:parent:hops:cost:neighbours:epoch:overhead:ackms:standby
    ViewMeshStateCmd = "ATC+MESHSTATE=?\r"
    ViewMeshStateCmd_ExpectedResponseStart = "ATC+MESHSTATE="

    # Mesh topology: addr:parent:deviceId[:neigh=cost,...] rows joined by |
    ViewMeshTopologyCmd = "ATC+MESHTOPO=?\r"
    ViewMeshTopologyCmd_ExpectedResponseStart = "ATC+MESHTOPO="

    # Receive Data
    ReceiveLORADataCmd = "ATC+REC=?\r"
    ReceiveLORADataCmd_ExpectedResponseStart1 = "OK"
    ReceiveLORADataCmd_ExpectedResponseNoDataStart1 = "EM"
    # OK<binary data>
    # EM

    # Get all LORA P2P parameters
    ViewLORAP2PParametersCmd = "ATC+P2PM=?\r"
    ViewLORAP2PParametersCmd_ExpectedResponseStart = "ATC+P2PM="
    # AT+P2PM=<runtime selector>:<Frequency>:<Spreading Factor>:<Bandwidth>:<Code Rate>:<Preamble Length>:<TX Power>:<low data rate optimize>:<crc on>:<rx gain>:<drf1268ds compat>:<send ack>:<payload length>:<mesh on>:<active root>:<standby root>:<node device id>
    # runtime selector {0=store in flash config, 1=runtime config}
    # Frequency in Hz ( 150000000 - 960000000 )
    # SF = {5..12, mesh designed for 5..8}
    # Bandwidth {0=125, 1=250, 2=500, 3=7.8, 4=10.4, 5=15.63, 6=20.83, 7=31.25}
    # CR = {0=4/4, 1=4/5, 2=4/6, 3=4/7, 4=4/8}
    # Preamble Length = {2-65535}
    # TX Power = {5-22}
    # Low data rate optimize {0=off, 1=on}
    # CRC on {0=off, 1=on}
    # RxGain {0=off, 1=on}
    # drf1268dsCompatMode {0=off, 1=on} will netid when sending ack (and disregard netid when calculating hash)
    # sendAck {0=off, 1=on}
    # payloadLength {0 = explicit header with length, 1-255 = no header, fixed length payload}
    # mesh on {0=off, 1=on}, active root {0/1}, standby root {0/1}, node device id = 12 hex chars (required when mesh fields present)

    # Set all LORA P2P parameters (same format as above)
    SetLORAP2PParametersCmd = "ATC+P2PM=0:{frequency}:{spreadingfactor}:{bandwidth}:{coderate}:{preamblelength}:{txpower}:{lowdatarateoptimize}:{crcon}:{rxgain}:{drf1268dscompatmode}:{sendack}:{payloadlength}:{meshenabled}:{activeroot}:{standbyroot}:{devid}\r"
    SetLORAP2PParametersCmd_ExpectedResponseStart = "OK"

    # Feature query: <p2p>:<widechannels>:<narrowchannels>:<mesh>, 1/0 each, more fields may be appended
    ViewFeaturesCmd = "ATC+FEATURES=?\r"
    ViewFeaturesCmd_ExpectedResponseStart = "ATC+FEATURES="

    # Legacy commands, for RAK3172 modules with the old (main/master) firmware that has no mesh support.
    # They are only used when ATC+P2PM is answered with AT_COMMAND_NOT_FOUND.
    LegacyViewLORAP2PParametersCmd = "ATC+P2P=?\r"
    LegacyViewLORAP2PParametersCmd_ExpectedResponseStart = "ATC+P2P="
    LegacySetLORAP2PParametersCmd = "ATC+P2P={frequency}:{spreadingfactor}:{bandwidth}:{coderate}:{preamblelength}:{txpower}:{lowdatarateoptimize}:{crcon}:{rxgain}:{drf1268dscompatmode}:{sendack}:{payloadlength}\r"

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
        #self.CRCOn: bool | None = None
        self.rxGain: bool | None = None
        self.drf1268dsCompatMode: bool | None = None
        self.sendAck: bool | None = None
        self.meshEnabled: bool = False
        self.meshActiveRoot: bool = False
        self.meshStandbyRoot: bool = False
        self.meshDeviceID: str = ""
        # False once the module answered that it doesn't know ATC+P2PM (old main/master firmware)
        self.meshFirmwareSupported: bool | None = None
        # srcaddr of the last frame delivered by the module, used to route a root's app ack downlink
        self.lastReceivedSrcAddr: int = 0

        self.totalNumberOfMessagesSent: int = 0
        self.totalNumberOfAcksReceived: int = 0
        self.acksReceivedSinceLastMessageSent: int = 0
        self.runningAveragePercentageAcked: float = 0.5
        self.hardwareAbstraction: HardwareAbstraction = hardwareAbstraction
        self.loraRadioDataHandler: LoraRadioDataHandler = LoraRadioDataHandler(2, 1, 1)
        self.ackReceivedMatchingLastSentMessage: bool = True
        self.serialLock: threading.Lock = threading.Lock()
        self.busySince: float | None = None
        self.staleBusyLogged: bool = False

    def GetIsInitialized(self, channel: str, loraRange: str, loraPower: int, codeRate: int, rxGain: bool,
                         drf1268dsCompatMode: bool, sendAck: bool, enabled: bool,
                         meshEnabled: bool = False, meshActiveRoot: bool = False, meshDeviceID: str = "",
                         meshStandbyRoot: bool = False) -> bool:
        LoraRadioRAK3172.WiRocLogger.verbose(f"channel {channel} {self.channel}")
        LoraRadioRAK3172.WiRocLogger.verbose(f"loraRange {loraRange} {self.loraRange}")
        LoraRadioRAK3172.WiRocLogger.verbose(f"loraPower {loraPower} {self.loraPower}")
        LoraRadioRAK3172.WiRocLogger.verbose(f"CodeRate {codeRate} {self.codeRate}")
        #LoraRadioRAK3172.WiRocLogger.verbose(f"CRCOn {crcOn} {self.CRCOn}")
        LoraRadioRAK3172.WiRocLogger.verbose(f"RxGain {rxGain} {self.rxGain}")
        LoraRadioRAK3172.WiRocLogger.verbose(f"drf1268dsCompatMode {drf1268dsCompatMode} {self.drf1268dsCompatMode}")
        LoraRadioRAK3172.WiRocLogger.verbose(f"sendAck {sendAck} {self.sendAck}")
        LoraRadioRAK3172.WiRocLogger.verbose(f"meshEnabled {meshEnabled} {self.meshEnabled}")
        LoraRadioRAK3172.WiRocLogger.verbose(f"meshActiveRoot {meshActiveRoot} {self.meshActiveRoot}")
        LoraRadioRAK3172.WiRocLogger.verbose(f"meshStandbyRoot {meshStandbyRoot} {self.meshStandbyRoot}")
        LoraRadioRAK3172.WiRocLogger.verbose(f"meshDeviceID {meshDeviceID} {self.meshDeviceID}")
        LoraRadioRAK3172.WiRocLogger.verbose(f"enabled {enabled} {self.enabled}")
        LoraRadioRAK3172.WiRocLogger.verbose(f"isInitialized {self.isInitialized}")

        return self.isInitialized and \
            channel == self.channel and \
            loraPower == self.loraPower and \
            loraRange == self.loraRange and \
            codeRate == self.codeRate and \
            rxGain == self.rxGain and \
            drf1268dsCompatMode == self.drf1268dsCompatMode and \
            sendAck == self.sendAck and \
            meshEnabled == self.meshEnabled and \
            meshActiveRoot == self.meshActiveRoot and \
            meshStandbyRoot == self.meshStandbyRoot and \
            meshDeviceID == self.meshDeviceID and \
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

    @staticmethod
    def GetEffectiveMeshFlags(meshActiveRoot: bool, meshStandbyRoot: bool, moduleIsRoot: bool,
                              switchedFromRoot: bool) -> tuple[bool, bool]:
        # In standby mode the firmware owns the election: a promoted standby (module is root) must
        # survive re-inits (channel change, restart) without being demoted, unless the user just
        # switched this device from MESHROOT to MESHSTANDBYROOT.
        if meshStandbyRoot and not switchedFromRoot and moduleIsRoot:
            return True, False
        return meshActiveRoot, meshStandbyRoot

    @staticmethod
    def BuildLORAP2PParametersCmd(channelData: ChannelData, loraPower: int, codeRate: int,
                                 rxGain: bool, drf1268dsCompatMode: bool, sendAck: bool, preambleLength: int,
                                 meshEnabled: bool = False, meshActiveRoot: bool = False,
                                 meshDeviceID: str = "", meshStandbyRoot: bool = False) -> str:
        if len(meshDeviceID) != 12 or not all(c in '0123456789abcdefABCDEF' for c in meshDeviceID):
            # a config value must never inject extra AT command separators
            meshDeviceID = ""
        # Mesh framing is incompatible with the DRF1268DS netid prefix, so compat mode is forced off
        # while mesh is enabled. sendack is passed through; the mesh firmware ignores it (its acks
        # are link-layer and never reach the host).
        return LoraRadioRAK3172.SetLORAP2PParametersCmd.format(frequency=str(channelData.Frequency),
                                                               spreadingfactor=str(channelData.SpreadingFactor),
                                                               bandwidth=str(channelData.RfBw),
                                                               coderate=str(codeRate),
                                                               preamblelength=str(preambleLength),
                                                               txpower=str(loraPower),
                                                               lowdatarateoptimize=("1" if channelData.LowDatarateOptimize else "0"),
                                                               crcon=("1" if channelData.CRCOn else "0"),
                                                               rxgain=("1" if rxGain else "0"),
                                                               drf1268dscompatmode=("1" if drf1268dsCompatMode and not meshEnabled else "0"),
                                                               sendack=("1" if sendAck else "0"),
                                                               payloadlength="0",
                                                               meshenabled=("1" if meshEnabled else "0"),
                                                               activeroot=("1" if meshEnabled and meshActiveRoot and not meshStandbyRoot else "0"),
                                                               standbyroot=("1" if meshEnabled and meshStandbyRoot else "0"),
                                                               devid=meshDeviceID
                                                               )

    def setParameters(self, channelData: ChannelData, channelNumber: int, loraPower: int, codeRate: int,
                      rxGain: bool, drf1268dsCompatMode: bool, sendAck: bool, preambleLength: int,
                      meshEnabled: bool = False, meshActiveRoot: bool = False,
                      meshDeviceID: str = "", meshStandbyRoot: bool = False) -> bool:
        if self.meshFirmwareSupported is False:
            if meshEnabled:
                return False
            setParameters: str = LoraRadioRAK3172.LegacySetLORAP2PParametersCmd.format(
                frequency=str(channelData.Frequency),
                spreadingfactor=str(channelData.SpreadingFactor),
                bandwidth=str(channelData.RfBw),
                coderate=str(codeRate),
                preamblelength=str(preambleLength),
                txpower=str(loraPower),
                lowdatarateoptimize=("1" if channelData.LowDatarateOptimize else "0"),
                crcon=("1" if channelData.CRCOn else "0"),
                rxgain=("1" if rxGain else "0"),
                drf1268dscompatmode=("1" if drf1268dsCompatMode else "0"),
                sendack=("1" if sendAck else "0"),
                payloadlength="0")
        else:
            setParameters: str = LoraRadioRAK3172.BuildLORAP2PParametersCmd(channelData, loraPower, codeRate, rxGain,
                                                                           drf1268dsCompatMode, sendAck, preambleLength,
                                                                           meshEnabled, meshActiveRoot, meshDeviceID,
                                                                           meshStandbyRoot)
        LoraRadioRAK3172.WiRocLogger.debug(f"LoraRadioRAK3172::setParameters(): {setParameters}")
        self.radioSerial.write(setParameters.encode('ascii'))
        self.radioSerial.flush()
        self.WaitForSerialUpToTimeMS(200)
        expectedLengthAtLeast = 4
        readParameterResp = self.getRadioReply(expectedLengthAtLeast)
        return readParameterResp.startswith(
            LoraRadioRAK3172.SetLORAP2PParametersCmd_ExpectedResponseStart.encode('ascii'))

    @staticmethod
    def ParseLORAP2PParametersResponse(readParameterRespStr: str) -> LoraParametersRAK3172 | None:
        # Reply: ATC+P2PM=<selector>:<radio params 1..12>:<mesh>:<active root>:<standby root>:<device id>
        # Firmware without ATC+P2PM is handled by ParseLegacyLORAP2PParametersResponse (ATC+P2P).
        prefix = LoraRadioRAK3172.ViewLORAP2PParametersCmd_ExpectedResponseStart
        if not readParameterRespStr.startswith(prefix):
            return None
        parameters = readParameterRespStr[len(prefix):].split(':')
        if len(parameters) != 17:
            return None
        loraModuleParameters = LoraParametersRAK3172()
        loraModuleParameters.Frequency = int(parameters[1])
        loraModuleParameters.SpreadingFactor = int(parameters[2])
        loraModuleParameters.Bandwidth = int(parameters[3])
        loraModuleParameters.CodeRate = int(parameters[4])
        loraModuleParameters.PreambleLength = int(parameters[5])
        loraModuleParameters.TransmitPower = int(parameters[6])
        loraModuleParameters.LowDataRateOptimize = (int(parameters[7]) > 0)
        loraModuleParameters.CRCOn = (int(parameters[8]) > 0)
        loraModuleParameters.RxGain = (int(parameters[9]) > 0)
        loraModuleParameters.Drf1268dsCompatMode = (int(parameters[10]) > 0)
        loraModuleParameters.SendAck = (int(parameters[11]) > 0)
        loraModuleParameters.PayloadLength = int(parameters[12])
        loraModuleParameters.MeshEnabled = (int(parameters[13]) > 0)
        loraModuleParameters.ActiveRoot = (int(parameters[14]) > 0)
        loraModuleParameters.StandbyRoot = (int(parameters[15]) > 0)
        loraModuleParameters.NodeDeviceID = parameters[16]
        return loraModuleParameters

    def getFeatures(self) -> dict | None:
        self.radioSerial.write(LoraRadioRAK3172.ViewFeaturesCmd.encode('ascii'))
        self.radioSerial.flush()
        self.WaitForSerialUpToTimeMS(200)
        respStr = self.getRadioReply(20).decode('ascii').rstrip()
        LoraRadioRAK3172.WiRocLogger.debug("LoraRadioRAK3172::getFeatures(): got: " + respStr)
        return LoraRadioRAK3172.ParseFeaturesResponse(respStr)

    @staticmethod
    def ParseFeaturesResponse(respStr: str) -> dict | None:
        prefix = LoraRadioRAK3172.ViewFeaturesCmd_ExpectedResponseStart
        if not respStr.startswith(prefix):
            return None
        fields = respStr[len(prefix):].strip().split(':')
        if len(fields) < 4:
            return None
        try:
            values = [int(f) for f in fields[:4]]
        except ValueError:
            return None
        names = ["p2p", "widechannels", "narrowchannels", "mesh"]
        return dict(zip(names, [v > 0 for v in values]))

    def getParameters(self) -> LoraParametersRAK3172 | None:
        LoraRadioRAK3172.WiRocLogger.debug("LoraRadioRAK3172::getParameters(): Enter, read parameters")
        features = self.getFeatures()
        if features is None:
            # Firmware without the feature query: classic P2P with wide and narrow channels, but no mesh
            features = {"p2p": True, "widechannels": True, "narrowchannels": True, "mesh": False}
        self.meshFirmwareSupported = features["mesh"]
        LoraRadioRAK3172.SaveMeshFirmwareSupported(self.meshFirmwareSupported)
        if not self.meshFirmwareSupported:
            LoraRadioRAK3172.WiRocLogger.info("LoraRadioRAK3172::getParameters() No mesh feature, using ATC+P2P")
            return self.getLegacyParameters()
        self.radioSerial.write(LoraRadioRAK3172.ViewLORAP2PParametersCmd.encode('ascii'))
        self.radioSerial.flush()
        self.WaitForSerialUpToTimeMS(200)
        expectedLengthAtLeast = 33
        readParameterResp = self.getRadioReply(expectedLengthAtLeast)
        readParameterRespStr = readParameterResp.decode('ascii').rstrip()
        LoraRadioRAK3172.WiRocLogger.debug("LoraRadioRAK3172::getParameters(): got: " + readParameterRespStr)
        try:
            if len(readParameterResp) >= expectedLengthAtLeast:
                loraModuleParameters = LoraRadioRAK3172.ParseLORAP2PParametersResponse(readParameterRespStr)
                if loraModuleParameters is not None:
                    return loraModuleParameters
                LoraRadioRAK3172.WiRocLogger.debug(
                    "LoraRadioRAK3172::getParameters(): unexpected number of parameters: " + readParameterRespStr)
            else:
                LoraRadioRAK3172.WiRocLogger.debug(
                    "LoraRadioRAK3172::getParameters(): got: " + readParameterRespStr + ", expected at least: " + str(
                        expectedLengthAtLeast) + " bytes")
        except Exception as e:
            LoraRadioRAK3172.WiRocLogger.error(
                "LoraRadioRAK3172::getParameters() Exception: " + str(e) + " readParameterRespStr: " + readParameterRespStr)

        LoraRadioRAK3172.WiRocLogger.error("LoraRadioRAK3172::getParameters() return None")
        return None

    def getLegacyParameters(self) -> LoraParametersRAK3172 | None:
        self.radioSerial.write(LoraRadioRAK3172.LegacyViewLORAP2PParametersCmd.encode('ascii'))
        self.radioSerial.flush()
        self.WaitForSerialUpToTimeMS(200)
        readParameterResp = self.getRadioReply(33)
        readParameterRespStr = readParameterResp.decode('ascii').rstrip()
        LoraRadioRAK3172.WiRocLogger.debug("LoraRadioRAK3172::getLegacyParameters(): got: " + readParameterRespStr)
        return LoraRadioRAK3172.ParseLegacyLORAP2PParametersResponse(readParameterRespStr)

    @staticmethod
    def ParseLegacyLORAP2PParametersResponse(readParameterRespStr: str) -> LoraParametersRAK3172 | None:
        # Reply: ATC+P2P=<freq>:<sf>:<bw>:<cr>:<preamble>:<txpower>:<ldro>:<crc>:<rxgain>:<compat>:<sendack>:<payloadlen>
        prefix = LoraRadioRAK3172.LegacyViewLORAP2PParametersCmd_ExpectedResponseStart
        if not readParameterRespStr.startswith(prefix):
            return None
        parameters = readParameterRespStr[len(prefix):].split(':')
        if len(parameters) != 12:
            return None
        try:
            loraModuleParameters = LoraParametersRAK3172()
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
            loraModuleParameters.MeshEnabled = False
            loraModuleParameters.ActiveRoot = False
            loraModuleParameters.StandbyRoot = False
            loraModuleParameters.NodeDeviceID = ""
            return loraModuleParameters
        except ValueError:
            return None

    @staticmethod
    def SaveMeshFirmwareSupported(supported: bool) -> None:
        # Persisted so the web service (a separate process without serial access) can report it to the app
        value = '1' if supported else '0'
        sett = DatabaseHelper.get_setting_by_key('RAK3172MeshFirmware')
        if sett is not None and sett.Value == value:
            return
        if sett is None:
            sett = SettingData()
            sett.Key = 'RAK3172MeshFirmware'
        sett.Value = value
        DatabaseHelper.save_setting(sett)

    @staticmethod
    def ParseMeshStateResponse(respStr: str) -> dict | None:
        # Reply: ATC+MESHSTATE=<14 colon separated decimal fields>
        # enabled:isroot:ownaddr:txq:state:alloc:parent:hops:cost:neighbours:epoch:overhead:ackms:standby
        prefix = LoraRadioRAK3172.ViewMeshStateCmd_ExpectedResponseStart
        if not respStr.startswith(prefix):
            return None
        fields = respStr[len(prefix):].strip().split(':')
        if len(fields) != 14:
            return None
        try:
            values = [int(f) for f in fields]
        except ValueError:
            return None
        names = ["enabled", "isroot", "ownaddr", "txq", "state", "alloc", "parent", "hops", "cost",
                 "neighbours", "epoch", "overhead", "ackms", "standby"]
        return dict(zip(names, values))

    def GetMeshState(self) -> dict | None:
        if self.meshFirmwareSupported is False:
            return None
        self.serialLock.acquire()
        try:
            if not self.radioSerial.is_open:
                return None
            while self.radioSerial.in_waiting > 0:
                self.radioSerial.read(1)
            self.radioSerial.write(LoraRadioRAK3172.ViewMeshStateCmd.encode('ascii'))
            self.radioSerial.flush()
            # The reply is a single line terminated by CRLF, there is no trailing OK
            data = bytearray()
            deadline = time.time() + 0.2
            while time.time() < deadline and not data.endswith(b'\n'):
                if self.radioSerial.in_waiting > 0:
                    data.append(self.radioSerial.read(1)[0])
                else:
                    time.sleep(0.01)
            respStr = data.decode('ascii', errors='replace').strip()
            LoraRadioRAK3172.WiRocLogger.debug("LoraRadioRAK3172::GetMeshState() got: " + respStr)
            return LoraRadioRAK3172.ParseMeshStateResponse(respStr)
        finally:
            self.serialLock.release()

    @staticmethod
    def ParseMeshTopologyResponse(respStr: str) -> list[dict] | None:
        # Reply: ATC+MESHTOPO=<addr>:<parent>:<deviceId>[:<neighbour>=<cost>,...]|...
        prefix = LoraRadioRAK3172.ViewMeshTopologyCmd_ExpectedResponseStart
        if not respStr.startswith(prefix):
            return None
        payload = respStr[len(prefix):].strip()
        if payload == "":
            return []
        rows = []
        for row in payload.split('|'):
            fields = row.split(':')
            if len(fields) < 3:
                return None
            deviceID = fields[2]
            if len(deviceID) != 12 or not all(c in '0123456789abcdefABCDEF' for c in deviceID):
                return None
            neighbours = []
            try:
                if len(fields) >= 4 and fields[3] != "":
                    for neighbour in fields[3].split(','):
                        pair = neighbour.split('=')
                        if len(pair) != 2:
                            return None
                        neighbours.append({"addr": int(pair[0]), "cost": int(pair[1])})
                rows.append({"addr": int(fields[0]), "parent": int(fields[1]),
                             "deviceId": deviceID, "neighbours": neighbours})
            except ValueError:
                return None
        return rows

    def GetMeshTopology(self) -> list[dict] | None:
        if self.meshFirmwareSupported is False:
            return None
        self.serialLock.acquire()
        try:
            if not self.radioSerial.is_open:
                return None
            while self.radioSerial.in_waiting > 0:
                self.radioSerial.read(1)
            self.radioSerial.write(LoraRadioRAK3172.ViewMeshTopologyCmd.encode('ascii'))
            self.radioSerial.flush()
            # A full 15-row reply is ~1 KB, nearly 0.1 s at 115200 baud
            data = bytearray()
            deadline = time.time() + 0.5
            while time.time() < deadline and not data.endswith(b'\n'):
                if self.radioSerial.in_waiting > 0:
                    data.append(self.radioSerial.read(1)[0])
                else:
                    time.sleep(0.01)
            respStr = data.decode('ascii', errors='replace').strip()
            LoraRadioRAK3172.WiRocLogger.debug("LoraRadioRAK3172::GetMeshTopology() got: " + respStr)
            return LoraRadioRAK3172.ParseMeshTopologyResponse(respStr)
        finally:
            self.serialLock.release()

    def GetIsEnabled(self) -> bool:
        return self.enabled

    def GetChannel(self) -> str:
        return self.channel

    def GetLastReceivedSrcAddr(self) -> int:
        return self.lastReceivedSrcAddr

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

    def Init(self, channel: str, loraRange: str, loraPower: int, codeRate: int, rxGain: bool,
             drf1268dsCompatMode: bool, sendAck: bool, enabled: bool,
             meshEnabled: bool = False, meshActiveRoot: bool = False, meshDeviceID: str = "",
             meshStandbyRoot: bool = False):
        LoraRadioRAK3172.WiRocLogger.info(
            f"LoraRadioRAK3172::Init() Port name: {self.portName} Channel: {channel} "
            f"LoraRange {loraRange} LoraPower: {loraPower} CodeRate: {codeRate} "
            f"RxGain {rxGain} drf1268dsCompatMode {drf1268dsCompatMode} "
            f"sendAck {sendAck} Enabled: {enabled} Mesh: {meshEnabled} "
            f"MeshActiveRoot: {meshActiveRoot} MeshStandbyRoot: {meshStandbyRoot} MeshDeviceID: {meshDeviceID}")

        switchedFromRoot = meshStandbyRoot and self.meshActiveRoot and not self.meshStandbyRoot
        self.channel = channel
        self.loraPower = loraPower
        self.loraRange = loraRange
        self.codeRate = codeRate
        self.rxGain = rxGain
        self.drf1268dsCompatMode = drf1268dsCompatMode  # no change of radio config, adds netid to message in senddata
        self.sendAck = sendAck
        self.meshEnabled = meshEnabled
        self.meshActiveRoot = meshActiveRoot
        self.meshStandbyRoot = meshStandbyRoot
        self.meshDeviceID = meshDeviceID
        preambleLength: int = 8
        self.enabled = enabled

        if not enabled:
            self.hardwareAbstraction.DisableLora()
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

            LoraRadioRAK3172.LoraModuleParameters = self.getParameters()
            if LoraRadioRAK3172.LoraModuleParameters is None:
                self.isInitialized = False
                LoraRadioRAK3172.WiRocLogger.error("LoraRadioRAK3172::Init() Could not get parameters")
                self.SetErrorCode(ErrorCodeData.ERR_LORA_CONF, "Lora config failed")
                return False
            channelData = DatabaseHelper.get_channel(channel, loraRange, 'RAK3172')
            if channelData is None:
                self.isInitialized = False
                LoraRadioRAK3172.WiRocLogger.error(f"LoraRadioRAK3172::Init() No channel data for {loraRange} {channel}")
                self.SetErrorCode(ErrorCodeData.ERR_LORA_CONF, "Lora config failed")
                return False
            if meshEnabled and self.meshFirmwareSupported is False:
                self.isInitialized = False
                LoraRadioRAK3172.WiRocLogger.error(
                    "LoraRadioRAK3172::Init() Mesh needs the LoRa mesh firmware, the module runs the old firmware")
                self.SetErrorCode(ErrorCodeData.ERR_LORA_CONF, "Lora config failed")
                return False
            if meshEnabled and loraRange not in ('MF', 'F', 'XF', 'UF'):
                # Mesh is designed for the faster standard ranges, any channel in them works
                self.isInitialized = False
                LoraRadioRAK3172.WiRocLogger.error(
                    f"LoraRadioRAK3172::Init() Mesh not supported on range {loraRange}")
                self.SetErrorCode(ErrorCodeData.ERR_LORA_CONF, "Lora config failed")
                return False
            LoraRadioRAK3172.WiRocLogger.verbose(f"Freq {channelData.Frequency} {LoraRadioRAK3172.LoraModuleParameters.Frequency} {channelData.Frequency == LoraRadioRAK3172.LoraModuleParameters.Frequency}")
            LoraRadioRAK3172.WiRocLogger.verbose(f"SpreadingFactor {channelData.SpreadingFactor} {LoraRadioRAK3172.LoraModuleParameters.SpreadingFactor} {channelData.SpreadingFactor == LoraRadioRAK3172.LoraModuleParameters.SpreadingFactor}")
            LoraRadioRAK3172.WiRocLogger.verbose(f"loraPower {loraPower} {LoraRadioRAK3172.LoraModuleParameters.TransmitPower} {loraPower == LoraRadioRAK3172.LoraModuleParameters.TransmitPower}")
            LoraRadioRAK3172.WiRocLogger.verbose(f"RfBw {channelData.RfBw} {LoraRadioRAK3172.LoraModuleParameters.Bandwidth} {channelData.RfBw == LoraRadioRAK3172.LoraModuleParameters.Bandwidth}")
            LoraRadioRAK3172.WiRocLogger.verbose(f"CodeRate {codeRate} {LoraRadioRAK3172.LoraModuleParameters.CodeRate} {codeRate == LoraRadioRAK3172.LoraModuleParameters.CodeRate}")
            LoraRadioRAK3172.WiRocLogger.verbose(f"LowDatarateOptimize {channelData.LowDatarateOptimize} {LoraRadioRAK3172.LoraModuleParameters.LowDataRateOptimize} {channelData.LowDatarateOptimize == LoraRadioRAK3172.LoraModuleParameters.LowDataRateOptimize}")
            LoraRadioRAK3172.WiRocLogger.verbose(f"CRCOn {channelData.CRCOn} {LoraRadioRAK3172.LoraModuleParameters.CRCOn} {channelData.CRCOn == LoraRadioRAK3172.LoraModuleParameters.CRCOn}")
            LoraRadioRAK3172.WiRocLogger.verbose(f"RxGain {rxGain} {LoraRadioRAK3172.LoraModuleParameters.RxGain} {rxGain == LoraRadioRAK3172.LoraModuleParameters.RxGain}")
            LoraRadioRAK3172.WiRocLogger.verbose(f"drf1268dsCompatMode {drf1268dsCompatMode} {LoraRadioRAK3172.LoraModuleParameters.Drf1268dsCompatMode} {drf1268dsCompatMode == LoraRadioRAK3172.LoraModuleParameters.Drf1268dsCompatMode}")
            LoraRadioRAK3172.WiRocLogger.verbose(f"sendAck {sendAck} {LoraRadioRAK3172.LoraModuleParameters.SendAck} {sendAck == LoraRadioRAK3172.LoraModuleParameters.SendAck}")
            effectiveActiveRoot, effectiveStandbyRoot = LoraRadioRAK3172.GetEffectiveMeshFlags(
                meshActiveRoot, meshStandbyRoot, LoraRadioRAK3172.LoraModuleParameters.ActiveRoot, switchedFromRoot)
            LoraRadioRAK3172.WiRocLogger.verbose(f"meshEnabled {meshEnabled} {LoraRadioRAK3172.LoraModuleParameters.MeshEnabled}")
            LoraRadioRAK3172.WiRocLogger.verbose(f"meshActiveRoot {effectiveActiveRoot} {LoraRadioRAK3172.LoraModuleParameters.ActiveRoot}")
            LoraRadioRAK3172.WiRocLogger.verbose(f"meshStandbyRoot {effectiveStandbyRoot} {LoraRadioRAK3172.LoraModuleParameters.StandbyRoot}")
            LoraRadioRAK3172.WiRocLogger.verbose(f"meshDeviceID {meshDeviceID} {LoraRadioRAK3172.LoraModuleParameters.NodeDeviceID}")

            # The module stores drf compat as 0 while mesh is enabled; send ack is stored as written
            drf1268dsCompatEffective = drf1268dsCompatMode and not meshEnabled
            if (channelData.Frequency == LoraRadioRAK3172.LoraModuleParameters.Frequency and
                    channelData.SpreadingFactor == LoraRadioRAK3172.LoraModuleParameters.SpreadingFactor and
                    loraPower == LoraRadioRAK3172.LoraModuleParameters.TransmitPower and
                    channelData.RfBw == LoraRadioRAK3172.LoraModuleParameters.Bandwidth and
                    codeRate == LoraRadioRAK3172.LoraModuleParameters.CodeRate and
                    channelData.LowDatarateOptimize == LoraRadioRAK3172.LoraModuleParameters.LowDataRateOptimize and
                    channelData.CRCOn == LoraRadioRAK3172.LoraModuleParameters.CRCOn and
                    rxGain == LoraRadioRAK3172.LoraModuleParameters.RxGain and
                    drf1268dsCompatEffective == LoraRadioRAK3172.LoraModuleParameters.Drf1268dsCompatMode and
                    sendAck == LoraRadioRAK3172.LoraModuleParameters.SendAck and
                    meshEnabled == LoraRadioRAK3172.LoraModuleParameters.MeshEnabled and
                    effectiveActiveRoot == LoraRadioRAK3172.LoraModuleParameters.ActiveRoot and
                    effectiveStandbyRoot == LoraRadioRAK3172.LoraModuleParameters.StandbyRoot and
                    meshDeviceID == LoraRadioRAK3172.LoraModuleParameters.NodeDeviceID and
                    preambleLength == LoraRadioRAK3172.LoraModuleParameters.PreambleLength):
                LoraRadioRAK3172.WiRocLogger.info("LoraRadioRAK3172::Init() Already correct parameters")
                self.isInitialized = True
                return True
            else:
                channelNumber = int(''.join(c for c in channel if c.isdigit()) or '0')
                if self.setParameters(channelData, channelNumber, loraPower, codeRate, rxGain, drf1268dsCompatMode, sendAck, preambleLength,
                                      meshEnabled, effectiveActiveRoot, meshDeviceID, effectiveStandbyRoot):
                    LoraRadioRAK3172.WiRocLogger.info("LoraRadioRAK3172::Init() Parameters set")
                    self.isInitialized = True
                    return True
                else:
                    LoraRadioRAK3172.WiRocLogger.error("LoraRadioRAK3172::Init() Setting parameters failed")
                    self.SetErrorCode(ErrorCodeData.ERR_LORA_CONF, "Lora config failed")
                    self.isInitialized = False
                    return False
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
        if not self.hardwareAbstraction.GetIsTransmittingReceiving():
            self.busySince = None
            self.staleBusyLogged = False
            return True
        now = time.monotonic()
        if self.busySince is None:
            self.busySince = now
        elif now - self.busySince > LoraRadioRAK3172.StaleBusyTimeoutS:
            # The module raises AUX from the TX-done callback, so a TX aborted by a P2PM write or a
            # lost TxDone IRQ leaves AUX low forever and the host would never send again. Longer than
            # the worst-case airtime in TimeOnAirData (8950 ms), so a real TX is never cut short; the
            # send that clears it completes normally and raises AUX again.
            if not self.staleBusyLogged:
                self.staleBusyLogged = True
                LoraRadioRAK3172.WiRocLogger.error(
                    f"LoraRadioRAK3172::IsReadyToSend() AUX low for more than {LoraRadioRAK3172.StaleBusyTimeoutS}s, "
                    "assuming the module's TX-done callback never ran (aborted TX), allowing a send to clear it")
            return True
        return False

    def SendData(self, messageData: bytearray, destAddr: int = 0) -> ReturnStatus:
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

                    channelNumber = int(''.join(c for c in self.channel if c.isdigit()) or '0')

                    data = bytearray([channelNumber]) + messageData if self.drf1268dsCompatMode and not self.meshEnabled else messageData
                    messageDataWithNetID = Utils.GetDataInHexUpperCase(data)

                    if self.meshEnabled and destAddr >= 2:
                        # Only 2..15 become a real downlink, 0/1 would be a local echo to the root's own host queue
                        messageString = LoraRadioRAK3172.SendLORADataCmdWithDest.format(dest=destAddr, data=messageDataWithNetID)
                    else:
                        messageString = LoraRadioRAK3172.SendLORADataCmd.format(data=messageDataWithNetID)
                    LoraRadioRAK3172.WiRocLogger.debug("LoraRadioRAK3172::SendData() messagestring: " + messageString)
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
                    self.radioSerial.read(2)  # remove also 'CR LF'
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
            if self.loraRadioDataHandler.HasData():
                # Normally there should never be data but it can happen if for example data with errors
                # has been added previously and the GetMessage returned a message of a shorter type. Try to get
                # a message now, likely it will not find a correct one and then clear the buffer
                message = self.loraRadioDataHandler.GetMessage()
                if message is None:
                    LoraRadioRAK3172.WiRocLogger.debug("LoraRadioRAK3172::GetRadioData() Datahandler had message data but no message was found")
                return message

            if self.hardwareAbstraction.GetLORAIRQValue():
                # clear the serial buffers
                while self.radioSerial.in_waiting > 0:
                    self.radioSerial.read(1)

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
                    if self.drf1268dsCompatMode and not self.meshEnabled:
                        # remove NetID (drf1268ds sends a netid, set as the channelnumber)
                        receivedMsgData = receivedMsgData[1:]

                    if self.meshEnabled:
                        # Mesh appends srcaddr + 6 byte node device id after the normal rssi/snr/status trailer.
                        # Keep the srcaddr so a root's app ack can be sent back as a downlink.
                        if len(receivedMsgData) < 11:
                            LoraRadioRAK3172.WiRocLogger.debug(
                                "LoraRadioRAK3172::GetRadioData() mesh frame too short: " + Utils.GetDataInHex(receivedMsgData,
                                                                                                   loggingLevel=logging.DEBUG))
                            return None
                        self.lastReceivedSrcAddr = receivedMsgData[-7]
                        receivedMsgData = receivedMsgData[:-7]

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
