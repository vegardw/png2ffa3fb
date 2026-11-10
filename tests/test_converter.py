import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import png2ffa3fb as converter


ROOT = Path(__file__).resolve().parents[1]
SIZE = (240, 320)
PIXELS = 240 * 320


class ConverterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.png = self.root / 'source.png'
        self.raw = self.root / 'screen.img'
        self.preview = self.root / 'decoded.png'

    def encode(self, image):
        image.save(self.png)
        converter.png_to_framebuffer(str(self.png), str(self.raw))
        data = self.raw.read_bytes()
        self.assertEqual(len(data), 153600)
        return data

    def test_known_rgb565_words(self):
        # Fixed format examples catch overflow independently of the decoder.
        cases = [
            ((0, 0, 0), 0x0000),
            ((255, 0, 0), 0xF800),
            ((0, 255, 0), 0x07E0),
            ((0, 0, 255), 0x001F),
            ((255, 255, 255), 0xFFFF),
            ((255, 255, 0), 0xFFE0),
            ((0, 255, 255), 0x07FF),
            ((255, 0, 255), 0xF81F),
            ((7, 7, 7), 0x0020),
            ((8, 0, 0), 0x0800),
            ((0, 8, 0), 0x0040),
            ((0, 0, 8), 0x0001),
            ((128, 0, 0), 0x8000),
            ((0, 128, 0), 0x0400),
            ((0, 0, 128), 0x0010),
            ((128, 128, 128), 0x8410),
        ]
        image = Image.new('RGB', SIZE)
        for x, (color, _) in enumerate(cases):
            image.putpixel((x, 0), color)
        data = self.encode(image)
        for x, (color, expected) in enumerate(cases):
            with self.subTest(color=color):
                offset = (PIXELS - 1 - x) * 2
                self.assertEqual(data[offset:offset + 2], struct.pack('<H', expected))

    def test_rotation_and_byte_order(self):
        image = Image.new('RGB', SIZE, 'white')
        image.putpixel((0, 0), (255, 0, 0))
        image.putpixel((239, 0), (0, 255, 0))
        image.putpixel((0, 319), (0, 0, 255))
        image.putpixel((239, 319), (0, 0, 0))
        data = self.encode(image)
        self.assertEqual(data[:2], b'\x00\x00')
        self.assertEqual(data[478:480], b'\x1f\x00')
        self.assertEqual(data[-480:-478], b'\xe0\x07')
        self.assertEqual(data[-2:], b'\x00\xf8')
        self.assertEqual(data[2:4], b'\xff\xff')

    def test_every_rgb565_color_round_trips(self):
        colors = [((r * 8), (g * 4), (b * 8))
                  for r in range(32) for g in range(64) for b in range(32)]
        pixels = colors + [(0, 0, 0)] * (PIXELS - len(colors))
        image = Image.new('RGB', SIZE)
        image.putdata(pixels)
        self.encode(image)
        converter.framebuffer_to_png(str(self.raw), str(self.preview))
        with Image.open(self.preview) as decoded:
            self.assertEqual(decoded.size, SIZE)
            self.assertEqual(decoded.tobytes(), image.tobytes())

    def test_rgba_composites_over_white(self):
        image = Image.new('RGBA', SIZE, (0, 0, 0, 0))
        image.putpixel((0, 0), (255, 0, 0, 255))
        image.putpixel((1, 0), (255, 0, 0, 128))
        data = self.encode(image)
        self.assertEqual(data[-2:], b'\x00\xf8')
        self.assertEqual(data[-4:-2], b'\xef\xfb')
        self.assertEqual(data[:2], b'\xff\xff')

    def test_grayscale_normalizes_to_rgb(self):
        data = self.encode(Image.new('L', SIZE, 128))
        self.assertEqual(data, b'\x10\x84' * PIXELS)

    def test_decoder_uses_known_raw_words(self):
        # Decode a golden byte sequence without calling the encoder.
        self.raw.write_bytes(b'\x00\xf8\xe0\x07\x1f\x00\xff\xff'
                             + b'\x00\x00' * (PIXELS - 4))
        converter.framebuffer_to_png(str(self.raw), str(self.preview))
        with Image.open(self.preview) as image:
            self.assertEqual(image.getpixel((239, 319)), (248, 0, 0))
            self.assertEqual(image.getpixel((238, 319)), (0, 252, 0))
            self.assertEqual(image.getpixel((237, 319)), (0, 0, 248))
            self.assertEqual(image.getpixel((236, 319)), (248, 252, 248))
            self.assertEqual(image.getpixel((0, 0)), (0, 0, 0))

    def test_wrong_png_size_preserves_destination(self):
        self.raw.write_bytes(b'keep existing output')
        for size in [(239, 320), (240, 319), (320, 240)]:
            with self.subTest(size=size):
                Image.new('RGB', size).save(self.png)
                with self.assertRaisesRegex(ValueError, '240x320'):
                    converter.png_to_framebuffer(str(self.png), str(self.raw))
                self.assertEqual(self.raw.read_bytes(), b'keep existing output')

    def test_wrong_raw_size_preserves_destination(self):
        self.preview.write_bytes(b'keep existing output')
        for length in [0, 153599, 153601]:
            with self.subTest(length=length):
                self.raw.write_bytes(bytes(length))
                with self.assertRaisesRegex(ValueError, '153600 bytes'):
                    converter.framebuffer_to_png(str(self.raw), str(self.preview))
                self.assertEqual(self.preview.read_bytes(), b'keep existing output')

    def test_cli_failure_then_success(self):
        self.png.write_bytes(b'not a PNG')
        self.raw.write_bytes(b'keep existing output')
        command = [sys.executable, str(ROOT / 'png2ffa3fb.py'), str(self.png), str(self.raw)]
        failed = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(failed.returncode, 1)
        self.assertIn('Error:', failed.stderr)
        self.assertEqual(self.raw.read_bytes(), b'keep existing output')
        Image.new('RGB', SIZE, 'red').save(self.png)
        passed = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(passed.returncode, 0, passed.stderr)
        self.assertEqual(self.raw.read_bytes(), b'\x00\xf8' * PIXELS)

    def test_cli_refuses_wrong_arguments_and_extensions(self):
        for args in [[], ['source.png'], ['source.png', 'target.png']]:
            with self.subTest(args=args):
                result = subprocess.run([sys.executable, str(ROOT / 'png2ffa3fb.py'), *args],
                                        capture_output=True, text=True, cwd=self.root)
                self.assertEqual(result.returncode, 1)
                self.assertTrue(result.stderr)
                self.assertFalse((self.root / 'target.png').exists())


if __name__ == '__main__':
    unittest.main()
