# Device test charts

Two charts for checking colours and orientation on a real display. Each is
encoded by the old converter (78f82dc, "before") and the fixed one ("after"),
from the same source PNG with NumPy 2.

| Chart | Source | Before | After | Preview |
| --- | --- | --- | --- | --- |
| Colour and orientation | [PNG](generated/color-source.png) | [img](generated/color-before.img) | [img](generated/color-after.img) | [comparison](generated/color-comparison.png) |
| Alpha over white | [PNG](generated/alpha-source.png) | [img](generated/alpha-before.img) | [img](generated/alpha-after.img) | [comparison](generated/alpha-comparison.png) |

- Only the `*-after.img` files are meant for the display. The `*-before.img`
  files show the old bug and are for comparison only.
- [manifest.json](generated/manifest.json) records versions and hashes.
  [SHA256SUMS](generated/SHA256SUMS) covers all files and
  [DEVICE_SHA256SUMS](generated/DEVICE_SHA256SUMS) only the raw images.

To display a chart, see [Show an image on the printer](../README.md#show-an-image-on-the-printer).
Both `*-after.img` charts looked as described below on one printer (2026-11-10).

## What you should see

Colour chart:

- "TOP / UP" is upright; the corners read 1, 2 at the top and 3, 4 at the bottom.
- Rows of red, green, blue, then cyan, magenta, yellow.
- A grey ramp from black to near-white, and red, green and blue ramps with 32
  steps each.
- Four corner markers, none clipped. The top-right marker is a darker green than
  the green bar.

Alpha chart: clear areas are white, and the coloured and black patches appear at
about 25 %, 50 % and 100 % opacity, as in the preview.

With the old converter, red and the high green bits are lost, so white and
several bars turn blue or dark.

## Regenerate

With Pillow and NumPy 2:

```sh
python3 tools/make_device_test.py device-tests/new-folder
```

The folder must not exist. The script runs the old converter from Git history,
so use a trusted checkout. It stops if it cannot reproduce the old bug or if the
new output differs from an independent RGB565 encoder.
