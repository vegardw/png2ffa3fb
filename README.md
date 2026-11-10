# png2ffa3fb

Convert between PNG images and raw framebuffer images for the Flashforge
Adventurer 3's 240 × 320 display.

## Usage

Install the dependencies, for example with [uv](https://docs.astral.sh/uv/):

```sh
uv venv
uv pip install Pillow NumPy
source .venv/bin/activate
```

Then convert in either direction:

```sh
python3 png2ffa3fb.py source.png destination.img
python3 png2ffa3fb.py source.img destination.png
```

- The PNG must be exactly 240 × 320 pixels; nothing is resized or cropped.
- The raw file is 153600 bytes of little-endian RGB565, rotated 180° to match
  how the display is mounted. Decoding rotates it back.
- RGBA images are composited over white. `LA` and palette transparency are not
  supported; convert such images to RGBA first.
- Decoded images keep 5 bits of red and blue and 6 bits of green.

Versions before f9c62e3 wrote RGBA5551 and lost colours under NumPy 2. Files made
with them show wrong colours on the display; convert them again.

## Show an image on the printer

On the printer (over SSH), save the current screen, show the image, then restore:

```sh
dd if=/dev/fb0 of=/tmp/saved.img bs=153600 count=1
cat image.img > /dev/fb0
cat /tmp/saved.img > /dev/fb0
```

This assumes the display layout of the tested printer: 16 bits per pixel and
480-byte rows (see `/sys/class/graphics/fb0/`). The printer's own software may
draw over the image while it runs.

## Tests

```sh
uv run python -m unittest discover -s tests -v
```

The tests cover pixel values, rotation, byte order, all 65536 colours, alpha,
grayscale and invalid input. They pass with Python 3.11 / NumPy 1.26 and
Python 3.13 / NumPy 2.2 (Pillow 11.1). The [device test charts](device-tests/README.md)
showed the expected colours and orientation on one printer (2026-11-10).

## License

Released under the [MIT License](LICENSE).
