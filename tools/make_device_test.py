"""Generate a reproducible NumPy-2 before/after display comparison in a new folder."""

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, __version__ as pillow_version


ROOT = Path(__file__).resolve().parents[1]
BASELINE = '78f82dc085bddfbcedf031ac0c34ff088c0ec6d1'
SIZE = (240, 320)
FONT = ImageFont.load_default()


def label(draw, xy, text, fill='black'):
    draw.text(xy, text, fill=fill, font=FONT)


def corners(draw):
    for box, number, color, ink in [
        ((0, 0, 19, 19), '1', 'red', 'white'),
        ((220, 0, 239, 19), '2', 'green', 'white'),
        ((0, 300, 19, 319), '3', 'blue', 'white'),
        ((220, 300, 239, 319), '4', 'white', 'black'),
    ]:
        draw.rectangle(box, fill=color)
        label(draw, (box[0] + 6, box[1] + 3), number, ink)


def color_chart():
    image = Image.new('RGB', SIZE, 'white')
    draw = ImageDraw.Draw(image)
    label(draw, (66, 5), 'TOP / UP')
    draw.polygon([(122, 21), (116, 30), (128, 30)], fill='black')
    label(draw, (54, 35), 'COLOR / ORIENTATION')
    for y, names, colors in [
        (64, ['RED', 'GREEN', 'BLUE'], ['red', '#00ff00', 'blue']),
        (127, ['CYAN', 'MAGENTA', 'YELLOW'], ['cyan', 'magenta', 'yellow']),
    ]:
        for x, name, color in zip([8, 84, 160], names, colors):
            label(draw, (x, y - 15), name)
            draw.rectangle((x, y, x + 71, y + 39), fill=color)
    label(draw, (57, 174), 'BLACK TO WHITE')
    for value in range(32):
        draw.rectangle((8 + value * 7, 190, 14 + value * 7, 213),
                       fill=(value * 8,) * 3)
    label(draw, (30, 217), '32 STEPS PER CHANNEL')
    for channel, y, name in [(0, 239, 'R'), (1, 257, 'G'), (2, 275, 'B')]:
        label(draw, (1, y), name)
        for value in range(32):
            rgb = [0, 0, 0]
            rgb[channel] = value * 8
            draw.rectangle((16 + value * 7, y, 22 + value * 7, y + 11), fill=tuple(rgb))
    label(draw, (89, 303), 'BOTTOM')
    corners(draw)
    return image


def alpha_chart():
    image = Image.new('RGBA', SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    label(draw, (66, 5), 'TOP / UP')
    label(draw, (58, 32), 'RGBA ON WHITE')
    for x, text in [(8, '25%'), (84, '50%'), (160, '100%')]:
        label(draw, (x, 52), text)
    for y, rgb in [(72, (255, 0, 0)), (127, (0, 255, 0)),
                   (182, (0, 0, 255)), (237, (0, 0, 0))]:
        for x, alpha in zip([8, 84, 160], [64, 128, 255]):
            draw.rectangle((x, y, x + 71, y + 39), fill=(*rgb, alpha))
    label(draw, (29, 284), 'CLEAR BACKGROUND = WHITE')
    label(draw, (89, 303), 'BOTTOM')
    corners(draw)
    return image


def expected_raw(source):
    # Independent format oracle for the inspected framebuffer's RGB565 layout.
    with Image.open(source) as image:
        rgba = image.convert('RGBA')
        rgb = Image.alpha_composite(Image.new('RGBA', SIZE, 'white'), rgba).convert('RGB')
        pixels = list(rgb.getdata())
    data = bytearray()
    for pixel in reversed(pixels):
        red, green, blue = pixel
        packed = ((red >> 3) << 11) | ((green >> 2) << 5) | (blue >> 3)
        data.extend(packed.to_bytes(2, 'little'))

    quantized = Image.new('RGB', SIZE)
    quantized.putdata([(red & 248, green & 252, blue & 248)
                       for red, green, blue in pixels])
    return bytes(data), quantized


def convert(script, source, destination):
    subprocess.run([sys.executable, str(script), str(source), str(destination)], check=True)


def generate(output):
    if output.exists() or output.is_symlink():
        raise ValueError('output directory must not already exist')
    if not output.parent.is_dir():
        raise ValueError('output parent must already be a directory')
    if int(np.__version__.split('.')[0]) != 2:
        raise ValueError('use NumPy 2.x to reproduce the baseline overflow')
    old_code = subprocess.check_output(['git', 'show', f'{BASELINE}:png2ffa3fb.py'], cwd=ROOT)
    current = ROOT / 'png2ffa3fb.py'
    result = {'baseline_revision': BASELINE, 'baseline_sha256': hashlib.sha256(old_code).hexdigest(),
              'fixed_sha256': hashlib.sha256(current.read_bytes()).hexdigest(),
              'python': platform.python_version(), 'numpy': np.__version__, 'pillow': pillow_version,
              'hardware_tested': False, 'patterns': {}, 'files': {}}
    with tempfile.TemporaryDirectory() as temp:
        stage = Path(temp)
        baseline = stage / 'baseline.py'
        baseline.write_bytes(old_code)
        for name, image in [('color', color_chart()), ('alpha', alpha_chart())]:
            source = stage / f'{name}-source.png'
            image.save(source)
            expected, quantized = expected_raw(source)
            for variant, script in [('before', baseline), ('after', current)]:
                raw = stage / f'{name}-{variant}.img'
                preview = stage / f'{name}-{variant}-preview.png'
                convert(script, source, raw)
                if raw.stat().st_size != 153600:
                    raise ValueError('unexpected raw image size')
                convert(current, raw, preview)
            before = (stage / f'{name}-before.img').read_bytes()
            after = (stage / f'{name}-after.img').read_bytes()
            if after != expected or before == expected:
                raise ValueError('comparison must reproduce the bug and match the independent oracle after fixing')
            with Image.open(stage / f'{name}-after-preview.png') as preview:
                if preview.tobytes() != quantized.tobytes():
                    raise ValueError('decoded output differs from the quantized source')
            comparison = Image.new('RGB', (480, 344), 'white')
            draw = ImageDraw.Draw(comparison)
            label(draw, (12, 5), 'BEFORE / LEGACY RGBA5551')
            label(draw, (252, 5), 'AFTER / FIXED')
            for x, variant in [(0, 'before'), (240, 'after')]:
                with Image.open(stage / f'{name}-{variant}-preview.png') as preview:
                    comparison.paste(preview, (x, 24))
            comparison.save(stage / f'{name}-comparison.png')
            result['patterns'][name] = {
                'different_pixels': sum(before[i:i + 2] != after[i:i + 2] for i in range(0, 153600, 2)),
                'fixed_matches_reference': True,
            }
        baseline.unlink()
        device_sums = ''.join(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n'
                              for path in sorted(stage.glob('*.img')))
        (stage / 'DEVICE_SHA256SUMS').write_text(device_sums)
        for path in sorted(stage.iterdir()):
            result['files'][path.name] = {'bytes': path.stat().st_size,
                                         'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        (stage / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n')
        sums = ''.join(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n'
                       for path in sorted(stage.iterdir()))
        (stage / 'SHA256SUMS').write_text(sums)
        output.mkdir()
        for path in sorted(stage.iterdir()):
            with (output / path.name).open('xb') as dest:
                dest.write(path.read_bytes())
    print(f'Created {output}: two before/after pairs, previews, comparisons and checksums.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='new directory under an existing parent')
    args = parser.parse_args()
    try:
        generate(args.output)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()
