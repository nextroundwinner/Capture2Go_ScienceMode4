"""
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

Example runs until enter key is pressed
"""


from concurrent.futures import ThreadPoolExecutor
import sys
import asyncio

import capture2go as c2g
import science_mode_4 as sm4

from vector import Vector
from quaternion import Quaternion
from algorithm import Algorithm


class Example:
    """Example class
    
    c2g_name: name (BLE or serial port)
    
    p24_port: P24 serial port"""

    def __init__(self, c2g_name: str, p24_port: str):
        self._c2g_name = c2g_name
        self._p24_port = p24_port

        self._running = True
        self._current = 10.0
        self._channel_count = 1

        self._algorithm = Algorithm(50)


    async def main(self):
        """Main function to run example"""
        await asyncio.gather(asyncio.create_task(self._handle_stimulator()),
                            asyncio.create_task(self._handle_sensor()),
                            asyncio.create_task(self._handle_keyboard_input()))


    async def _handle_stimulator(self):
        """Handle p24 device"""


        async def update(mid_level: sm4.LayerMidLevel):
            cc1 = sm4.MidLevelChannelConfiguration(True, 3, 20, [sm4.ChannelPoint(200, self._current),
                                                                sm4.ChannelPoint(100, 0),
                                                                sm4.ChannelPoint(200, -self._current)])
            await mid_level.update([cc1] * self._channel_count)


        return
        # disable ScienceMode logging
        sm4.logger().disabled = True
        # create serial port connection
        connection = sm4.SerialPortConnection(self._p24_port)
        # open connection, now we can read and write data
        connection.open()

        # create science mode device
        device = sm4.DeviceP24(connection)
        # call initialize to get basic information (serial, versions) and stop any
        # active stimulation/measurement to have a defined state
        await device.initialize()

        # get mid level layer to call mid level commands
        mid_level = device.get_layer_mid_level()
        # call init mid level, we want to stop on all stimulation errors
        await mid_level.init(True)
        # simple stimulation pattern
        await update(mid_level)

        # stimulate for 15s
        while self._running:
            # simple stimulation pattern
            await update(mid_level)

            # we have to call get_current_data() every 1.5s to keep stimulation ongoing
            cd = await mid_level.get_current_data() # pylint:disable=unused-variable
            # print(cd)

            await asyncio.sleep(0.5)

        # call stop mid level
        await mid_level.stop()

        # close serial port connection
        connection.close()


    async def _handle_sensor(self):
        """Handle Capture2Go device"""
        imu = (await c2g.connect([self._c2g_name]))[0]

        await imu.init(abortRecording=True, abortStreaming=True)
        await imu.send(c2g.pkg.CmdSetMeasurementMode(
            timestamp=0,
            fullFloat200HzEnabled=False,
            fullFixedMode=c2g.pkg.SamplingMode.MODE_DISABLED,
            fullPackedMode=c2g.pkg.SamplingMode.MODE_50HZ,
            quatFloatMode=c2g.pkg.SamplingMode.MODE_DISABLED,
            quatFixedMode=c2g.pkg.SamplingMode.MODE_DISABLED,
            quatPackedMode=c2g.pkg.SamplingMode.MODE_DISABLED,
            statusMode=1,
            calibDataMode=c2g.pkg.CalibrationDataMode.CALIB_DATA_DISABLED,
            processExtensionMode=c2g.pkg.ProcessExtensionMode.NO_EXTENSION,
            syncMode=c2g.pkg.SyncMode.NO_SYNC,
            syncId=0,
            disableBiasEstimation=False,
            disableMagDistRejection=False,
            disableMagData=True
        ))
        await imu.send(c2g.pkg.CmdStartStreaming())

        async for package in imu:
            if not self._running:
                break

            parsed = package.parse()
            if 'gyr' in parsed and 'quat' in parsed:
                gyr = parsed['gyr']
                quat = parsed['quat']
                # rest = parsed['restDetected']
                sample_count = len(gyr)
                for x in range(sample_count):
                    gyr_sample = Vector(gyr[x][0], gyr[x][1], gyr[x][2])
                    quat_sample = Quaternion(quat[x][0], quat[x][1],
                                             quat[x][2], quat[x][3])
                    angle = self._algorithm.update_state(gyr_sample, quat_sample)
                    # ToDo: adjust stimulation parameters based on angle


        await imu.send(c2g.pkg.CmdStopStreaming())
        # wait until sensor has really stopped sending data
        await asyncio.sleep(1)
        await imu.disconnect()


    async def _handle_keyboard_input(self) -> str:
        """Wait for enter key to end program"""
        loop = asyncio.get_running_loop()
        executor = ThreadPoolExecutor()
        await loop.run_in_executor(executor, lambda: input("Press enter to close program\n"))
        self._running = False
        executor.shutdown(wait=True)



if __name__ == "__main__":
    # adjust Capture2Go name (BLE or serial port) and P24 serial port
    # according your setup
    example = Example(c2g_name="COM4", p24_port="COM3")
    asyncio.run(example.main())
    sys.exit(0)
