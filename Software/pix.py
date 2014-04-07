"""
Pix module: contains methods to write and read pixel data, and
to make measurements of the chip. (Currently using the HitOr and
Counter and occasionally the MSO4104.) Several methods also save 
the state of the chip on completion, to help skip unnecessary 
steps. (e.g. whether or not the dacs of the pixels are set.)
"""

import random
import sys
import time
import os
import argparse

import chip
#import dscope
#import numpy as np
#from scipy.optimize import leastsq
#from scipy.special import erf



def vth_to_electrons(vth):
    """ Converts Voltage (V) for injection to electron equivalent. """
    return vth * 2.27e-15 / (1.602e-19)


def binary_list(x):
    """ Returns a list of the binary digits for an integer x. """
    return binary_list(x/2) + [x%2] if x > 1 else [x]


def filled_binary_list(x,nbits=5):
    """ Returns a list of length nbits of the binary digits for an integer x. """
    vals = binary_list(x)
    if len(vals) > nbits:
        print 'Too large an integer (%i) to fit in %i bits.' % (x,nbits)
        raise ValueError
    vals = [0]*(nbits - len(vals)) + vals
    return vals[::-1]
                

def binary_string(x,nbits=5):
    """ Returns a string of 0/1 of the binary digits of x. """
    blist = filled_binary_list(x,nbits)
    return ''.join((str(x) for x in blist))

def interpret_dac_value(value):
    """ Converts a variety of input types (binary_string, binary_list, ...) into a 0-31 integer. """
    try:
        if type(value) == str and len(value) == 5:
            return interpret_dac_value(list(value))
        elif type(value) == str:
            return interpret_dac_value(int(value))
        elif type(value) == list:
            if type(value[0]) == int:
                return interpret_dac_value(sum(2**i * val for i,val in enumerate(value)))
            else:
                return interpret_dac_value([int(i) for i in value])
        elif type(value) == int:
            if value > 31 or value < 0:
                raise ValueError
            return value
        else:
            raise ValueError
    except ValueError:
        raise ValueError('Could not interpret dac value: %s, should fall within [0,31].' % value)


class State:
    """State class, which records the state of the chip.

    Notes:
    The state is saved to/read from state.dat. This is used
    to allow the state setting functions (such as setting the
    dacs of every pixel to tuned values) to be skipped when
    they are note necessary. 
    Currently state records the following values:
    grid:    0  if setup points to 0,17
             1  if setup points to 1-16
    tuned:   0  if the dacs of all pixels are not tuned
             1  if the dacs of all pixels are tuned
             -1 if only some pixels are tuned
    small_tuned:
             0  if column 0,17 are not tuned
             1  ...
             -1 ...
    enabled: 0  if all pixels are disabled
             1  if all pixels are enabled
             -1 if only some pixels are enabled
    vth:     n  if set to value n
             -1 if vth value is unknown
    hitor:   0  if hit_or is disabled on all
             1  if hit_or is enabled on all
             -1 if only some have hit_or enabled 
    """
    def __init__(self):
        self.grid = 0 
        self.tuned = 0 
        self.small_tuned = 0
        self.enabled = 0 
        self.vth = 0
        self.hitor = 0
        
    @classmethod
    def from_file(cls):
        """ Return a state instance with the values recorded in state.dat"""
        infile = open('state.dat','r')
        line = infile.readlines()[0]
        infile.close()
        values = line.strip().split(' ')
        state = cls()
        state.grid = int(values[0])
        state.tuned = int(values[1])
        state.small_tuned = int(values[2])
        state.enabled = int(values[3])
        state.vth = int(values[4])
        state.hitor = int(values[5])
        return state

    def save(self):
        """ Save the current values to state.dat"""
        outfile = open('state.dat','w')
        outfile.write('%i %i %i %i %i %i\n' % (self.grid, self.tuned, self.small_tuned, self.enabled, self.vth, self.hitor))


class PixelColumn:
    ''' A container for the dac values of a column of pixels.

    Also stores other relevant data such as the measured threshold and noise.
    Notes:
    By default, values are returned as binary strings, where
    the first position is the least significant bit. It is 
    assumed that any list or string will follow this convention.
    '''
    npix = 64
    data_forms = {'fixed':int, 'dacs':int, 'measured':int, 'thresh':float, 'noise':float}

    def __init__(self):
        self.data = {'fixed':np.zeros(self.npix), 'dacs':np.ones(self.npix) * 16, 'measured':np.zeros(self.npix), 'thresh':np.zeros(self.npix), 'noise':np.zeros(self.npix)}

    @classmethod
    def from_string(cls, string):
        col = cls()
        for line in string.split('\n')[:-1]:
            key, vals = line.split(':')            
            vals.strip()
            if key not in cls.data_forms:
                print "Unrecognized key: %s in input string." % key
                continue
            vals = [ cls.data_forms[key](float(val)) for val in vals.split(',')]
            col.data[key] = vals
        return col

    def set(self, row, value):
        value = interpret_dac_value(value)
        if not 0 <= value <= 31:
            print "Value for dac (%i) outside of range. Value not saved."
            return
        self.data['dacs'][row] = value
        self.data['fixed'][row] = 1

    def set_data(self, key, row, value):
        self.data[key][row] = value

    def get_data(self, key, row):
        return self.data[key][row]

    def set_thresh(self, row, value, error):
        self.set_data('thresh', row, value)
        self.set_data('noise', row, error)
        self.set_data('measured', row, 1)

    def get_thresh(self, row):
        return self.get_data('thresh', row)

    def get_noise(self, row):
        return self.get_data('noise', row)

    def is_measured(self, row):
        return bool(self.data['measured'][row])

    def all_measured(self):
        return all( (self.is_measured(row) for row in xrange(self.npix)) )

    def get_int(self,row):
        return int(self.data['dacs'][row])

    def get_bstring(self,row):
        return binary_string(self.get_int(row))

    def get_blist(self,row):
        return filled_binary_list(self.get_int(row))    

    def get(self,row):
        return self.get_bstring(row)

    def is_set(self,row):
        return bool(self.data['fixed'][row])

    def __getitem__(self,row):
        return self.get(row) 

    def __setitem__(self,row,value):
        self.set(row,value)

    def __str__(self):
        return '\n'.join(('%s: %s' % (key,','.join((str(val) for val in vals))) for key, vals in self.data.iteritems()))


class PixelLibrary:
    """ Storage container for data from a grid of pixels.
    
    Is actually just an interface for a list of PixelColumns.
    Notes:
    Provides methods to save to/load from a human readable csv. 
    """
    
    def __init__(self, ncols=18):
        self.cols = [PixelColumn() for i in xrange(ncols)]

    @classmethod
    def from_file(cls, fname):
        if not os.path.isfile(fname):
            return cls()
        infile = open(fname,'r')
        lines = infile.readlines()
        infile.close()
        inst = cls(0)
        blocks = []
        for line in lines:
            if 'column' in line:
                blocks.append([])
            elif line.strip() != '':
                blocks[-1].append(line)
        inst.cols.extend((PixelColumn.from_string(''.join(block)) for block in blocks))
        return inst

    def set(self, col, row, value):
        self.cols[col].set(row, value)

    def set_data(self, key, col, row, value):
        self.cols[col].data[key][row] = value

    def get_data(self, key, col, row):
        return self.cols[col].data[key][row]

    def get_data_all(self, key):
        output = []
        for col in self.cols:
            output.extend((col.data[key][row] for row in xrange(col.npix) if col.is_measured(row) ))
        return output

    def get_thresh_all(self):
        output = []
        for col in self.cols:
            output.extend((vth_to_electrons(col.data['thresh'][row]) for row in xrange(col.npix) if col.is_measured(row) ))
        return output

    def get_data_grid(self, key):
        output = []
        for col in self.cols:
            if col.all_measured():
                output.append([col.data[key][row] for row in xrange(col.npix) ])
        return output

    def get_thresh_grid(self):
        """ This function handles converting to electron equivalent."""
        output = []
        for col in self.cols:
            if col.all_measured():
                output.append([vth_to_electrons(col.data['thresh'][row]) for row in xrange(col.npix) ])
        return output

    def get_data_col(self, key, col):
        output = []
        output.extend((self.cols[col].data[key][row] for row in xrange(self.cols[col].npix) if self.cols[col].is_measured(row) ))
        return output

    def get_thresh_col(self, col):
        output = []
        output.extend((vth_to_electrons(self.cols[col].data['thresh'][row]) for row in xrange(self.cols[col].npix) if self.cols[col].is_measured(row) ))
        return output

    def set_thresh(self, col, row, value, error):
        self.cols[col].set_thresh(row, value, error)

    def is_measured(self, col, row):
        return self.cols[col].is_measured(row)

    def get_thresh(self, col, row):
        return self.get_data('thresh', col, row)

    def get_noise(self, col, row):
        return self.get_data('noise', col, row)

    def get_int(self,col,row):
        return self.cols[col].get_int(row)

    def get_bstring(self,col,row):
        return binary_string(self.get_int(col,row))

    def get_blist(self,col,row):
        return filled_binary_list(self.get_int(col,row))    

    def get(self,col,row):
        return self.get_bstring(col,row)
    
    def is_set(self,col,row=None):
        if row is None:
            return self.cols[col].fixed.all()
        else:
            return self.cols[col].is_set(row)

    def __getitem__(self,col):
        return self.cols[col]

    def save(self, outname):
        if '.' not in outname:
            outfile = open(outname+'.csv','w')
        else:
            outfile = open(outname,'w')
        for i,col in enumerate(self.cols):
            outfile.write('column %i\n' % i)
            outfile.write(str(col))
            outfile.write('\n')
        outfile.close()
    

# This kind of binary search can be problematic. It will turn into a linear search if actual > midpoint + 2*width
def interval_search(target_low, target_high, midpoint, width, minwidth, upper_lim, lower_lim, func, args=[]):
    """ Interval based binary search used for measuring voltage thresholds. """
    if midpoint > upper_lim:
        print 'Edge of safe interval reached without finding midpoint, returning interval edge: %f' % upper_lim
        return upper_lim
    elif midpoint < lower_lim:
        print 'Edge of safe interval reached without finding midpoint, returning interval edge: %f' % lower_lim
        return lower_lim
    val = func(midpoint,*args)
    if val <= target_low:
        midpoint = midpoint+width
        width = width/2
        if width < minwidth: width = minwidth
        return interval_search(target_low, target_high, midpoint, width, minwidth, upper_lim, lower_lim, func, args)
    if val >= target_high:
        midpoint = midpoint-width
        width = width/2
        if width < minwidth: width = minwidth
        return interval_search(target_low, target_high, midpoint, width, minwidth, upper_lim, lower_lim, func, args)
    else:
        return midpoint
        

def get_count(amp,hpcntr,hpgene): 
    """ Returns the count measured by the counter after the generator is triggered once."""
    DELAY=0.002 
    chip.hpcntr.write(":INIT:CONT ON")
    chip.hpcntr.write("TOT:GATE ON")
    while(not chip.hpcntr.finished()): pass 

    hpgene.write("VOLT %f" % amp)
    
    hpcntr.write(":INIT:CONT ON")
    hpcntr.write("TOT:GATE ON")
    while(not hpcntr.finished()): pass 
    
    hpgene.write("*TRG")
    while(not hpgene.finished()): pass
    
    hpcntr.write("TOT:GATE OFF")
    while(not hpcntr.finished()): pass 
    
    time.sleep(DELAY)
    hpcntr.write("FETCH:ARRAY? -1")
    gbuf=hpcntr.read()
    count=int(float(gbuf))
    return count



def timed_count(delay, hpcntr): 
    """ Returns the number of counts during delay, without any injection."""
    INTERNAL_DELAY=0.002 
    chip.hpcntr.write(":INIT:CONT ON")
    chip.hpcntr.write("TOT:GATE ON")
    while(not chip.hpcntr.finished()): pass 

    hpcntr.write(":INIT:CONT ON")
    hpcntr.write("TOT:GATE ON")
    while(not hpcntr.finished()): pass 
    
    time.sleep(delay)

    hpcntr.write("TOT:GATE OFF")
    while(not hpcntr.finished()): pass 
    
    time.sleep(INTERNAL_DELAY)
    hpcntr.write("FETCH:ARRAY? -1")
    gbuf=hpcntr.read()
    count=int(float(gbuf))
    return count


def time_until_hit(hpcntr, max_time): 
    """ Waits for a hit and records the time waited, up to max_time. """
    INTERNAL_DELAY=0.002 
    chip.hpcntr.write(":INIT:CONT ON")
    chip.hpcntr.write("TOT:GATE ON")
    while(not chip.hpcntr.finished()): pass 

    hpcntr.write(":INIT:CONT ON")
    hpcntr.write("TOT:GATE ON")
    while(not hpcntr.finished()): pass 
    start_time = time.time()

    count = 0
    while count == 0 and time.time() - start_time < max_time:
        time.sleep(INTERNAL_DELAY)
        hpcntr.write("FETCH:ARRAY? -1")
        gbuf=hpcntr.read()
        count=int(float(gbuf))

    output = time.time() - start_time
    
    hpcntr.write("TOT:GATE OFF")
    while(not hpcntr.finished()): pass     
    return output


def sample_counts(hpcntr, hpgene, npoints=4, ninjects=255):
    """ Returns an array of voltages, counts from measuring a pixel.

    Notes:
    It finds the upper and lower shoulders of the scurve and measures
    npoints along the curve, as well as a few above and below. 
    Ninjects is the number of injections sent by the generator, and is
    used here to find the shoulders of the scurve.
    The internal values for the initial guess and intial width of the 
    binary search might need to be tuned, if the searches seem slow.
    """
    noise = .015
    bottom_low = 2
    bottom_high = (ninjects * 2) // 10
    top_low = (ninjects * 8) // 10
    top_high = ninjects - 2
    #ledge = interval_search(bottom_low, bottom_high,            .225, .08, noise/5.0, 1.0, 0.03, get_count, [hpcntr,hpgene]);
    ledge = interval_search(bottom_low, bottom_high,            .8, .4, noise/5.0, 1.3, 0.027, get_count, [hpcntr,hpgene]);
    hedge = interval_search(   top_low,    top_high, ledge+2*noise, .02, noise/5.0, 1.4, 0.027, get_count, [hpcntr,hpgene]);

    xs = np.linspace(ledge,hedge,npoints)
    xs = np.insert(xs,[0]*2,np.arange(-2,0)*noise + xs[0])
    xs = np.append(xs,np.arange(1,3)*noise + xs[-1])
    xs = xs[ xs > .025 ]
    counts = np.array([get_count(x,hpcntr,hpgene) for x in xs])
    return xs, counts


def scurve(v,x):
    """ Functional form of an scurve using standard gaussian variables."""
    # v = [mu,sigma,N]
    return .5*v[2]*(1 + erf((x - v[0])/(1.4142*v[1])))


def fit_scurve(xs, counts):
    """ Calculates the parameters of an scurve given voltages, counts.
    
    Notes: The fit has three parameters (mu, sigma, N), but only
    mu, sigma are returned because N is usually uninteresting.
    """
    err = lambda v, x, y: (scurve(v,x) - y)
    v0 = [(xs[0] + xs[1])/2, .01, 255]
    v, success = leastsq(err, v0, args=(xs,counts))    
    return v[0], v[1]

"""
def plot_scurve(v, x, y, color='#7A973A'):
    fig = figure()
    x_fine = np.linspace(x[0],x[-1], 200)
    ax = fig.add_subplot(111)
    ax.plot(x_fine, scurve(v,x_fine), color=color)
    ax.plot(x, y, 'o', color=color)
    ax.plot([v[0],v[0]], [0,v[2] * 1.2], color=color, linestyle='--')
    ax.plot([v[0]-v[1],v[0]-v[1]], [0,v[2] * 1.2], color=color, linestyle='--')
    ax.plot([v[0]+v[1],v[0]+v[1]], [0,v[2] * 1.2], color=color, linestyle='--')
    ax.set_ylim(-1, v[2] * 1.1)
    ax.set_ylabel('Number of Triggers',fontsize=16)
    ax.set_xlabel('Injection Voltage (V)',fontsize=16)
    text(v[0] + v[1]*2, .5 * v[2] * 1.1, "Threshold = %.4f\nNoise = %.4f" % (v[0],v[1]), fontsize=16)
"""

def command_test():
    """ Test of the commands generated by chip.driver. """
    driver = chip.DgeneDriver(chip.dgene, config_size=800)
    outfile = open('commands_test.txt','w')
    commands = driver._gen_config_command(chip.getDacBusPat()[::-1]+chip.getCtrlBusPat()[::-1])
    for key, val in commands[0].iteritems():
        outfile.write(key + '\n')
        outfile.write(''.join(val) + '\n')

    commands = driver._gen_config_command(chip.get_control_pattern_pixel(12,cnfgbits='01100001',lden='1',ss0='0',ss1='0',config_mode='00')[::-1])
    for key, val in commands[0].iteritems():
        outfile.write(key + '\n')
        outfile.write(''.join(val) + '\n')
    outfile.close()


# State setting functions.
def clear_chip(driver):
    """ Explicitly sets bits of all columns to zero. 

    Notes:
    Consider using driver.clear_all_columns, which does the same
    but also clears columns 0,17. It is much faster.
    """
    state = State.from_file()
    if state.tuned == 0 and state.enabled == 0:
        return
    state.tuned = -1
    state.enabled = -1
    state.save()
    for col in xrange(1,17):
        driver.clear_single_column(col)
    state.tuned = 0
    state.enabled = 0
    state.save()

def enable_chip(driver):
    """ Enable hit and inject on every pixel on every column. 

    Notes:
    This is used rather than driver.enable_all_columns because
    this function selectively enables only the grid/small columns.
    """
    state = State.from_file()
    if state.enabled == 1:
        return
    state.enabled = -1
    state.save()
    if state.grid != 0:
        for col in xrange(1,17):
            driver.enable_single_column(col)
    else: 
        for col in [0,17]:
            driver.enable_single_column(col)        
    state.enabled = 1
    state.save()

def write_chip_tuned(pix, driver=None):
    """ Write DAC patterns to every pixel from PixelLibrary pix. 

    Notes:
    In the process, hit/inject are disabled on all pixels, and
    not re-enabled (this is intentional).
    If driver is None, this function will create its own driver and
    initalize the blocks. This is to save time, but note that this
    means that any other drivers need to be initialized after calling
    this function.
    """
    state = State.from_file()
    if state.tuned == 1:
        return
    if driver is None:
        driver = chip.DgeneDriver(chip.dgene, config_size=380)
        driver.init_blocks()
    driver.clear_all_columns()
    state.tuned = -1
    state.enabled = 0
    state.save()
    for col in xrange(1,17):
        for index in xrange(5):
            print "Writing column %i, index %i" % (col, index)
            pix_pattern = [pix[col][row][index] for row in xrange(64)]
            driver.write_pixel_pattern(col, pix_pattern, index)
    state.tuned = 1
    state.save()

def write_small_tuned(pix, driver=None):
    """ Write DAC patterns to every pixel from PixelLibrary pix. 

    Notes:
    In the process, hit/inject are disabled on all pixels, and
    not re-enabled (this is intentional).
    If driver is None, this function will create its own driver and
    initalize the blocks. This is to save time, but note that this
    means that any other drivers need to be initialized after calling
    this function.
    """
    state = State.from_file()
    if state.small_tuned == 1:
        return
    if driver is None:
        driver = chip.DgeneDriver(chip.dgene, config_size=380)
        driver.init_blocks()
    driver.clear_single_column(0)
    driver.clear_single_column(17)
    state.small_tuned = -1
    state.enabled = 0
    state.save()
    for col in [0,17]:
        for index in xrange(5):
            print "Writing column %i, index %i" % (col, index)
            pix_pattern = [pix[col][row][index] for row in xrange(64)]
            driver.write_pixel_pattern(col, pix_pattern, index)
    state.small_tuned = 1
    state.save()


def enable_hitor_chip(driver=None):
    """ Enables hitor on all pixels if needed.

    Notes:
    If driver is None, this function will create its own driver and
    initalize the blocks. This is to save time, but note that this
    means that any other drivers need to be initialized after calling
    this function.
    """
    state = State.from_file()
    if state.hitor == 1:
        return
    if driver is None:
        driver = chip.DgeneDriver(chip.dgene, config_size=380)
        driver.init_blocks()
    driver.enable_hitor_all_columns()
    state.hitor = 1
    state.save()

def disable_hitor_chip(driver=None):
    """ Enables hitor on all pixels if needed.

    Notes:
    If driver is None, this function will create its own driver and
    initalize the blocks. This is to save time, but note that this
    means that any other drivers need to be initialized after calling
    this function.
    """
    state = State.from_file()
    if state.hitor == 0:
        return
    if driver is None:
        driver = chip.DgeneDriver(chip.dgene, config_size=380)
        driver.init_blocks()
    driver.disable_hitor_all_columns()
    state.hitor = 0
    state.save()

def set_config(vth, driver=None, PrmpVbp=142, PrmpVbf=11, **kwargs):
    """Set global voltage threshold, and optionally other settings.
    
    Notes:
    If driver is None, this function will create its own driver and
    initalize the blocks. This is to save time, but note that this
    means that any other drivers need to be initialized after calling
    this function.
    """
    state = State.from_file()
    if driver is None:
        driver = chip.DgeneDriver(chip.dgene, config_size=800)
        driver.init_blocks()
    if driver.config_size < 800:
        print "The configuration size for the driver is too small to program the config."
        raise ValueError
    state = State.from_file()
    state.vth = vth
    state.save()
    driver.program_config(chip.get_dac_pattern(vth, PrmpVbp=PrmpVbp, PrmpVbf=PrmpVbf)[::-1]+chip.get_control_pattern(**kwargs)[::-1],zero=False) 

# Measurement functions
def test_thresh(npoints, ninjects, driver, hpcntr, hpgene, col, row, dacbits):
    """Measure a threshold using variable setting for the fitting and injecting.

    Notes: 
    This was used to test the repeatability of measuring the threshold for a given
    pixel. We found that using other setting of npoints, ninjects gave identical
    values for the threshold and noise.
    """ 
    state = State.from_file()
    state.tuned = -1
    state.save()
    chip.init_hpgene(hpgene, ninjects)
    driver.clear_single_column(col)
    driver.enable_single_pixel(col, row, dacbits=dacbits, zero=False)
    xs, counts = sample_counts(hpcntr, hpgene, npoints, ninjects)
    return fit_scurve(xs, counts)


def measure_thresh(driver, hpcntr, hpgene, col, row, dacbits):
    """Measure the threshold of the pixel at col, row with dac set to dacbits.
    
    Notes:
    This version guaruntees that the dac bits are correct by zeroing them out
    first. This costs an extra write step, and makes it take about 1.5* as long.
    """
    state = State.from_file()
    state.tuned = -1
    state.save()
    driver.clear_single_column(col)
    driver.enable_single_pixel(col, row, dacbits=dacbits, zero=False)
    xs, counts = sample_counts(hpcntr, hpgene)
    return fit_scurve(xs, counts)


def measure_thresh_fast(driver, hpcntr, hpgene, col, row):
    """Measure the threshold of the pixel at col, row.
    
    Notes:
    This version assumes that the dacbits are already set on the pixel being
    measured, so that it can be done as fast as possible.
    """
    driver.enable_single_pixel(col, row, dacbits='00000', zero=False)
    xs, counts = sample_counts(hpcntr, hpgene)
    return fit_scurve(xs, counts)

# Aggregate measurement functions.
def measure_counts(driver, hpcntr, vth=100, **kwargs):
    """Measure the count rate at various VbpTh settings."""
    counts = 0
    rates = []
    current = vth
    vths = []
    delay = 8
    while (counts < 1000):
        set_config(current, driver, **kwargs)
        counts = float(timed_count(delay, hpcntr))
        rates.append(counts/delay)
        vths.append(current)
        print current
        if counts > 10 and delay > 1:
            delay = delay // 2
        if delay == 8:
            current -= 2
        else:
            current -= 1
        if current < 20:
            return vths,rates
    return vths, rates
    

def scan_column(col, driver, hpcntr, hpgene, pixels=None, overwrite=False):
    """Measure and record the voltage threshold and noise for col."""
    if pixels is None:
        pixels = PixelLibrary.from_file('pixels.csv')
    for row in xrange(64):
        if pixels.is_measured(col, row): continue
        print col, row
        if not overwrite:
            v = measure_thresh_fast(driver, hpcntr, hpgene, col, row)
        else:
            v = measure_thresh(driver, hpcntr, hpgene, col, row, '00001')
        print v
        pixels.set_thresh(col, row, v[0], v[1])
    pixels.save('pixels.csv')


def scan_chip(driver, hpcntr, hpgene, pixels_name='pixels_scan.csv', pixels_dac=None, overwrite=False):
    """Measure and record the voltage threshold and noise for the large pixels on the chip."""
    pixels = PixelLibrary.from_file(pixels_name)
    if pixels_dac is not None:
        for col in xrange(1,17):
            for row in xrange(64):
                pixels[col][row] = pixels_dac[col][row]
    state = State.from_file()
    state.enabled = -1
    state.grid = 1
    state.save()
    driver.disable_all_columns()
    for col in xrange(1,17):
        scan_column(col, driver, hpcntr, hpgene, pixels, overwrite)
    pixels.save(pixels_name) 

def scan_small(driver, hpcntr, hpgene, pixels_name='pixels_scan_small.csv', pixels_dac=None):
    """Measure and record the voltage threshold and noise for the large pixels on the chip."""
    pixels = PixelLibrary.from_file(pixels_name)
    if pixels_dac is not None:
        for col in [0,17]:
            for row in xrange(64):
                pixels[col][row] = pixels_dac[col][row]
    state = State.from_file()
    state.grid = -1
    state.enabled = -1
    state.save()
    driver.disable_all_columns()
    for col in [0,17]:
        scan_column(col, driver, hpcntr, hpgene, pixels=pixels)
    pixels.save(pixels_name) 


def tune_pixel(driver, hpcntr, hpgene, col, row, target, orig, noise, perbit, orig_index=16):
    """ Tune a pixel using a fast, naive algorithm based on the measured threshold at dac=orig_index (orig).
    
    Notes:
    Returns the threshold it has been tuned to, along with the index
    and noise of that threshold. This algorithm works for many of the
    pixels, but some are off by a few 'perbit' values.
    """ 
    orig_index = interpret_dac_value(orig_index)
    index = orig_index + int((target-orig) / perbit)
    if index > 30: index = 30
    if index < 1: index = 1
    estimate1 = measure_thresh(driver, hpcntr, hpgene, col, row, binary_string(index))
    if estimate1[0] >= target:
        estimate2 =  measure_thresh(driver, hpcntr, hpgene, col, row, binary_string(index-1))
        index2 = index - 1
    else:
        estimate2 =  measure_thresh(driver, hpcntr, hpgene, col, row, binary_string(index+1))
        index2 = index + 1
    thresh = estimate1 if abs(estimate1[0] - target) < abs(estimate2[0] - target) else estimate2
    index = index if abs(estimate1[0] - target) < abs(estimate2[0] - target) else index2
    return index, thresh[0], thresh[1]


def tune_pixel_careful(driver, hpcntr, hpgene, col, row, target, orig_bits, orig_th, perbit):
    """ Tune a pixel using a careful algorithm which scans until the threshold is within an interval of target.
    
    Notes:
    The orig_bits, orig_th determine if it searches up or down from a given point.
    Returns the threshold it has been tuned to, along with the index
    and noise of that threshold. 
    """ 
    index = interpret_dac_value(orig_bits)
    thresh = orig_th
    best_index, best_thresh, noise = 0, 0, 0
    estimates = []
    fixed = False

    while (abs(best_thresh - target) > .75 * perbit and index >= 0 and index <= 31 ):
        thresh, noise = measure_thresh(driver, hpcntr, hpgene, col, row, binary_string(index))
        estimates.append((index, thresh, noise))
        if not fixed:
            if thresh < target: 
                operator = lambda x: x + 1
                fixed = True
            else: 
                operator = lambda x: x - 1
                fixed = True
        best_index, best_thresh, noise = min(estimates, key = lambda x: abs(x[1]-target))
        if operator(index) > index and thresh > target + 2*perbit: break # give up because it already passed the best value
        if operator(index) < index and thresh < target - 2*perbit: break # give up because it already passed the best value
        index = operator(index)

    # Do one more step if it didn't reach an edge.
    if (index >= 0 and index <= 31):
        thresh, noise = measure_thresh(driver, hpcntr, hpgene, col, row, binary_string(index))
        estimates.append((index, thresh, noise))
        best_index, best_thresh, noise = min(estimates, key = lambda x: abs(x[1]-target))
    return best_index, best_thresh, noise


def tune_columns(driver, hpcntr, hpgene, cols, target, perbit, orig_pix, new_pix=None, outname='pixels_tune1.csv'):
    """ Tune all of the columns in cols using the fast algorithm, and save. """
    if new_pix is None:
        new_pix = PixelLibrary.from_file('pixels_tune1.csv')
    for col in cols:
        for row in xrange(PixelColumn.npix):
            if new_pix.is_measured(col, row): continue
            print col, row
            dacbits, thresh, error = tune_pixel(driver, hpcntr, hpgene, col, row, target, orig_pix.get_thresh(col,row),orig_pix.get_noise(col,row), perbit, orig_pix[col][row])
            print dacbits, thresh, error
            new_pix[col][row] = dacbits
            new_pix.set_thresh(col, row, thresh, error)
        new_pix.save(outname)
    new_pix.save(outname)


def tune_columns_careful(driver, hpcntr, hpgene, cols, target, perbit, orig_pix, new_pix=None):
    """ Tune all of the columns in cols using the careful algorithm, and save. 

    Notes:
    If a given pixels is already with 1.5*perbit from the target, it is skipped.
    """
    if new_pix is None:
        new_pix = PixelLibrary.from_file('pixels_tune2.csv')
    for col in cols:
        for row in xrange(PixelColumn.npix):
            if abs(target - orig_pix.get_thresh(col, row)) < 1.0 * perbit: 
                dacbits = orig_pix[col][row]
                thresh = orig_pix.get_thresh(col,row)
                error = orig_pix.get_noise(col,row)
                new_pix[col][row] = dacbits
                new_pix.set_thresh(col, row, thresh, error)
                continue
            print col, row
            dacbits, thresh, error = tune_pixel_careful(driver, hpcntr, hpgene, col, row, target, orig_pix[col][row], orig_pix.get_thresh(col,row), perbit)
            print dacbits, thresh, error
            new_pix[col][row] = dacbits
            new_pix.set_thresh(col, row, thresh, error)
        new_pix.save('pixels_tune2.csv')
    new_pix.save('pixels_tune2.csv')


def test_dac():
    """ Tests the voltages for several pixels over all the dac values."""
    chip.init_hpgene(chip.hpgene, 255)
    chip.init_hpcntr(chip.hpcntr)
    driver = chip.DgeneDriver(chip.dgene, config_size=380)
    driver.init_blocks()
    outfile = open('dactest_outliers.dat', 'w')
    points = [(5,48), (5,45), (8,21), (8,54)]
    for col, row in points:
        for dacbits in (binary_string(x) for x in xrange(32)):
            vth, noise = measure_thresh(driver, chip.hpcntr, chip.hpgene, col, row, dacbits)
            outfile.write("(col = %i, row = %i, DAC = %s) Vth: %.3f Noise: %.3f\n" % (col, row, dacbits, vth, noise))
    outfile.close()



def find_minimum_vth(driver, min_time, vth=150, **kwargs):
    """ Find the minimum vth which does not produce any hits in min_time. 

    Notes:
    This does not change the enabled/disabled state of any pixels, so it
    can be used for a single pixel up to the whole chip, depending on the
    hit enable bit of the pixels.
    """
    set_config(vth, driver, **kwargs)
    delay = 1
    time.sleep(1) #let noise clear
    # decrement until I start getting noise hits in 1 second.
    while (timed_count(delay, chip.hpcntr) == 0 ):
        print vth
        vth -= 10
        if vth <= 0:
            raise ValueError("Reached VbpTh <= 0, which really shouldn't have happened.")
        set_config(vth, driver, **kwargs)
    
    # increment until I just stop getting any noise hits in 60 seconds.
    while (time_until_hit(chip.hpcntr, min_time) < min_time ):
        vth += 2
        if vth >= 150:
            raise ValueError("Reached VbpTh >= 150, which really shouldn't have happened.")
        set_config(vth, driver, **kwargs)
        print vth
    return vth


def main_minimize_untuned():
    """ Find minimum vth with all pixels enabled, without applying any dac settings. """
    chip.init_hpcntr(chip.hpcntr)
    driver = chip.DgeneDriver(chip.dgene, config_size=800)
    driver.init_blocks()
    enable_chip(driver)
    find_minimum_vth(driver, 20)


def main_minimize_tuned():
    """ Find minimum vth with all pixels enabled and set to tuned dac values. """
    chip.init_hpcntr(chip.hpcntr)
    driver = chip.DgeneDriver(chip.dgene, config_size=800)
    driver.init_blocks()
    pix = PixelLibrary.from_file('pixels_tune_final.csv')
    write_chip_tuned(pix, driver)
    enable_chip(driver)
    find_minimum_vth(driver, 60)


def main_tune(args):
    """ Tune the entire chip, saving results to pixels_tune1.csv and pixels_tune2.csv. 

    Notes:
    Takes about 7 hours to run.
    The first tune is based on a scan of the chip, made by running main_scan.
    The results of the first tune are saved in pixels_tune1.csv. This tune applies
    to every pixel, but can be inaccurate.
    The results of the second tune are saved in pixels_tune2.csv. This tune applies
    only to pixels which are not close to target after the first tune, and is guaranteed
    to find the best possible dac setting.
    """
    chip.init_hpgene(chip.hpgene, 255)
    chip.init_hpcntr(chip.hpcntr)
    set_config(150)

    driver = chip.DgeneDriver(chip.dgene, config_size=380)
    driver.init_blocks()
    driver.disable_all_columns()

    state = State.from_file()
    state.grid = 1
    state.hitor = -1
    state.enabled = 0
    state.save()

    enable_hitor_chip(driver)
    #perbit=.01285
    # determine perbit using random pixels
    all_pixels = [(x,y) for x in xrange(1,17) for y in xrange(64)]
    test_pixels = random.sample(all_pixels, 100)
    dac0 = []
    dac16 = []
    for pix in test_pixels:
        dac0.append(measure_thresh(driver, chip.hpcntr, chip.hpgene, pix[0], pix[1], '00000')[0])
        print dac0[-1]
        dac16.append(measure_thresh(driver, chip.hpcntr, chip.hpgene, pix[0], pix[1], '00001')[0])
        print dac16[-1]
    dac0, dac16 = np.array(dac0), np.array(dac16)
    target1 = np.average(dac16)
    print "First target: ", target1
    perbit = np.average(dac16 - dac0) / 16.0
    print "Perbit: ", perbit

    # tune once to find a decent minimum threshold
    scan_chip(driver, chip.hpcntr, chip.hpgene, pixels_name = 'pixels_scan_high.csv', overwrite=True)
    orig_pix = PixelLibrary.from_file('pixels_scan_high.csv')
    tune_columns(driver, chip.hpcntr, chip.hpgene, range(1,17), target1, perbit, orig_pix, outname='pixels_tune_high.csv')
    tuned_pix = PixelLibrary.from_file('pixels_tune_high.csv')
    tune_columns_careful(driver, chip.hpcntr, chip.hpgene, range(1,17), target1, perbit, tuned_pix)        

def main_scan(args):
    """ Scan the thresholds of the chip at vth, and save to pixels_scan.

    Notes: If pixels_dac_name is provided, it uses the pixel dac settings
    stored in that file to set the dac thresholds before scanning.
    """
    chip.init_hpgene(chip.hpgene, 255)
    chip.init_hpcntr(chip.hpcntr)
    set_config(args.vth)
    driver = chip.DgeneDriver(chip.dgene, config_size=380)
    driver.init_blocks()
    state = State.from_file()
    state.hitor = -1
    state.save()
    if args.pixels:
        pixels_dac = PixelLibrary.from_file(args.pixels)
        write_chip_tuned(pixels_dac, driver)
        enable_hitor_chip(driver)
        scan_chip(driver, chip.hpcntr, chip.hpgene, pixels_dac = pixels_dac)
    else:
        enable_hitor_chip(driver)
        scan_chip(driver, chip.hpcntr, chip.hpgene)

def main_detuning_scan(min_vth=82, max_vth=150):
    """ Scan the thresholds of the chip at several vth, and save to pixels_scan_vth.    """
    chip.init_hpgene(chip.hpgene, 255)
    chip.init_hpcntr(chip.hpcntr)
    driver1 = chip.DgeneDriver(chip.dgene, config_size=800)
    driver2 = chip.DgeneDriver(chip.dgene, config_size=380)
    pixels_dac = PixelLibrary.from_file('pixels_tune_final.csv')
    state = State.from_file()
    if state.tuned != 1:
        print "tuning"
        driver2.init_blocks()
        write_chip_tuned(pixels_dac, driver)
    for vth in np.linspace(min_vth, max_vth, 5):
        vth = int(vth)
        driver1.init_blocks()
        set_config(vth, driver1)
        driver2.init_blocks()
        scan_chip(driver2, chip.hpcntr, chip.hpgene, pixels_name = 'pixels_scan_%i.csv' % vth, pixels_dac = pixels_dac)

def main_chip_thresholds():
    """ Find minimum thresholds for each clock/count setting for the entire chip."""
    chip.init_hpgene(chip.hpgene, 255)
    chip.init_hpcntr(chip.hpcntr)
    driver_setup = chip.DgeneDriver(chip.dgene, config_size=380)
    driver_setup.init_blocks()
    write_chip_tuned(PixelLibrary.from_file('pixels_tune_final.csv'), driver_setup)
    enable_chip(driver_setup)
    driver = chip.DgeneDriver(chip.dgene, config_size=800)
    driver.init_blocks()
    config_options = {'none':   {'config_mode':'11'}, 
                      'clock':  {'config_mode':'11','count_hits_not':'1', 'count_clear_not':'1'}, 
                      'count':  {'config_mode':'11','count_hits_not':'1', 'count_clear_not':'1', 'count_enable':'1'},
                      'readout':{'config_mode':'11','count_hits_not':'1', 'count_clear_not':'1', 'count_enable':'1', 
                                 'global_readout_enable':'1'}}
    mins = {}
    for config, options in config_options.iteritems(): 
        if config == 'none':
            driver.disable_count_clock()
        else:
            driver.enable_count_clock()
        mins[config].append(find_minimum_vth(driver, 60, **options))
    print 'None:                    %i' % mins['none']
    print 'Clock:                   %i' % mins['clock']
    print 'Clock + Count:           %i' % mins['count']
    print 'Clock + Count + Readout: %i' % mins['readout']

def main_column_thresholds():
    """ Find minimum thresholds for each clock/count setting for each column. """
    chip.init_hpgene(chip.hpgene, 255)
    chip.init_hpcntr(chip.hpcntr)
    write_chip_tuned(PixelLibrary.from_file('pixels_tune_final.csv'))
    driver = chip.DgeneDriver(chip.dgene, config_size=800)
    driver.init_blocks()
    mins = {'none':[], 'clock':[], 'count':[], 'readout':[]}
    config_options = {'none':   {}, 
                      'clock':  {'count_hits_not':'1', 'count_clear_not':'1'}, 
                      'count':  {'count_hits_not':'1', 'count_clear_not':'1', 'count_enable':'1'},
                      'readout':{'count_hits_not':'1', 'count_clear_not':'1', 'count_enable':'1', 
                                 'global_readout_enable':'1'}}
    for col in xrange(1,17):
        for config, option in config_options.iteritems():
            if config == 'none':
                driver.disable_count_clock()
            else:
                driver.enable_count_clock()
            mins[config].append(find_minimum_vth(driver, 60, col=col, **options))
    for config in config_options.keys():
        print '%s:' % config
        print mins[config]


def main_column_counts():
    """ Measure dark rate for selected columns. """
    chip.init_hpgene(chip.hpgene, 255)
    chip.init_hpcntr(chip.hpcntr)
    state = State.from_file()
    if state.tuned != 1 or state.enabled != 1:
        driver_setup = chip.DgeneDriver(chip.dgene, config_size=380)
        driver_setup.init_blocks()
        write_chip_tuned(PixelLibrary.from_file('pixels_tune_final.csv'), driver_setup)
        enable_chip(driver_setup)
    driver = chip.DgeneDriver(chip.dgene, config_size=800)
    driver.init_blocks()
    config_options = {'none':   {}, 
                      'clock':  {'count_hits_not':'1', 'count_clear_not':'1'}, 
                      'count':  {'count_hits_not':'1', 'count_clear_not':'1', 'count_enable':'1'},
                      'readout':{'count_hits_not':'1', 'count_clear_not':'1', 'count_enable':'1', 
                                 'global_readout_enable':'1'}}
    outfile = open('column_counts.csv', 'w')
    for col in [1,2,3,6,15,16]:
        for config, option in config_options.iteritems():
            if config == 'none':
                driver.disable_count_clock()
            else:
                driver.enable_count_clock()
            outfile.write('Column: %i Config: %s\n' % (col,config))
            vths, rates = measure_counts(driver, chip.hpcntr, vth=70, config_mode = '11')
            outfile.write(','.join((str(vth) for vth in vths)) + '\n')
            outfile.write(','.join((str(rate) for rate in rates)) + '\n')
    outfile.close()


def main_column_counts_chip_enabled():
    """ Measure dark rate for selected columns with chip enabled. """
    chip.init_hpgene(chip.hpgene, 255)
    chip.init_hpcntr(chip.hpcntr)
    state = State.from_file()
    driver_setup = chip.DgeneDriver(chip.dgene, config_size=380)
    driver = chip.DgeneDriver(chip.dgene, config_size=800)
    if state.tuned != 1 or state.enabled != 1:
        driver_setup.init_blocks()
        write_chip_tuned(PixelLibrary.from_file('pixels_tune_final.csv'), driver_setup)
        enable_chip(driver_setup)
    
    state = State.from_file()
    state.hitor = -1
    state.save()

    config_options = {'none':   {'config_mode':'11'}, 
                      'clock':  {'config_mode':'11','count_hits_not':'1', 'count_clear_not':'1'}, 
                      'count':  {'config_mode':'11','count_hits_not':'1', 'count_clear_not':'1', 'count_enable':'1'},
                      'readout':{'config_mode':'11','count_hits_not':'1', 'count_clear_not':'1', 'count_enable':'1', 
                                 'global_readout_enable':'1'}}
    outfile = open('column_counts_chip_redo.csv', 'w')
    for col in [1,2,3,6,15,16]:
        print col
        driver_setup.init_blocks()
        driver_setup.disable_hitor_all_columns()
        driver_setup.enable_hitor_single_column(col)
        driver.init_blocks()
        for config, option in config_options.iteritems():
            if config == 'none':
                driver.disable_count_clock()
            else:
                driver.enable_count_clock()
            outfile.write('Column: %i Config: %s\n' % (col,config))
            vths, rates = measure_counts(driver, chip.hpcntr, vth=70, config_mode = '11')
            outfile.write(','.join((str(vth) for vth in vths)) + '\n')
            outfile.write(','.join((str(rate) for rate in rates)) + '\n')
    outfile.close()
    enable_hitor_chip()




def main_chip_counts():
    """ Measure the dark rate of noise with the entire chip enabled. """ 
    chip.init_hpgene(chip.hpgene, 255)
    chip.init_hpcntr(chip.hpcntr)
    state = State.from_file()
    if state.tuned != 1 or state.enabled != 1:
        driver_setup = chip.DgeneDriver(chip.dgene, config_size=380)
        driver_setup.init_blocks()
        write_chip_tuned(PixelLibrary.from_file('pixels_tune_final.csv'), driver_setup)
        enable_chip(driver_setup)
    driver = chip.DgeneDriver(chip.dgene, config_size=800)
    driver.init_blocks()

    config_options = {'none':   {'config_mode':'11'}, 
                      'clock':  {'config_mode':'11','count_hits_not':'1', 'count_clear_not':'1'}, 
                      'count':  {'config_mode':'11','count_hits_not':'1', 'count_clear_not':'1', 'count_enable':'1'},
                      'readout':{'config_mode':'11','count_hits_not':'1', 'count_clear_not':'1', 'count_enable':'1', 
                                 'global_readout_enable':'1'}}

    outfile = open('chip_counts.csv', 'w')
    for config, option in config_options.iteritems():
        if config == 'none':
            driver.disable_count_clock()
        else:
            driver.enable_count_clock()
        outfile.write('Config: %s\n' % config)
        vths, rates = measure_counts(driver, chip.hpcntr,**options)
        outfile.write(','.join((str(vth) for vth in vths)) + '\n')
        outfile.write(','.join((str(rate) for rate in rates)) + '\n')    
    outfile.close()

def main_pixel_scurve(vth=84):
    """ Measure and record scurves of pixels spaced throughout chip.
    
    Tunes the chip and sets threshold to the tuning threshold.
    """
    chip.init_hpgene(chip.hpgene, 255)
    chip.init_hpcntr(chip.hpcntr)
    state = State.from_file()
    if state.tuned != 1:
        driver_setup = chip.DgeneDriver(chip.dgene, config_size=380)
        driver_setup.init_blocks()
        write_chip_tuned(PixelLibrary.from_file('pixels_tune_final.csv'), driver_setup)
        enable_chip(driver_setup)
    state.enabled = -1
    state.save()
    driver = chip.DgeneDriver(chip.dgene, config_size=800)
    driver.init_blocks()
    driver.disable_all_columns()
    set_config(vth, driver)

    config_options = {'none':   {}, 
                      'clock':  {'count_hits_not':'1', 'count_clear_not':'1'}, 
                      'count':  {'count_hits_not':'1', 'count_clear_not':'1', 'count_enable':'1'},
                      'readout':{'count_hits_not':'1', 'count_clear_not':'1', 'count_enable':'1', 
                                 'global_readout_enable':'1'}}
    
    outfile = open('scurves.csv', 'w')
    for col in [1,2,3,6,15,16]:
        for row in [0,31]:
            print col, row
            for config, options in config_options.iteritems():
                if config == 'none':
                    driver.disable_count_clock()
                else:
                    driver.enable_count_clock()
                driver.enable_single_pixel(col, row, zero=False, **options)
                xs, counts = sample_counts(chip.hpcntr, chip.hpgene)
                vth, noise = fit_scurve(xs, counts)
                outfile.write('Column: %i Row: %i Config: %s Vth: %.4f Noise: %.4f\n' % (col, row, config, vth, noise))
                outfile.write(','.join((str(x) for x in xs)) + '\n')
                outfile.write(','.join((str(count) for count in counts)) + '\n')
    outfile.close()


def main_pixel_setup_single(col, row, vth=150):
    """ Setup one pixel to test with external devices. 

    This method disables all other pixels and enables hit/inject
    on the specified pixel. It also sets the global vth to the
    vth argument.
    """
    chip.init_hpgene(chip.hpgene, 255)
    chip.init_hpcntr(chip.hpcntr)
    driver = chip.DgeneDriver(chip.dgene, config_size=800)
    driver.init_blocks()
    driver.enable_hitor_all_columns()
    driver.disable_all_columns()

    set_config(vth, driver)
    driver.enable_single_pixel(col, row, zero=False)


def main_test_pixel_analog(col, row, chip_noise=False, freq=50):
    """ Measure and save the fourier spectrum of noise for the specified pixel.

    The MSO4104 scope needs to be connected to the analog output on
    channel1, and the window should be set to something appropriate 
    in advance. 
    If chip_noise is True, enables the entire chip while running.
    """
    config_options = {'none':   {}, 
                      'clock':  {'count_hits_not':'1', 'count_clear_not':'1'}, 
                      'count':  {'count_hits_not':'1', 'count_clear_not':'1', 'count_enable':'1'},
                      'readout':{'count_hits_not':'1', 'count_clear_not':'1', 'count_enable':'1', 
                                 'global_readout_enable':'1'}}
    
    state = State.from_file()
    state.enabled = 1
    state.hitor = 0
    state.save()
    outfile = open('pixels_direct.csv', 'w')
    #chip.init_hpgene(chip.hpgene, 255)
    chip.init_hpcntr(chip.hpcntr)

    driver = chip.DgeneDriver(chip.dgene, config_size=800)
    driver.init_blocks()

    vth = 150
    set_config(vth, driver)
    if not chip_noise:
        driver.disable_hitor_all_columns()
        driver.disable_all_columns()
    else:
        for config,options in config_options.iteritems():
            options['config_mode'] = '11'
        enable_chip(driver)
    driver.disable_count_clock()

    scope = dscope.ScopeInst(0)
    scope.init_fourier_transform(1)

    if not chip_noise:
        outfile = open('pixel_test_analog_%i_%i.csv' % (col,row), 'w')
    else:
        outfile = open('pixel_test_analog_%i_%i_chip.csv' % (col,row), 'w')
    for config, options in config_options.iteritems():
        if config == 'none':
            driver.disable_count_clock()
        else:
            driver.enable_count_clock(freq)
        if not chip_noise:
            driver.enable_single_pixel(col, row, zero=False, **options)
        else:
            set_config(vth, driver, **options)
        traces  = [scope.ftrace(timeout=.1) for i in xrange(500)]
        ys = sum((trace[1] for trace in traces))/ 100.0
        xs = traces[0][0]
        outfile.write('VbpTh: %i Column: %i Row: %i Config: %s\n' % (vth, col, row, config))
        outfile.write(','.join((str(x) for x in xs)) + '\n')
        outfile.write(','.join((str(y) for y in ys)) + '\n')
    outfile.close()


def main_test_pixel_digital(col, row, chip_noise=False, freq=50, configs=['none','clock','count','readout'],config_mode='11', address=None):
    """ Find minimum Vbpth and measure dark rates for a single pixel.

    Can be used with the hitOr or the direct hit output, but the
    counter needs to be plugged in to the corresponding location.
    If chip_noise is True, enables the entire chip while running.
    """
    suffix = '_%i_%i_%i_%s' % (col, row, freq*1000, config_mode)
    if address is None:
        address = col
    else:
        suffix += '_address_%i' % address
    suffix += '.csv'

    config_options = {'none':   {'col':address}, 
                      'clock':  {'col':address, 'count_hits_not':'1', 'count_clear_not':'1'}, 
                      'count':  {'col':address, 'count_hits_not':'1', 'count_clear_not':'1', 'count_enable':'1'},
                      'readout':{'col':address, 'count_hits_not':'1', 'count_clear_not':'1', 'count_enable':'1', 
                                 'global_readout_enable':'1'}}

    for key in config_options.keys():
        if key not in configs:
            config_options.pop(key,0)

    chip.init_hpgene(chip.hpgene, 255)
    chip.init_hpcntr(chip.hpcntr)
    driver = chip.DgeneDriver(chip.dgene, config_size=800)
    driver.init_blocks()
    if not chip_noise:
        driver.enable_hitor_all_columns()
        driver.disable_all_columns()
        driver.enable_single_pixel(col, row, zero=False)
        config_mode = '00'
        state = State.from_file()
        state.enabled = -1 
        state.hitor = 1
        state.save()
    else:
        for config,options in config_options.iteritems():
            options['config_mode'] = config_mode
        state = State.from_file()
        state.enabled = -1 
        state.hitor = -1
        state.save()
        driver.disable_hitor_all_columns()
        driver.enable_hitor_single_pixel(col, row)
        enable_chip(driver)
    
    outfile_rate = open('pixel_test_darkrate'+suffix, 'w')
    outfile_scurve = open('pixel_test_scurve'+suffix, 'w')
    for config, options in config_options.iteritems():
        if config == 'none':
            driver.disable_count_clock()
        else:
            driver.enable_count_clock(freq)
        vths, rates = measure_counts(driver, chip.hpcntr, vth=140, **options)
        outfile_rate.write('Column: %i Row: %i Config: %s\n' % (col, row, config))        
        outfile_rate.write(','.join((str(vth) for vth in vths)) + '\n')
        outfile_rate.write(','.join((str(rate) for rate in rates)) + '\n')
        min_vth = max((vths[i] for i in xrange(len(vths)) if rates[i] >= 1.0 ))
        print min_vth
        if address == col:
            set_config(min_vth, driver, **options)
            xs, counts = sample_counts(chip.hpcntr, chip.hpgene)
            vth, noise = fit_scurve(xs, counts)
            outfile_scurve.write('Column: %i Row: %i Config: %s Vth: %.4f Noise: %.4f Vbpth: %i\n' % (col, row, config, vth, noise, min_vth))
            outfile_scurve.write(','.join((str(x) for x in xs)) + '\n') 
            outfile_scurve.write(','.join((str(count) for count in counts)) + '\n')        

            set_config(min_vth+5, driver, **options)
            xs, counts = sample_counts(chip.hpcntr, chip.hpgene)
            vth, noise = fit_scurve(xs, counts)
            outfile_scurve.write('Column: %i Row: %i Config: %s Vth: %.4f Noise: %.4f Vbpth: %i\n' % (col, row, config, vth, noise, min_vth+5))
            outfile_scurve.write(','.join((str(x) for x in xs)) + '\n') 
            outfile_scurve.write(','.join((str(count) for count in counts)) + '\n')        
    outfile_rate.close()
    outfile_scurve.close()

def test_config_current(vth=84):
    driver = chip.DgeneDriver(chip.dgene, config_size=800)
    driver.init_blocks()
    driver.enable_count_clock(50000)
    for config_mode in ['00', '01','10','11']:
        opts = {'col':0, 'count_hits_not':'1', 'count_clear_not':'1', 'config_mode':config_mode}    
        set_config(vth, driver, **opts)
        a = raw_input('waiting')


def source_scan(args):
    vth = args.vth
    driver = chip.DgeneDriver(chip.dgene, config_size=800)
    driver.init_blocks()
    pixels_dac = PixelLibrary.from_file(pixels_dac_name)
    enable_hitor_chip(driver)
    state = State.from_file()
    state.grid = 1
    state.enabled = -1
    state.tuned = -1
    state.save()
    write_chip_tuned(pixels_dac, driver)
    driver.disable_all_columns()
    enable_chip(driver)
    chip.init_hpgene(chip.hpgene, 255)
    chip.init_hpcntr(chip.hpcntr)
    count = 1000
    counts, vbpths = [], []
    while count > 5 or vth < 120:
        set_config(vth, driver, config_mode='11') # look at all pixels
        count = float(timed_count(args.delay, chip.hpcntr))
        counts.append(count)
        vbpths.append(vth)
        print vth, count
        vth += 1
    outfile = open('pixel_source_rate.csv', 'w')
    outfile.write(','.join((str(vbpth) for vbpth in vbpths)) + '\n')
    outfile.write(','.join((str(count) for count in counts)) + '\n')
    outfile.close()
        
def main_setup(args):
    print "Assuming the chip is oriented with the control header at the top:\n"
    print "  The power supply on the right should be connected to 1.5V (J30)" 
    print "  The substrate supply on the left should be connected to -7.0V (J33)\n"
    print "  The HP Generator should be connected to the upper right limo connection (J54)\n"
    print "  The data generator channels should be connected to the correspondingly\n  named header on the top of the chip.\n    These names are listed in the data generator, but as a guide,\n    the data generator channels are in the correct order from left to right,\n    and the connection pattern is (from the left) XXCCCXCCCCXCC\n    where X is not connected and C is connected.\n"
    print "  The counter should be connected to the hitor (second connection from the left\n    on the top row.)\n\n"
    print "For analog tests:" 
    print "  Channel 1 on the scope should be connected to the corresponding pixel." 
    print "  For small pixel tests, load Setup2 from memory; for large load Setup3." 
    return

def main_noise(args):
    main_test_pixel_digital(args.col, args.row, True, args.freq, configs=['none','count'], config_mode='11')
    return

def main_analog(args):
    driver = chip.DgeneDriver(chip.dgene, config_size=800)
    driver.init_blocks()
    if args.type == 'small':
        set_config(150, driver, config_mode = '11') #for small pixel
    elif args.type == 'large':
        set_config(150, driver, PrmpVbp = 244, PrmpVbf = 1, config_mode = '11') #for large pixel
    driver.enable_hitor_all_columns()
    driver.disable_all_columns()
    return


def test_single(col, row):
    chip.init_hpgene(chip.hpgene, 255)
    chip.init_hpcntr(chip.hpcntr)

    # Changes the analog settings of the preamp.
    set_config(150) # first argument is vbp_th, numbers that tend to be good: 80-150

    # config_size controls the size of the instruction: 380 for column operation, 800 for config operation
    driver = chip.DgeneDriver(chip.dgene, config_size=380)
    driver.init_blocks()
    # Set each pixel to not output hits
    driver.disable_all_columns()
    # Turn on hits for the one we want.
    driver.enable_single_pixel(col, row)

    # Records what we changed
    state = State.from_file()
    state.enabled = -1
    state.save()
    
    # Actual measurement
    # predefined method to do this:
    v = measure_thresh_fast(driver, chip.hpcntr, chip.hpgene, col, row)
    print v
    


def main_command_line():
    parser = argparse.ArgumentParser(description="Present a few options from pix.py to be used from the command line for testing.\nNote that pix.py contains commands to do much more than the options here.")
    subparsers = parser.add_subparsers(title = 'Functions')

    setup = subparsers.add_parser('setup', help='Print instructions for the physical setup of the chip.')
    setup.set_defaults(func=main_setup)

    noise = subparsers.add_parser('noise', help='Run digital noise test for a single pixel.')
    noise.set_defaults(func=main_noise)
    noise.add_argument('--col', dest='col', type=int, default=8, help='The column to read in the noise scan.')
    noise.add_argument('--row', dest='row', type=int, default=63, help='The row to read in the noise scan.')
    noise.add_argument('--freq', dest='freq', type=float, default=50.0, help='Set the external clock frequency.')

    analog = subparsers.add_parser('analog', help='Setup pixels in configuration for analog tests using the oscilloscope.')
    analog.set_defaults(func=main_analog)
    analog.add_argument('type', choices=['small','large'], help='The type of pixel that will be tested. (This controls what setting will be used for the bias voltages.)')

    tune = subparsers.add_parser('tune', help='Tune the large pixels of the chip. (Also records the results to pixels_tune2.csv)')
    tune.set_defaults(func=main_tune)

    scan = subparsers.add_parser('scan', help='Scan the chip and save to pixels_scan.csv')                        
    scan.set_defaults(func=main_scan)
    scan.add_argument('--vth', dest='vth', type=int, default=150, help='The vth setting to scan the chip at.')
    scan.add_argument('--pixels', dest='pixels', help='If provided, the chip is tuned to the values stored in this file before scanning.')

    source = subparsers.add_parser('source', help='Run integral scan of source through the hitor. Note: this needs to be done after tuning.')
    source.set_defaults(func=source_scan)
    source.add_argument('--vth', dest='vth', type=int, default=80, help='The vth setting to start the source scan.')
    source.add_argument('--delay', dest='delay', type=int, default=1, help='How many seconds to wait while counting hits.')
    
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main_command_line()


