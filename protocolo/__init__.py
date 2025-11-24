"""
Protocolo - A Serial Communication Protocol Library

A Python library for serial communication with packet encoding/decoding,
CRC validation, and file transfer capabilities.
"""

from .codec import Codec
from .enlace import Enlace, InvalidCRC, Timeout, splice_file

__version__ = "0.1.0"
__all__ = ["Codec", "Enlace", "InvalidCRC", "Timeout", "splice_file"]
