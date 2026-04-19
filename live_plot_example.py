"""
Provides an example how to use SensorStim Capture2Go sensor (https://www.capture2go.com)
in combination with a Hasomed Science ScienceMode4 stimulator (https://github.com/ScienceMode)
"""
#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025
# SensorStim Neurotechnology GmbH <support@capture2go.com>
# HasomedScience GmbH <sciencemode@hasomed.de>
#
# SPDX-License-Identifier: MIT

import threading
import queue
import argparse
import asyncio
from dataclasses import dataclass
from enum import IntEnum

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

import capture2go as c2g
import science_mode_4 as sm4

# matplotlib.use('QtAgg')

@dataclass
class ImuData:
    """DTO for imu measurement data"""
    gyr: np.typing.NDArray[np.float64]
    acc: np.typing.NDArray[np.float64]
    mag: np.typing.NDArray[np.float64]
    euler: np.typing.NDArray[np.float64]


class Muscles(IntEnum):
    """Muscles, each one is attached to a channel"""
    QUADRICEPS = 0
    GLUTEUS_MAXIMUS = 1
    HAMSTRINGS = 2
    GASTROCNEMIUS = 3
    TIBIALIS_ANTERIOR = 4


async def get_imu_data(name: str, q_gui: queue.Queue[ImuData], q_stim: queue.Queue[ImuData]):
    """Handles communication with Capture2Go device"""
    imu, = await c2g.connect([name])
    await imu.init(setTime=True, abortStreaming=True)
    await imu.send(c2g.pkg.CmdSetMeasurementMode(fullPackedMode=c2g.pkg.SamplingMode.MODE_200HZ, statusMode=1))
    await imu.send(c2g.pkg.CmdStartStreaming())
    try:
        async for package in imu:
            if isinstance(package, c2g.pkg.DataFullPacked):
                parsed = package.parse()

                gyr = np.rad2deg(parsed['gyr'])
                acc = parsed['acc']
                mag = parsed['mag']

                euler = np.zeros((8, 3))
                for i in range(8):
                    # euler[i] = np.rad2deg(c2g.utils.eulerAngles(parsed['quat9D'][i], 'zxy', True))

                    quat = parsed['quat'][i]
                    vec = c2g.utils.rotateinv(quat, np.array([0, 0, 1], float))
                    crank_angle = np.atan2(vec[1], vec[0])

                    euler[i] = [np.rad2deg(crank_angle), np.nan, np.nan]

                imu_data = ImuData(gyr, acc, mag, euler)
                q_gui.put(imu_data)
                q_stim.put(imu_data)
            else:
                print('package:', package)

    except asyncio.CancelledError:
        print('Stopping streaming.')
        await imu.send(c2g.pkg.CmdStopStreaming())
        await imu.disconnect()


class ImuDataPlot:
    """Class for plotting imu measurement values"""

    def __init__(self):
        self.queue: queue.Queue[ImuData] = queue.Queue()

        self.n = 800  # Number of samples to plot (at 200 Hz).
        self.t = np.arange(-self.n, 0, dtype=float)/200
        self.gyr = np.full((self.n, 3), np.nan)
        self.acc = np.full((self.n, 3), np.nan)
        self.mag = np.full((self.n, 3), np.nan)
        self.euler = np.full((self.n, 3), np.nan)

        self.create_plot()

        self.anim = FuncAnimation(self.fig, self.update_plot, interval=40, blit=True, cache_frame_data=False)


    def create_plot(self):
        """Create plot"""
        self.fig = plt.figure(figsize=(10, 8), constrained_layout=True)
        self.ax = self.fig.subplots(2, 2)

        for ax in (self.ax[0, 0], self.ax[0, 1], self.ax[1, 0]):
            ax.set_prop_cycle('color', ['#d62728', '#2ca02c', '#1f77b4'])  # Use RGB color cycle.

        self.gyr_lines = self.ax[0, 0].plot(self.t, self.gyr)
        self.ax[0, 0].set_xlim(self.t[0], self.t[-1])
        self.ax[0, 0].set_ylim(-800, 800)
        self.ax[0, 0].set_title('Gyroscope [°/s]')
        self.ax[0, 0].set_xlabel('Time [s]')
        self.ax[0, 0].legend('xyz', loc='upper left')

        self.acc_lines = self.ax[0, 1].plot(self.t, self.acc)
        self.ax[0, 1].set_xlim(self.t[0], self.t[-1])
        self.ax[0, 1].set_ylim(-20, 20)
        self.ax[0, 1].set_title('Accelerometer [m/s²]')
        self.ax[0, 1].set_xlabel('Time [s]')
        self.ax[0, 1].legend('xyz', loc='upper left')

        self.mag_lines = self.ax[1, 0].plot(self.t, self.mag)
        self.ax[1, 0].set_xlim(self.t[0], self.t[-1])
        self.ax[1, 0].set_ylim(-100, 100)
        self.ax[1, 0].set_title('Magnetometer [µT]')
        self.ax[1, 0].set_xlabel('Time [s]')
        self.ax[1, 0].legend('xyz', loc='upper left')

        self.ax[1, 1].set_prop_cycle('color', ['#1f77b4', '#d62728', '#2ca02c', ])  # Use BRG color cycle.
        self.euler_lines = self.ax[1, 1].plot(self.t, self.euler)
        self.ax[1, 1].set_xlim(self.t[0], self.t[-1])
        self.ax[1, 1].set_ylim(-180, 180)
        self.ax[1, 1].set_title('Orientation as z-x\'-y\'\' Euler angles [°]')
        self.ax[1, 1].set_xlabel('Time [s]')
        self.ax[1, 1].legend(['z', 'x\'', 'y\'\''], loc='upper left')

        for ax in self.ax.flatten():
            ax.grid()


    def update_plot(self, frame): # pylint:disable=unused-argument
        """Update plot with new imu values"""
        # Read IMU data from the queue.
        while True:
            try:
                imu_data = self.queue.get_nowait()
                self.gyr = np.vstack([self.gyr[8:], imu_data.gyr])
                self.acc = np.vstack([self.acc[8:], imu_data.acc])
                self.mag = np.vstack([self.mag[8:], imu_data.mag])
                self.euler = np.vstack([self.euler[8:], imu_data.euler])
            except queue.Empty:
                break

        # Update the plot.
        for i, line in enumerate(self.gyr_lines):
            line.set_ydata(self.gyr[:, i])
        for i, line in enumerate(self.acc_lines):
            line.set_ydata(self.acc[:, i])
        for i, line in enumerate(self.mag_lines):
            line.set_ydata(self.mag[:, i])
        for i, line in enumerate(self.euler_lines):
            line.set_ydata(self.euler[:, i])

        return self.gyr_lines + self.acc_lines + self.mag_lines + self.euler_lines


class Stimulator:
    """Represents a P24 device"""

    def __init__(self, com_port: str):
        self.com_port = com_port

        self.queue: queue.Queue[ImuData] = queue.Queue()
        self.current = 50
        self.last_active_muscles: set[Muscles] = {}
        self.last_angle = 0
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

            # stimulate for 15s
            while True:

                angle = self.last_angle
                while True:
                    try:
                        imu_data = self.queue.get_nowait()
                        angle = imu_data.euler[:-1][0][0]
                    except queue.Empty:
                        break

                self.last_angle = angle
                await self.update(mid_level, angle)

                # we have to call get_current_data() every 1.5s to keep stimulation ongoing
                cd = await mid_level.get_current_data() # pylint:disable=unused-variable
                # print(cd)

                await asyncio.sleep(0.5)

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


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Example for real-time streaming of IMU orientations.')
    parser.add_argument('imu_device', help='IMU device name ("IMU_*" or "usb)')
    parser.add_argument('sciencemode_device', help='ScienceMode device name ("COM*")')
    args = parser.parse_args()

    print(f'Using matplotlib backend {matplotlib.get_backend()!r}.')

    plot = ImuDataPlot()
    stim = Stimulator(args.sciencemode_device)

    async def run_hardware_tasks():
        try:
            await asyncio.gather(
                get_imu_data(args.imu_device, plot.queue, stim.queue),
                stim.handle_communication()
            )
        except asyncio.CancelledError:
            # Expected behavior during shutdown
            pass


    def start_background_loop(loop):
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_hardware_tasks())


    hw_loop = asyncio.new_event_loop()
    hw_thread = threading.Thread(target=start_background_loop, args=(hw_loop,), daemon=True)
    hw_thread.start()

    plt.show()

    for task in asyncio.all_tasks(hw_loop):
        hw_loop.call_soon_threadsafe(task.cancel)

    # wait until devices are finished deinitializing
    asyncio.sleep(2.0)

    hw_thread.join(timeout=2.0)


if __name__ == '__main__':
    main()
