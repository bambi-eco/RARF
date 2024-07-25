from enum import Enum


class Direction(Enum):
    UP = 0b001
    DOWN = 0b010
    LEFT = 0b011
    RIGHT = 0b100
    FORWARD = 0b101
    BACKWARD = 0b110
