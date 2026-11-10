# Display comparison

The files in [generated/](generated/) compare the original encoder at
`78f82dc085bddfbcedf031ac0c34ff088c0ec6d1` with the fixed encoder using **the same
source PNGs and NumPy 2 environment**. The `*-after.img` files use the corrected
RGB565 layout and are the only raw files in this directory eligible for a device
write. The `*-before.img` files intentionally preserve the legacy RGBA5551
baseline for comparison and must not be written. The previous queued set is
preserved in [generated-rgba5551-queued/](generated-rgba5551-queued/).

| Pattern | Source | Old encoder | Fixed encoder | Preview |
| --- | --- | --- | --- | --- |
| Colour and orientation | [color-source.png](generated/color-source.png) | [color-before.img](generated/color-before.img) | [color-after.img](generated/color-after.img) | [Side-by-side comparison](generated/color-comparison.png) |
| Alpha over white | [alpha-source.png](generated/alpha-source.png) | [alpha-before.img](generated/alpha-before.img) | [alpha-after.img](generated/alpha-after.img) | [Side-by-side comparison](generated/alpha-comparison.png) |

Each `.img` is exactly **153600 bytes**. PNG previews are decoded from the actual
raw files; only the `*-after.img` files are suitable for the framebuffer. The
corrected raw files are also checked against a separate RGB565 encoder, and decoded
colours against the quantized source. [manifest.json](generated/manifest.json)
records exact dependency versions, converter identities and artifact hashes;
[SHA256SUMS](generated/SHA256SUMS) covers the generated files.
[DEVICE_SHA256SUMS](generated/DEVICE_SHA256SUMS) covers just the four raw files.

## Physical result

On 2026-11-10 both `*-after.img` files were written to the display of one
Adventurer 3 (fb_ili9341, 240 × 320, reported RGB565 `R11/5 G5/6 B0/5 A0/0`,
480-byte rows, zero offsets) following the procedure below, with the screen
saved first and restored byte-for-byte afterwards. Observed by the operator:

* Colour chart: orientation and corner numbers, red/green/blue and
  cyan/magenta/yellow rows, grayscale and R/G/B ramps and all four markers
  (including the darker green top-right marker) as described; no clipping.
* Alpha chart: white clear areas and the 25%/50%/100% patches as in the fixed
  preview.
* Neither image was redrawn by another process while displayed.

This verifies the display path on that printer only; other units and variants
may differ. The `*-before.img` files were not written.

## What to observe

For the colour chart after the fix:

* “TOP / UP” is upright; corners read **1, 2** at the top and **3, 4** at the bottom.
* The first row is bright red, green and blue; the next is cyan, magenta and yellow.
* The grayscale bar progresses from black to near-white, and the individual R/G/B
  ramps are in their labelled colours. There are 32 discrete levels per ramp.
* All four corner markers are visible without clipping. The top-right marker
  uses a darker green than the bright green colour bar.

The old encoder under NumPy 2 loses red and the high green bits, so white and
several colour bars become blue/dark rather than matching the source. Compare
the actual screen with the previews rather than relying only on apparent brightness.

For the alpha chart, clear areas become white. Red/green/blue and black patches
are composited at approximately 25%, 50% and 100% opacity. Pastel patches and
grays should match the fixed preview. This checks preservation of the existing
RGBA behavior; this patch does not change the separate `LA`/palette limitations.

## Attended device procedure

Do this with the printer idle, before the motion workout, using only the reviewed
`*-after.img` files. Never transfer or write the `*-before.img` legacy baseline.
This is a display-memory test; it does not require a Klipper restart, GPIO
operation or firmware update.

1. Transfer `color-after.img` and `alpha-after.img` to a new temporary folder on
   the printer's OpenWrt board, together with `DEVICE_SHA256SUMS`. Check each
   file is 153600 bytes and verify the matching checksum lines where `sha256sum`
   is available.
2. Before writing any newly generated files, confirm the active framebuffer has
   the expected 240 × 320 visible area, tightly packed 480-byte rows, 16-bit
   little-endian RGB565 fields (`R11/5 G5/6 B0/5 A0/0`) and zero display offsets.
   Use the framebuffer's runtime information rather than assuming the format
   from its bit depth. See the
   [Linux framebuffer API](https://www.kernel.org/doc/html/latest/fb/api.html).
   Stop if the layout differs.
3. Save the current screen from `/dev/fb0` into a new regular file. From the
   uploaded folder on the printer, the following captures one expected frame
   and checks that it is complete:

   ```sh
   test ! -e saved-screen.img || exit 1
   dd if=/dev/fb0 of=saved-screen.img bs=153600 count=1
   test "$(wc -c < saved-screen.img)" -eq 153600 || exit 1
   ```

4. Display the reviewed RGB565 colour chart:

   ```sh
   cat color-after.img > /dev/fb0
   ```

5. Repeat with `alpha-after.img`. Record colours,
   orientation, clipping and whether another process redraws the display. Use
   the shell for switching images; avoid touchscreen controls while the test
   picture covers the interface. If the screen keeps being redrawn, stop and
   resolve display ownership before drawing conclusions.
6. Restore the saved screen before continuing with other tests:

   ```sh
   cat saved-screen.img > /dev/fb0
   ```

A visually correct chart verifies this display path on the tested printer. It
does not establish every Adventurer 3 variant's framebuffer layout or validate
a replacement UI.

## Reproduce the files

From the repository root, using Python with Pillow and **NumPy 2.x**:

```sh
python3 tools/make_device_test.py device-tests/generated
```

The destination must not already exist; the generator refuses to overwrite a
previous result. Choose another new folder to keep an earlier comparison.
The baseline revision must be present in Git. The generator runs that revision's
converter locally as well as the current script, so use a trusted checkout.
It does not access any device or install software. A failure to reproduce the old
bug or match the independent expected output prevents publishing the result folder.
