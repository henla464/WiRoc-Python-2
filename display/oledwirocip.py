import display.displaystatemachine
import display.displaystate
from PIL import Image
from PIL import ImageDraw
from battery import Battery
import logging
from chipGPIO.hardwareAbstraction import HardwareAbstraction

OledDisplayState = display.displaystate.OledDisplayState

class OledWiRocIP(display.displaystate.OledDisplayState):
    def __init__(self):
        self.imageChanged = True
        self.wiRocIPAddress = ""
        self.OledImage = Image.new('1', (display.displaystate.OledDisplayState.OledWidth, display.displaystate.OledDisplayState.OledHeight))
        self.OledDraw = ImageDraw.Draw(self.OledImage)
        self.OledDraw.text((3, 1), "WiRoc IP address", font=self.OledThinFont2, fill=255)

    def Draw(self,channel, ackRequested, wiRocMode, dataRate, deviceName, sirapTCPEnabled, sendSerialActive, sirapIPAddress, sirapIPPort, wiRocIPAddress):
        if len(set(self.wiRocIPAddress).intersection(wiRocIPAddress)) != len(wiRocIPAddress):
            self.wiRocIPAddress = wiRocIPAddress
            self.imageChanged = True
            logging.debug("OledStartup::Draw wiRocIPAddress changed")
            self.OledDraw.rectangle((1, 16, 128, 31), outline=0, fill=0)
            if len(self.wiRocIPAddress) > 0:
                self.OledDraw.text((2, 16), self.wiRocIPAddress[0], font=self.OledThinFont2, fill=255)

        if self.imageChanged:
            display.displaystate.OledDisplayState.OledDisp.image(self.OledImage)
            self.OledDisp.display()

    def Next(self):
        # set imageChanged to true because next time this state is entered we
        # should draw the image
        self.imageChanged = True
        return display.displaystatemachine.DisplayStateMachine.OledStartup
