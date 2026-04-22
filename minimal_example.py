#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025
# SensorStim Neurotechnology GmbH <support@capture2go.com>
# HasomedScience GmbH <sciencemode@hasomed.de>
#
# SPDX-License-Identifier: MIT

"""
Provides an example how to use SensorStim Capture2Go sensor (https://www.capture2go.com)
in combination with a Hasomed Science ScienceMode4 stimulator (https://github.com/ScienceMode)
"""

import argparse
import asyncio
from enum import IntEnum

import numpy as np

import capture2go as c2g
import science_mode_4 as sm4


class Muscles(IntEnum):
    """Muscles, each one is attached to a channel"""
    QUADRICEPS = 0
    GLUTEUS_MAXIMUS = 1
    HAMSTRINGS = 2
    GASTROCNEMIUS = 3
    TIBIALIS_ANTERIOR = 4


async def get_imu_data(name: str, queue: asyncio.Queue[float]):
    """Handles communication with Capture2Go device"""

    # Connect, initialize, start real-time orientation streaming.
    imu, = await c2g.connect([name])
    await imu.init(setTime=True, abortStreaming=True)
    await imu.send(c2g.pkg.CmdSetMeasurementMode(statusMode=1))
    await imu.send(c2g.pkg.CmdStartRealTimeStreaming(mode=c2g.pkg.RealTimeDataMode.REAL_TIME_DATA_QUAT))
    try:
        async for package in imu:
            if isinstance(package, c2g.pkg.DataQuatFixedRt):
                parsed = package.parse()

                # Calculate crank angle.
                quat = parsed['quat']
                vec = c2g.utils.rotateinv(quat, np.array([0, 0, 1], float))
                crank_angle = np.rad2deg(np.atan2(vec[1], vec[0]))

                queue.put_nowait(crank_angle)
                print(f'crank angle: {crank_angle:.1f} °')
            else:
                print('package:', package)

    except asyncio.CancelledError:
        print('Stopping streaming.')
        await imu.send(c2g.pkg.CmdStopStreaming())
        await imu.disconnect()


class Stimulator:
    """Represents a P24 device"""

    def __init__(self, com_port: str, queue: asyncio.Queue[float]):
        self.com_port = com_port

        self.queue = queue
        self.current = 50
        self.last_active_muscles: set[Muscles] = {}
        self.muscle_ranges = {
                Muscles.QUADRICEPS: (0, 120),
                Muscles.GLUTEUS_MAXIMUS: (10, 100),
                Muscles.HAMSTRINGS: (60, 180),
                Muscles.GASTROCNEMIUS: (120, 240),
                Muscles.TIBIALIS_ANTERIOR: (270, 360)
            }


    async def handle_communication(self):
        """Handles communication with P24 device"""
        try:
            # disable ScienceMode logging
            sm4.logger().disabled = True
            # create serial port connection
            connection = sm4.SerialPortConnection(self.com_port)
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
            # start stimulation
            await self.update(mid_level, 0)

            while True:
                try:
                    angle = await asyncio.wait_for(self.queue.get(), timeout=0.5)
                    await self.update(mid_level, angle)
                except TimeoutError:
                    # we have to call get_current_data() every 1.5s to keep stimulation ongoing
                    pass

                await mid_level.get_current_data()

        except asyncio.CancelledError:
            print('Stopping stimulating')
            # call stop mid level
            await mid_level.stop()

            # close serial port connection
            connection.close()


    async def update(self, mid_level: sm4.LayerMidLevel, angle: float):
        """Update active stimulation channels based on input angle"""
        normalized_angle = (angle + 360.0) % 360.0
        active_muscles: list[Muscles] = []
        for muscle, (start, end) in self.muscle_ranges.items():
            if start <= normalized_angle <= end:
                active_muscles.append(muscle)

        # update stimulation only if something changed
        if active_muscles != self.last_active_muscles:
            self.last_active_muscles = active_muscles

            cc = [None] * 8
            for x in active_muscles:
                cc[x] = (sm4.MidLevelChannelConfiguration(True, 1, 20,
                                                           [sm4.ChannelPoint(200, self.current),
                                                            sm4.ChannelPoint(100, 0),
                                                            sm4.ChannelPoint(200, -self.current)]))
            await mid_level.update(cc)


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Example for combining Capture2Go IMUs and the P24 stimulator.')
    parser.add_argument('imu_device', help='IMU device name ("IMU_*" or "usb/COM*")')
    parser.add_argument('sciencemode_device', help='ScienceMode device name ("COM*")')
    args = parser.parse_args()

    queue: asyncio.Queue[float] = asyncio.Queue()
    stimulator = Stimulator(args.sciencemode_device, queue)

    try:
        await asyncio.gather(
            get_imu_data(args.imu_device, queue),
            stimulator.handle_communication(),
        )
    except asyncio.CancelledError:
        # Expected behavior during shutdown
        print('cancelled.')


if __name__ == '__main__':
    asyncio.run(main())
