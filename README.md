# png2ffa3fb

Convert between PNG images and raw framebuffer images for the Flashforge
Adventurer 3's 240 × 320 display.

## Usage

I suggest using [uv](https://docs.astral.sh/uv/) to create the virtual
environment and install the dependencies:

```sh
uv venv
uv pip install Pillow NumPy
```

Then run from this checkout with the environment activated:

```sh
source .venv/bin/activate
python3 png2ffa3fb.py source.png destination.img
python3 png2ffa3fb.py source.img destination.png
```

The encoder does not resize or clip: input must be exactly 240 × 320 pixels.
The raw file is exactly 153600 bytes, with little-endian RGB565 pixels (red
bits 15–11, green 10–5, blue 4–0). The converter rotates 180° in both
directions for the screen's mounting orientation. Decoded red and blue values
have five-bit precision, while green has six-bit precision.

RGBA input is composited over white. The existing implementation does not
support `LA` directly and does not retain palette transparency; normalize those
inputs to RGBA first if alpha must be preserved against white.

## NumPy compatibility

NumPy 2 preserves the eight-bit type of channel scalars during shifts, which
caused the old encoder to lose high colour bits. The encoder now converts each
channel to a Python integer before shifting. The file layout is the
runtime-reported RGB565 layout. See NumPy's
[data-type promotion migration notes](https://numpy.org/doc/2.0/numpy_2_0_migration_guide.html#changes-to-numpy-data-type-promotion).

## Tests

The regression suite uses the standard library's unittest runner and the same
Pillow/NumPy dependencies as the converter:

```sh
uv run python -m unittest discover -s tests -v
```

It checks fixed pixel words, rotation, byte order, all 65536 RGB565 colours,
RGBA-on-white compositing, grayscale conversion, and invalid inputs without
clobbering an existing destination. It also checks CLI failure followed by a
successful conversion. The suite passes with these checked combinations:

| Python | NumPy | Pillow |
| --- | --- | --- |
| 3.11.18 | 1.26.4 | 11.1.0 |
| 3.13.16 | 2.2.4 | 11.1.0 |

File-level checks do not establish physical display colour or orientation. The
`*-after.img` charts in [device tests](device-tests/README.md) were viewed on an
Adventurer 3 on 2026-11-10 and showed the expected colours and orientation.

For before/after raw images and a device test procedure, see
[device tests](device-tests/README.md).

## License

Released under the [MIT License](LICENSE).
