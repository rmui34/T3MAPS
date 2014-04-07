"""
Chip module: Provides a driver class which drastically speeds up the writing
time for common tasks by choosing a custom setup for the data generator. This
class handles all of the direct writing to the chip. Also contains utility
functions to generate the binary sequences of common control patterns.
"""

#import visa
from copy import deepcopy


###############################################################################
# ChipCnfg Constants

BitDuration=1 #a bit duration as a funtion of the data generator internal bit duration
ClkUnit='0'*BitDuration+'1'*BitDuration
ClkUnitDuration=len(ClkUnit)

MAXROWS = 64

# Data generator data blocks
CNFGSIZE0=10
CNFGSIZE1=10+16+10  #16 is the number of bits in the control part of the shift register 10 and 10 are added for safety and to issue the LDSTB command
CNFGSIZE2=(MAXROWS+176)   # Number of bit per column (or double columns). This is will be use for the main pixel column but also for the dac progeamming
CNFGSIZE3=CNFGSIZE1
CNFGSIZE4=CNFGSIZE0

STRTBLKSIZE=50*ClkUnitDuration
CNFGBLKSIZE=(CNFGSIZE0+CNFGSIZE1+CNFGSIZE2+CNFGSIZE3+CNFGSIZE4)*ClkUnitDuration
ENDBLKSIZE=100*ClkUnitDuration



Blocks=['STRTBLK','CNFGBLK','ENDBLK']
BlocksDict={'STRTBLK':STRTBLKSIZE,'CNFGBLK':CNFGBLKSIZE,'ENDBLK':ENDBLKSIZE}

# List values are:
#     SEQUENCE LINE NUMBER, SEQUENCE REPITION, SEQUENCE LINE TO JUMP TO, 
#     TRIGGER WAIT FLAG, EVENT JUMP FLAG, INFINITE LOOP FLAG
SEQDict={'STRTBLK':['0','1','0','0','0','0'],
         'CNFGBLK':['1','1','0','0','0','0'],
         'ENDBLK': ['2','1','0','0','0','1']}

ALLBLKSSIZE = sum(BlocksDict.values())


# Default settings for control.
GlbRoEn='0'
SRDO_LD='0'
NCout2='0'
CntMode='0'
CntEn='0'
CntRN='0'
S0='0'
S1='0'
CnfgMode0_1='00'
LD_IN0_7='00000000'
LDENABLE_SEL='0'
SRCLR_SEL='0'
HITLD_IN='0'
NCout21_25='00000'
AddrIn0_5='111111' #11111'

# Data generator channel settings
CMOSHI=1.5
CMOSLOW=0

InputSignalsPodsDict={
'SRIN_ALL': ["PODA",8,8,CMOSHI,CMOSLOW],
'SRCK_G': ["PODA",7,7,CMOSHI,CMOSLOW],
'GCfgCK': ["PODA",6,6,CMOSHI,CMOSLOW],
'Dacld': ["PODA",5,5,CMOSHI,CMOSLOW],
'Stbld': ["PODA",4,4,CMOSHI,CMOSLOW],
'Stbclr': ["PODA",3,3,CMOSHI,CMOSLOW],
'SlAltBus': ["PODA",2,2,CMOSHI,CMOSLOW],
'CntCK': ["PODA",1,1,CMOSHI,CMOSLOW],
'SRDO_CK': ["PODA",0,0,CMOSHI,CMOSLOW],
'NU': ["PODA",9,9,CMOSHI,CMOSLOW],
'HiCf': ["PODA",10,10,CMOSHI,CMOSLOW],
'LoCf': ["PODA",11,11,CMOSHI,CMOSLOW]}

InputSignalsDefaultsDict={
'SRIN_ALL': ['0','0'],
'SRCK_G': ['0','0'],
'GCfgCK': ['0','0'],
'Dacld': ['0','0'],
'Stbld': ['0','0'],
'Stbclr': ['0','0'],
'SlAltBus': ['0','0'],
'CntCK': ['0','0'],
'SRDO_CK': ['0','0'],
'NU': ['0','0'],
'HiCf': ['0','0'],
'LoCf': ['0','0']}

# Original data generator setup.
def CreateBlocs(dgene):
    dgene.write(":DATA:BLOC:DEL:ALL")
    dgene.write(":DATA:BLOC:RENAME \"UNNAMED\",\"STRTBLK\"")
    dgene.write(":DATA:BLOC:SIZE \"STRTBLK\"," + str(ALLBLKSSIZE))

    Blkaddr=STRTBLKSIZE
    for blk in Blocks[1:]:
       dgene.write(":DATA:BLOC:ADD "+str(Blkaddr)+",\""+ blk +"\"")
       Blkaddr+=BlocksDict[blk]
    return

def initPats(i, dgene):
    if i>1 or i<0:
        i=0
    for key in InputSignalsPodsDict.keys():
        default=InputSignalsDefaultsDict[key][i][0]*ALLBLKSSIZE
        Str2Dgene=':DATA:PATT:BIT '+str(InputSignalsPodsDict[key][2])+',0,'+str(ALLBLKSSIZE)+',#'+ str(len(str(ALLBLKSSIZE)))+str(ALLBLKSSIZE)+default +'\n'
        dgene.write(Str2Dgene)
        dgene.write(':MODE:STATE ENHANCED')        
    return

def initSeqs(dgene):
    dgene.write(':DATA:SEQ:DEL:ALL')      
    for seqName in Blocks: #SEQDict.keys():
        messg=':DATA:SEQ:ADD '
        messg += SEQDict[seqName][0] + ',\"' + seqName + '\",' + SEQDict[seqName][1]+ ',' + SEQDict[seqName][2] + ',' +SEQDict[seqName][3]+ ',' +SEQDict[seqName][4]+ ',' +SEQDict[seqName][5]
        dgene.write(messg)
    return 

###############################################################################


# Utility functions

def repeat_each(string, n=2):
    """Repeat each character in string n times. """
    return ''.join((c*n for c in string))

def shift_right(string, fill='0', n=1):
    """Shift the string right by n places, filling on the left with fill. """
    if len(fill) != 1: 
        print "Fill argument should be a single character, using default '0'."
        fill = '0'
    if n > len(string):
        n = len(string)
    return fill*n + string[:len(string)-n]

def generate_clock(length, n=2, start='0'):
    if start not in ['0','1']:
        print "Invalid start specified for clock_pattern, using default '0'."
        start = '0'
    if start == '0':
        end = '1'
    else:
        end = '0'
    return ''.join((start*n + end*n for x in xrange(length)))

def binary_list(x):
    """Return a list of the binary digits of int(x). """
    x = int(x)
    return binary_list(x/2) + [x%2] if x > 1 else [x]

def filled_binary_list(x,nbits=5):
    """Return a list of length nbits of the binary digits of int(x). """
    vals = binary_list(x)
    vals = [0]*(nbits - len(vals)) + vals
    return vals[::-1]                

def binary_string(x,nbits=5,invert=False):
    """Return an nbit long string of the binary digits of int(x). """
    blist = filled_binary_list(x,nbits)
    if not invert: 
        return ''.join((str(x) for x in blist))
    else:
        return ''.join((str(x) for x in blist))[::-1]


# Pattern Generators

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

class Writer:
    def __init__(self, filename):
        self.filename = filename

    def write(self, s):
        with open(self.filename, 'a') as f:
            f.write(s)


class DgeneDriver:
    """Controls issuing commands to the a generator in an efficient way.

    Designed to help optimize programs to run certain types of commands as fast 
    as possible, by setting up the blocks and instruction sequences.

    Arguments
    dgene: The data generator instrument which will be used to send commands.
    number_instructions: The number of config blocks sent in one command.
        The default value 4 is good for most pixel based commands.
    config_size: The number of bits in a configuration block. Needs to be long 
      enough to accomodate all commands issued, but shorter is faster.
    """
    def __init__(self, dgene, number_instructions=4, config_size=None):
        self.dgene = dgene
        self.n = number_instructions
        self._n_enabled = 1
        self.blocks = deepcopy(BlocksDict)
        self.block_opts = deepcopy(SEQDict)
        self.config_size = self.blocks.pop('CNFGBLK')
        if config_size is not None:
            self.config_size = config_size
        self.config_seq = self.block_opts.pop('CNFGBLK')
        self.all_block_size = ALLBLKSSIZE

    def init_blocks(self):
        """ Setup the blocks on the data generator. """
        self.block_opts['ENDBLK'][0] = self.n + 1
        sorted_keys = ['STRTBLK']
        for i in xrange(self.n):
            sorted_keys.append('CNFGBLK%i' % i)
            self.blocks['CNFGBLK%i' % i] = self.config_size
            self.config_seq[0] = str(i + 1)
            self.block_opts['CNFGBLK%i' % i] = deepcopy(self.config_seq)
        sorted_keys.append('ENDBLK')
        self.all_block_size = sum(self.blocks.values())
        # Create the blocks
        self.dgene.write(":DATA:BLOC:DEL:ALL")
        self.dgene.write(":DATA:BLOC:RENAME \"UNNAMED\",\"STRTBLK\"")
        self.dgene.write(":DATA:BLOC:SIZE \"STRTBLK\",%i" % self.all_block_size)
        addr = self.blocks['STRTBLK']
        for block in sorted_keys[1:]:
            self.dgene.write(':DATA:BLOC:ADD %i,"%s"' % (addr, block))
            addr += self.blocks[block]
        # Init SLALTBUS to 1
        self.dgene.write(":MODE:UPDate AUTO")
        self.dgene.write(':DATA:PATT:BIT %i,0,%i,#%i%i%s\n' % (InputSignalsPodsDict['SlAltBus'][2], self.all_block_size, len(str(self.all_block_size)), self.all_block_size, '1'*self.all_block_size))
        # Write the block options
        self.dgene.write(':DATA:SEQ:DEL:ALL')
        for name in sorted_keys:
            opts = self.block_opts[name]
            self.dgene.write(':Data:SEQ:ADD %s,"%s",%s,%s,%s,%s,%s' % (opts[0],name,opts[1],opts[2],opts[3],opts[4],opts[5]))
        # Update number enabled
        self._n_enabled = self.n

    def reset_to_defaults(self):
        """ Return the data generator to the setup used by ChipCnfg.

        Notes:
        This function sets SLALTBUS to 0 in an intermediate step, and thus
        resets the entire chip to its defaults.
        There is no need to call this in between consecutive tests, as 
        long as they are all done using the pix.py/chip.py framework.
        """
        self.n = 1
        CreateBlocs(self.dgene)
        initSeqs(self.dgene)
        self.dgene.write(":MODE:UPDate MAN")
        initPats(0, self.dgene)
        self.all_block_size = ALLBLKSSIZE
        # Init SLALTBUS to 1
        self.dgene.write(':DATA:PATT:BIT %i,0,%i,#%i%i%s\n' % (InputSignalsPodsDict['SlAltBus'][2], self.all_block_size, len(str(self.all_block_size)), self.all_block_size, '1'*self.all_block_size))
        self.dgene.write(':DATA:UPDate')
        self._n_enabled = 1;

    def write_blocks(self, commands, outfile=None):
        """ Write the commands contained in commands.

        Commands should be a list of dictionaries. Each list is sent as a
        separate command. Each dictionary key is the channel to write to and
        each value is a list of blocks to write. The list of blocks are written
        in as few commands as possible given the current setup.
        """
        for command in commands:
            instructions = []
            for key, block_list in command.iteritems():
                split_lists = [block_list[i:i+self.n] for i in xrange(0, len(block_list), self.n)]
                for i,split_list in enumerate(split_lists):
                    if len(split_list) < self.n:
                        split_list += (self.n - len(split_list)) * ['0' * self.config_size]
                    subcommand = '0'*self.blocks['STRTBLK']
                    subcommand += ''.join(split_list)
                    subcommand += '0'*self.blocks['ENDBLK']
                    if len(subcommand) != self.all_block_size:
                        print "The subcommand is %i bits and should be %i bits." % (len(subcommand),self.all_block_size)
                    if len(instructions) < i + 1:
                        instructions.append([])
                    output = ':DATA:PATT:BIT %i,0,%i,#%i%i%s\n' % (InputSignalsPodsDict[key][2], self.all_block_size, len(str(self.all_block_size)), self.all_block_size, subcommand)
                    instructions[i].append(output)
            for instruction in instructions:
                instruction.insert(0,'MODE:UPDate MAN')
                instruction.append('DATA:UPDate')
                instruction.append('*TRG')
                if outfile is not None:
                    outfile.write('; '.join(instruction))
                for outstr in instruction:
                    self.dgene.write(outstr)
                

    def _gen_config_command(self, pattern, load_dacs=True, load_control=True, clone=True):
        # Generate a command which will be used to program config.
        # First entry is the actual command and second entry is a zeroing command.
        # The entries are dictionaries of channel:[single_block]
        load_dacs = '1' if load_dacs else '0'
        load_control = '1' if load_control else '0'

        SregData=repeat_each(pattern,ClkUnitDuration)
        SregPat='0'*(CNFGSIZE0*ClkUnitDuration) + SregData+'0'*(self.config_size-(CNFGSIZE0*ClkUnitDuration)-len(SregData))
        SregPat=shift_right(SregPat)

        ClkData=generate_clock(len(pattern),BitDuration)
        ClkPat='0'*(CNFGSIZE0*ClkUnitDuration)+ClkData+'0'*(self.config_size-(CNFGSIZE0*ClkUnitDuration)-len(ClkData))

        # Make sure the load (ctrl and dac) are set correctly 
        LDZeroLengthBefore=(CNFGSIZE0*ClkUnitDuration)+ len(ClkData) + 2
        LDPatLength=4
        LDPat='0'*LDZeroLengthBefore + load_control*LDPatLength + '0'*(self.config_size-LDPatLength-LDZeroLengthBefore)
        LD_dacsPat='0'*LDZeroLengthBefore + load_dacs*LDPatLength + '0'*(self.config_size-LDPatLength-LDZeroLengthBefore)

        # Store instructions to return
        commands = []
        zero = self.config_size*'0'
        if clone:
            commands = [{'Stbld':[LDPat],'Dacld':[LD_dacsPat],'GCfgCK':[ClkPat],'NU':[ClkPat],'SRIN_ALL':[SregPat]},
                        {'Stbld':[zero],'Dacld':[zero],'GCfgCK':[zero],'NU':[zero],'SRIN_ALL':[zero]}]
        else:
            commands = [{'Stbld':[LDPat],'Dacld':[LD_dacsPat],'GCfgCK':[ClkPat],'SRIN_ALL':[SregPat]},
                        {'Stbld':[zero],'Dacld':[zero],'GCfgCK':[zero],'SRIN_ALL':[zero]}]
        return commands


    def _gen_column_command(self, pattern, clone=True):
        # Generate a command which will be used to program a column.
        # First entry is the actual command and second entry is a zeroing command.
        # The entries are dictionaries of channel:[single_block]
        if len(pattern) != MAXROWS:
            print "Invalid pattern length for program_column (should be %i). Appending zeroes." % MAXROWS
            pattern += '0'*(MAXROWS - len(pattern))

        colSreg=pattern[::-1]
        SregData=repeat_each(colSreg,ClkUnitDuration)
        SregPat='0'*(CNFGSIZE0*ClkUnitDuration)+SregData+'0'*(self.config_size-(CNFGSIZE0*ClkUnitDuration)-len(SregData))
        SregPat=shift_right(SregPat)
        ClkData=generate_clock(len(colSreg),BitDuration)
        ClkPat='0'*(CNFGSIZE0*ClkUnitDuration)+ClkData+'0'*(self.config_size-(CNFGSIZE0*ClkUnitDuration)-len(ClkData))

        # Store instructions to return
        zero = self.config_size*'0'
        if clone:
            commands = [{'SRCK_G':[ClkPat], 'NU':[ClkPat], 'SRIN_ALL':[SregPat]},
                        {'SRCK_G':[zero], 'NU':[zero], 'SRIN_ALL':[zero]}]
        else:
            commands = [{'SRCK_G':[ClkPat], 'SRIN_ALL':[SregPat]},
                        {'SRCK_G':[zero], 'SRIN_ALL':[zero]}]            
        return commands

    def _combine_commands(self, *commands):
        # Expect the commands to be in the order they should be sent.
        keys = reduce(lambda s1,s2: set.union(s1,s2), [set(command.keys()) for command in commands ])
        output = dict((key,[]) for key in keys)
        for command in commands:
            n_instr = len(command.values()[0])
            for key in keys:
                if key in command: 
                    output[key] += command[key]
                else:
                    zero = [self.config_size*'0']*n_instr
                    output[key] += zero
        return output

    def program_config(self, pattern, load_control=True, load_config=True, clone=True, zero=True):
        """ Program the configuration bits on the chip."""
        command, zero = self._gen_config_command(pattern, load_control, load_config, clone)
        if zero:
            commands = [command, zero]
        else:
            commands = [command]
        self.write_blocks(commands)
        return

    def program_column(self, pattern, clone=True):
        """ Program the column bits on the chip."""
        commands = self._gen_column_command(pattern, clone)
        # don't write the zero command
        self.write_blocks(commands[:-1])
        return

    def readout_single_pixel(self, row, clone=True):
        """ Set the column SR to readout the specified pixel. """
        self.program_column(''.join(['0' if i != row else '1' for i in xrange(MAXROWS)]))

    def enable_single_pixel(self, col, row, dacbits='00000', zero=False, **kwargs):
        """ Enable a single pixel to inject charge and output on hitOr. """
        ldbus = '011' + dacbits # enable hit, inject, and dacbit pattern
        pix_pattern = ''.join(['0' if i != row else '1' for i in xrange(MAXROWS)])
        load_pattern = get_control_pattern_pixel(col,config_bits=ldbus,lden='1')[::-1] 
        def_pattern = get_control_pattern_pixel(col, **kwargs)[::-1]
    
        instr1, zero_config = self._gen_config_command(def_pattern, False, True) # point sr to correct column 
        instr2, zero_column = self._gen_column_command(pix_pattern, col)         # program the column sr      
        instr3 = self._gen_config_command(load_pattern, False, True)[0]          # load the ldbus pattern     
        instr4 = self._gen_config_command(def_pattern, False, True)[0]           # return load to zero        
        
        if zero:
            commands = [self._combine_commands(instr1,instr2,instr3,instr4), self._combine_commands(zero_config,zero_column)]
        else:
            commands = [self._combine_commands(instr1,instr2,instr3,instr4)]
        self.write_blocks(commands)
        return


    def write_pixel_pattern(self, col, pattern, dacindex=0, zero=False):
        """ Enable a single pixel to inject charge and output on hitOr. """
        dacbits = ''.join(('1' if x == dacindex else '0' for x in xrange(5)))
        ldbus = '000' + dacbits 
        pix_pattern = pattern
        load_pattern = get_control_pattern_pixel(col,config_bits=ldbus,lden='1')[::-1] 
        def_pattern = get_control_pattern_pixel(col)[::-1]
        instr1, zero_config = self._gen_config_command(def_pattern, False, True) # point sr to correct column 
        instr2, zero_column = self._gen_column_command(pix_pattern, col)         # program the column sr      
        instr3 = self._gen_config_command(load_pattern, False, True)[0]          # load the ldbus pattern     
        instr4 = self._gen_config_command(def_pattern, False, True)[0]           # return load to zero        
        
        if zero:
            commands = [self._combine_commands(instr1,instr2,instr3,instr4), self._combine_commands(zero_config,zero_column)]
        else:
            commands = [self._combine_commands(instr1,instr2,instr3,instr4)]
        self.write_blocks(commands)
        return

    def clear_single_column(self, col, zero=False):
        """ Set all bits to zero for every pixel on column. """
        ldbus = '11111111' # load all to write zero to all
        pix_pattern = ''.join(['0' for i in xrange(MAXROWS)])
        load_pattern = get_control_pattern_pixel(col,config_bits=ldbus,lden='1')[::-1] 
        def_pattern = get_control_pattern_pixel(col)[::-1]
        instr1, zero_config = self._gen_config_command(def_pattern, False, True) # point sr to correct column 
        instr2, zero_column = self._gen_column_command(pix_pattern, col)         # program the column sr      
        instr3 = self._gen_config_command(load_pattern, False, True)[0]          # load the ldbus pattern     
        instr4 = self._gen_config_command(def_pattern, False, True)[0]           # return load to zero        
        
        if zero:
            commands = [self._combine_commands(instr1,instr2,instr3,instr4), self._combine_commands(zero_config,zero_column)]
        else:
            commands = [self._combine_commands(instr1,instr2,instr3,instr4)]
        self.write_blocks(commands)
        return

    def clear_all_columns(self, zero=False):
        """ Set all bits to zero for every pixel. """
        ldbus = '11111111' # load all to write zero to all
        pix_pattern = ''.join(['0' for i in xrange(MAXROWS)])
        load_pattern = get_control_pattern_pixel(0,config_bits=ldbus,lden='1',config_mode='11')[::-1] 
        def_pattern = get_control_pattern_pixel(0, config_mode='11')[::-1]
        instr1, zero_config = self._gen_config_command(def_pattern, False, True) # point sr to correct column 
        instr2, zero_column = self._gen_column_command(pix_pattern, 0)         # program the column sr      
        instr3 = self._gen_config_command(load_pattern, False, True)[0]          # load the ldbus pattern     
        instr4 = self._gen_config_command(def_pattern, False, True)[0]           # return load to zero        
        
        if zero:
            commands = [self._combine_commands(instr1,instr2,instr3,instr4), self._combine_commands(zero_config,zero_column)]
        else:
            commands = [self._combine_commands(instr1,instr2,instr3,instr4)]
        self.write_blocks(commands)
        return

    def disable_single_column(self, col, zero=False):
        """ Disable hit/inject on every pixel on the column. """
        ldbus = '01100000' # write zeroes to hit, inject
        pix_pattern = ''.join(['0' for i in xrange(MAXROWS)])
        load_pattern = get_control_pattern_pixel(col,config_bits=ldbus,lden='1')[::-1] 
        def_pattern = get_control_pattern_pixel(col)[::-1]
        instr1, zero_config = self._gen_config_command(def_pattern, False, True) # point sr to correct column 
        instr2, zero_column = self._gen_column_command(pix_pattern, col)         # program the column sr      
        instr3 = self._gen_config_command(load_pattern, False, True)[0]          # load the ldbus pattern     
        instr4 = self._gen_config_command(def_pattern, False, True)[0]           # return load to zero        
        
        if zero:
            commands = [self._combine_commands(instr1,instr2,instr3,instr4), self._combine_commands(zero_config,zero_column)]
        else:
            commands = [self._combine_commands(instr1,instr2,instr3,instr4)]
        self.write_blocks(commands)
        return

    def disable_all_columns(self, zero=False):
        """ Disable hit/inject on every pixel. """
        ldbus = '01100000' # write zeroes to hit, inject
        pix_pattern = ''.join(['0' for i in xrange(MAXROWS)])
        load_pattern = get_control_pattern_pixel(0,config_bits=ldbus,lden='1',config_mode='11')[::-1] 
        def_pattern = get_control_pattern_pixel(0, config_mode='11')[::-1]
        instr1, zero_config = self._gen_config_command(def_pattern, False, True) # point sr to correct column 
        instr2, zero_column = self._gen_column_command(pix_pattern, 0)         # program the column sr      
        instr3 = self._gen_config_command(load_pattern, False, True)[0]          # load the ldbus pattern     
        instr4 = self._gen_config_command(def_pattern, False, True)[0]           # return load to zero        
        
        if zero:
            commands = [self._combine_commands(instr1,instr2,instr3,instr4), self._combine_commands(zero_config,zero_column)]
        else:
            commands = [self._combine_commands(instr1,instr2,instr3,instr4)]
        self.write_blocks(commands)
        return

    def disable_hitor_all_columns(self, zero=False):
        """ Disable hit/inject on every pixel. """
        ldbus = '10000000' # write 1 to hit_or_not
        pix_pattern = ''.join(['1' for i in xrange(MAXROWS)])
        load_pattern = get_control_pattern_pixel(0,config_bits=ldbus,lden='1',config_mode='11')[::-1] 
        def_pattern = get_control_pattern_pixel(0, config_mode='11')[::-1]
        instr1, zero_config = self._gen_config_command(def_pattern, False, True) # point sr to correct column 
        instr2, zero_column = self._gen_column_command(pix_pattern, 0)         # program the column sr
        instr3 = self._gen_config_command(load_pattern, False, True)[0]          # load the ldbus pattern     
        instr4 = self._gen_config_command(def_pattern, False, True)[0]           # return load to zero        
        
        if zero:
            commands = [self._combine_commands(instr1,instr2,instr3,instr4), self._combine_commands(zero_config,zero_column)]
        else:
            commands = [self._combine_commands(instr1,instr2,instr3,instr4)]
        self.write_blocks(commands)
        return

    def enable_hitor_all_columns(self, zero=False):
        """ Disable hit/inject on every pixel. """
        ldbus = '10000000' # write 0 to hit_or_not
        pix_pattern = ''.join(['0' for i in xrange(MAXROWS)])
        load_pattern = get_control_pattern_pixel(0,config_bits=ldbus,lden='1',config_mode='11')[::-1] 
        def_pattern = get_control_pattern_pixel(0, config_mode='11')[::-1]
        instr1, zero_config = self._gen_config_command(def_pattern, False, True) # point sr to correct column 
        instr2, zero_column = self._gen_column_command(pix_pattern, 0)         # program the column sr      
        instr3 = self._gen_config_command(load_pattern, False, True)[0]          # load the ldbus pattern     
        instr4 = self._gen_config_command(def_pattern, False, True)[0]           # return load to zero        
        
        if zero:
            commands = [self._combine_commands(instr1,instr2,instr3,instr4), self._combine_commands(zero_config,zero_column)]
        else:
            commands = [self._combine_commands(instr1,instr2,instr3,instr4)]
        self.write_blocks(commands)
        return

    def enable_single_column(self, col, dacbits='00000', zero=False):
        """ Enable a single column to inject charge and output on hitOr. """
        ldbus = '011' + dacbits # enable hit, inject
        pix_pattern = ''.join(['1' for i in xrange(MAXROWS)]) # enable all pixels
        load_pattern = get_control_pattern_pixel(col,config_bits=ldbus,lden='1')[::-1] 
        def_pattern = get_control_pattern_pixel(col)[::-1]
        instr1, zero_config = self._gen_config_command(def_pattern, False, True) # point sr to correct column 
        instr2, zero_column = self._gen_column_command(pix_pattern, col)         # program the column sr      
        instr3 = self._gen_config_command(load_pattern, False, True)[0]          # load the ldbus pattern     
        instr4 = self._gen_config_command(def_pattern, False, True)[0]           # return load to zero        
        
        if zero:
            commands = [self._combine_commands(instr1,instr2,instr3,instr4), self._combine_commands(zero_config,zero_column)]
        else:
            commands = [self._combine_commands(instr1,instr2,instr3,instr4)]
        self.write_blocks(commands)
        return

    def enable_hitor_single_column(self, col, zero=False):
        """ Enable a single column to inject charge and output on hitOr. """
        ldbus = '10000000'# enable hit, inject
        pix_pattern = ''.join(['0' for i in xrange(MAXROWS)]) # enable hitor pixels
        load_pattern = get_control_pattern_pixel(col,config_bits=ldbus,lden='1')[::-1] 
        def_pattern = get_control_pattern_pixel(col)[::-1]
        instr1, zero_config = self._gen_config_command(def_pattern, False, True) # point sr to correct column 
        instr2, zero_column = self._gen_column_command(pix_pattern, col)         # program the column sr      
        instr3 = self._gen_config_command(load_pattern, False, True)[0]          # load the ldbus pattern     
        instr4 = self._gen_config_command(def_pattern, False, True)[0]           # return load to zero        
        
        if zero:
            commands = [self._combine_commands(instr1,instr2,instr3,instr4), self._combine_commands(zero_config,zero_column)]
        else:
            commands = [self._combine_commands(instr1,instr2,instr3,instr4)]
        self.write_blocks(commands)
        return

    def enable_hitor_single_pixel(self, col, row, zero=False):
        """ Enable a single column to inject charge and output on hitOr. """
        ldbus = '10000000'# enable hit, inject
        pix_pattern = ''.join(['1' if i != row else '0' for i in xrange(MAXROWS)])
        load_pattern = get_control_pattern_pixel(col,config_bits=ldbus,lden='1')[::-1] 
        def_pattern = get_control_pattern_pixel(col)[::-1]
        instr1, zero_config = self._gen_config_command(def_pattern, False, True) # point sr to correct column 
        instr2, zero_column = self._gen_column_command(pix_pattern, col)         # program the column sr      
        instr3 = self._gen_config_command(load_pattern, False, True)[0]          # load the ldbus pattern     
        instr4 = self._gen_config_command(def_pattern, False, True)[0]           # return load to zero        
        
        if zero:
            commands = [self._combine_commands(instr1,instr2,instr3,instr4), self._combine_commands(zero_config,zero_column)]
        else:
            commands = [self._combine_commands(instr1,instr2,instr3,instr4)]
        self.write_blocks(commands)
        return

    def enable_all_columns(self, dacbits='00000', zero=False):
        """ Enable all columns to inject charge and output on hitOr. 

        Notes:
        Important to realize that this also enables cols 0,17.
        """
        ldbus = '011' + dacbits # enable hit, inject
        pix_pattern = ''.join(['1' for i in xrange(MAXROWS)]) # enable all pixels
        load_pattern = get_control_pattern_pixel(0,config_bits=ldbus,lden='1',config_mode='11')[::-1] 
        def_pattern = get_control_pattern_pixel(0, config_mode='11')[::-1]
        instr1, zero_config = self._gen_config_command(def_pattern, False, True) # point sr to correct column 
        instr2, zero_column = self._gen_column_command(pix_pattern, 0)         # program the column sr      
        instr3 = self._gen_config_command(load_pattern, False, True)[0]          # load the ldbus pattern     
        instr4 = self._gen_config_command(def_pattern, False, True)[0]           # return load to zero        
        
        if zero:
            commands = [self._combine_commands(instr1,instr2,instr3,instr4), self._combine_commands(zero_config,zero_column)]
        else:
            commands = [self._combine_commands(instr1,instr2,instr3,instr4)]
        self.write_blocks(commands)
        return

    def enable_count_clock(self, freq=50):
        """ Enable the external counting clock. 

        Notes:
        The option period argument sets the number of cycles high/low
        for each clock unit. This can be used to alter the effective
        frequency. The minimum is period=2. There will be some edge
        effects where the cycle repeats though, because the length
        is not guarunteed to be a multiple of the clock pattern.
        Also, don't use a period greater than ~50, because the length of
        the repeating piece is only 400.
        """
        if freq > 50:
            print "Maximum frequency is 50 MHz."
            freq = 50
        if freq < 1e-3:
            print "Frequencies lower than 1 KHz not supported."
            freq = 1e-3
        period = 2

        clock_pattern = ('0'*period + '1'*period) * (self.all_block_size // (2*period) + 1)
        clock_pattern = clock_pattern[:self.all_block_size]
        if freq > 1:
            self.dgene.write(':SOURCE:OSCILLATOR:INTERNAL:FREQUENCY %iMHZ' % (4*freq))
        if freq < 1:
            self.dgene.write(':SOURCE:OSCILLATOR:INTERNAL:FREQUENCY %iKHZ' % (4*1000*freq))
        self.dgene.write(':DATA:PATT:BIT %i,0,%i,#%i%i%s\n' % (InputSignalsPodsDict['CntCK'][2], self.all_block_size, len(str(self.all_block_size)), self.all_block_size, clock_pattern))        
        return

    def disable_count_clock(self):
        """ Disable the external counting clock."""
        clock_pattern_disable = '0' * self.all_block_size
        self.dgene.write(':DATA:PATT:BIT %i,0,%i,#%i%i%s\n' % (InputSignalsPodsDict['CntCK'][2], self.all_block_size, len(str(self.all_block_size)), self.all_block_size, clock_pattern_disable))        
        self.dgene.write(':SOURCE:OSCILLATOR:INTERNAL:FREQUENCY 200MHZ' )
        return

# End of class Driver


###############################################################################
# GPIB Class and Initializations

# Currently, the only used instruments are 
GpibInstDict={"TDS754":"1","DG2020":"3","HPPSUPLY":"6","HPLA":"7","HPGENE":"5","HPCNTR":"10","TAWG":"4","KT2002":"16","KT237":"17","KT237b":"15","KT2000":"18","LECGENE":"2","KT2410":"13"}


#class GpibInst(visa.GpibInstrument):
 #   def __init__(self,name):       
   #     visa.GpibInstrument.__init__(self,"GPIB::"+GpibInstDict[name],board_number=0)
   # def finished(self):
    #    self.write("*OPC?")
     #   if self.read()[0] == '1':
     #       return True
      #  else:
       #     return False

        
def init_hpgene(hpgene, ninjects=255):
    hpgene.write("*RST")
    hpgene.write("*CLS")
    hpgene.write("*ESE 1")
    hpgene.write("*SRE 16")
    hpgene.write("*OPC")
    while hpgene.finished() is False: pass

    hpgene.write("FUNC:USER NRAMP")
    while not hpgene.finished() : pass

    hpgene.write("FUNC:SHAP USER")
    while not hpgene.finished() : pass

    hpgene.write("VOLT 0.2")
    hpgene.write("VOLT:OFFSet 0.0")

    hpgene.write("OUTPut:LOAD 50")

    hpgene.write("TRIGger:SOURce BUS")

    hpgene.write("BM:SOURce INT")

    hpgene.write("BM:NCYC %i" % ninjects)
    hpgene.write("FREQ 10000")
    hpgene.write("BM:STATe ON")
    return

def init_hpcntr(hpcntr):
    hpcntr.write("*RST");
    hpcntr.write("*CLS");
    hpcntr.write("*OPC");
    
    hpcntr.write(":CONF:TOT:CONT (@1),(@1)")
    hpcntr.write(":INIT:CONT OFF")

    hpcntr.write(":INP1:COUP DC")
    hpcntr.write(":INP1:IMP MAX")

    hpcntr.write(":INP:LEV:AUTO 0")
    hpcntr.write(":INP:LEV 0.5")

    hpcntr.write(":INP1:SLOP NEG")
    hpcntr.write(":INP1:ATT 1")

    hpcntr.write(":SENS:ACQ:HOFF:STAT ON")
    hpcntr.write(":SENS:ACQ:HOFF:TIME 10e-6")
    return

#dgene=GpibInst("DG2020")
#hpgene=GpibInst("HPGENE")
#hpcntr=GpibInst("HPCNTR")
