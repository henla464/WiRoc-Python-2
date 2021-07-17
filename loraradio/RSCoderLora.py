__author__ = 'henla464'

import unireedsolomon as rs

class RSCoderLora(object):
    coder = rs.RSCoder(24, 20)

    @staticmethod
    def encode(messageData):
        messageDataAndRSCodeWithNullBytes = RSCoderLora.coder.encode(messageData)
        print("length" + str(len(messageDataAndRSCodeWithNullBytes)))
        rsCodeOnly = messageDataAndRSCodeWithNullBytes[-4:]
        return bytearray(rsCodeOnly.encode('latin-1'))

    @staticmethod
    def check(messageDataThatRSCalculatedOverWithRSCode):
        return RSCoderLora.coder.check(messageDataThatRSCalculatedOverWithRSCode)

    @staticmethod
    def decode(messageDataThatRSCalculatedOverWithRSCode, erasures_positions = None):
        noOfZerosToPad = 24 - len(messageDataThatRSCalculatedOverWithRSCode)
        print(noOfZerosToPad)
        if erasures_positions is not None:
            for i in range(len(erasures_positions)):
                erasures_positions[i] += noOfZerosToPad - 1
        print("adjusted erasure position after padding: " + str(erasures_positions))
        paddedWithZeros = bytearray(bytes([0]*noOfZerosToPad)) + messageDataThatRSCalculatedOverWithRSCode
        print("padded with zeros: " + str(paddedWithZeros))
        msgAndCodeTuple = RSCoderLora.coder.decode(paddedWithZeros,  erasures_pos=erasures_positions)
        print("decoded: " + str(bytearray((msgAndCodeTuple[0] + msgAndCodeTuple[1]).encode('latin-1'))))
        return bytearray((msgAndCodeTuple[0] + msgAndCodeTuple[1]).encode('latin-1'))