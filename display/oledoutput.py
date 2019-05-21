import display.displaystatemachine
import display.displaystate
from PIL import Image
from PIL import ImageDraw
from battery import Battery
import logging
from chipGPIO.hardwareAbstraction import HardwareAbstraction

OledDisplayState = display.oleddisplaystate.OledDisplayState

class OledOutput(display.oleddisplaystate.OledDisplayState):
    def __init__(self):
        self.imageChanged = True
        self.showPort = False
        self.sirapTCPEnabled = None
        self.sendSerialActive = None
        self.sirapIPAddress = ""
        self.sirapIPPort = ""
        self.OledImage = Image.new('1', (display.oleddisplaystate.OledDisplayState.OledWidth, display.oleddisplaystate.OledDisplayState.OledHeight))
        self.OledDraw = ImageDraw.Draw(self.OledImage)
        self.OledDraw.text((3, 1), "Out:", font=self.OledThinFont2, fill=255)
        self.OledDraw.text((3, 16), "To:" , font=self.OledThinFont2, fill=255)


    def Draw(self,channel, ackRequested, wiRocMode, dataRate, deviceName, sirapTCPEnabled, sendSerialActive, sirapIPAddress, sirapIPPort, wiRocIPAddress):
        if self.sirapTCPEnabled != sirapTCPEnabled:
            self.imageChanged = True
            logging.debug("OledStartup::Draw sirapTCPEnabled changed")
            self.OledDraw.rectangle((28, 1, 63, 15), outline=0, fill=0)
            if sirapTCPEnabled:
                self.OledDraw.text((28, 1), "SIRAP", font=self.OledThinFont2, fill=255)
            else:
                self.OledDraw.rectangle((22, 16, 128, 31), outline=0, fill=0)
        if sirapTCPEnabled:
            if not self.showPort:
                self.sirapIPAddress = sirapIPAddress
                self.imageChanged = True
                logging.debug("OledStartup::Draw sirapIPAddress changed")
                self.OledDraw.rectangle((20, 16, 100, 31), outline=0, fill=0)
                if sirapIPAddress != None:
                    self.OledDraw.text((20, 16), sirapIPAddress, font=self.OledThinFont2, fill=255)
            else:
                self.sirapIPPort = sirapIPPort
                self.imageChanged = True
                logging.debug("OledStartup::Draw sirapIPPort changed")
                self.OledDraw.rectangle((22, 16, 128, 31), outline=0, fill=0)
                self.OledDraw.text((22, 16), "Port: " + str(sirapIPPort), font=self.OledThinFont2, fill=255)
        self.showPort = not self.showPort

        if self.sendSerialActive != sendSerialActive:
            self.imageChanged = True
            logging.debug("OledStartup::Draw sendSerialActive changed")
            self.OledDraw.rectangle((64, 1, 128, 15), outline=0, fill=0)
            if sendSerialActive:
                self.OledDraw.text((64, 1), "USB", font=self.OledThinFont2, fill=255)
        if ((self.sirapTCPEnabled != sirapTCPEnabled or self.sendSerialActive != sendSerialActive)
            and not sirapTCPEnabled and not sendSerialActive):
            logging.debug("OledStartup::Draw not serial and not sirap")
            self.OledDraw.rectangle((28, 1, 128, 15), outline=0, fill=0)
            self.OledDraw.text((28, 1), "RADIO", font=self.OledThinFont2, fill=255)
        self.sendSerialActive = sendSerialActive
        self.sirapTCPEnabled = sirapTCPEnabled

        if self.imageChanged:
            display.oleddisplaystate.OledDisplayState.OledDisp.image(self.OledImage)
            self.OledDisp.display()

    def Next(self):
        # set imageChanged to true because next time this state is entered we
        # should draw the image
        self.imageChanged = True
        return display.displaystatemachine.DisplayStateMachine.OledWiRocIP
