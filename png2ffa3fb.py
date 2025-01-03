#!/usr/bin/env python

# Script for converting between a 240x320 PNG image and a raw framebuffer file containg raw pixels that can
# be displayed on the Flashforge Adventurer 3 screen by executing "cat file.img > /dev/fb0" on the printer.
# The script also rotates the image 180 degrees, since the Adventurer 3 screen is mounted upside down.
# Requires Pillow and numpy to be installed.

from PIL import Image
import numpy as np
from struct import unpack
from sys import argv, exit, stderr
from typing import List
from os import stat

# Framebuffer config for the Flashforge Adventurer 3
width                =  240
height               =  320
bytes_per_pixel      =    2
unpack_format_string = '<H'
rotation             =  180

def main(argv: List[str]) -> None:
    """
    Main function to handle command line arguments and invoke the appropriate conversion function.
    
    Args:
    argv (List[str]): Command line arguments.
    
    Raises:
    SystemExit: If incorrect number of arguments or unsupported file extensions are provided.
    """
    if len(argv) != 3:
        print(f"Usage: {argv[0]} source destination", file=stderr)
        exit(1)

    source_file = argv[1]
    dest_file = argv[2]

    source_ext = source_file[-4:].lower()
    dest_ext = dest_file[-4:].lower()
    
    try:
        if source_ext == '.img' and dest_ext == '.png':
            framebuffer_to_png(source_file, dest_file)
        elif source_ext == '.png' and dest_ext == '.img':
            png_to_framebuffer(source_file, dest_file)
        else:
            raise ValueError("Application only converts between .img and .png")
    except Exception as e:
        print(f"Error: {e}", file=stderr)
        exit(1)

def png_to_framebuffer(source: str, destination: str) -> None:
    """
    Converts a PNG image to a raw framebuffer format suitable for the Flashforge Adventurer 3 screen.

    Args:
    source (str): Path to the source PNG file.
    destination (str): Path to the destination raw framebuffer file.

    Raises:
    ValueError: If the source PNG dimensions are incorrect.
    """
    with Image.open(source) as img:
        if img.size != (width, height):
            raise ValueError(f"PNG must have dimensions {width}x{height}")
        
        if 'A' in img.mode:
            # Since alpha is a single bit and seems to be ignored in the A3 framebuffer, composite
            # the image on a white background and convert to RGB if the PNG has an alpha channel
            img = Image.alpha_composite(Image.new(img.mode, img.size, 'white'), img).convert('RGB')
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        img = img.rotate(rotation)


        img_array = np.array(img).reshape(-1, 3)
        bytes_array = np.zeros((width * height, bytes_per_pixel), dtype=np.uint8)

        # The pixel is saved as a 16 bit little endian value with the following bits used
        # for the different channels: RRRRRGGGGGBBBBBA (RGBA5551)
        # Since it is little endian the actual on disk structure is |GGBBBBBA|RRRRRGGG|
        for i in range(width * height):
            r = (img_array[i][0] >> 3) & 0x1F
            g = (img_array[i][1] >> 3) & 0x1F
            b = (img_array[i][2] >> 3) & 0x1F
            pixel = (r << 11) | (g << 6) | (b << 1) | 1  # Setting alpha to 1
            bytes_array[i, 0] = pixel & 0xFF
            bytes_array[i, 1] = (pixel >> 8) & 0xFF

        with open(destination, 'wb') as f:
            f.write(bytes_array.tobytes())

def framebuffer_to_png(source: str, destination: str) -> None:
    """
    Converts a raw framebuffer file suitable for the Flashforge Adventurer 3 screen to a PNG image.

    Args:
    source (str): Path to the source raw framebuffer file.
    destination (str): Path to the destination PNG file.

    Raises:
    ValueError: If the source raw framebuffer file size is incorrect, the size should be width * height * bytes per pixel
    """
    expected_size = width * height * bytes_per_pixel

    if stat(source).st_size != expected_size:
        raise ValueError(f"IMG file must be {expected_size} bytes ({width}x{height} {bytes_per_pixel * 8}bpp)")

    # numpy arrays are [height, width], not [width, height]
    img_array = np.zeros((height, width, 3), dtype=np.uint8)
    
    with open(source, 'rb') as f:
        for i in range(height):
            for j in range(width):
                # The pixel is saved as a 16 bit little endian value with the following bits used
                # for the different channels: RRRRRGGGGGBBBBBA (RGBA5551)
                # Since it is little endian the actual on disk structure is |GGBBBBBA|RRRRRGGG|
                pixel = unpack(unpack_format_string, f.read(bytes_per_pixel))[0]
                img_array[i, j] = [
                    ((pixel >> 11) & 0x1F) << 3,  # red
                    ((pixel >> 6)  & 0x1F) << 3,  # green
                    ((pixel >> 1)  & 0x1F) << 3   # blue
                ]
    
    img = Image.fromarray(img_array).rotate(rotation)
    img.save(destination)

if __name__ == '__main__':
    main(argv)
