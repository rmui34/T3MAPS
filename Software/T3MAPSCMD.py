__author__ = 'Maximilian Golub'
import serial
import io
import pix
import chip
import os
from pycallgraph import PyCallGraph
from pycallgraph.output import GraphvizOutput

BAUD = 9600
COMPORT = 'COM7'
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
#TX_OFF = '10101010';

class RawConversionException(Exception):
        def __init__(self, value):
                self.value = value
        def __str__(self):
                return repr(self.value)

def graph():
        with PyCallGraph(output=GraphvizOutput()):
                commandString = patternRead()

def manual(port):
        port.open()
        commandString = patternRead()
        byteCMDString = convertCMDString(commandString)
        FPGA_write(port,byteCMDString)
        Winput = raw_input("Write data to T3MAPS? (Y/N): ")
        if (Winput == "Y"):
                FPGA_write(port,WRITE,False)
                Winput2 = raw_input("Read data from FGPA fifo? (Y/N): ")
                if (Winput2 == "Y"):
                        readData(port)
                        port.close()
                else:
                        print("Read aborted")
                        port.close()
        else:
                print("Write aborted")
                port.close()

def auto(port):
        port.open()
        commandString = patternRead()
        byteCMDString = convertCMDString(commandString)
        FPGA_write(port,byteCMDString)
        check = raw_input("Are you sure you want to run? (Y/N): ")
        if (check.lower() == "y"):
                FPGA_write(port, byteCMDString)
                port.close()
        else:
                print("Aborted.")
                port.close()

def readData(port):
        shiftData = open('shiftData.txt', 'w')
        FPGA_write(port,TRANSMIT,False)
        data = port.read(400)
        print("Data read")
        print(data)
        shiftData.write(data)
        shiftData.close()

def parseData(data):
        parseData_file = open('parsedData.txt', 'w')
        for x in xrange(0, len(data), 8):
                slice = data[x:x+7]
                print(len(slice))
                parseData_file.write('{0:08b}'.format(slice))

def encode(byte):
        #if(len(byte)==8):
        temp = ""
        temp += onezero(byte)
        #else:
        #        print(len(byte))
        #        raise RawConversionException

def onezero(bit):
        byteS = ""
        for x in bit:
                if(x == 1):
                       byteS += "1"
                else:
                        byteS += "0"
        return byteS[::-1]

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

def convertCMDString(stringList):
        byteList = ''
        for x in range(0,len(stringList),8):
                byteList += convertToRaw(stringList[x:x+8])
        return byteList

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

def genFinalBits(stringList):
        finalBytes = ''
        finalBits = []
        #stringList = [Dacld, Stbld, SRCK_G, GCfgCK, SRIN_ALL, NU, NU, NU]
        for x in range(VAL-5):
                for y in (stringList):
                        #print(x)
                        finalBits.append(y[x])
        return finalBytes.join(finalBits)

def rx_test(port):
        FPGA_write(port,RX, False)
        for x in range(250):
                FPGA_write(port, "10101010", False)
                FPGA_write(port, "01010101", False)
                print(x)
        FPGA_write(port, RX_OFF, False)
        FPGA_write(port,WRITE,False)
        port.close()

#Call the main method upon execution.
if __name__ == "__main__":
        port = serial.Serial(port=COMPORT,baudrate=BAUD, bytesize=8,stopbits=1, timeout=TIMEOUT)
        manual()
