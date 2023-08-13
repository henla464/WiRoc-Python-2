import display.displaystatemachine
import display.displaystate
from display.oleddisplaystate import OledDisplayState
from PIL import Image
from PIL import ImageDraw
from battery import Battery
import logging
from chipGPIO.hardwareAbstraction import HardwareAbstraction
from display.displaydata import DisplayData


class OledOutput(OledDisplayState):
    def __init__(self):
        self.wiRocLogger = logging.getLogger('WiRoc.Display')
        self.imageChanged = True
        self.showPort = False
        self.sirapTCPEnabled = None
        self.sendSerialActive = None
        self.sirapIPAddress = ""
        self.sirapIPPort = ""
        self.OledImage = Image.new('1', (OledDisplayState.OledWidth, OledDisplayState.OledHeight))
        self.OledDraw = ImageDraw.Draw(self.OledImage)
        self.OledDraw.text((3, 1), "Out:", font=self.OledThinFont2, fill=255)
        self.OledDraw.text((3, 16), "To:" , font=self.OledThinFont2, fill=255)

    def Draw(self, displayData: DisplayData):
        if self.sirapTCPEnabled != displayData.sirapTCPEnabled:
            self.imageChanged = True
            self.wiRocLogger.debug("OledStartup::Draw sirapTCPEnabled changed")
            self.OledDraw.rectangle((28, 1, 63, 15), outline=0, fill=0)
            if displayData.sirapTCPEnabled:
                self.OledDraw.text((28, 1), "SIRAP", font=self.OledThinFont2, fill=255)
            else:
                self.OledDraw.rectangle((22, 16, 128, 31), outline=0, fill=0)
        if displayData.sirapTCPEnabled:
            if not self.showPort:
                self.sirapIPAddress = displayData.sirapIPAddress
                self.imageChanged = True
                self.wiRocLogger.debug("OledStartup::Draw sirapIPAddress changed")
                self.OledDraw.rectangle((20, 16, 100, 31), outline=0, fill=0)
                if displayData.sirapIPAddress != None:
                    self.OledDraw.text((20, 16), displayData.sirapIPAddress, font=self.OledThinFont2, fill=255)
            else:
                self.sirapIPPort = displayData.sirapIPPort
                self.imageChanged = True
                self.wiRocLogger.debug("OledStartup::Draw sirapIPPort changed")
                self.OledDraw.rectangle((22, 16, 128, 31), outline=0, fill=0)
                self.OledDraw.text((22, 16), "Port: " + str(sirapIPPort), font=self.OledThinFont2, fill=255)
            self.showPort = not self.showPort

        if self.sendSerialActive != displayData.sendSerialActive:
            self.imageChanged = True
            self.wiRocLogger.debug("OledStartup::Draw sendSerialActive changed")
            self.OledDraw.rectangle((64, 1, 128, 15), outline=0, fill=0)
            if displayData.sendSerialActive:
                self.OledDraw.text((64, 1), "USB", font=self.OledThinFont2, fill=255)
        if ((self.sirapTCPEnabled != displayData.sirapTCPEnabled or self.sendSerialActive != displayData.sendSerialActive)
                and not displayData.sirapTCPEnabled and not displayData.sendSerialActive):
            self.imageChanged = True
            self.wiRocLogger.debug("OledStartup::Draw not serial and not sirap")
            self.OledDraw.rectangle((28, 1, 128, 15), outline=0, fill=0)
            self.OledDraw.text((28, 1), "RADIO", font=self.OledThinFont2, fill=255)

        self.sendSerialActive = displayData.sendSerialActive
        self.sirapTCPEnabled = displayData.sirapTCPEnabled

        if self.imageChanged:
            self.imageChanged = False
            OledDisplayState.OledDisp.image(self.OledImage)
            self.OledDisp.display()

    def Next(self):
        # set imageChanged to true because next time this state is entered we
        # should draw the image
        self.imageChanged = True
        return display.displaystatemachine.DisplayStateMachine.OledWiRocIP
