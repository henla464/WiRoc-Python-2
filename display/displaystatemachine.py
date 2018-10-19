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
import display.displaystate
import display.oledstartup
import display.olednormal
import display.sevensegnormal

DisplayState = display.displaystate.DisplayState
OledDisplayState = display.displaystate.OledDisplayState

class DisplayStateMachine(object):
    SevenSegNormal = None
    OledStartup = None
    OledNormal = None

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
            byteRead = self.bus.read_byte(OledDisplayState.OledAddress)
            if byteRead > 0:
                self.TypeOfDisplay = 'OLED'
                if self.runningOnChip:
                    self.OledDisp = Adafruit_SSD1306.SSD1306_128_32(rst=None, i2c_bus=2)
                elif self.runningOnNanoPi:
                    self.OledDisp = Adafruit_SSD1306.SSD1306_128_32(rst=None, i2c_bus=0)
                # Initialize library.
                OledDisplayState.OledDisp.begin()

                # Clear display.
                OledDisplayState.OledWidth = self.OledDisp.width
                OledDisplayState.OledHeight = self.OledDisp.height

                # Available states
                DisplayStateMachine.SevenSegNormal = display.sevensegnormal.SevenSegNormal()
                DisplayStateMachine.OledStartup = display.oledstartup.OledStartup()
                DisplayStateMachine.OledNormal = display.olednormal.OledNormal()

                logging.info("Display::Init initialized the OLED")
            else:
                if self.runningOnChip:
                    self.TypeOfDisplay = '7SEG'
                else:
                    self.TypeOfDisplay = 'NO_DISPLAY'
        except Exception as ex:
            print(ex)
            if self.runningOnChip:
                self.TypeOfDisplay = '7SEG'
            else:
                self.TypeOfDisplay = 'NO_DISPLAY'

        if HardwareAbstraction.Instance == None:
            HardwareAbstraction.Instance = HardwareAbstraction(self.TypeOfDisplay)

        if self.TypeOfDisplay == 'OLED':
            self.currentState = DisplayStateMachine.OledStartup
        elif self.TypeOfDisplay == '7SEG':
            self.currentState = DisplayStateMachine.SevenSegNormal


    def GetTypeOfDisplay(self):
        return self.TypeOfDisplay

    def Draw(self, channel, ackRequested, wiRocMode, dataRate, deviceName):
        if self.currentState != None:
            if HardwareAbstraction.Instance.GetIsShortKeyPress():
                HardwareAbstraction.Instance.ClearShortKeyPress()
                self.currentState = self.currentState.Next()
            self.currentState.Draw(channel, ackRequested, wiRocMode, dataRate, deviceName)

"""
class Display(object):
    def __init__(self):
        logging.info("Display::Init start")
        self.TypeOfDisplay = None

        self.OledDisp = None
        self.OledAddress = 0x3c
        self.OledWidth = 0
        self.OledHeight = 0
        self.OledImage = None
        self.OledDisplayState = 'startup' #startup, normal
        self.batteryPercent = 0
        self.wifiStrength = None
        self.channel = None
        self.wirocMode = None
        self.ackRequested = None
        self.dataRate = None
        self.isCharging = None
        self.imageChanged = False
        self.runningOnChip = socket.gethostname() == 'chip'
        self.runningOnNanoPi = socket.gethostname() == 'nanopiair'
        try:
            if self.runningOnChip:
                self.bus = SMBus(2)
            elif self.runningOnNanoPi:
                self.bus = SMBus(0)
            byteRead = self.bus.read_byte(self.OledAddress)
            if byteRead > 0:
                self.TypeOfDisplay = 'OLED'
                if self.runningOnChip:
                    self.OledDisp = Adafruit_SSD1306.SSD1306_128_32(rst=None, i2c_bus=2)
                elif self.runningOnNanoPi:
                    self.OledDisp = Adafruit_SSD1306.SSD1306_128_32(rst=None, i2c_bus=0)
                # Initialize library.
                self.OledDisp.begin()

                # Clear display.
                self.OledWidth = self.OledDisp.width
                self.OledHeight = self.OledDisp.height
                self.OledImage = Image.new('1', (self.OledWidth , self.OledHeight))
                self.OledDraw = ImageDraw.Draw(self.OledImage)
                #self.OledDraw.rectangle((0, 0, self.OledWidth, self.OledHeight), outline=0, fill=0)
                self.OledThinFont = ImageFont.truetype('display/GeosansLight.ttf', 10)
                self.OledThinFont2 = ImageFont.truetype('display/GeosansLight.ttf', 14)
                self.OledBoldFont = ImageFont.truetype('display/theboldfont.ttf', 44)
                self.OledDraw.text((0, 0), 'CH', font=self.OledThinFont, fill=255)
                self.OledDisp.image(self.OledImage)
                self.OledDisp.display()
                logging.info("Display::Init initialized the OLED")
            else:
                if self.runningOnChip:
                    self.TypeOfDisplay = '7SEG'
                else:
                    self.TypeOfDisplay = 'NO_DISPLAY'
        except Exception as ex:
            print(ex)
            if self.runningOnChip:
                self.TypeOfDisplay = '7SEG'
            else:
                self.TypeOfDisplay = 'NO_DISPLAY'

    def GetTypeOfDisplay(self):
        return self.TypeOfDisplay

    def DrawOledBattery(self):
        percent = Battery.GetBatteryPercent()
        logging.debug("Display::DrawOledBattery percent: " + str(percent) + " prev battery: " + str(self.batteryPercent))
        if self.batteryPercent is not None and abs(self.batteryPercent - percent) < 2:
            return None
        self.batteryPercent = percent
        self.imageChanged = True
        logging.debug("Display::DrawOledBattery imagechanged")

        top = 1
        x = 96
        self.OledDraw.rectangle((x, top, x+23, top+10), outline=0, fill=0)

        # Battery outline
        self.OledDraw.rectangle((x, top, x + 20, top + 10), outline=255, fill=0)
        self.OledDraw.rectangle((x + 20, top + 3, x + 23, top + 7), outline=255, fill=0)
        # Fill charge percentage
        width = int((percent - 5) / 5)
        self.OledDraw.rectangle((x + 1, top + 1, x + width, top + 9), outline=255, fill=255)

    def DrawIsCharging(self):
        newIsCharging = Battery.IsCharging()
        if newIsCharging != self.isCharging:
            self.isCharging = newIsCharging
            self.imageChanged = True
            logging.debug("Display::DrawIsCharging imagechanged")
            x = 121
            top = 3
            #lightning
            self.OledDraw.rectangle((x + 1, top, x + 6, top + 8), outline=0, fill=0)
            if self.isCharging:
                self.OledDraw.line((x + 3, top, x + 3, top), fill=255)
                self.OledDraw.line((x + 3, top + 1, x + 3, top + 1), fill=255)
                self.OledDraw.line((x + 3, top + 2, x + 3, top + 2), fill=255)
                self.OledDraw.line((x + 2, top + 3, x + 3, top + 3), fill=255)
                self.OledDraw.line((x + 1, top + 4, x + 6, top + 4), fill=255)
                self.OledDraw.line((x + 4, top + 5, x + 5, top + 5), fill=255)
                self.OledDraw.line((x + 4, top + 6, x + 4, top + 6), fill=255)
                self.OledDraw.line((x + 4, top + 7, x + 4, top + 7), fill=255)
                self.OledDraw.line((x + 4, top + 8, x + 4, top + 8), fill=255)

    def DrawOledDataRate(self, dataRate):
        if self.dataRate != dataRate:
            self.dataRate = dataRate
            self.imageChanged = True
            logging.debug("Display::DrawOledDataRate imagechanged")
            self.OledDraw.rectangle((41, 0, 60, 12), outline=0, fill=0)
            if dataRate == 293:
                self.OledDraw.text((41, 1), 'L', font=self.OledThinFont2, fill=255)
            if dataRate == 537:
                self.OledDraw.text((41, 1), 'ML', font=self.OledThinFont2, fill=255)
            if dataRate == 977:
                self.OledDraw.text((41, 1), 'MS', font=self.OledThinFont2, fill=255)
            if dataRate == 1758:
                self.OledDraw.text((41, 1), 'S', font=self.OledThinFont2, fill=255)

    def GetWifiSignalStrength(self):
        wifiInUseSSIDSignal = str(subprocess.check_output(["nmcli", "-t", "-f", "in-use,ssid,signal", "device", "wifi"]))
        for row in wifiInUseSSIDSignal.split('\\n'):
            if row.startswith('*'):
                return int(row.split(':')[2])

        return 0

    def DrawOledWifi(self):
        percent = self.GetWifiSignalStrength()

        if percent == 0:
            return None

        if percent == self.wifiStrength:
            return None
        self.wifiStrength = percent
        self.imageChanged = True
        logging.debug("Display::DrawOledWifi imagechanged")

        x = 72
        top = 2
        self.OledDraw.rectangle((x, top, x+21, top+9), outline=0, fill=0)
        self.OledDraw.arc([(x, top), (x + 16, top + 16)], 210, 330, fill=255)
        self.OledDraw.arc([(x + 3, top + 3), (x + 13, top + 13)], 210, 335, fill=255)
        self.OledDraw.ellipse((x + 7, top + 7, x + 9, top + 9), outline=255, fill=255)

        if False: #nmcli on chip doesn't give correct numbers when connected to wifi, maybe nanopi does?
            if (percent > 80):
                self.OledDraw.line((x + 14, top + 9, x + 14, top + 8), fill=255)
            if (percent > 60):
                self.OledDraw.line((x + 16, top + 9, x + 16, top + 5), fill=255)
            if (percent > 40):
                self.OledDraw.line((x + 18, top + 9, x + 18, top + 2), fill=255)
            if (percent > 20):
                self.OledDraw.line((x + 20, top + 9, x + 20, top + -1), fill=255)

    def DrawOled(self, channel, ackRequested, wiRocMode, dataRate):
        # Draw a black filled box to clear the image.
        if self.channel != channel:
            self.channel = channel
            self.imageChanged = True
            logging.debug("Display::DrawOled channel imagechanged")
            self.OledDraw.rectangle((14, 0, 39, 31), outline=0, fill=0)
            self.OledDraw.text((14, 0), str(channel), font=self.OledBoldFont, fill=255)
        if self.wirocMode != wiRocMode:
            self.wirocMode = wiRocMode
            self.imageChanged = True
            logging.debug("Display::DrawOled wirocMode imagechanged")
            self.OledDraw.rectangle((41, 16, 102, 31), outline=0, fill=0)
            self.OledDraw.text((41, 16), wiRocMode, font=self.OledThinFont2, fill=255)
        if self.ackRequested != ackRequested:
            self.ackRequested = ackRequested
            self.imageChanged = True
            logging.debug("Display::DrawOled ackRequested imagechanged")
            self.OledDraw.rectangle((101, 16, 127, 31), outline=0, fill=0)
            if not ackRequested:
                self.OledDraw.text((101, 16), 'X', font=self.OledThinFont2, fill=255)

        self.DrawOledDataRate(dataRate)
        self.DrawOledWifi()
        self.DrawOledBattery()
        self.DrawIsCharging()

        if self.imageChanged:
            self.imageChanged = False
            self.OledDisp.image(self.OledImage)
            self.OledDisp.display()

    def Draw7Seg(self, channel, ackRequested):
        #def displayChannel(self, channel, ackRequested):
        if channel != self.channel or ackRequested != self.ackRequested:
            self.channel = channel
            self.ackRequested = ackRequested
            lightSegA = channel in [2, 3, 5, 6, 7, 8, 9]
            lightSegB = channel in [1, 2, 3, 4, 7, 8, 9]
            lightSegC = channel in [1, 3, 4, 5, 6, 7, 8, 9]
            lightSegD = channel in [2, 3, 5, 6, 8]
            lightSegE = channel in [2, 6, 8]
            lightSegF = channel in [4, 5, 6, 8, 9]
            lightSegG = channel in [2, 3, 4, 5, 6, 8, 9]

            if True:
                lightSegA = not lightSegA
                lightSegB = not lightSegB
                lightSegC = not lightSegC
                lightSegD = not lightSegD
                lightSegE = not lightSegE
                lightSegF = not lightSegF
                lightSegG = not lightSegG
                ackRequested = not ackRequested

            digitalWrite(0, int(lightSegA))
            digitalWrite(1, int(lightSegB))
            digitalWrite(2, int(lightSegC))
            digitalWrite(3, int(lightSegD))
            digitalWrite(4, int(lightSegE))
            digitalWrite(5, int(lightSegF))
            digitalWrite(6, int(lightSegG))

            digitalWrite(7, int(ackRequested))
        return None

    def Draw(self, channel, ackRequested, wiRocMode, dataRate):
        if self.TypeOfDisplay == 'OLED':
            self.DrawOled(channel, ackRequested, wiRocMode, dataRate)
        elif self.TypeOfDisplay == '7SEG':
            self.Draw7Seg(channel, ackRequested)


"""
#myDisplay = Display()
#myDisplay.Draw('4', True, 'SENDER', 293)
