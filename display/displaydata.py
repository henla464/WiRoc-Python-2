from dataclasses import dataclass
from datamodel.datamodel import ErrorCodeData


@dataclass(init=True)
class DisplayData(object):
    channel : int = None
    ackRequested : bool = None
    wiRocMode : str = None
    loraRange : str = None
    wiRocDeviceName : str = None
    sirapTCPEnabled : bool = None
    sendSerialActive : bool = None
    sirapIPAddress : str = None
    sirapIPPort : int = None
    wiRocIPAddresses : list[str] = None
    errorCodes : list[ErrorCodeData] = None