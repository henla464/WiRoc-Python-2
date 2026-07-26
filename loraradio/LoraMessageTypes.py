__author__ = 'henla464'


class LoraMessageTypes:
    """LoRa message type constants. Kept in a separate module to avoid circular imports
    between settings.py and LoraRadioMessageRS.py."""

    MessageTypeSIPunch: int = 3
    MessageTypeStatus: int = 4
    MessageTypeLoraAck: int = 5
    MessageTypeSIPunchDouble: int = 6
    MessageTypeSIPunchReDCoS: int = 7
    MessageTypeSIPunchDoubleReDCoS: int = 8
    MessageTypeHAMCallSign: int = 9
    MessageTypeStatus2: int = 10
