import display.displaystatemachine
import display.displaystate
from display.oleddisplaystate import OledDisplayState
from PIL import Image
from PIL import ImageDraw
from battery import Battery
import logging
from chipGPIO.hardwareAbstraction import HardwareAbstraction
from display.displaydata import DisplayData


class OledNormal(OledDisplayState):
    def __init__(self):
        super().__init__()
        self.wiRocLogger = logging.getLogger('WiRoc.Display')
        self.batteryPercent = 0
        self.batteryWidth = None
        self.NormalOledImage = None
        self.wifiNoOfBars = -2
        self.wifiNoOfBarsPrevious = -2
        self.channel: str | None = None
        self.wiRocMode = None
        self.ackRequested = None
        self.loraRange = None
        self.isCharging = None
        self.OledImage = Image.new('1', (OledDisplayState.OledWidth, OledDisplayState.OledHeight))
        self.OledDraw = ImageDraw.Draw(self.OledImage)

    def DrawOledBattery(self):
        percent = Battery.GetBatteryPercent()
        width = max(int((percent - 5) / 5), 1)
        self.wiRocLogger.debug("OledNormal::DrawOledBattery percent: " + str(percent) + " prev battery: " + str(self.batteryPercent) + " batteryWidth: " + str(width) + " prev batteryWidth: " + str(self.batteryWidth))
        if self.batteryWidth is not None and self.batteryWidth == width:
            return None
        self.batteryPercent = percent
        self.batteryWidth = width
        self.imageChanged = True
        self.wiRocLogger.debug("OledNormal::DrawOledBattery imagechanged")

        top = 1
        x = 96
        self.OledDraw.rectangle((x, top, x+23, top+10), outline=0, fill=0)

        # Battery outline
        self.OledDraw.rectangle((x, top, x + 20, top + 10), outline=255, fill=0)
        self.OledDraw.rectangle((x + 20, top + 3, x + 23, top + 7), outline=255, fill=0)
        # Fill charge percentage
        self.OledDraw.rectangle((x + 1, top + 1, x + width, top + 9), outline=255, fill=255)

    def DrawIsCharging(self):
        newIsCharging = Battery.IsCharging()
        if newIsCharging != self.isCharging:
            self.isCharging = newIsCharging
            self.imageChanged = True
            self.wiRocLogger.debug("OledNormal::DrawIsCharging imagechanged")
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

    def DrawOledLoraRange(self, loraRange):
        if self.loraRange != loraRange:
            self.loraRange = loraRange
            self.imageChanged = True
            self.wiRocLogger.debug("OledNormal::DrawOledRange imagechanged")
            self.OledDraw.rectangle((41, 0, 60, 13), outline=0, fill=0)
            self.OledDraw.text((41, 1), loraRange, font=self.OledThinFont2, fill=255)

    def DrawOledWifi(self):
        percent = HardwareAbstraction.Instance.GetWifiSignalStrength()

        noOfBars = None
        # None is returned for devices that doesn't support getting signal strength
        if percent is None or percent == 0:
            noOfBars = -1
        else:
            noOfBars = 0
            if percent > 75:
                noOfBars = 4
            elif percent > 55:
                noOfBars = 3
            elif percent > 35:
                noOfBars = 2
            elif percent > 15:
                noOfBars = 1

        # Same value two times in row, or this is the first time
        if (noOfBars == self.wifiNoOfBars and noOfBars != self.wifiNoOfBarsPrevious) or self.wifiNoOfBarsPrevious == -1:
            self.wiRocLogger.debug(
                "OledNormal::DrawOledWifi imagechanged: old: " + str(self.wifiNoOfBarsPrevious) + " new: " + str(
                    noOfBars))

            self.imageChanged = True

            x = 72
            top = 2
            self.OledDraw.rectangle((x, top - 1, x + 21, top + 9), outline=0, fill=0)
            if noOfBars >= 0:
                self.OledDraw.arc([(x, top), (x + 16, top + 16)], 210, 330, fill=255)
                self.OledDraw.arc([(x + 3, top + 3), (x + 13, top + 13)], 210, 335, fill=255)
                self.OledDraw.ellipse((x + 7, top + 7, x + 9, top + 9), outline=255, fill=255)
            if noOfBars >= 1:
                self.OledDraw.line((x + 14, top + 9, x + 14, top + 8), fill=255)
            if noOfBars >= 2:
                self.OledDraw.line((x + 16, top + 9, x + 16, top + 5), fill=255)
            if noOfBars >= 3:
                self.OledDraw.line((x + 18, top + 9, x + 18, top + 2), fill=255)
            if noOfBars >= 4:
                self.OledDraw.line((x + 20, top + 9, x + 20, top + -1), fill=255)
        self.wifiNoOfBarsPrevious = self.wifiNoOfBars
        self.wifiNoOfBars = noOfBars
        return None

    def Draw(self, displayData: DisplayData):
        if self.channel != displayData.channel:
            self.channel = displayData.channel
            self.imageChanged = True
            self.wiRocLogger.debug("OledNormal::DrawOled channel imagechanged")
            # Draw a black filled box to clear part of the image.
            if self.channel.startswith('HAM'):
                self.OledDraw.rectangle((0, 0, 39, 31), outline=0, fill=0)
                self.OledDraw.text((14, 0), displayData.channel[3:], font=self.OledBoldFont, fill=255)
                self.OledDraw.text((2, 0), 'H', font=self.OledThinFont, fill=255)
                self.OledDraw.text((2, 10), 'A', font=self.OledThinFont, fill=255)
                self.OledDraw.text((1, 20), 'M', font=self.OledThinFont, fill=255)
            else:
                self.OledDraw.rectangle((0, 0, 39, 31), outline=0, fill=0)
                self.OledDraw.text((14, 0), displayData.channel, font=self.OledBoldFont, fill=255)
                self.OledDraw.text((0, 0), 'CH', font=self.OledThinFont, fill=255)

        if self.wiRocMode != displayData.wiRocMode:
            self.wiRocMode = displayData.wiRocMode
            self.imageChanged = True
            self.wiRocLogger.debug("OledNormal::DrawOled wiRocMode imagechanged")
            self.OledDraw.rectangle((41, 16, 102, 31), outline=0, fill=0)
            self.OledDraw.text((41, 16), displayData.wiRocMode, font=self.OledThinFont2, fill=255)
        if self.ackRequested != displayData.ackRequested:
            self.ackRequested = displayData.ackRequested
            self.imageChanged = True
            self.wiRocLogger.debug("OledNormal::DrawOled ackRequested imagechanged")
            self.OledDraw.rectangle((101, 16, 127, 31), outline=0, fill=0)
            if not displayData.ackRequested:
                self.OledDraw.text((101, 16), 'X', font=self.OledThinFont2, fill=255)

        self.DrawOledLoraRange(displayData.loraRange)
        self.DrawOledWifi()
        self.DrawOledBattery()
        self.DrawIsCharging()

        if self.imageChanged:
            self.imageChanged = False
            OledDisplayState.OledDisp.image(self.OledImage)
            OledDisplayState.OledDisp.show()

    def Next(self):
        # set imageChanged to true because next time this state is entered we
        # should draw the image
        self.imageChanged = True
        return display.displaystatemachine.DisplayStateMachine.OledOutput
