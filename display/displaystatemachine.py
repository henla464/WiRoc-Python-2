from smbus2 import SMBus
import Adafruit_SSD1306
#from PIL import Image
#from PIL import ImageDraw
#from PIL import ImageFont
import socket
import sys
sys.path.append('..')
#from chipGPIO.chipGPIO import *
#from battery import Battery
#import subprocess
import logging
from chipGPIO.hardwareAbstraction import HardwareAbstraction

#DisplayState = display.displaystate.DisplayState
#OledDisplayState = None

class DisplayStateMachine(object):
    SevenSegNormal = None
    OledStartup = None
    OledNormal = None
    OledOutput = None
    OledWiRocIP = None

    hardwareAbstraction = None
    def __init__(self):
        logging.info("DisplayStateMachine::Init start")
        self.TypeOfDisplay = None
        self.currentState = None
        self.runningOnChip = socket.gethostname() == 'chip'
        self.runningOnNanoPi = socket.gethostname() == 'nanopiair'
        try:
            if self.runningOnChip:
                self.bus = SMBus(2)
            elif self.runningOnNanoPi:
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
                import display.sevensegnormal
                OledDisplayState = display.oleddisplaystate.OledDisplayState
                if self.runningOnChip:
                    logging.debug("on chip")
                    OledDisplayState.OledDisp = Adafruit_SSD1306.SSD1306_128_32(rst=None, i2c_bus=2)
                    logging.debug("after oleddisp")
                elif self.runningOnNanoPi:
                    OledDisplayState.OledDisp = Adafruit_SSD1306.SSD1306_128_32(rst=None, i2c_bus=0)
                # Initialize library.
                OledDisplayState.OledDisp.begin()

                # Clear display.
                OledDisplayState.OledWidth = OledDisplayState.OledDisp.width
                OledDisplayState.OledHeight = OledDisplayState.OledDisp.height

                # Available states
                DisplayStateMachine.SevenSegNormal = display.sevensegnormal.SevenSegNormal()
                DisplayStateMachine.OledStartup = display.oledstartup.OledStartup()
                DisplayStateMachine.OledNormal = display.olednormal.OledNormal()
                DisplayStateMachine.OledOutput = display.oledoutput.OledOutput()
                DisplayStateMachine.OledWiRocIP = display.oledwirocip.OledWiRocIP()

                logging.info("Display::Init initialized the OLED")
            else:
                if self.runningOnChip:
                    logging.debug("DisplayStateMachine::Init 7SEG 1")
                    self.TypeOfDisplay = '7SEG'
                else:
                    logging.debug("DisplayStateMachine::Init No display 1")
                    self.TypeOfDisplay = 'NO_DISPLAY'
        except Exception as ex:
            print(ex)
            if self.runningOnChip:
                logging.debug("DisplayStateMachine::Init 7SEG 2")
                self.TypeOfDisplay = '7SEG'
            else:
                logging.debug("DisplayStateMachine::Init no display")
                self.TypeOfDisplay = 'NO_DISPLAY'

        if HardwareAbstraction.Instance == None:
            HardwareAbstraction.Instance = HardwareAbstraction(self.TypeOfDisplay)

        if self.TypeOfDisplay == 'OLED':
            self.currentState = None
        elif self.TypeOfDisplay == '7SEG':
            import display.sevensegnormal
            # Available states
            DisplayStateMachine.SevenSegNormal = display.sevensegnormal.SevenSegNormal()
            self.currentState = DisplayStateMachine.SevenSegNormal


    def GetTypeOfDisplay(self):
        return self.TypeOfDisplay

    def Draw(self, channel, ackRequested, wiRocMode, loraRange, deviceName, sirapTCPEnabled, sendSerialActive, sirapIPAddress, sirapIPPort, wiRocIPAddress):
        if self.currentState != None:
            if HardwareAbstraction.Instance.GetIsShortKeyPress() or self.currentState == self.OledStartup:
                HardwareAbstraction.Instance.ClearShortKeyPress()
                self.currentState = self.currentState.Next()
        else:
            self.currentState = DisplayStateMachine.OledStartup
        if self.currentState != None:
            self.currentState.Draw(channel, ackRequested, wiRocMode, loraRange, deviceName, sirapTCPEnabled, sendSerialActive, sirapIPAddress, sirapIPPort, wiRocIPAddress)

