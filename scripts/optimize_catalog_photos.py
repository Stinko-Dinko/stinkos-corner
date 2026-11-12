#!/usr/bin/env python3
"""Preview-only product image optimization.

The 71 uploaded original photographs stay in Google Drive. This creates small
web-ready copies in the preview branch and composed, image-filled card frames
without cropping the product subject out of portrait photographs.
"""
from pathlib import Path
import json
from PIL import Image, ImageFilter, ImageOps

catalog_js=Path("data/catalog.js").read_text(encoding="utf8")
catalog=json.loads(catalog_js[catalog_js.index("{"):catalog_js.rindex("}")+1])
photos=sorted({name for p in catalog["products"] for name in p.get("images",[])})
assert len(photos)==71, f"Expected 71 approved photos, got {len(photos)}"
out_total=0
for n,relative in enumerate(photos,1):
    source=Path(relative)
    if not source.is_file():
        raise SystemExit(f"Missing source: {relative}")
    img=ImageOps.exif_transpose(Image.open(source)).convert("RGB")
    # Web pages do not need the source camera's full-size 3000-4000 pixel JPEGs.
    img.thumbnail((1600,1600),Image.Resampling.LANCZOS)
    img.save(source,"JPEG",quality=79,optimize=True,progressive=True,subsampling=0)
    # Card frame uses the source photograph edge-to-edge as a soft background
    # and places the COMPLETE subject-bearing photograph above it.
    # This avoids cutting off portrait decals with a harsh center-crop.
    w,h=900,788
    blurred=ImageOps.fit(img,(w,h),Image.Resampling.LANCZOS,centering=(0.5,0.5))
    blurred=blurred.filter(ImageFilter.GaussianBlur(radius=25))
    foreground=img.copy()
    foreground.thumbnail((w,h),Image.Resampling.LANCZOS)
    left=(w-foreground.width)//2
    top=(h-foreground.height)//2
    blurred.paste(foreground,(left,top))
    target=Path("images/cards")/source.relative_to("images/products")
    target=target.with_suffix(".webp")
    target.parent.mkdir(parents=True,exist_ok=True)
    blurred.save(target,"WEBP",quality=78,method=5)
    out_total+=target.stat().st_size
    print(f"{n:02d}/71 {source.stat().st_size//1024} KB photo, {target.stat().st_size//1024} KB card: {relative}",flush=True)
print(f"Completed 71 optimized photos and 71 framed card images; cards total {out_total//1024} KB",flush=True)
