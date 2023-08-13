from chipGPIO.hardwareAbstraction import HardwareAbstraction
from smbus2 import SMBus
import Adafruit_SSD1306
import socket
import sys
import logging
from display.displaydata import DisplayData

sys.path.append('..')


class DisplayStateMachine(object):
    OledStartup = None
    OledNormal = None
    OledOutput = None
    OledWiRocIP = None
    OledShutdown = None
    OledErrorCode = None

    hardwareAbstraction = None

    def __init__(self):
        self.wiRocLogger = logging.getLogger('WiRoc.Display')
        self.wiRocLogger.info("DisplayStateMachine::Init() start")
        self.currentState = None
        try:
            self.bus = SMBus(0)
            oledAddress = 0x3c
            byteRead = self.bus.read_byte(oledAddress)
            if byteRead > 0:
                self.TypeOfDisplay = 'OLED'
                from display.oleddisplaystate import OledDisplayState
                import display.oledstartup
                import display.olednormal
                import display.oledoutput
                import display.oledwirocip
                import display.oledshutdown
                import display.olederrorcodes
                OledDisplayState = display.oleddisplaystate.OledDisplayState
                OledDisplayState.OledDisp = Adafruit_SSD1306.SSD1306_128_32(rst=None, i2c_bus=0)
                # Initialize library.
                OledDisplayState.OledDisp.begin()

                # Clear display.
                OledDisplayState.OledWidth = OledDisplayState.OledDisp.width
                OledDisplayState.OledHeight = OledDisplayState.OledDisp.height

                # Available states
                DisplayStateMachine.OledStartup = display.oledstartup.OledStartup()
                DisplayStateMachine.OledNormal = display.olednormal.OledNormal()
                DisplayStateMachine.OledOutput = display.oledoutput.OledOutput()
                DisplayStateMachine.OledWiRocIP = display.oledwirocip.OledWiRocIP()
                DisplayStateMachine.OledErrorCode = display.olederrorcodes.OledErrorCodes()
                DisplayStateMachine.OledShutdown = display.oledshutdown.OledShutdown()

                self.wiRocLogger.info("DisplayStateMachine::Init() initialized the OLED")
            else:
                self.wiRocLogger.debug("DisplayStateMachine::Init() No display 1")
                self.TypeOfDisplay = 'NO_DISPLAY'
        except Exception as ex:
            # print(ex)
            self.wiRocLogger.debug("DisplayStateMachine::Init no display")
            self.TypeOfDisplay = 'NO_DISPLAY'

        if HardwareAbstraction.Instance is None:
            HardwareAbstraction.Instance = HardwareAbstraction()

        self.currentState = None

    def GetTypeOfDisplay(self):
        return self.TypeOfDisplay

    def Draw(self, displayData: DisplayData):
        # channel, ackRequested, wiRocMode, loraRange, deviceName, sirapTCPEnabled, sendSerialActive, sirapIPAddress, sirapIPPort, wiRocIPAddress, errorCodes
        if self.currentState is not None:
            if HardwareAbstraction.Instance.GetIsShortKeyPress() or self.currentState == self.OledStartup:
                HardwareAbstraction.Instance.ClearShortKeyPress()
                self.currentState = self.currentState.Next()
            elif HardwareAbstraction.Instance.GetIsLongKeyPress():
                self.currentState = DisplayStateMachine.OledShutdown
        else:
            self.currentState = DisplayStateMachine.OledStartup

        if self.currentState is not None:
            self.currentState.Draw(displayData)
