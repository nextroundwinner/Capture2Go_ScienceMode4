"""Vector class"""

from __future__ import annotations
from typing import Self
import math


class Vector:
    """Represents a 3d vector """

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 1.0):
        self._x = x
        self._y = y
        self._z = z


    @property
    def x(self) -> float:
        """Returns x component of vector"""
        return self._x


    @property
    def y(self) -> float:
        """Returns y component of vector"""
        return self._y


    @property
    def z(self) -> float:
        """Returns z component of vector"""
        return self._z


    def length(self) -> float:
        """Length of vector"""
        return math.sqrt(self._x**2 + self._y**2 + self._z**2)


    def normalize(self):
        """Normalize vector to length of 1.0"""
        length = self.length()
        if abs(length) < 0.001:
            raise ValueError()

        self._x /= length
        self._y /= length
        self._z /= length


    def add(self, v: Vector):
        """Adds vector v to current vector"""
        self._x += v.x
        self._y += v.y
        self._z += v.z


    def abs(self):
        """Makes all components absolute"""
        self._x = abs(self._x)
        self._y = abs(self._y)
        self._z = abs(self._z)


    def __str__(self):
        return f"x: {round(self._x, 2)}, y: {round(self._y, 2)}, z: {round(self._z, 2)}"


    @staticmethod
    def dot_product(v1: Self, v2: Self) -> float:
        """Dot product between a1 and a2"""
        return v1.x * v2.x + v1.y * v2.y + v1.z * v2.z
