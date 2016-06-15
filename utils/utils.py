__author__ = 'henla464'

class Utils:
    CRC_POLYNOM = 0x8005
    @staticmethod
    def computeCRC(byteArray):
        #Compute the crc checksum of value. This implementation is
        #a reimplementation of the Java function in the SI Programmers
        #manual examples."""

        def twoBytes(s):
            #generator that split a string into parts of two chars"""
            if len(s) == 0:
                # immediately stop on empty string
                raise StopIteration

            # add 0 to the string and make it even length
            if len(s) % 2 == 0:
                s.append(0)
                s.append(0) # += '\x00\x00'
            else:
                s.append(0)  # += '\x00'

            for i in range(0, len(s), 2):
                yield s[i:i+2]

        if len(byteArray) < 1:
            # return value for 1 or no data byte is 0
            return bytearray(b'\x00\x00')

        crc = byteArray[0] << 8 + byteArray[1]

        for bytePair in twoBytes(byteArray[2:]):
            val = bytePair[0] << 8 + bytePair[1]

            for j in range(16):
                if (crc & 0x8000) != 0:
                    crc <<= 1

                    if (val & 0x8000) != 0:
                        crc += 1 # rotate carry
                        crc ^= Utils.CRC_POLYNOM
                    else:
                        crc <<= 1
                        if (val & 0x8000) != 0:
                            crc += 1 # rotate carry

                val <<= 1

        # truncate to 16 bit and convert to char
        crc &= 0xFFFF
        return bytearray([crc >> 8, crc & 0xFF])
