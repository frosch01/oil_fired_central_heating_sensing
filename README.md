# sensing_oil_fired_central_heating
Collecting data from a oil fired central heating

## 1-wire setup and testing

### Register ds2482 network bridge on I²C.
Expected ID of ds2428 is 0x18
```bash
i2cdetect -y 1
echo ds2482 0x18 > /sys/bus/i2c/devices/i2c-1/new_device
```

### Read w1 therm sensors via shell command

see: https://www.kernel.org/doc/Documentation/w1/w1.generic

```bash
time grep "t=" 10-0008036ad694/w1_slave 10-0008036aeae2/w1_slave 10-00080373db9b/w1_slave
```

## Planning

### New Features

1. ADD: For therm sensors, there shall be a means to create a group of events in a single call
2. ADD: For therm sensors, there be a means to register a group of events in a single call
3. ADD: For therm sensor, there shall be added the differentiated value to current value
4. ADD: Implement a screen saver for the OLED display. 
5. ADD: Supress short activations of flame sensing on burner power on

### Bugs

1. FIX: There are too many log entries at the file. Eliminate bubbling event source
