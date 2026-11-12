#!/usr/bin/env python3
"""Stage catalog photographs from the existing public Drive website/images folder.

Only catalog-referenced photos are imported. New or changed sources are optimized
using the same established card treatment; unchanged files are not regenerated.
Everything is staged before the GitHub workflow commits. Never delete old assets.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from PIL import Image, ImageFilter, ImageOps
import gdown

DRIVE_IMAGES_FOLDER = "1ef7rffsUvJbzYPhZwekxISeT9vbqWZ2m"
ROOT = Path.cwd()
HASH_FILE = ROOT / "data" / "image-source-hashes.json"
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp")

def die(message):
    raise SystemExit("IMAGE SYNC BLOCKED: " + message)

def safe_path(value):
    if not isinstance(value, str):
        die("A photo path is not text")
    value = value.strip().replace("\\", "/")
    if not value or value.startswith("/") or ".." in Path(value).parts:
        die(f"Invalid photo path: {value!r}")
    if value.startswith(("https://", "http://")):
        return None
    if not value.startswith("images/") or not value.lower().endswith(IMAGE_SUFFIXES):
        die(f"Expected an images/... image filename: {value!r}")
    return value

def all_references(catalog):
    refs = set()
    products = catalog.get("products", [])
    if not products:
        die("Workbook contains no products")
    for product in products:
        if not product.get("active"):
            continue
        for path in product.get("images", []):
            if path and (p := safe_path(path)):
                refs.add(p)
    for collection in catalog.get("collections", []):
        if collection.get("active"):
            for path in collection.get("images", []):
                if path and (p := safe_path(path if path.startswith(("images/","http://","https://")) else "images/collections/" + path)):
                    refs.add(p)
    for character in catalog.get("characters", []):
        if character.get("active"):
            for path in character.get("images", []):
                if path and (p := safe_path(path if path.startswith(("images/","http://","https://")) else "images/characters/" + path)):
                    refs.add(p)
    for item in catalog.get("social", []):
        if item.get("active") and item.get("image_path"):
            path = item["image_path"]
            if path.startswith(("http://","https://")):
                continue
            if p := safe_path(path):
                refs.add(p)
    return sorted(refs)

def drive_listing():
    # gdown 6.3's --json recursively enumerates public Drive folders, including
    # future product folders and newly named photos. No fixed Drive file IDs.
    cmd = ["gdown", f"https://drive.google.com/drive/folders/{DRIVE_IMAGES_FOLDER}", "--json", "--quiet"]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if p.returncode:
        die("Could not list your Drive images folder: " + p.stderr[-1200:])
    try:
        records = json.loads(p.stdout)
    except ValueError:
        die("Drive folder listing returned invalid JSON")
    mapping = {}
    for entry in records:
        full = str(entry.get("path", "")).replace("\\", "/").strip("/")
        url = entry.get("url")
        if not isinstance(url, str) or not url.startswith("https://drive.google.com/"):
            continue
        parts = full.split("/")
        # The listing may include the Drive root folder name "images" or not.
        if "images" in parts:
            parts = parts[parts.index("images")+1:]
        elif "products" in parts:
            parts = parts[parts.index("products"):]
        elif parts and parts[0] in ("shared", "header", "cursor", "collections", "characters", "new-arrivals", "coming-soon", "social"):
            pass
        else:
            continue
        if len(parts) < 2:
            continue
        path = "images/" + "/".join(parts)
        if path in mapping and mapping[path] != url:
            die("Duplicate Drive filenames for " + path)
        mapping[path] = url
    if len(mapping) < 20:
        die(f"Drive scan found only {len(mapping)} image files; refusing to publish")
    return mapping

def sha256(path):
    dig = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024*1024), b""):
            dig.update(block)
    return dig.hexdigest()

def image_card_target(name):
    return (ROOT / "images" / "cards" / Path(name).relative_to("images/products")).with_suffix(".webp")

def optimize(src, target, card):
    with Image.open(src) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    image.thumbnail((1600,1600), Image.Resampling.LANCZOS)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Preserve the approved optimized gallery specification.
    if target.suffix.lower() in (".jpg",".jpeg"):
        image.save(target, "JPEG", quality=79, optimize=True, progressive=True, subsampling=0)
    elif target.suffix.lower() == ".png":
        image.save(target, "PNG", optimize=True)
    else:
        image.save(target, "WEBP", quality=79, method=5)
    if card is None:
        return
    w,h = 900,788
    blur = ImageOps.fit(image,(w,h),Image.Resampling.LANCZOS,centering=(0.5,0.5))
    blur = blur.filter(ImageFilter.GaussianBlur(radius=25))
    foreground = image.copy()
    foreground.thumbnail((w,h),Image.Resampling.LANCZOS)
    blur.paste(foreground,((w-foreground.width)//2,(h-foreground.height)//2))
    card.parent.mkdir(parents=True,exist_ok=True)
    blur.save(card,"WEBP",quality=78,method=5)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog",default="/tmp/stinkos-output/catalog.json")
    parser.add_argument("--scan-only",action="store_true")
    args = parser.parse_args()
    catalog = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
    expected = all_references(catalog)
    sources = drive_listing()
    print(f"Drive scan: {len(sources)} photographs, {len(expected)} catalog-referenced paths",flush=True)
    missing = [p for p in expected if p not in sources and not (ROOT / p).is_file()]
    if missing:
        die("Referenced images are missing from Drive and GitHub:\n" + "\n".join(missing[:40]))
    if args.scan_only:
        print("SCAN OK. No files modified.",flush=True)
        return
    old = json.loads(HASH_FILE.read_text(encoding="utf-8")) if HASH_FILE.is_file() else {}
    updated = dict(old)
    changes = 0
    with tempfile.TemporaryDirectory(prefix="stinkos-images-") as tmp:
        temp = Path(tmp)
        for i,path in enumerate(expected,1):
            # Absent in Drive but present on GitHub: keep established assets.
            if path not in sources:
                print(f"[{i}/{len(expected)}] Existing GitHub asset: {path}",flush=True)
                continue
            local = temp / ("source" + Path(path).suffix)
            for attempt in range(1,4):
                try:
                    gdown.download(url=sources[path], output=str(local), quiet=True, retries=2)
                    with Image.open(local) as check:
                        check.verify()
                    break
                except Exception as exc:
                    local.unlink(missing_ok=True)
                    if attempt == 3:
                        die(f"Download failed after three attempts: {path}: {exc}")
            digest = sha256(local)
            dest = ROOT / path
            card = image_card_target(path) if path.startswith("images/products/") else None
            if old.get(path) == digest and dest.is_file() and (card is None or card.is_file()):
                print(f"[{i}/{len(expected)}] Unchanged: {path}",flush=True)
                local.unlink(missing_ok=True)
                continue
            # Keep the complete image for non-product decorative areas.
            if card is None:
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes(local.read_bytes())
            else:
                optimize(local,dest,card)
            updated[path] = digest
            changes += 1
            print(f"[{i}/{len(expected)}] Optimized: {path}",flush=True)
            local.unlink(missing_ok=True)
    HASH_FILE.parent.mkdir(exist_ok=True)
    HASH_FILE.write_text(json.dumps(updated,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(f"IMAGE SYNC COMPLETE. {len(expected)} referenced photos valid; {changes} new/changed photos processed.",flush=True)

if __name__=="__main__":
    main()
