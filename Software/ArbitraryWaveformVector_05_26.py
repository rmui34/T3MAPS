###############################################################################
# GPIB Class and Initializations

import visa
from struct import pack
import time

GpibInstDict={"TDS754":"1","DG2020":"3","HPPSUPLY":"6","HPLA":"7","HPGENE":"5","HPCNTR":"10","TAWG":"4","KT2002":"16","KT237":"17","KT237b":"15","KT2000":"18","LECGENE":"2","KT2410":"13"}

"""class GpibInst():
    def __init__(self):       
        rm = visa.ResourceManager()
        dsgene = rm.get_instrument('GPIB::19')"""

class GpibInst(visa.GpibInstrument):
    __GPIB_ADDRESS = 19

    def __init__(self,reset=True):       
        visa.GpibInstrument.__init__(self, self.__GPIB_ADDRESS, timeout=30)

    # create a pulse
    def init_dsgene(self, numVertex): # runs wave
    	self.write("*CLS") # clears standard event status byte
        self.write("*SRE 16") # enable "message available" bit (sees if data is in the output buffer)

        checkSum = 0 # initialize checksum
        data = [0, 0, 100, 0, 101, -2047, 200, 0]
        for i in range(0, len(data)):
            checkSum += data[i]

        self.write("LDWF?1, 4") #checks if machine is ready to download waveform ("0" --> point format)
	
	if self.read() != "1":
		print "Error with LDWF"
		quit()

        print data
	
	out = ""

        for count in range(len(data)):
            self.write(pack('H',data[count]))
		#self.write(chr(data[count]))

	self.write(pack('H',checkSum))
	#self.write(chr(checkSum))

        self.write("FUNC 5") # sets to arbitrary waveform


#def __main__():
print "Step1"
generator=GpibInst()
print "Step2"
generator.init_dsgene(4)
print "Step3"


'''    def finished(self):
        self.write("*SRE? 7")
        return self.read()[0] == '1'

    def read(self, command):
        self.write(command)
        return self.read_raw() '''


