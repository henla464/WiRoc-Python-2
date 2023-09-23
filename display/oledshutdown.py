import display.displaystatemachine
import display.displaystate
from display.oleddisplaystate import OledDisplayState
from PIL import Image
from PIL import ImageDraw
from battery import Battery
import logging
from chipGPIO.hardwareAbstraction import HardwareAbstraction
from display.displaydata import DisplayData


class OledShutdown(OledDisplayState):
    def __init__(self):
        self.wiRocLogger = logging.getLogger('WiRoc.Display')
        self.imageChanged = True
        self.OledImage = Image.new('1', (OledDisplayState.OledWidth, OledDisplayState.OledHeight))
        self.OledDraw = ImageDraw.Draw(self.OledImage)
        self.OledDraw.text((3, 12), "Shutting Down...", font=self.OledThinFont2, fill=255)

    def Draw(self, displayData: DisplayData):
        if self.imageChanged:
            self.imageChanged = False
            OledDisplayState.OledDisp.image(self.OledImage)
            self.OledDisp.show()

    def Next(self):
        # set imageChanged to true because next time this state is entered we
        # should draw the image
        self.imageChanged = True
        return display.displaystatemachine.DisplayStateMachine.OledStartup
