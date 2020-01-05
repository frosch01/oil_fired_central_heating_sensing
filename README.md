# sensing_oil_fired_central_heating
Collecting data from a oil fired central heating


# Check if ds2482 network bridge is seen on i2c. Expected ID is 0x18
i2cdetect -y 1

# Tell the kernel to take over control of ds2482 
echo ds2482 0x18 > /sys/bus/i2c/devices/i2c-1/new_device

# Read time values
time grep "t=" 10-0008036ad694/w1_slave 10-0008036aeae2/w1_slave 10-00080373db9b/w1_slave

see: https://www.kernel.org/doc/Documentation/w1/w1.generic

Todo:

1. CHANGE: For therm sensors, there shall be a means to create a group of events in a single call
2. CHANGE: For therem sensors, there be a means to register a group of events in a single call
3. FIX: Somehow, there are too many log entries at the end. Eliminate bubling event source
4. ADD: Implement a screen saver for the OLED display. 
