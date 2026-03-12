"""Quaternion class"""

from __future__ import annotations
import math

from vector import Vector


class Quaternion:
    """Represents a quaternion and provides some methods"""

    def __init__(self, w: float = 1.0, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self._w = w
        self._x = x
        self._y = y
        self._z = z


    @property
    def w(self) -> float:
        """Returns w component of quaternion"""
        return self._w


    @property
    def x(self) -> float:
        """Returns x component of quaternion"""
        return self._x


    @property
    def y(self) -> float:
        """Returns y component of quaternion"""
        return self._y


    @property
    def z(self) -> float:
        """Returns z component of quaternion"""
        return self._z


    def length(self) -> float:
        """Length of quaternion"""
        return math.sqrt(self._w**2 + self._x**2 + self._y**2 + self._z**2)


    def normalize(self):
        """Normalize quaternion to length of 1.0"""
        length = self.length()
        if abs(length) < 0.001:
            raise ValueError()

        self._w /= length
        self._x /= length
        self._y /= length
        self._z /= length


    def conjugate(self):
        """Conjugate quaternion"""
        self._x = -self._x
        self._y = -self._y
        self._z = -self._z


    def axis_angle_from_quat(self) -> tuple[Vector, float]:
        """Converts a quaternion into its equivalent axis-angle form"""
        self.normalize()

        w = min(max(self._w, -1.0), 1.0)
        angle = 2.0 * math.acos(w)
        s = math.sqrt(max(1.0 - w**2, 0.0))
        if s < 0.0001:
            axis = Vector(0.0, 0.0, 1.0)
        else:
            axis = Vector(self._x / s, self._y / s, self._z / s)
        return axis, angle


    @staticmethod
    def multiply(q1: Quaternion, q2: Quaternion) -> Quaternion:
        """Multiplies q1 with q2 and returns a new quaternion"""
        w = q1.w * q2.w - q1.x * q2.x - q1.y * q2.y - q1.z * q2.z
        x = q1.w * q2.x + q1.x * q2.w + q1.y * q2.z - q1.z * q2.y
        y = q1.w * q2.y - q1.x * q2.z + q1.y * q2.w + q1.z * q2.x
        z = q1.w * q2.z + q1.x * q2.y - q1.y * q2.x + q1.z * q2.w

        return Quaternion(w, x, y, z)


    @staticmethod
    def relative_quat(qr: Quaternion, q1: Quaternion) -> Quaternion:
        """Calculates rotation from q2 to qr"""
        tmp = Quaternion(q1.w, q1.x, q1.y, q1.z)
        tmp.conjugate()
        res = Quaternion.multiply(qr, tmp)
        return res


    @staticmethod
    def angle_around_axis(qr: Quaternion, q1: Quaternion, axis_u: Vector) -> float:
        """Calculates angle around axis_u from a starting quaternion qr to another quaternion q1"""
        u = Vector(axis_u.x, axis_u.y, axis_u.z)
        u.normalize()

        q_rel = Quaternion.relative_quat(qr, q1)
        a, theta = q_rel.axis_angle_from_quat()

        cos_phi = Vector.dot_product(a, u)
        theta_u = theta * cos_phi
        return theta_u
