class LoraToSITransform(object):
    @staticmethod
    def GetInputMessageType():
        return "LORA"

    @staticmethod
    def GetOutputMessageType():
        return "SI"

    @staticmethod
    def GetName():
        return "LoraToSITransform"

    #payloadData is a bytearray
    @staticmethod
    def Transform(payloadData):
        return {"Data":payloadData[5:], "CustomData": None}
