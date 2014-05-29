import numpy as np
from numpy import ma
from matplotlib.pyplot import step, legend, xlim, ylim, show

file = open("shiftData_before.txt","rb")
change = 2
for i in range(6):
    name = file.readline().strip("\n\r")
    data = file.readline().strip("\n\r")
    data = [int(s) for s in data]
    x = range(0,354)
    y = [s + change * i for s in data]
    step(x, y, label=name)
legend()
xlim(0, 354)
ylim(0, 20)
show()