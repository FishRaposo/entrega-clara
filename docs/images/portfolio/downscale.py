"""Downscale the 2x Playwright card renders to exactly 1000x750.

Requires Pillow. Run from the repository root:
    python docs/images/portfolio/downscale.py

The renderer (`app/web/scripts/build-portfolio-cards.mjs`) writes
`*-2x.png` at 2000x1500. This script converts each to its 1000x750
portfolio name with Lanczos resampling and removes the intermediate.
"""

from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
TARGET = (1000, 750)

for source in sorted(HERE.glob("*-2x.png")):
    destination = source.with_name(source.name.replace("-2x", ""))
    with Image.open(source) as image:
        resized = image.convert("RGB").resize(TARGET, Image.Resampling.LANCZOS)
        resized.save(destination, optimize=True)
    source.unlink()
    print(f"wrote {destination.name} ({TARGET[0]}x{TARGET[1]})")
