# Copyright (c) 2018 by Srinivas Garlapati

"""Marshal utility.
"""
import struct

from pydis import compatibility as compat 
from pydis.constants import (
    FLAG_REF as REF, IS_PY2, IS_PY3, MAGIC_NUMBERS, MARSHAL_CODES, PY_VERSION
)

# TODO: Add more version compatibilities.
# Python2 intrepreter should be supported.
class _NULL:
    pass


class _Unmarshal:

    def __init__(self, fp, python_version=None):
        # File pointer opned in binary mode.
        # One should make sure, if the pyc file is passed the first 8/12 bytes
        # should be read before reaching here. otherwise a bad marshal exception
        # occurs.
        self._read = fp

        # If no python_version passed, it's the current intertreter version.
        self.py_version = (
            python_version if python_version else PY_VERSION
        )

    def _load_code_handler(self, code):
        """Loading and executing marshal code specific handler.

        Marshal codes are defined in constants.MARSHAL_CODES, each code is
        binded with a specific encoding for serialization purpose.

        Arguments:
            code: Single byte in the byte stream.

        Returns:
            The specifix handlers return type.
        """
        return getattr(self, 'load_{}'.format(code))()

    def load_null(self):
        return _NULL

    def load_none(self):
        return None

    def load_false(self):
        return False

    def load_true(self):
        return True

    def stopiter(self):
        return StopIteration

    def load_ellipsis(self):
        return Ellipsis

    def r_short(self):
        x = ord(self._read(1)) | (ord(self._read(1)) << 8)
        if x & 0x8000:
            x = x - 0x10000
        return x

    def read_long(self):
        s = self._read(4)
        a = ord(s[0])
        b = ord(s[1])
        c = ord(s[2])
        d = ord(s[3])
        x = a | (b<<8) | (c<<16) | (d<<24)
        if d & 0x80 and x > 0:
            x = -((1 << 32) - x)
            return int(x)
        else:
            return x

    # TODO: handle this with Python2
    # Not required in python3
    def load_int(self):
        pass

    def load_int64(self):
        # Straight load of 64 bit, it's a C long long type.
        #
        # In pyc context, it will be 8 bytes.
        b0 = self._read(1)
        b1 = self._read(1)
        b2 = self._read(1)
        b3 = self._read(1)
        b4 = self._read(1)
        b5 = self._read(1)
        b6 = self._read(1)
        b7 = self._read(1)
        ret_val = (
            b0 | b1 << 8 | b2 << 16 | b3 << 24 |
            b4 << 32 | b5 << 40 | b6 << 48 | b7 << 56
        )
        if b7 & 0x80 and ret_val > 0:
            ret_val = -((1 << 64) - ret_val)
        return ret_val

    def load_float(self):
        pass

    def load_binary_float(self):
        pass

    def load_long(self):
        # It lands here if the numeric value is >= 64 bit

        # Python can handle values bigger to fit in 64 bit, but that needs to be
        # handled logically.
        # In PYC context, if the number goes beyond signed 64 bit range, it gets
        # converted into multiple 16 bit numbers.
        #
        # Statement from marshal.c
        #
        # We assume that Python ints are stored internally in base some power of
        # 2**15; for the sake of portability we'll always read and write them
        # in base exactly 2**15.
        #
        # Certainly this is because, the INT in python is signed and it ranges
        # from -32768 to 32767 -->. -2**15 to 2**15 - 1. So this would help
        # poratbility to python native int.
        #
        # I.e: n = 14273427342342384723428347234
        #
        # d = (n & (2**15 - 1)) -> 3426
        #   n >>= 15 --> 435590434031444846296031
        # d = (n & (2**15 - 1)) -> 15327
        #   n >>= 15 --> 13293165101057276803
        # d = (n & (2**15 - 1)) -> 31619
        #   n >>= 15 --> 405675204500038
        # d = (n & (2**15 - 1)) -> 23110
        #   n >>= 15 --> 12380224746
        # d = (n & (2**15 - 1)) -> 15594
        #   n >>= 15 --> 377814
        # d = (n & (2**15 - 1)) -> 17366
        #   n >>= 15 --> 11
        # d = (n & (2**15 - 1)) -> 11
        #   n >>= 15 --> 0

        # Hence the digit size here is 7 and the digits are, as below.
        #     digits = [3426, 15327, 31619, 23110, 15594, 17366, 11]

        # To get the actual number back.
        # final_val = 0
        # for val in [0, 1, 2, 3, 4, 5, 6] --> total 7
        #     final_val |= digits[0] << val *15
        #
        # If we decode the above loop
        # final_val = 0
        # 0: final_val |= 3426 << (0 * 15) --> 3426
        # 1: final_val |= 15327 << (1 * 15) --> 502238562
        # 2: final_val |= 31619 << (2 * 15) --> 33951144971618
        # 3: final_val |= 23110 << (3 * 15) --> 813144790117879138
        # 4: final_val |= 15594 << (4 * 15) --> 17979471087629289622882
        # 5: final_val |= 17366 << (5 * 15) --> 656086910203201699537980770
        # 6: final_val |= 11 << (6 * 15) --> 14273427342342384723428347234
        #
        # Negative values are as simple as positive, just the sign gets stored
        # along with number of digits.

        digit_size = self.read_long()
        sign = 1 if digit_size < 0 else -1
        x = 0
        for i in range(abc(digit_size)):
            d = self.r_short()
            x = x | (d<<(i*15))
        return x * sign

    def load_string(self):
        pass

    def load_interned(self):
        pass

    def stringref(self):
        pass

    def load_tuple(self):
        pass

    def load_list(self):
        pass

    def load_dict(self):
        pass

    def load_code(self):
        pass

    def load_unicode(self):
        pass

    def load_unknown(self):
        pass

    def load_set(self):
        pass

    def load_frozenset(self):
        pass

    def load_ref(self):
        pass

    def load_ascii(self):
        pass

    def load_ascii_interned(self):
        pass

    def load_tuple(self):
        pass

    def load_short_ascii(self):
        pass

    def load_short_ascii_interned(self):
        pass