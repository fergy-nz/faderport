# faderport
An abstract class to interface with a Presonus FaderPort device.

The Presonus FaderPort is a USB MIDI controller that features a
motorized fader, an endless rotary controller and a bunch of buttons.
This class will handle the basic interfacing to the device. You
write a concrete subclass to implement your application specific
requirements.

This subclass must implement the following methods:

* `on_open` — Called when MIDI port has opened,
* `on_button` — Called when button is pressed or released,
* `on_fader_touch` — Called when fader is touched or released,
* `on_fader` — Called when fader is moved,
* `on_rotary` — Called when the Pan control is rotated,
* `on_close` — Called when MIDI port is about  to close.

The `fader` property allows you to read or set the fader position
on a scale of 0 to 1023.

You can turn the button lights on and off individually using
`light_on` and `light_off`.

You can display hexadecimal characters (0-9, A-F) using `char_on`.
This will use the button LEDs in a dot matrix style.
(Extending this to the a full alphanumeric character set is an
exercise left to the reader).

There are some methods for 'fancy' display effects, because why not?
Check out: `countdown`, `snake`, `blink` and `chase`

> **IMPORTANT NOTE** - There is a 'feature' in the FaderPort that can
> cause you some problems. If the 'Off' button is lit the fader will
> not send value updates when it's moved.

# Installation
You'll need Python 3.6 or later.

Then:
```sh
pip install faderport
```
should do the trick.

This will also install the
**[mido](http://mido.readthedocs.io/en/latest/index.html)** package and
[**python-rtmidi**](https://pypi.org/project/python-rtmidi/) backend.

Currently this has only been tested on Windows with a single FaderPort
because that's all I have access to.

The adventurous can read the mido docs and try alternative backends.

# Testing
Make sure your FaderPort is installed and connected and then:
```sh
from faderport import test
test()
```

This will instantiate a derived 'TestFaderPort' class, which also serves as
an example implementation, and then run through some of it's features.

It will display some light patterns and move your fader and then monitor
your actions until you hit the *"Off"* button on the FaderPort.

Try out the Pan knob, the fader and some of the buttons.

Try holding *"shift"* (on the FaderPort) and tweaking the Pan knob at the
same time.

# Change List
- Version 1.0.1 - Added a reset command at startup. Sometimes when
  faderport is reconnected it can get in a weird mode. The *Bank*
  light is lit and our code doesn't work. This seems to fix it.
- Version 1.0.0 - Initial Release

