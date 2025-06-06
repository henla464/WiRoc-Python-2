__author__ = 'henla464'

from struct import pack
from datetime import datetime
import logging, os, random

class Utils:
    WiRocLogger = logging.getLogger('WiRoc')
    CRC_POLYNOM = 0x8005
    CRC_BIT16 = 0x8000

    @staticmethod
    def toInt(byteArr):
        if len(byteArr) == 2:
            return (byteArr[0] << 8) + byteArr[1]
        elif len(byteArr) == 3:
            return (byteArr[0] << 16) + (byteArr[1] << 8) + (byteArr[2])
        elif len(byteArr) == 4:
            return (byteArr[0] << 24) + (byteArr[1] << 16) + (byteArr[2] << 8) + byteArr[3]

    @staticmethod
    def CalculateCRC(byteArr):
        # Compute the crc checksum of value. This implementation is
        # a reimplementation of the Java function in the SI Programmers
        # manual examples and the sireader python module

        def listOfTwoBytes(slicedByteArr):
            # generates list of elements, each element a bytearray of two bytes
            if len(slicedByteArr) == 0:
                return

            # add 0 to the string and make it even length
            if len(slicedByteArr) % 2 == 0:
                slicedByteArr.append(0x00)
            slicedByteArr.append(0x00)

            for i in range(0, len(slicedByteArr), 2):
                yield slicedByteArr[i:i + 2]

        if len(byteArr) < 2:
            # return value for 1 or no data byte is 0
            return bytearray(bytes([0x00, 0x00]))

        crc = Utils.toInt(byteArr[0:2])

        for twoBytes in listOfTwoBytes(byteArr[2:]):
            val = Utils.toInt(twoBytes)

            for j in range(16):
                if (crc & Utils.CRC_BIT16) != 0:
                    crc <<= 1

                    if (val & Utils.CRC_BIT16) != 0:
                        crc += 1  # rotate carry

                    crc ^= Utils.CRC_POLYNOM
                else:
                    crc <<= 1

                    if (val & Utils.CRC_BIT16) != 0:
                        crc += 1  # rotate carry

                val <<= 1

        # truncate to 16 bit and convert to char
        crc &= 0xFFFF
        return bytearray(crc.to_bytes(2, byteorder='big'))

    @staticmethod
    def DecodeCardNr(number):
        """Implementation copied from the sireader module

           Decodes a 4 byte cardnr to an int. SI-Card numbering is a bit odd:

           SI-Card 5:
              - byte 0:   always 0 (not stored on the card)
              - byte 1:   card series (stored on the card as CNS)
              - byte 2,3: card number
              - printed:  100'000*CNS + card number
              - nr range: 1-65'000 + 200'001-265'000 + 300'001-365'000 + 400'001-465'000

           SI-Card 6/6*/8/9/10/11/pCard/tCard/fCard/SIAC1:
              - byte 0:   card series (SI6:00, SI9:01, SI8:02, pCard:04, tCard:06, fCard:0E, SI10+SI11+SIAC1:0F)
              - byte 1-3: card number
              - printed:  only card number
              - nr range:
                  - SI6: 500'000-999'999 + 2'003'000-2'003'400 (WM2003) + 16'711'680-16'777'215 (SI6*)
                  - SI9: 1'000'000-1'999'999, SI8: 2'000'000-2'999'999
                  - pCard: 4'000'000-4'999'999, tCard: 6'000'000-6'999'999
                  - SI10: 7'000'000-7'999'999, SIAC1: 8'000'000-8'999'999
                  - SI11: 9'000'000-9'999'999, fCard: 14'000'000-14'999'999

           The card nr ranges guarantee that no ambigous values are possible
           (500'000 = 0x07A120 > 0x04FFFF = 465'535 = highest technically possible value on a SI5)

           Byte 0 seem to always be 0 regardless of card series...
        """
        # Should probably change to number[0:4] so that this will work when card numbers >= 16 777 216
        nr = Utils.toInt(number[1:4])
        if nr < 500000:
            # SI5 card
            ret = Utils.toInt(number[2:4])
            if number[1] < 2:
                # Card series 0 and 1 do not have the 0/1 printed on the card
                return ret
            else:
                return number[1] * 100000 + ret
        else:
            # SI6/8/9
            return nr

    @staticmethod
    def EncodeCardNr(number) -> int:
        if 200000 < number <= 265000:
            return (number - 200000) + 0x20000
        elif 300000 < number <= 365000:
            return (number - 300000) + 0x30000
        elif 400000 < number <= 465000:
            return (number - 400000) + 0x40000
        elif 65000 < number < 500000:
            return 0
        else:
            return number

    @staticmethod
    def DecodeStationNumber(stationNumberBytes: bytearray) -> int:
        # Two lowest bits are part of
        stationNumber:int = ((stationNumberBytes[0] & 0x03) << 8) + stationNumberBytes[1]
        return stationNumber

    @staticmethod
    def GetSirapDataFromSIData(siMessage):
        #if len(siPayloadData) < 12:
        #    logging.error("Utils::GetSirapDataFromSIData() length siPayloadData less than 12")
        #    return None
        #punchData = PunchData(siPayloadData)
        punch = 0  # type of data
        codeDay = 0  # obsolete
        #time = ((punchData.TwelveHourTimer[0] << 8) + punchData.TwelveHourTimer[1]) * 10 + punchData.SubSecond
        time = siMessage.GetTimeAsTenthOfSeconds()
        #if punchData.TwentyFourHour == 1:
        #    time += 36000 * 12
        byteArr = bytearray(pack("<cHIII", bytes([punch]), siMessage.GetStationNumber(), siMessage.GetSICardNumber(), codeDay, time))
        return byteArr

    @staticmethod
    def SetTime(hour, minute, second):
        import ctypes
        import ctypes.util
        import time

        # /usr/include/linux/time.h:
        #
        # define CLOCK_REALTIME                     0
        CLOCK_REALTIME = 0

        # /usr/include/time.h
        #
        # struct timespec
        #  {
        #    __time_t tv_sec;            /* Seconds.  */
        #    long int tv_nsec;           /* Nanoseconds.  */
        #  };
        class timespec(ctypes.Structure):
            _fields_ = [("tv_sec", ctypes.c_long),
                        ("tv_nsec", ctypes.c_long)]

        librt = ctypes.CDLL(ctypes.util.find_library("rt"))

        today = datetime.today()
        year = today.year
        month = today.month
        day = today.day
        ts = timespec()
        ts.tv_sec = int(time.mktime(datetime(year, month, day, hour, minute, second).timetuple()))
        ts.tv_nsec = 0

        # http://linux.die.net/man/3/clock_settime
        Utils.WiRocLogger.debug("before time set: "+ str(datetime.now()))
        librt.clock_settime(CLOCK_REALTIME, ctypes.byref(ts))
        Utils.WiRocLogger.debug("after time set: " + str(datetime.now()))

    @staticmethod
    def SetDateTime(year, month, day, hour, minute, second):
        import ctypes
        import ctypes.util
        import time

        # /usr/include/linux/time.h:
        #
        # define CLOCK_REALTIME                     0
        CLOCK_REALTIME = 0

        # /usr/include/time.h
        #
        # struct timespec
        #  {
        #    __time_t tv_sec;            /* Seconds.  */
        #    long int tv_nsec;           /* Nanoseconds.  */
        #  };
        class timespec(ctypes.Structure):
            _fields_ = [("tv_sec", ctypes.c_long),
                        ("tv_nsec", ctypes.c_long)]

        librt = ctypes.CDLL(ctypes.util.find_library("rt"))

        ts = timespec()
        ts.tv_sec = int(time.mktime(datetime(year, month, day, hour, minute, second).timetuple()))
        ts.tv_nsec = 0

        # http://linux.die.net/man/3/clock_settime
        Utils.WiRocLogger.debug("Util::SetDateTime before time set: " + str(datetime.now()))
        librt.clock_settime(CLOCK_REALTIME, ctypes.byref(ts))
        Utils.WiRocLogger.debug("Util::SetDateTime after time set: " + str(datetime.now()))

    @staticmethod
    def GetDataInHex(data, loggingLevel):
        if logging.getLogger('WiRoc.Input').isEnabledFor(loggingLevel) or \
                logging.getLogger('WiRoc.Output').isEnabledFor(loggingLevel):
            dataInHex = ''.join(format(x, '02x') for x in data)
            return dataInHex
        return "(Not printed in this logging level)"

    @staticmethod
    def GetShouldDropMessage(dropPercentage):
        return random.choices([True, False], weights=[dropPercentage, 100-dropPercentage], k=1)[0]

