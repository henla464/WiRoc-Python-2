__author__ = 'henla464'

#import unireedsolomon as rs
from reedsolo import RSCodec, ReedSolomonError

class RSCoderLora(object):
    #coder = rs.RSCoder(24, 20)
    coder = RSCodec(4, nsize=63)
    coderLong = RSCodec(8, nsize=63)

    @staticmethod
    def encode(messageData):
        rsCodes = RSCoderLora.coder.encode(messageData)[-4:]
        return rsCodes

    @staticmethod
    def encodeLong(messageData):
        rsCodes = RSCoderLora.coderLong.encode(messageData)[-8:]
        return rsCodes

    @staticmethod
    def check(messageDataThatRSCalculatedOverWithRSCode):
        return RSCoderLora.coder.check(messageDataThatRSCalculatedOverWithRSCode)[0]

    @staticmethod
    def checkLong(messageDataThatRSCalculatedOverWithRSCode):
        return RSCoderLora.coderLong.check(messageDataThatRSCalculatedOverWithRSCode)[0]

    @staticmethod
    def decode(messageDataThatRSCalculatedOverWithRSCode, erasures_positions = None):
        #noOfZerosToPad = 24 - len(messageDataThatRSCalculatedOverWithRSCode)
        #print(noOfZerosToPad)
        #if erasures_positions is not None:
        #    for i in range(len(erasures_positions)):
        #        erasures_positions[i] += noOfZerosToPad - 1
        #print("adjusted erasure position after padding: " + str(erasures_positions))
        #paddedWithZeros = bytearray(bytes([0]*noOfZerosToPad)) + messageDataThatRSCalculatedOverWithRSCode
        #print("padded with zeros: " + str(paddedWithZeros))
        #msgAndCodeTuple = RSCoderLora.coder.decode(paddedWithZeros,  erasures_pos=erasures_positions)
        #print("decoded: " + str(bytearray((msgAndCodeTuple[0] + msgAndCodeTuple[1]).encode('latin-1'))))
        # return bytearray((msgAndCodeTuple[0] + msgAndCodeTuple[1]).encode('latin-1'))
        decoded_msg, decoded_msgecc, errata_pos = RSCoderLora.coder.decode(messageDataThatRSCalculatedOverWithRSCode, erase_pos=erasures_positions)
        return decoded_msgecc

    @staticmethod
    def decodeLong(messageDataThatRSCalculatedOverWithRSCode, erasures_positions=None):
        # noOfZerosToPad = 24 - len(messageDataThatRSCalculatedOverWithRSCode)
        # print(noOfZerosToPad)
        # if erasures_positions is not None:
        #    for i in range(len(erasures_positions)):
        #        erasures_positions[i] += noOfZerosToPad - 1
        # print("adjusted erasure position after padding: " + str(erasures_positions))
        # paddedWithZeros = bytearray(bytes([0]*noOfZerosToPad)) + messageDataThatRSCalculatedOverWithRSCode
        # print("padded with zeros: " + str(paddedWithZeros))
        # msgAndCodeTuple = RSCoderLora.coder.decode(paddedWithZeros,  erasures_pos=erasures_positions)
        # print("decoded: " + str(bytearray((msgAndCodeTuple[0] + msgAndCodeTuple[1]).encode('latin-1'))))
        # return bytearray((msgAndCodeTuple[0] + msgAndCodeTuple[1]).encode('latin-1'))
        decoded_msg, decoded_msgecc, errata_pos = RSCoderLora.coderLong.decode(messageDataThatRSCalculatedOverWithRSCode,
                                                                           erase_pos=erasures_positions)
        return decoded_msgecc