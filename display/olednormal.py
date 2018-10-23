import display.displaystatemachine
import display.displaystate
from PIL import Image
from PIL import ImageDraw
from battery import Battery
import logging
from chipGPIO.hardwareAbstraction import HardwareAbstraction

OledDisplayState = display.displaystate.OledDisplayState

class OledNormal(OledDisplayState):
    def __init__(self):
        self.batteryPercent = 0
        self.NormalOledImage = None
        self.wifiStrength = None
        self.channel = None
        self.wirocMode = None
        self.ackRequested = None
        self.dataRate = None
        self.isCharging = None
        self.imageChanged = False
        self.OledImage = Image.new('1', (OledDisplayState.OledWidth, OledDisplayState.OledHeight))
        self.OledDraw = ImageDraw.Draw(self.OledImage)
        # self.OledDraw.rectangle((0, 0, self.OledWidth, self.OledHeight), outline=0, fill=0)
        self.OledDraw.text((0, 0), 'CH', font=self.OledThinFont, fill=255)

    def DrawOledBattery(self):
        percent = Battery.GetBatteryPercent()
        logging.debug("OledNormal::DrawOledBattery percent: " + str(percent) + " prev battery: " + str(self.batteryPercent))
        if self.batteryPercent is not None and abs(self.batteryPercent - percent) < 2:
            return None
        self.batteryPercent = percent
        self.imageChanged = True
        logging.debug("OledNormal::DrawOledBattery imagechanged")

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
            logging.debug("OledNormal::DrawIsCharging imagechanged")
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
            logging.debug("OledNormal::DrawOledDataRate imagechanged")
            self.OledDraw.rectangle((41, 0, 60, 12), outline=0, fill=0)
            if dataRate == 293:
                self.OledDraw.text((41, 1), 'L', font=self.OledThinFont2, fill=255)
            if dataRate == 537:
                self.OledDraw.text((41, 1), 'ML', font=self.OledThinFont2, fill=255)
            if dataRate == 977:
                self.OledDraw.text((41, 1), 'MS', font=self.OledThinFont2, fill=255)
            if dataRate == 1758:
                self.OledDraw.text((41, 1), 'S', font=self.OledThinFont2, fill=255)

    def DrawOledWifi(self):
        percent = HardwareAbstraction.Instance.GetWifiSignalStrength()

        if percent == 0:
            return None

        if percent == self.wifiStrength:
            return None
        self.wifiStrength = percent
        self.imageChanged = True
        logging.debug("OledNormal::DrawOledWifi imagechanged")

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

    def Draw(self, channel, ackRequested, wiRocMode, dataRate, deviceName, sirapTCPEnabled, sendSerialActive, sirapIPAddress, sirapIPPort):
        if self.channel != channel:
            self.channel = channel
            self.imageChanged = True
            logging.debug("OledNormal::DrawOled channel imagechanged")
            # Draw a black filled box to clear part of the image.
            self.OledDraw.rectangle((14, 0, 39, 31), outline=0, fill=0)
            self.OledDraw.text((14, 0), str(channel), font=self.OledBoldFont, fill=255)
        if self.wirocMode != wiRocMode:
            self.wirocMode = wiRocMode
            self.imageChanged = True
            logging.debug("OledNormal::DrawOled wirocMode imagechanged")
            self.OledDraw.rectangle((41, 16, 102, 31), outline=0, fill=0)
            self.OledDraw.text((41, 16), wiRocMode, font=self.OledThinFont2, fill=255)
        if self.ackRequested != ackRequested:
            self.ackRequested = ackRequested
            self.imageChanged = True
            logging.debug("OledNormal::DrawOled ackRequested imagechanged")
            self.OledDraw.rectangle((101, 16, 127, 31), outline=0, fill=0)
            if not ackRequested:
                self.OledDraw.text((101, 16), 'X', font=self.OledThinFont2, fill=255)

        self.DrawOledDataRate(dataRate)
        self.DrawOledWifi()
        self.DrawOledBattery()
        self.DrawIsCharging()

        if self.imageChanged:
            self.imageChanged = False
            OledDisplayState.OledDisp.image(self.OledImage)
            OledDisplayState.OledDisp.display()

    def Next(self):
        # set imageChanged to true because next time this state is entered we
        # should draw the image
        self.imageChanged = True
        return display.displaystatemachine.DisplayStateMachine.OledOutput
