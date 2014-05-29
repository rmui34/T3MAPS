__author__ = 'Maximilian Golub','Bo Wang'
import serial
import Command
#######################################################################################################################
#Settings for serial communication, predefined FPGA commands and pin mapping
BAUD = 9600
COMPORT = 5
TIMEOUT = 5

"""There are some predefined commands:
To write data to the FPGA: 11111111
The write command bit: 01111111
This writes out to T3MAPS, and collects data
To transmit data back to the computer: 01111110"""
RX = '11111111'
RX_OFF = '11111110'
WRITE = '01111111'
TRANSMIT = '01111110'
TRANSMIT_OFF = '10111111'

#a dictionary of the command pin mapping
pinDict = {0:'SRIN_ALL',
           1:'SRCK_G',
           2:'GCfgCK',
           3:'Dacld',
           4:'Stbld',
           5:'SlAltBus',
           6:'NU',
           7:'NU'}
#######################################################################################################################
#RawConversionException class
class RawConversionException(Exception):
        def __init__(self, value):
                self.value = value
        def __str__(self):
                return repr(self.value)

#######################################################################################################################
#Conversion methods for serial communication
def convertToByte(list):
    """Takes a list and output the list as a data bus list"""
    s=""
    for i in range(len(list[0])):
        for j in range(len(list)-1,-1,-1):
            s+=(list[j][i])
    return s

def convertToRaw(byte):
    """Converts 8 bits into a format that pyserial
    will convert into the correct pattern"""
    if(len(byte) == 8):
            temp = hex(int(byte, 2)) #Crazy but it works
            temp2 = temp[2:4]
            if (len(temp2) == 1):
                    return ('0'+temp2).decode('hex')
            else:
                    return temp2.decode('hex')
    else:
             raise RawConversionException

def convertCMDString(stringList):
    """Takes a string and converts it entirely to the raw bit format
    using the above method."""
    byteList = ''
    for x in range(0,len(stringList),8):
        byteList += convertToRaw(stringList[x:x+8])
    return byteList

def convertFPGAHits(data):
    """converts readout output file FF to 1 and otherwise 0"""
    final = ""
    for datum in data:
        temp = int(ord(datum))
        if(temp == 255):
            final+='1'
        elif(temp == 0):
            final+='0'
        else:
            raise Exception
    return final
########################################################################################################################
#Single Command generation methods
def commandRead(commandDict):
    """Takes a dictionary of command constructed in Command.py and return a data bus list"""
    stringList = []
    for i in range(8):
        stringList.append(commandDict[pinDict[i]])
    shiftData = open('shiftData_before.txt', 'w')
    for s in pinDict.values():
        if (s != "NU"):
            shiftData.write(s+"\n")
            shiftData.write(commandDict[s]+"\n")
    shiftData.close()
    return convertToByte(stringList)

def FPGA_write(port, commandString, RX_ON = True):
    """Writes data to the FPGA system using pyserial.
    By default, the method will assume that you
    need to use the RX flag. For testing purposes, using RX_ON
    False will result in just the byte you specify being sent."""
    if(port.isOpen()):
        if(RX_ON):
            port.write(convertToRaw(RX))
            bytesWritten = port.write(commandString)
            port.write(convertToRaw(RX_OFF))
            print(bytesWritten)
            return bytesWritten
        else:
            port.write(convertToRaw(commandString))
    else:
        print("Serial port failure")
        raise Exception

def readData(port,lenData):
    """Reads data from the serial port to a file called shiftData.txt."""
    shiftData = open('shiftData.txt', 'wb')
    FPGA_write(port,TRANSMIT,False)
    data = port.read(lenData)
    final = convertFPGAHits(data)
    shiftData.write(final)
    shiftData.close()

def commonSetup(port,commandDict):
    """Common setup between auto and manual methods"""
    port.close()
    port.open()
    commandString = commandRead(commandDict)
    byteCMDString = convertCMDString(commandString)
    len_Data = FPGA_write(port,byteCMDString)
    return len_Data

def manual(port,commandDict):
    """The manual method of controlling T3MAPS.
    The user must manually verify each step"""
    len_Data=commonSetup(port,commandDict)
    Winput = raw_input("Write data to T3MAPS? (y/n): ")

    if (Winput.lower() == "y"):
        FPGA_write(port,WRITE,False)
        Winput2 = raw_input("Read data from FGPA fifo? (y/n): ")
        if (Winput2.lower() == "y"):
            readData(port,len_Data)
            port.close()
        else:
            print("Read aborted")
            port.close()
    else:
        print("Write aborted")
        port.close()

def auto(port,commandDict):
    """The automatic method to write a stream to control T3MAPS.
Will not lose data due to built in buffer in computer"""
    len_Data=commonSetup(port,commandDict)
    readData(port, len_Data)

#Call the main method upon execution.
if __name__ == "__main__":
    port = serial.Serial(port=COMPORT,baudrate=BAUD, bytesize=8,stopbits=1, timeout=TIMEOUT)
    manual(port,Command.set_config())
