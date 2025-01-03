# png2ffa3fb
Small tool to convert PNG files to raw framebuffer data for the Flashforge Adventurer 3 3D printer.

## Usage
Convert png to framebuffer data:
```
./png2ffa3fb source.png destination.img
```

Convert framebuffer data to png:
```
./png2ffa3fb source.img destination.png
```

## Requirements
Requires the python packages Pillow and numpy to be installed.

## Misc
* The tool does not perform any resizing/clipping, the PNG image must be exactly 240x320 pixels
* The Adventurer 3 touch screen is mounted upside down, so the image is rotated 180 degress

## License
Released under the MIT License

