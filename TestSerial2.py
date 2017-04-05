import serial
 # Module sys has to be imported:
import sys
import pyudev
import time, os
from serial import Serial
from serial.serialutil import SerialException
import serial.tools.list_ports

mySerial = serial.Serial()


def _send_command():
    global mySerial
    try:
        if mySerial.inWaiting() != 0:
            raise Exception(
                'Input buffer must be empty before sending command. Currently %s bytes in the input buffer.' % self._serial.inWaiting())


        cmd = bytes([0xFF, 0x02, 0x02, 0xF0, 0x01, 0x4D, 0x6D, 0x0A, 0x03])
        mySerial.write(cmd)
        print("command sent")
    except (SerialException, OSError) as  msg:
        print('Could not send command: %s' % msg)

    return mySerial.in_waiting

def _connect_reader(port):
    global mySerial
    print("connect")
    try:
        mySerial = Serial(port, baudrate=38400, timeout=5)
    except (SerialException, OSError):
        print("Could not open port '%s'" % port)

    # flush possibly available input
    try:
        mySerial.flushInput()
    except (SerialException, OSError) as msg:
        # This happens if the serial port is not ready for
        # whatever reason (eg. there is no real device behind this device node).
        print("Could not flush port '%s'" % msg)


    try:
        # try at 38400 baud, extended protocol
        _send_command()
    except:
        try:
            print("exc send_command")
            mySerial.baudrate = 4800
        except (SerialException, OSError) as msg:
            raise Exception('Could not set port speed to 4800: %s' % msg)
        try:
            _send_command()
        except:
            print('This module only works with BSM7/8 stations: %s')

    time.sleep(0.5)
    print("waiting in")
    while mySerial.in_waiting != 0:
        readBytes = mySerial.read()
        print(readBytes)


while True:

    mylist = serial.tools.list_ports.grep('10c4:800a|0525:a4aa')
    for a in mylist:
        print(a.device)

    time.sleep(5)
    continue

    serialPort = None
    # https://github.com/dhylands/usb-ser-mon/blob/master/find_port.py
    uDevContext = pyudev.Context()
    for device in uDevContext.list_devices(subsystem='tty'):
        if 'ID_VENDOR_ID' in device:
            if device['ID_VENDOR_ID'].lower() == '10c4' and \
                            device['ID_MODEL_ID'].lower() == '800a':
                serialPort = device.device_node
            elif device['ID_VENDOR_ID'].lower() == '0525' and \
                            device['ID_MODEL_ID'].lower() == 'a4aa':
                serialPort = device.device_node
    if serialPort is not None:
        _connect_reader(serialPort)
        time.sleep(10)
        continue
        mySerial.baudrate = 38400
        mySerial.port = serialPort
        #mySerial.writeTimeout = 1
        #mySerial.port = '/dev/ttyUSB3'
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

        print("Check if any bytes waiting")
        noOfBytes = mySerial.in_waiting
        print("No of bytes: " + str(noOfBytes))

        print("ReceiveSIAdapter::Init() serial port open")

        msdMode = bytes([0xFF, 0x02, 0x02, 0xF0, 0x01, 0x4D, 0x6D, 0x0A, 0x03])
        a = mySerial.write(msdMode)

        #mySerial.flushOutput()
        #mySerial.flushInput()
        time.sleep(1)
        print("written: " + str(a))
        print("Check if any bytes out waiting")
        #noOfBytes = mySerial.out_waiting
        print("No of bytes out: " + str(noOfBytes))

        expectedLength = 3
        response = bytearray()
        startFound = False
        while mySerial.in_waiting > 0:

            bytesRead = mySerial.read(1)
            print("bytesRead: " + str(bytesRead))

            if bytesRead[0] == 0x02:
                startFound = True
            if startFound:
                response.append(bytesRead[0])
                if len(response) == 3:
                    expectedLength = response[2] + 6
                if len(response) == expectedLength:
                    break
                if len(response) < expectedLength and mySerial.in_waiting == 0:
                    print("ReceiveSIAdapter::Init() sleep and wait for more bytes")
                    time.sleep(0.05)
                    if mySerial.in_waiting == 0:
                        break

        print("ReceiveSIAdapter::Init() received: " + str(response))
        time.sleep(10)
        #mySerial.close()
