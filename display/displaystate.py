from display.displaydata import DisplayData


class DisplayState(object):

    def Draw(self, displayData: DisplayData):
        assert(0,"Draw not implemented")

    def Next(self):
        assert(0,"Next not implemented")
