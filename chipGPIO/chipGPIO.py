import os

INPUT = "in"
OUTPUT = "out"
LOW = 0
HIGH = 1
GPIO_PATH = "/sys/class/gpio"  # The root of the GPIO directories
EXPANDER = "pcf8574a"  # This is the expander that is used on CHIP for the XIOs

def get_xio_base():
    '''
    Determines the base of the XIOs on the system by iterating through the /sys/class/gpio
    directory and looking for the expander that is used. It then looks for the
    "base" file and returns its contents as an integer
    '''
    names = os.listdir(GPIO_PATH)
    for name in names:  # loop through child directories
        prefix = GPIO_PATH + "/" + name + "/"
        file_name = prefix + "label"
        if os.path.isfile(file_name):  # is there a label file in the directory?
            with open(file_name) as label:
                contents = label.read()
            if contents.startswith(EXPANDER):  # does label contain our expander?
                file_name = prefix + "base"
                with open(file_name) as base:  # read the sibling file named base
                    contents = base.read()
                return int(contents)  # convert result to an int


def pinMode(pin,mode):
        pinMapped = str(pin+get_xio_base())
        os.system("sudo sh -c 'echo "+pinMapped+" > /sys/class/gpio/export' > /dev/null 2>&1")
        os.system("sudo sh -c 'echo "+mode+" > /sys/class/gpio/gpio"+pinMapped+"/direction'")
        # sys.stdout.write("XIO-P"+str(pin)+" set to "+str(mode)+".\n")

def pinModeNonXIO(pin, mode):
    pinMapped = str(pin)
    os.system("sudo sh -c 'echo "+pinMapped+" > /sys/class/gpio/export' > /dev/null 2>&1")
    os.system("sudo sh -c 'echo "+mode+" > /sys/class/gpio/gpio"+pinMapped+"/direction'")
    #sys.stdout.write("NONXIO"+str(pin)+" set to "+str(mode)+".\n")

def digitalWrite(pin,state):
    pinMapped = str(pin+get_xio_base())
    os.system("sudo sh -c 'echo "+str(state)+" > /sys/class/gpio/gpio"+pinMapped+"/value'")

def digitalWriteNonXIO(pin, state):
    pinMapped = str(pin)
    os.system("sudo sh -c 'echo " + str(state) + " > /sys/class/gpio/gpio" + pinMapped + "/value'")

def digitalReadNonXIO(pin):
    pinMapped = str(pin)
    value = os.popen("cat /sys/class/gpio/gpio" + pinMapped + "/value").read()
    # todo: change to subprocess
    #p = subprocess.Popen(("cat /sys/class/gpio/gpio" + pinMapped + "/value").split(), stdout=subprocess.PIPE)
    #value, _ = p.communicate()
    return int(value)

def digitalRead(pin):
    pinMapped = str(pin+get_xio_base())
    value = os.popen("cat /sys/class/gpio/gpio"+pinMapped+"/value").read()
    return int(value)