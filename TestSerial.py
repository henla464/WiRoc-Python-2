import serial
import time
 # Module sys has to be imported:
import sys

# Iteration over all arguments:
for eachArg in sys.argv:
        print(eachArg)

mySerial = serial.Serial()


mySerial.baudrate = 38400
mySerial.port = sys.argv[1]
#mySerial.writeTimeout = 1
#mySerial.port = '/dev/ttyUSB5'
#mySerial.port = '/dev/ttyGS0'
#mySerial.timeout = 5

if mySerial.is_open:
    print("Serial is open")
else:
    print("Serial is not open")



if not mySerial.is_open:
    print("Try to open")
    mySerial.open()
    print("After try to open")

if mySerial.is_open:
    print("Serial is now open")
else:
    print("Serial is still not open")

if sys.argv[2] == '1':
    print("Check if any bytes waiting")
    noOfBytes = mySerial.inWaiting()
    print("No of bytes: " + str(noOfBytes))

if sys.argv[2] == '2':
    print("Write a byte")
    msdMode = bytes([0xFF, 0x02, 0x02, 0xF0, 0x01, 0x4D, 0x6D, 0x0A, 0x03])
    mySerial.write(msdMode)
    print("After write a byte")
    time.sleep(0.1)
    while mySerial.in_waiting > 0:
        # print("looking for stx: ", end="")
        bytesRead = mySerial.read(1)
        print(bytesRead)
    print("After read a byte")

if sys.argv[2] == '3':
    print("Read a byte")
    myByte = mySerial.read(1)
    print("After read a byte")

mySerial.close()

