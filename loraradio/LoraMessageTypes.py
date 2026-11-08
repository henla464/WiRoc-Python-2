__author__ = 'henla464'


class LoraMessageTypes:
    """LoRa message type constants. Kept in a separate module to avoid circular imports
    between settings.py and LoraRadioMessageRS.py."""

    MessageTypeLoraAck: int = 5
    MessageTypeSIPunchReDCoS: int = 7
    MessageTypeSIPunchDoubleReDCoS: int = 8
    MessageTypeHAMCallSign: int = 9
    MessageTypeStatus2: int = 10
    MessageTypeSIPunchSubSecond: int = 11
    MessageTypeSIPunchDoubleSubSecond: int = 12
