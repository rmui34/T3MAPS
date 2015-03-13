TMAPS-ATLYS
============

The firmware code for the ATLYS dev board to control T3MAPS

This branch is the most up to date, but is currently untested. Changes include:

An automated mode.
Fixed ucf from a test ucf to one that actually uses the correct pins.
Better comments in the code.
This readme.
A gitignore for everything ISE spits out
Larger default FIFOs
No opening and closing of the serial port. (Which was silly slow). 

A short user guide:

Currently, the python script calls the manual mode, which is what the master branch uses. In this mode, you are required to enter yes or no at each step in the process. This is slow!
To use this mode, SW0 MUST BE UP!!!!

Now the software has a method that is automated. To enable this, SW0 must be down (position 0…). Currently, this method cannot be called just by running the script. 

Comments on the software coming soon!


