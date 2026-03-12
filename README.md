# ScienceMode4 Python Integration with Capture2Go imu

## Introduction

Provides an example how to use SensorStim Capture2Go sensor (https://www.capture2go.com)
in combination with a Hasomed Science ScienceMode4 stimulator (https://github.com/ScienceMode)

This example uses data from a Capture2Go device to adjust stimulation parameters of P24

For Capture2Go device:
- Connect to device
- Set measurement mode
- Start streaming
- Processing data
  - Calculate angle of cyclic movement from gyro and orientation
  - Derive current and channel count from angle
- Stop streaming
- Disconnect

For P24 device:
- Connect to device
- Initialize mid level mode
- Update stimulation parameters accoring current angle of cyclic movement
- Stop stimulation
- Disconnect


## Hints
- Adjust name/port for both devices depending on your setup
- Example runs until enter key is pressed