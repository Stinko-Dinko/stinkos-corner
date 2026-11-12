#!/usr/bin/env python3
"""Copy the already-approved first product photo for each catalog item into the preview branch.
No HTML, design, pricing, or catalog edits. Source image bytes remain unchanged.
"""
import json
import os
from pathlib import Path
import sys
import gdown

PHOTO_IDS = {
  "eggplant-decal":"1V1Z56hLXzvfUNF2Ig-BAGws1WibG5Iox",
  "fuck-you-knewave-decal":"1w5BPoYYatbQagT0zaNN7JJ8D1IfCaxMb",
  "censored-eat-shit-long-decal":"1AFa8talVrhKnGXwlQUhmTok15Hi8GDel",
  "love-tucson-decal":"1zbjA6YKKF_JlpI8bRy2DaxnFcQPRoPvg",
  "cunt-decal":"1lPRF9YPCbyKoWS18l3rDDPdbORqai6E8",
  "cat-heart-poop-decal":"1u61EFQQe6hBjFCpjFpE1o4oCp8FHW1yS",
  "dog-heart-poop-decal":"1AfwH5_OzbWnJr86X3DknjxsxRQRha5pj",
  "bird-poop-trail-decal":"1HbB8io6kyzY5q5Gx15kP1RbXa5DEY6uZ",
  "cat-poop-trail-decal":"12C76tmnA2QF_L15BMDdlEBHQfJZ2zYhN",
  "my-cat-thinks-you-suck-decal":"1dr8qiFvLUHwrQHjwQZAOEjFXHfdXSOep",
  "eat-shit-stacked-decal":"1F88acGQe_-uyUxguPQI9g-JyU79SVrR5",
  "emoji-eat-shit-decal":"1Bz9uKNJO1p0NrYJeHevzF71EhccBqfEr",
  "bitch-script-decal":"1IT8QRXAt0eLoBaW8hxpKpqzgS4tSIxvd",
  "emoji-peach-decal":"1vyllKU0T-lFMy108xsgwoIA-VW-GLqDd",
  "fuck-off-decal":"16_NtwuTXoFBlWf2YUqNXBgmgnP1EkxlY",
  "poopin-guy-decal":"1TEceBSXOdIesbbR19ThL_RZjB3yh0lv-",
  "asshole-cat-decal":"19sYUHfasT3NhOtjEAjQBbXlM4kKebj4z",
  "my-dog-thinks-you-suck-decal":"1frjt8i_6yuwFrqvYtfB68JoCmPqOYzAZ",
  "my-bird-thinks-you-suck-decal":"1jNw6-Xrc_rSceUzPSj-G1irgtuxDaWsE",
  "fuck-off-street-sign-decal":"16L1ZiEi6dCateXdgkT96zzlDWma4Khnl",
  "magical-as-fuck-sticker-sheet":"16EJ-fE2Xuh1k9c16xj9E01FqiXc3Ipu5",
  "hotdog-slut-sticker":"1N1TT26AoOe8AtTyC_1aZOKXRDjgL8J7R",
  "creampie-whore-sticker":"1V10CZs6-DFn4g-CnXc6OXQ8xOZW6tgtG",
  "fuck-you-so-much-heart-sticker":"1bZWXkDJGsZ_ROb1xOfgSA4IzcZpfQQWV",
  "go-fuck-yourself-retro-sticker":"1nra890mIyh-MVCFmyDuu7RStAm-k-E4p",
  "cunt-multicolor-lettering-sticker":"1tOyWMj2dAvH9zbE_fM795iO5zLjVjypz",
  "magical-as-fuck-unicorn-sticker":"1eHk6yVtIRtQM0lL91UmhShPZzY8ckfS7",
  "zombie-attack-sticker-sheet":"12vyBw7c7DrQs2o4cU-T8NdLUE838uy_E",
  "sex-drugs-rock-n-roll-sticker-sheet":"1eCg-fIdGaaTdDA2HkERGPGMyQfLOEOUM",
  "emoji-tongue-magnet":"1OG7iLWOFCQABDqtBSUdkATTVl0SfQ7jU",
  "fuck-off-rainbow-magnet":"10xPFIH2-PfLKN2et8Wnrgv5i3ntj4uNL",
  "poop-emoji-magnet":"15pARuN6IaxEBVdwSQZmP3N_0crBZ9hLA",
  "eat-emoji-magnet":"1O85L512s5e2tkBOQcqvZfduaY30MUPgr",
  "go-fuck-yourself-retro-magnet":"1tawdhsG0ltXPXbfHkTnGvBRmnZQlbtbR",
  "eggplant-emoji-magnet":"1ilqRGiAFHqK_JZNaaSXvKj_BkkGUrfFJ",
  "fuck-you-so-much-heart-magnet":"1Mz2pqi5swWfQqUhJe9OfGYttQXDpn-5j",
  "emoji-peach-magnet":"1pdnW_x7btliK_nfTkjbEQQTwPT_Mf0SH"
}

raw = Path("data/catalog.js").read_text(encoding="utf-8")
catalog = json.loads(raw[raw.index("{"):raw.rindex("}")+1])
products = catalog["products"]
if len(products) != 37 or set(PHOTO_IDS) != {p["product_id"] for p in products}:
    raise SystemExit("Product IDs differ from the inspected catalog; refusing to guess")
errors = []
for index, product in enumerate(products, 1):
    product_id = product["product_id"]
    target = Path(product["images"][0])
    if not str(target).startswith("images/products/") or ".." in target.parts:
        raise SystemExit("Unsafe product image path")
    if target.is_file() and target.stat().st_size > 1000:
        print(f"{index}/37 already present: {target}", flush=True)
        continue
    target.parent.mkdir(parents=True,exist_ok=True)
    try:
        result = gdown.download(id=PHOTO_IDS[product_id], output=str(target), quiet=True, fuzzy=True)
        if not result or not target.is_file() or target.stat().st_size < 1000:
            raise RuntimeError("Google Drive returned no image")
        with target.open("rb") as file:
            magic=file.read(12)
        if not (magic.startswith(b"\\xff\\xd8\\xff") or magic.startswith(b"\\x89PNG") or magic.startswith(b"RIFF")):
            raise RuntimeError("Downloaded file does not look like an image")
        print(f"{index}/37 downloaded: {target} ({target.stat().st_size} bytes)", flush=True)
    except Exception as exc:
        target.unlink(missing_ok=True)
        errors.append(f"{product_id}: {exc}")
if errors:
    print("\n".join(errors),file=sys.stderr)
    raise SystemExit(f"Could not download {len(errors)} product photos")
print("All 37 catalog card images are now present at their approved paths.")
