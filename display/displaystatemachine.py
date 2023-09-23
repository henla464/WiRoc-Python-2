from chipGPIO.hardwareAbstraction import HardwareAbstraction
#from smbus2 import SMBus
#import Adafruit_SSD1306
import board
import busio
import adafruit_ssd1306

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
            #self.bus = SMBus(0)
            oledAddress = 0x3c

            self.TypeOfDisplay = 'OLED'
            from display.oleddisplaystate import OledDisplayState
            import display.oledstartup
            import display.olednormal
            import display.oledoutput
            import display.oledwirocip
            import display.oledshutdown
            import display.olederrorcodes
            OledDisplayState = display.oleddisplaystate.OledDisplayState
            #OledDisplayState.OledDisp = Adafruit_SSD1306.SSD1306_128_32(rst=None, i2c_bus=0)
            #i2c = busio.I2C(board.SCL, board.SDA)
            i2c = board.I2C()
            OledDisplayState.OledWidth = 128  # OledDisplayState.OledDisp.width
            OledDisplayState.OledHeight = 32  # OledDisplayState.OledDisp.height
            OledDisplayState.OledDisp = adafruit_ssd1306.SSD1306_I2C(OledDisplayState.OledWidth, OledDisplayState.OledHeight, i2c, addr=oledAddress)


            # Clear display
            #OledDisplayState.OledDisp.begin()
            OledDisplayState.OledDisp.fill(0)
            OledDisplayState.OledDisp.show()

            # Available states
            DisplayStateMachine.OledStartup = display.oledstartup.OledStartup()
            DisplayStateMachine.OledNormal = display.olednormal.OledNormal()
            DisplayStateMachine.OledOutput = display.oledoutput.OledOutput()
            DisplayStateMachine.OledWiRocIP = display.oledwirocip.OledWiRocIP()
            DisplayStateMachine.OledErrorCode = display.olederrorcodes.OledErrorCodes()
            DisplayStateMachine.OledShutdown = display.oledshutdown.OledShutdown()

            self.wiRocLogger.info("DisplayStateMachine::Init() initialized the OLED")

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
