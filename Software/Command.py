__author__ = 'Maximilian Golub','Bo Wang'

from collections import defaultdict

#Number of rows in each pixel column
MAXROWS = 64

#These are bits that are not used in command generation, Everything associated with count is not working
GLOBAL_READOUT_ENABLE='0'
SRDO_LOAD='0'
NCOUT2='0'
COUNT_HITS_NOT='0'
COUNT_ENABLE='0'
COUNT_CLEAR_NOT='0'
SRCLR_SEL='0'
NCOUT21_25='00000'
LSB_SIX_BITS=GLOBAL_READOUT_ENABLE+SRDO_LOAD+NCOUT2+COUNT_HITS_NOT+COUNT_ENABLE+COUNT_CLEAR_NOT
TDAC = '00000'

#######################################################################################################################
# Utility Functions
def generate_clock(length, n=1, start='0'):
    """Generate a clock pattern with n*2 bits as a period"""
    if start not in ['0','1']:
        print "Invalid start specified for clock_pattern, using default '0'."
        start = '0'
    if start == '0':
        end = '1'
    else:
        end = '0'
    return ''.join((start*n + end*n for x in xrange(length)))

def binary_string(string,bits):
    """Convert a string or integer to it's binary string form
    of n bits"""
    b_string = bin(int(string))[2:]
    if(len(b_string) < bits):
        b_string = '0'*(bits-len(b_string))+b_string
    return b_string
#######################################################################################################################
# Basic Command construction
# Commands are reversed because we are using a shift register
def get_control_pattern(col,hit_or = '0', hit='0',inject='0',lden='0',S0='0',S1='0', hitld_in = '0', config_mode='00'):
    """This is the last 32 bits(Counting from LSB) out of 176 bits in the configuration register
    Whenever you want to generate a pixel command, you have to set the configuration first
    Every parameter can be found in FEI4 manual, lden is the load enable signal for pixel register"""
    column_address = binary_string(col, 6)
    return (LSB_SIX_BITS + S0 + S1 + config_mode + hit_or + hit + inject + TDAC + lden + SRCLR_SEL + hitld_in + NCOUT21_25 + column_address)[::-1]

def get_dac_pattern(vth=150, DisVbn=49, VbpThStep=100, PrmpVbp=142, PrmpVbnFol=35, PrmpVbf=11): # fol35 vbp142 vbf11
    """This is the first 144bit(Counting from LSB) out of 176 bits in the configuration register,
    It is only called once during the set_config command, and never changed afterwards"""
    default=binary_string(129,8)# just for padding, no special meaning
    return (default*4 + binary_string(DisVbn,8) + default*6 + binary_string(VbpThStep,8) + binary_string(PrmpVbp,8) + binary_string(PrmpVbnFol,8) + binary_string(vth,8) + binary_string(PrmpVbf,8) + default*2)[::-1]

def pixel_command(row,num,is_hit_or=True,enable=True):
    """This method generates a pixel command, which start at row and enables num pixels after it.
    Pixel index Starts with row 0
    hit_or True, enable True: enable command for hit_or
    hit_or True, enable False: disable command for hit_or
    hit_or False, enable True: enable command for hit_inject
    hit_or False, enable False, disable command for hit_inject"""
    if (is_hit_or and enable) or (not is_hit_or and not enable):
        return ('1'*(row)+'0'*num+ '1'*(MAXROWS-row-num))[::-1]
    else:
        return ('0'*(row)+'1'*num+ '0'*(MAXROWS-row-num))[::-1]
#######################################################################################################################
#CommandDict Generation and combine
def _gen_single_command(pattern, load_dacs=False, load_control=True, config=True):
    """Generate a command dictionary
     if config True, generate a config command, else generate a column command
    a pulse on load_dacs loads the first 144 bits in the config shift register
    a pulse on load_control loads the last 32 bits in the config shift register
    By default, this does not load the first 144 bits"""
    load_dacs = '1' if load_dacs else '0'
    load_control = '1' if load_control else '0'

    SregPat=''.join([bit*2 for bit in pattern])+4*'0'+'1'
    ClkPat=generate_clock(len(pattern))+4*'0'+'1'

    # Make sure the load (ctrl and dac) are set correctly
    LDZeroLengthBefore= len(SregPat) - 3
    LDPat='0'*LDZeroLengthBefore + load_control*2+'0'
    LD_dacsPat='0'*LDZeroLengthBefore + load_dacs*2+'0'
    emptyPat='0'*len(LDPat)
    SlAltBusPat='1'*(len(LDPat)-1)+'0'

    if(config):
        commands_dict = {'Stbld':LDPat,'Dacld':LD_dacsPat,'GCfgCK':ClkPat,'SRIN_ALL':SregPat,'SRCK_G':emptyPat,'SlAltBus':SlAltBusPat,'NU':emptyPat}
    else:
        commands_dict = {'Stbld':emptyPat,'Dacld':emptyPat,'GCfgCK':emptyPat,'SRIN_ALL':SregPat,'SRCK_G':ClkPat,'SlAltBus':SlAltBusPat,'NU':emptyPat}
    return commands_dict

def command_Dict_combine(*args):
    """Combining multiple command dictionaries, this used in more complex commands associated with pixel commands"""
    combined_dict=defaultdict(str)
    for dict in args:
        for key in dict.keys():
            combined_dict[key]+=dict[key]
    return combined_dict
########################################################################################################################
#Complex command dictionary generation
def set_config(vth=150,PrmpVbp=142,PrmpVbf=11,config_mode="00"):
    return _gen_single_command(get_dac_pattern(vth,PrmpVbp,PrmpVbf)+get_control_pattern(63,config_mode),load_dacs=True)

def point_to_column(col,config_mode):
    """Used only in pixel commands to point the shift_register to correct column"""
    return _gen_single_command(get_control_pattern(col,config_mode))

def load_pixel_reg(row,is_hit_or,num,enable):
    return _gen_single_command(pixel_command(row,num,is_hit_or,enable))

def load_ldbus(col,hit_or,hit,inject):
    return _gen_single_command(get_control_pattern(col,hit_or=str(hit_or),hit=str(hit),inject=str(inject),lden="1"))

def hitor_hit_inject(col=0,row=0,is_hit_or=True,single_pixel=False,single_column=False,all=False,enable=True):
    """hit_or, hit, inject manipulation"""
    if(is_hit_or):
        hit_or,hit,inject=1,0,0
    else:
        hit_or,hit,inject=0,1,1
    if(all):
        config_mode="11"
    elif(single_column or single_pixel):
        config_mode = "00"
        if(single_column):
            num=64
        else:
            num=1
    else:
        raise Exception
    return command_Dict_combine(point_to_column(col,config_mode),load_pixel_reg(row,is_hit_or,num,enable),load_ldbus(col,hit_or,hit,inject),point_to_column(col,config_mode))

