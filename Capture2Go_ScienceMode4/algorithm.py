"""Simple algorithm to evaluate a cyclic movement"""

from collections import deque
import math

from vector import Vector
from quaternion import Quaternion

class Algorithm:
    """
    Simple algorithm to evaluate a cyclic movement
    Holds a state and update it with new measurement samples
    
    Calculates main rotation axis from gyroscope values and uses this
    axis to estimate an angle around this axis from a origin quaternion
    
    call update_state() to update internal state for each measurement sample

    sensor must be attached to the bicycle crank to have enough rotation around
    the sensor itself
    """


    def __init__(self, sample_rate: int = 100):
        self._sample_rate = sample_rate
        self._sample_count = 0
        self._rest = False

        self._last_gyro_samples = deque[Vector](maxlen=sample_rate)
        self._main_rotation_axis = Vector(0, 0, 0)

        self._origin_quat: Quaternion = None
        self._angle = 0.0


    def update_state(self, gyro_sample: Vector, quat_sample: Quaternion) -> float:
        """Update state with a new gyro and quaternion sample and returns current angle"""

        self._sample_count += 1

        # save absolute gyro sample
        gyro_sample.abs()
        self._last_gyro_samples.append(gyro_sample)

        # update internal state
        self._update_rest()
        self._update_main_rotation_axis()

        # use first quaternion as origin quaternion
        if self._origin_quat is None:
            self._origin_quat = quat_sample

        # update angle only if sensor is moving, otherwise return last value
        if self._rest:
            return self._angle

        # using main rotation axis for calculation of angle between origin quaternion and current quaternion
        self._angle = Quaternion.angle_around_axis(self._origin_quat, quat_sample, self._main_rotation_axis)
        self._angle *= 180.0 / math.pi
        if self._sample_count % 10 == 0:
            print(f"angle: {self._angle} - axis {self._main_rotation_axis}")

        return self._angle


    def _set_rest(self, rest: bool):
        if self._rest != rest:
            # print(f"Rest changed {self._rest} -> {rest}")
            self._rest = rest


    def _update_rest(self):
        v = Vector(0, 0, 0)
        for x in list(self._last_gyro_samples)[-self._sample_rate/2:]:
            v.add(x)

        # sensor is in a rest state if sum of last xx gyro sample is smaller than 1 degree
        self._set_rest(v.length() < 1.0)

        # if self._sample_count % 100 == 0:
        #     print(f"Rest: {v.length()}")


    def _update_main_rotation_axis(self):
        # update rotation axis only if sensor is moving
        if self._rest:
            return

        # calculate main rotation axis by adding up last second of (absolute) gyro samples
        # and normalize result
        v = Vector(0, 0, 0)
        for x in self._last_gyro_samples:
            v.add(x)

        v.normalize()
        self._main_rotation_axis = v

        # if self._sample_count % 100 == 0:
        #     print(f"Main rotation axis: {self._main_rotation_axis}")
