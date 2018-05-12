import collections
from itertools import cycle, islice
from collections import namedtuple
from abc import ABC, abstractmethod
import time

import mido

Button = namedtuple('Button', ['name', 'press', 'light'])
Button.__doc__ = "FaderPort button details."
Button.name.__doc__ = "Button name, usually what's written on the physical button."
Button.press.__doc__ = "MIDI note sent when button is pressed and released."
Button.light.__doc__ = "MIDI note to send to illuminate the button."

# These are the FaderPort buttons, specifically ordered to "snake" down from
# the top to the bottom. Changing the order will mess up the pattern :-(

BUTTONS = [
    Button(name='Mute', press=18, light=21),
    Button(name='Solo', press=17, light=22),
    Button(name='Rec', press=16, light=23),
    Button(name='Output', press=22, light=17),
    Button(name='Chan Up', press=21, light=18),
    Button(name='Bank', press=20, light=19),
    Button(name='Chan Down', press=19, light=20),
    Button(name='Read', press=10, light=13),
    Button(name='Write', press=9, light=14),
    Button(name='Touch', press=8, light=15),
    Button(name='Off', press=23, light=16),
    Button(name='Undo', press=14, light=9),
    Button(name='Trns', press=13, light=10),
    Button(name='Proj', press=12, light=11),
    Button(name='Mix', press=11, light=12),
    Button(name='Shift', press=2, light=5),
    Button(name='Punch', press=1, light=6),
    Button(name='User', press=0, light=7),
    Button(name='Loop', press=15, light=8),
    Button(name='Record', press=7, light=0),
    Button(name='Play', press=6, light=1),
    Button(name='Stop', press=5, light=2),
    Button(name='Fast Fwd', press=4, light=3),
    Button(name='Rewind', press=3, light=4)
]

_button_from_name = {x.name: x for x in BUTTONS}
_button_from_name["Rec Arm"] = _button_from_name["Rec"]  # Add an alias
_button_from_press = {x.press: x for x in BUTTONS}


def button_from_name(name: str) -> Button:
    """
    Given a button name return the corresponding Button
    :param name: The name of a button
    :return: a Button
    """
    return _button_from_name[name.title()]


def button_from_press(press: int) -> Button:
    """
    Given a button press value return the corresponding button
    :param press: The value emitted by a pressed button
    :return: a Button
    """
    return _button_from_press.get(press, None)


# characters maps characters to the indices of the buttons that will
# display that character (as a matrix) when lit.
CHARACTERS = {
    '0': (0, 1, 3, 6, 7, 9, 10, 11, 13, 14, 15, 18, 20, 21, 22),
    '1': (1, 4, 5, 9, 12, 17, 19, 20, 21, 22),
    '2': (0, 1, 3, 6, 10, 12, 16, 19, 20, 21, 22, 23),
    '3': (0, 1, 3, 6, 9, 11, 15, 18, 20, 21, 22),
    '4': (1, 4, 5, 7, 9, 11, 12, 13, 14, 17, 20, 21),
    '5': (0, 1, 2, 6, 7, 8, 9, 11, 15, 18, 20, 21, 22),
    # '5': (0, 1, 2, 5, 8, 9, 11, 16, 18, 20, 21),
    '6': (0, 1, 2, 6, 7, 8, 9, 11, 14, 15, 18, 20, 21, 22),
    '7': (3, 4, 5, 6, 10, 12, 16, 23),
    '8': (0, 1, 3, 6, 8, 9, 11, 14, 15, 18, 20, 21, 22),
    '9': (0, 1, 3, 6, 8, 9, 10, 11, 15, 18, 20, 21, 22),
    'A': (4, 5, 7, 10, 11, 12, 13, 14, 15, 18, 19, 23),
    'B': (4, 5, 6, 7, 10, 12, 13, 14, 15, 18, 20, 21, 22, 23),
    'C': (4, 5, 7, 10, 14, 15, 18, 20, 21, 22),
    'D': (4, 5, 6, 7, 10, 11, 14, 15, 18, 20, 21, 22, 23),
    'E': (4, 5, 6, 7, 13, 14, 15, 20, 21, 22, 23),
    'F': (4, 5, 6, 7, 13, 14, 15, 23)
}


class FaderPort(ABC):
    """
    An abstract class to interface with a Presonus FaderPort device.

    The Presonus FaderPort is a USB MIDI controller that features a
    motorized fader, an endless rotary controller and a bunch of buttons.
    This class will handle the basic interfacing to the device. You
    write a concrete subclass to implement your application specific
    requirements.

    This subclass must implement the following methods:

    * `on_button` — Called when button is pressed or released,
    * `on_close` — Called when MIDI port is about  to close,
    * `on_fader` — Called when fader is moved,
    * `on_fader_touch` — Called when fader is touched or released,
    * `on_open` — Called when MIDI port has opened,
    * `on_rotary` — Called when the Pan control is rotated.

    The `fader` property allows you to read or set the fader position
    on a scale of 0 to 1023.

    You can turn the button lights on and off individually using
    `light_on` and `light_off`.

    You can display hexadecimal characters (0-9, A-F) using `char_on`.
    This will use the button LEDs in a dot matrix style.
    (Extending this to the a full alphanumeric character set is an
    exercise left to the reader).

    There some methods for 'fancy' display effects, because why not?
    Check out: `countdown`, `snake`, `blink` and `chase`

    **IMPORTANT NOTE** - There is a 'feature' in the FaderPort that can
    cause you some problems. If the 'Off' button is lit the fader will
    not send value updates when it's moved.
    """

    def __init__(self):
        self.inport = None
        self.outport = None
        self._fader = 0
        self._msb = 0

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self, number=0):
        """
        Open the FaderPort and register a callback so we can send and
        receive MIDI messages.
        :param number: 0 unless you've got more than one FaderPort attached.
                       In which case 0 is the first, 1 is the second etc
                       I only have access to a single device so I can't
                       actually test this.
        """
        self.inport = mido.open_input(find_faderport_input_name(number))
        self.outport = mido.open_output(find_faderport_output_name(number))
        self.inport.callback = self._message_callback
        self.on_open()

    def close(self):
        self.on_close()
        self.inport.callback = None
        self.fader = 0
        self.all_off()
        self.outport.reset()
        self.inport.close()
        self.outport.close()

    @abstractmethod
    def on_open(self):
        """Called after the FaderPort has been opened."""
        pass

    @abstractmethod
    def on_close(self):
        """Called when the FaderPort is closing."""
        pass

    def _message_callback(self, msg):
        """Callback function to handle incoming MIDI messages."""
        if msg.type == 'polytouch':
            button = button_from_press(msg.note)
            if button:
                self.on_button(button, msg.value != 0)
            elif msg.note == 127:
                self.on_fader_touch(msg.value != 0)
        elif msg.type == 'control_change' and msg.control == 0:
            self._msb = msg.value
        elif msg.type == 'control_change' and msg.control == 32:
            self._fader = (self._msb << 7 | msg.value) >> 4
            self.on_fader(self._fader)
        elif msg.type == 'pitchwheel':
            self.on_rotary(1 if msg.pitch < 0 else -1)
        else:
            print('Unhandled:', msg)

    @abstractmethod
    def on_rotary(self, direction: int):
        """
        Called when the FaderPort "Pan" control is changed.
        :param direction:  1 if clockwise, -1 if anti-clockwise
        """
        pass

    @abstractmethod
    def on_button(self, button: Button, state: bool):
        """
        Called when a FaderPort button is pressed and released.
        :param button: The Button in question
        :param state:  True if pressed, False when released.
        """
        pass

    @abstractmethod
    def on_fader_touch(self, state: bool):
        """
        Called when the fader is touched and when it is released.
        :param state: True if touched, False when released.
        """
        pass

    @abstractmethod
    def on_fader(self, value: int):
        """
        Called when the Fader has been moved.
        :param value: The new fader value.
        """
        pass

    @property
    def fader(self) -> int:
        """"Returns the position of the Fader in the range 0-1023"""
        return self._fader

    @fader.setter
    def fader(self, value: int):
        """Move the fader to a new position in the range 0 to 1023."""
        self._fader = int(value) if 0 < value < 1024 else 0
        self.outport.send(mido.Message('control_change', control=0,
                                       value=self._fader >> 7))
        self.outport.send(mido.Message('control_change', control=32,
                                       value=self._fader & 0x7F))

    def light_on(self, button: Button):
        """Turn the light on for the given Button.

        NOTE! If yuo turn the "Off" button light on, the fader won't
        report value updates when it's moved."""
        self.outport.send(mido.Message('polytouch', note=button.light, value=1))

    def light_off(self, button: Button):
        """Turn the light off for the given Button"""
        self.outport.send(mido.Message('polytouch', note=button.light, value=0))

    def all_off(self):
        """Turn all the button lights off."""
        for button in BUTTONS:
            self.light_off(button)

    def all_on(self):
        """Turn all the button lights on.

        NOTE! The fader will not report value changes while the "Off"
        button is lit."""
        for button in BUTTONS:
            self.light_on(button)

    def snake(self, duration: float = 0.03):
        """
        Turn the button lights on then off in a snakelike sequence.
        NOTE! Does not remember prior state of lights and will finish
        with all lights off.
        :param duration: The duration to hold each individual button.
        """
        for button in BUTTONS:
            self.light_on(button)
            time.sleep(duration)

        for button in reversed(BUTTONS):
            self.light_off(button)
            time.sleep(duration)

    def blink(self, interval: float = 0.2, n: int = 3):
        """
        Blink all the lights on and off at once.
        NOTE! Does not remember prior state of lights and will finish
        with all lights off.
        :param interval: The length in seconds of an ON/OFF cycle
        :param n: How many times to cycle ON and OFF
        :return:
        """
        for i in range(n):
            self.all_on()
            time.sleep(interval / 2)
            self.all_off()
            time.sleep(interval / 2)

    def char_on(self, c):
        """
        Use button lights (as matrix) to display a hex character.
        :param c: String containing one of 0-9,A-F
        """
        if c.upper() in CHARACTERS:
            for i in CHARACTERS[c.upper()]:
                self.light_on(BUTTONS[i])

    def countdown(self, interval: float = 0.5):
        """
        Display a numeric countdown from 5
        :param interval: The interval in seconds for each number.
        """
        for c in '54321':
            self.char_on(c)
            time.sleep(interval * 0.66667)
            self.all_off()
            time.sleep(interval * 0.33333)

    def chase(self, duration: float = 0.08, num_lights: int = 2, ticks: int = 20):
        """
        Display an animated light chaser pattern
        Chase will last ticks * duration seconds
        :param duration: How long each chase step will last in seconds
        :param num_lights: How many lights in the chase (1 to 4)
        :param ticks: How many chase steps.
        """
        seq = [
            button_from_name('Chan Down'),
            button_from_name('Bank'),
            button_from_name('Chan Up'),
            button_from_name('Output'),
            button_from_name('Off'),
            button_from_name('Undo'),
            button_from_name('Loop'),
            button_from_name('User'),
            button_from_name('Punch'),
            button_from_name('Shift'),
            button_from_name('Mix'),
            button_from_name('Read'),
        ]

        num_lights = num_lights if num_lights in [1, 2, 3, 4] else 2

        its = [cycle(seq) for _ in range(num_lights)]
        for i, it in enumerate(its):
            if i:
                consume(it, i * (len(seq) // num_lights))

        for x in range(ticks):
            for it in its:
                button = next(it)
                self.light_on(button)
            time.sleep(duration)
            self.all_off()


def find_faderport_input_name(number=0):
    """
    Find the MIDI input name for a connected FaderPort.

    NOTE! Untested for more than one FaderPort attached.
    :param number: 0 unless you've got more than one FaderPort attached.
                   In which case 0 is the first, 1 is the second etc
    :return: Port name or None
    """
    ins = [i for i in mido.get_input_names() if i.lower().startswith('faderport')]
    if 0 <= number < len(ins):
        return ins[number]
    else:
        return None


def find_faderport_output_name(number=0):
    """
    Find the MIDI output name for a connected FaderPort.

    NOTE! Untested for more than one FaderPort attached.
    :param number: 0 unless you've got more than one FaderPort attached.
                   In which case 0 is the first, 1 is the second etc
    :return: Port name or None
    """
    outs = [i for i in mido.get_output_names() if i.lower().startswith('faderport')]
    if 0 <= number < len(outs):
        return outs[number]
    else:
        return None


class TestFaderPort(FaderPort):
    """
    A class for testing the FaderPort functionality and demonstrating
    some of the possibilities.
    """

    def __init__(self):
        super().__init__()
        self._shift = False
        self.cycling = False
        self.should_exit = False

    @property
    def shift(self):
        return self._shift

    def on_open(self):
        print('FaderPort opened!!')

    def on_close(self):
        print('FaderPort closing...')

    def on_rotary(self, direction):
        print(f"Pan turned {'clockwise' if direction > 0 else 'anti-clockwise'}.")
        if self.shift:
            if direction > 0:
                if self.fader < 1023:
                    self.fader += 1
            else:
                self.fader -= 1

    def on_button(self, button, state):
        print(f"Button: {button.name} {'pressed' if state else 'released'}")
        if button.name == 'Shift':
            self._shift = not self._shift
        if button.name == 'Off' and not state:
            self.should_exit = True
        if not self.cycling:
            if state:
                self.light_on(button)
            else:
                self.light_off(button)

    def on_fader_touch(self, state):
        print(f"Fader: {'touched' if state else 'released'}")

    def on_fader(self, value):
        print(f"Fader: {self.fader}")


def consume(iterator, n):  # Copied consume From the itertool docs
    """Advance the iterator n-steps ahead. If n is none, consume entirely."""
    # Use functions that consume iterators at C speed.
    if n is None:
        # feed the entire iterator into a zero-length deque
        collections.deque(iterator, maxlen=0)
    else:
        # advance to the empty slice starting at position n
        next(islice(iterator, n, n), None)


def test():
    with TestFaderPort() as f:
        f.countdown()
        f.fader = 1023
        f.snake()
        f.fader = 512
        f.blink()
        f.fader = 128
        f.chase(num_lights=3)
        f.fader = 0
        print('Try the buttons, the rotary and the fader. The "Off" '
              'button will exit.')
        while not f.should_exit:
            time.sleep(1)


if __name__ == '__main__':
    test()
