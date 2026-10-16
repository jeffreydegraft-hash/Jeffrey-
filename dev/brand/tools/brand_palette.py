"""Sample the dominant colours of a brand image (logo, label art, banner).

Usage: python3 -I brand_palette.py <image> [n_colours=6]
Ignores fully/mostly transparent pixels (logo PNG/SVG-rendered backgrounds),
quantises with Pillow's median cut, prints hex + share, and WCAG contrast of
each colour against white and #1D1D1F so text colours can be checked.
"""
import sys
from PIL import Image

def lum(rgb):
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)

path = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 6
im = Image.open(path).convert("RGBA")
im.thumbnail((600, 600))
data = im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata()
px = [p[:3] for p in data if p[3] >= 200]
if not px:
    sys.exit("no opaque pixels")
flat = Image.new("RGB", (len(px), 1))
flat.putdata(px)
q = flat.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
pal = q.getpalette()[: n * 3]
counts = sorted(q.getcolors(), reverse=True)
total = sum(c for c, _ in counts)
print(f"{path}: {len(px)} opaque px sampled")
for c, idx in counts:
    rgb = tuple(pal[idx * 3: idx * 3 + 3])
    hx = "#%02X%02X%02X" % rgb
    print(f"  {hx}  {100 * c / total:5.1f}%   vs white {contrast(rgb, (255,255,255)):4.1f}:1   vs #1D1D1F {contrast(rgb, (29,29,31)):4.1f}:1")
