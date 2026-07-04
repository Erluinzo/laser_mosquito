"""MCP4922 dual 12-bit DAC over SPI.

Same wire format as the original scripts (command nibble 0011 for channel A,
1011 for channel B: unbuffered, 1x gain, output active) but packed with
integer operations instead of binary strings, and clamped so an out-of-range
value can never produce a malformed SPI frame.
"""
import config

_CMD = {"A": 0x3000, "B": 0xB000}


class Mcp4922(object):
    def __init__(self, spi=None):
        if spi is None:
            import spidev
            spi = spidev.SpiDev()
            spi.open(config.SPI_BUS, config.SPI_DEVICE)
            spi.max_speed_hz = config.SPI_SPEED_HZ
        self._spi = spi

    def write(self, channel, value):
        """Set one channel ("A" or "B") to a 12-bit value, clamped to 0-4095."""
        value = max(0, min(4095, int(round(value))))
        word = _CMD[channel] | value
        self._spi.xfer2([word >> 8, word & 0xFF])

    def write_xy(self, value_a, value_b):
        self.write("A", value_a)
        self.write("B", value_b)

    def close(self):
        self._spi.close()


class MockSpi(object):
    """Stands in for spidev when running with --sim on a machine without SPI."""

    def __init__(self):
        self.last = None
        self.writes = 0

    def xfer2(self, data):
        self.last = list(data)
        self.writes += 1

    def close(self):
        pass
