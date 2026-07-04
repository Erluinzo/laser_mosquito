"""Laser gating.

The laser is wired to a GPIO pin and is only switched on when ALL of:
 - the operator started the tracker with --arm
 - a target has been confirmed for CONFIRM_FRAMES consecutive frames
 - the on-time watchdog (MAX_ON_SECONDS + COOLDOWN_SECONDS) allows it
The pin is forced low at startup, on target loss, and at interpreter exit.

!! Only ever connect a laser pointer of 1 mW or less. See the project README:
the original author's strong warning about eye damage applies to every part
of this code.
"""
import atexit
import time

import config

try:
    import Jetson.GPIO as GPIO
except ImportError:
    GPIO = None


class LaserGate(object):
    def __init__(self, armed):
        self._armed = armed
        self._confirmed = 0
        self._on_since = None
        self._cooldown_until = 0.0
        self.is_on = False
        self._gpio = GPIO if (armed and GPIO is not None) else None
        if armed and GPIO is None:
            print("safety: Jetson.GPIO not available, laser output is simulated")
        if self._gpio:
            self._gpio.setmode(self._gpio.BOARD)
            self._gpio.setup(config.LASER_GPIO_PIN, self._gpio.OUT,
                             initial=self._gpio.LOW)
        atexit.register(self.off)

    def update(self, target_confirmed):
        """Call once per frame; switches the laser according to the rules."""
        now = time.monotonic()
        self._confirmed = self._confirmed + 1 if target_confirmed else 0
        want_on = (self._armed
                   and self._confirmed >= config.CONFIRM_FRAMES
                   and now >= self._cooldown_until)
        if (self.is_on and self._on_since is not None
                and now - self._on_since > config.MAX_ON_SECONDS):
            want_on = False  # watchdog expired, force an off-period
            self._cooldown_until = now + config.COOLDOWN_SECONDS
        self._set(want_on, now)
        return self.is_on

    def off(self):
        self._set(False, time.monotonic())

    def _set(self, on, now):
        if on and not self.is_on:
            self._on_since = now
        if not on:
            self._on_since = None
        if on != self.is_on and self._gpio:
            self._gpio.output(config.LASER_GPIO_PIN,
                              self._gpio.HIGH if on else self._gpio.LOW)
        self.is_on = on
