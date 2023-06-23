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
#mySerial.port = '/dev/ttyUSB5'
#mySerial.port = '/dev/ttyGS0'
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
    #msdMode = bytes([0xFF, 0x02, 0x02, 0xF0, 0x01, 0x4D, 0x6D, 0x0A, 0x03])
    #AT+NAMEWiRoc: 
    #cmd = bytes([0x41, 0x54, 0x2B, 0x4E, 0x41, 0x4D, 0x45, 0x57, 0x69, 0x52, 0x6f, 0x63]) #msMode
    #cmd = bytes([0xFF, 0x02, 0x83, 0x02, 0x00, 0x80, 0xBF, 0x17, 0x03])
    #cmd = bytes([0xFF, 0x02, 0x82, 0x02, 0x34, 0x01, 0x10, 0x11, 0x03])  # set srr channel 0x01
    cmd = bytes([0xFF, 0x02, 0x82, 0x02, 0x34, 0x00, 0x90, 0x14, 0x03])  # set srr channel 0x00
    #AT+BAUD 38400
    #msdMode = bytes([0x41, 0x54, 0x2B, 0x42, 0x41, 0x55, 0x44, 0x36])
    time.sleep(1)
    noOfBytes = mySerial.write(cmd)
    time.sleep(0.1)
    outw = mySerial.out_waiting
    print("bytes written " + str(noOfBytes))
    print("bytes left in outbuffer " + str(outw))
    #mySerial.flush()
    print("After write a byte")
    time.sleep(0.1)
    while True:
        if mySerial.in_waiting > 0:
           #print("in waiting: " + str(mySerial.in_waiting))
           myBytes = mySerial.read(1)
           print(hex(int(myBytes[0])))
        else:
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
           #print("After read a byte")


mySerial.close()

