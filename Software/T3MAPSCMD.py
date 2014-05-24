__author__ = 'Maximilian Golub'
import serial
import pix
import chip
import os
import threading

BAUD = 9600
COMPORT = 'COM4'
VAL = 500
TIMEOUT = None;
#There are some predefined commands:
#To write data to the FPGA: 11111111
#The write command bit: 01111111
#This writes out to T3MAPS, and collects data
#To transmit data back to the computer: 01111110
RX = '11111111'
RX_OFF = '11111110'
WRITE = '01111111'
TRANSMIT = '01111110'
TRANSMIT_OFF = '10111111'

class RawConversionException(Exception):
        def __init__(self, value):
                self.value = value
        def __str__(self):
                return repr(self.value)
"""
Creates a call graph of the pix.py script. Used for reverse engineering only.
"""
"""
def graph():
        with PyCallGraph(output=GraphvizOutput()):
                commandString = patternRead()
"""

"""
The manual method of controlling T3MAPS. The user must manually verify each step
"""
def manual(port):
        port.close()
        port.open()
        commandString = patternRead()
        byteCMDString = convertCMDString(commandString)
        FPGA_write(port,byteCMDString)
        Winput = raw_input("Write data to T3MAPS? (y/n): ")
        if (Winput.lower() == "y"):
                FPGA_write(port,WRITE,False)
                Winput2 = raw_input("Read data from FGPA fifo? (y/n): ")
                if (Winput2.lower() == "y"):
                        readData(port)
                        port.close()
                else:
                        print("Read aborted")
                        port.close()
        else:
                print("Write aborted")
                port.close() #hopefully kills the other process...

"""
Automatic mathod of controlling T3MAPS, once confirmed, an entire pattern will be written to the FPGA.
"""
def auto(port):
        port.close()
        port.open()
        read_thread = threading.Thread(target=readData, args=port)
        read_thread.start()

        print "hey"
        commandString = patternRead()
        byteCMDString = convertCMDString(commandString)
        check = raw_input("Are you sure you want to run? (Y/N): ")
        if (check.lower() == "y"):
                FPGA_write(port, byteCMDString)
                while(read_thread.is_alive):
                       pass
                port.close()
        else:
                print("Aborted.")
                port.close()

"""
Reads data from the serial port to a file.
"""
def readData(port):
        shiftData = open('shiftData.txt', 'wb')
        FPGA_write(port,TRANSMIT,False)
        shiftData.write(port.read(490))
        shiftData.close()
        print("Here")

"""
Not used
"""
def parseData(data):
        parseData_file = open('parsedData.txt', 'w')
        for x in xrange(0, len(data), 8):
                slice = data[x:x+7]
                print(len(slice))
                parseData_file.write('{0:08b}'.format(slice))

"""
Not used
"""
def encode(byte):
        #if(len(byte)==8):
        temp = ""
        temp += onezero(byte)
        #else:
        #        print(len(byte))
        #        raise RawConversionException

"""
Not used
"""
def onezero(bit):
        byteS = ""
        for x in bit:
                if(x == 1):
                       byteS += "1"
                else:
                        byteS += "0"
        return byteS[::-1]

"""
Converts 8 bits into a format that pyserial
will convert into the correct pattern
"""
def convertToRaw(byte):
        if(len(byte) == 8):
                temp = hex(int(byte, 2)) #Crazy but it works
                temp2 = temp[2:4]
                if (len(temp2) == 1):
                        return ('0'+temp2).decode('hex')
                else:
                       return temp2.decode('hex')
        else:
                raise RawConversionException

"""
Takes a string and converts it entirely to the raw bit format
using the above method.
"""
def convertCMDString(stringList):
        byteList = ''
        for x in range(0,len(stringList),8):
                byteList += convertToRaw(stringList[x:x+8])
        return byteList

"""
Writes data to the FPGA system using pyserial.
By default, the method will assume that you
need to use the RX flag. For testing purposes, using RX_ON
False will result in just the byte you specify being sent.
"""
def FPGA_write(port, commandString, RX_ON = True):
        if(port.isOpen()):
                if(RX_ON):
                        port.write(convertToRaw(RX))
                        bytesWritten = port.write(commandString)
                        port.write(convertToRaw(RX_OFF))
                        print(bytesWritten)
                else:
                        port.write(convertToRaw(commandString))
        else:
                print("Serial port failure")

"""
Generates the bit pattern from pix.py, then returns that pattern
as a bitarray.
"""
def patternRead():

        Dacld = ""
        Stbld = ""
        SRCK_G = ""
        GCfgCK = ""
        SRIN_ALL = ""
        NU = ""
        HiCf = ""
        LoCf = ""
        SRDO_CK = ""
        CntCK = ""
        SlAltBus = ""
        Stbclr = ""

        pinDict = {
        8:SRIN_ALL,
        7:SRCK_G,
        6:GCfgCK,
        5:Dacld,
        4:Stbld,
        3:Stbclr,
        2:SlAltBus,
        1:CntCK,
        0:SRDO_CK,
        9:NU,
        10:HiCf,
        11:LoCf}

        writer = chip.Writer("rawPattern.txt")
        bits = []
        driver = chip.DgeneDriver(writer, number_instructions = 1, config_size=800)
        pix.set_config(150, driver) #Hardcoded for now
        pattern = open("rawPattern.txt", 'r')

        for stream in pattern:
                bits.append(stream)

        for item in bits:
                item = item.split('#')
                dictIndex = item[0].split(',')
                if item[0][0] == 'D' :
                        break
                if item[0][0] == 'M' or item [0][0] == ':' :
                        pinDict[int(dictIndex[0][-1])] = item[1][4:VAL]
                #set the value of pinDict using the value of the last
                #character of x[0] which should be the pin to output
                #to. The value is the second part of x, x[1].
                #the first 4 characters and after val-4 are not used.
        pattern.close()
        os.remove('rawPattern.txt')
        #for reference the old stringList:
        #stringList = [Dacld, Stbld, SRCK_G!!!!!!MUST CHANGE!!!!!!!Now is NU TEMP, GCfgCK, SRIN_ALL, NU, NU, NU]
        stringList = [pinDict[5].rstrip(), pinDict[4].rstrip(), pinDict[9].rstrip(), pinDict[6].rstrip(),
                      pinDict[8].rstrip(), pinDict[9].rstrip(), pinDict[9].rstrip(), pinDict[9].rstrip()]
        shiftData = open('shiftData_before.txt', 'w')
        shiftData.write(pinDict[8].rstrip())
        shiftData.close()
        return genFinalBits(stringList)

def binary_string(x,nbits=5,invert=False):
    """Return an nbit long string of the binary digits of int(x). """
    blist = filled_binary_list(x,nbits)
    if not invert:
        return ''.join((str(x) for x in blist))
    else:
        return ''.join((str(x) for x in blist))[::-1]

def binary_list(x):
    """Return a list of the binary digits of int(x). """
    x = int(x)
    return binary_list(x/2) + [x%2] if x > 1 else [x]

def filled_binary_list(x,nbits=5):
    """Return a list of length nbits of the binary digits of int(x). """
    vals = binary_list(x)
    vals = [0]*(nbits - len(vals)) + vals
    return vals[::-1]

def get_control_pattern_pixel(col,config_bits='00000000',lden='0',S0='0',S1='0',config_mode='00', global_readout_enable='0', count_hits_not='0', count_enable='0', count_clear_not='0', SRDO_load='0'):
    column_address = binary_string(col, 6)
    return global_readout_enable + SRDO_load + NCout2 + count_hits_not + count_enable + count_clear_not + S0 + S1 + config_mode + config_bits + lden + SRCLR_SEL + HITLD_IN + NCout21_25 + column_address


def get_dac_pattern(vth=150, DisVbn=49, VbpThStep=100, PrmpVbp=142, PrmpVbnFol=35, PrmpVbf=11): # fol35 vbp142 vbf11
    default=binary_string(129,8,invert=True)
    return default + default + default + default + binary_string(DisVbn,8) + default + default + default + default + default + default + binary_string(VbpThStep,8) + binary_string(PrmpVbp,8) + binary_string(PrmpVbnFol,8) + binary_string(vth,8) + binary_string(PrmpVbf,8) + default + default


def get_control_pattern(global_readout_enable='0', count_hits_not='0', count_enable='0', count_clear_not='0', config_mode = '00', SRDO_load='0', S0='0', S1='0', col=None):
    if col is None:
        column_address = '111111'
    else:
        column_address = binary_string(col, 6)
    return global_readout_enable + SRDO_load + NCout2 + count_hits_not + count_enable + count_clear_not + S0 + S1 + config_mode + LD_IN0_7 + LDENABLE_SEL + SRCLR_SEL + HITLD_IN + NCout21_25 + column_address



"""
takes a 2d array and creates a string that is the serial
representation of that array.
"""
def genFinalBits(stringList):
        finalBytes = ''
        finalBits = []
        #stringList = [Dacld, Stbld, SRCK_G, GCfgCK, SRIN_ALL, NU, NU, NU]
        for x in range(VAL-5):
                for y in (stringList):
                        finalBits.append(y[x])
        return finalBytes.join(finalBits)

"""
Generates a clock pattern for testing.
"""
def rx_test(port):
        FPGA_write(port,RX, False)
        for x in range(500):
                FPGA_write(port, "10101010", False)
                FPGA_write(port, "01010101", False)
                print(x)
        FPGA_write(port, RX_OFF, False)
        FPGA_write(port,WRITE,False)
        readData(port)
        port.close()

#Call the main method upon execution.
if __name__ == "__main__":
    port = serial.Serial(port=COMPORT,baudrate=BAUD, bytesize=8,stopbits=1, timeout=TIMEOUT)
    manual(port)
    #rx_test(port)
