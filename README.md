# Example how to use Capture2Go imu and ScienceMode4 python lib together

## Introduction

Provides an example how to use SensorStim Capture2Go sensor (https://www.capture2go.com)
in combination with a Hasomed Science ScienceMode4 stimulator (https://github.com/ScienceMode).

This example uses data from a Capture2Go device to adjust stimulation parameters of P24.

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

This examples expects a cyclic movement of the imu. The sensor must be attached to the 
bicycle crank to have enough rotation around the sensor itself.

## Hints
- Adjust name/port for both devices depending on your setup
- run main.py
- Example runs until enter key is pressed