__author__ = 'henla464'


class LoraParameters(object):

    def __init__(self):
        self.DeviceID: int|None = None
        self.NetID: int|None = None
        self.BaudRate: int|None = None
        self.DataBit: int|None = None
        self.ParityCheck: int|None = None
        self.StopBit: int|None = None
        self.DataRate: int|None = None
        self.SpreadingFactor: int|None = None
        self.Bandwidth: int|None = None
        self.CodeRate: int|None = None
        self.TransmitPower: int|None = None
        self.TransmitFrequency: int|None = None
        self.ReceiveFrequency: int|None = None
        self.IDRxGainEnable: int|None = None
        self.LBTEnable: int|None = None
        self.RSSIEnable: int|None = None
        self.SensorType: int|None = None
        self.PreWakeUp: int|None = None
        self.WorkMode: int|None = None
        self.StarMode: int|None = None
        self.CADPeak: int|None = None
        self.SleepTime: int|None = None
        self.StartID: int|None = None
        self.EndID: int|None = None
        self.TimeSlot: int|None = None