from PIL import ImageFont
from display.displaystate import DisplayState
from display.displaydata import DisplayData


class OledDisplayState(DisplayState):
    OledDisp = None
    #OledAddress = 0x3c
    OledWidth = 0
    OledHeight = 0
    OledThinFont = ImageFont.truetype('display/GeosansLight.ttf', 10)
    OledThinFont2 = ImageFont.truetype('display/GeosansLight.ttf', 14)
    OledBoldFont = ImageFont.truetype('display/theboldfont.ttf', 44)

    def __init__(self):
        self.imageChanged: bool = True

    def Draw(self, displayData: DisplayData):
        assert(0,"Draw not implemented")

    def Next(self):
        assert(0,"Next not implemented")

    def SetImagedChanged(self):
        self.imageChanged = True

