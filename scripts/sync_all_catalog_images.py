#!/usr/bin/env python3
"""Fill missing product images for catalog preview using the approved Drive files.
No design, product, or pricing changes. Keep original bytes and filenames intact.
"""
import json
import sys
from pathlib import Path
import gdown

def read_catalog():
    raw=Path("data/catalog.js").read_text(encoding="utf-8")
    return json.loads(raw[raw.index("{"):raw.rindex("}")+1])

catalog=read_catalog()
expected={path for product in catalog["products"] for path in product.get("images", [])}
assert len(catalog["products"])==37 and len(expected)==71, "Unexpected catalog. Refusing to guess."
manifest=[]
for i in range(1,8):
    manifest.extend(json.loads(Path(f"scripts/image-manifest-{i:02d}.json").read_text(encoding="utf-8")))
by_path={}
for item in manifest:
    path=item["path"]
    if path in by_path and by_path[path] != item["drive_id"]:
        raise SystemExit(f"Conflicting source IDs for {path}")
    by_path[path]=item["drive_id"]
missing=expected-set(by_path)
if missing:
    raise SystemExit("Drive source mapping is incomplete: "+repr(sorted(missing)))
print(f"Validated {len(expected)} catalog images against {len(by_path)} Drive paths.",flush=True)
failures=[]
downloaded=0
for i,path in enumerate(sorted(expected),1):
    dest=Path(path)
    if dest.is_file() and dest.stat().st_size>1000:
        continue
    if not path.startswith("images/products/") or ".." in dest.parts:
        raise SystemExit(f"Unsafe image path: {path}")
    dest.parent.mkdir(parents=True,exist_ok=True)
    try:
        result=gdown.download(id=by_path[path], output=str(dest), quiet=True, fuzzy=True)
        if not result or not dest.is_file() or dest.stat().st_size<1000:
            raise ValueError("Download missing or empty")
        magic=dest.read_bytes()[:12]
        if not (magic.startswith(bytes.fromhex("ffd8ff")) or magic.startswith(bytes.fromhex("89504e47")) or magic.startswith(b"RIFF")):
            raise ValueError("Downloaded file has invalid image signature")
        downloaded+=1
        print(f"[{i}/{len(expected)}] {path} ({dest.stat().st_size} bytes)", flush=True)
    except Exception as exc:
        dest.unlink(missing_ok=True)
        failures.append(f"{path}: {exc}")
if failures:
    print("\n".join(failures),file=sys.stderr)
    raise SystemExit(f"Failed to fetch {len(failures)} images")
print(f"All {len(expected)} catalog image paths verified. New downloads: {downloaded}.",flush=True)
