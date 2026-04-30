# ./env/bin/python3 TestSerial.py 9600 /dev/ttyS1 1
# ./env/bin/python3 TestSerial.py 9600 /dev/ttyS1 2
# ./env/bin/python3 TestSerial.py 9600 /dev/ttyS1 4

import serial
import time
# Module sys has to be imported:
import sys

# Iteration over all arguments:
for eachArg in sys.argv:
    print(eachArg)

mySerial = serial.Serial()

mySerial.baudrate = int(sys.argv[1])
mySerial.port = sys.argv[2]
mySerial.writeTimeout = 1
mySerial.timeout = 5

if mySerial.is_open:
    print("Serial is open")
else:
    print("Serial is not open")

if not mySerial.is_open:
    print("Try to open")
    mySerial.open()
    time.sleep(1)
    mySerial.reset_input_buffer()
    mySerial.reset_output_buffer()

    print("After try to open")

if mySerial.is_open:
    print("Serial is now open")
else:
    print("Serial is still not open")

if sys.argv[3] == '1':
    print("Check if any bytes waiting")
    noOfBytes = mySerial.inWaiting()
    print("No of bytes: " + str(noOfBytes))

if sys.argv[3] == '2':
    print("Write a byte")
    EnterATMode = bytes([0xFF, 0xFF,  # sync word
                         0x02,  # length
                         0x1B,  # cmd code: Enter AT
                         0x1D])  # CRC
    time.sleep(1)
    noOfBytes = mySerial.write(EnterATMode)
    time.sleep(0.1)
    outw = mySerial.out_waiting
    print("bytes written " + str(noOfBytes))
    print("bytes left in outbuffer " + str(outw))
    # mySerial.flush()
    print("After write a byte")
    time.sleep(0.1)
    while mySerial.in_waiting > 0:
        print("in waiting: " + str(mySerial.in_waiting))
        myBytes = mySerial.read(1)
        print(hex(int(myBytes[0])))
        time.sleep(0.1)
    print("After read a byte")

    ReadParameter = bytes([0xFF, 0xFF,  # sync word
                           0x02,  # length
                           0x01,  # cmd code: Enter AT
                           0x03])  # CRC
    ReadChannelRSSI = bytes([0xFF, 0xFF,  # sync word
                             0x02,  # length
                             0x11,  # cmd code: read channel RSSI
                             0x13])  # CRC
    ReadDataRSSI = bytes([0xFF, 0xFF,  # sync word
                          0x02,  # length
                          0x0F,  # cmd code: read data RSSI
                          0x11])  # CRC

    Reset = bytes([0xFF, 0xFF,  # sync word
                   0x02,  # length
                   0x15,  # reset
                   0x17])  # CRC
    time.sleep(1)
    noOfBytes = mySerial.write(Reset)
    time.sleep(0.1)
    outw = mySerial.out_waiting
    print("bytes written " + str(noOfBytes))
    print("bytes left in outbuffer " + str(outw))
    # mySerial.flush()
    print("After write a byte")
    time.sleep(0.1)
    while mySerial.in_waiting > 0:
        print("in waiting: " + str(mySerial.in_waiting))
        myBytes = mySerial.read(1)
        print(hex(int(myBytes[0])))
        time.sleep(0.1)
    print("After read a byte")

if sys.argv[3] == '3':
    print("Read a byte")
    while True:
        time.sleep(0.1)
        if mySerial.in_waiting > 0:
            print("in waiting: " + str(mySerial.in_waiting))
            myBytes = mySerial.read(1)
            print(myBytes)
            # print("After read a byte")

if sys.argv[3] == '4':
    print("Write a byte")
    ack = bytes([0x85, 0xcb, 0x0e, 0xcb, 0x0e, 0xcb, 0x0e])
    time.sleep(1)
    noOfBytes = mySerial.write(ack)
    time.sleep(0.1)
    outw = mySerial.out_waiting
    print("bytes written " + str(noOfBytes))
    print("bytes left in outbuffer " + str(outw))
    # mySerial.flush()
    print("After write a byte")
    time.sleep(0.1)
    while mySerial.in_waiting > 0:
        print("in waiting: " + str(mySerial.in_waiting))
        myBytes = mySerial.read(1)
        print(hex(int(myBytes[0])))
        time.sleep(0.1)

mySerial.close()

