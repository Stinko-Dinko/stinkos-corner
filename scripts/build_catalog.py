#!/usr/bin/env python3
"""Build Stinko's Corner catalog data from the master spreadsheet.

Keep this script and Stinkos_Product_Catalog.xlsx in the admin folder.
Output: ../website/data/catalog.js and catalog.json.

The spreadsheet is the source of truth for categories, curated collections,
characters, storefront filters/sorts, products, variations, and product media.
The existing website templates must consume those fields; generating the data
alone does not install page controls or a checkout.
"""

from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"


def col_index(cell_ref: str) -> int:
    match = re.match(r"([A-Z]+)", cell_ref)
    if not match:
        return 0
    result = 0
    for letter in match.group(1):
        result = result * 26 + ord(letter) - 64
    return result - 1


def parse_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    return ["".join((t.text or "") for t in si.iter(f"{{{NS_MAIN}}}t"))
            for si in root.findall(f"{{{NS_MAIN}}}si")]


def workbook_sheet_paths(zf: zipfile.ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    relmap = {x.attrib["Id"]: x.attrib["Target"] for x in rels.findall(f"{{{NS_PKG_REL}}}Relationship")}
    found = {}
    for sh in workbook.find(f"{{{NS_MAIN}}}sheets"):
        target = relmap[sh.attrib[f"{{{NS_REL}}}id"]].lstrip("/")
        found[sh.attrib["name"]] = target if target.startswith("xl/") else "xl/" + target
    return found


def cell_value(cell: ET.Element, shared: list[str]):
    typ = cell.attrib.get("t")
    if typ == "inlineStr":
        data = cell.find(f"{{{NS_MAIN}}}is")
        return "" if data is None else "".join((t.text or "") for t in data.iter(f"{{{NS_MAIN}}}t"))
    raw = cell.find(f"{{{NS_MAIN}}}v")
    if raw is None or raw.text is None:
        return None
    if typ == "s":
        return shared[int(raw.text)]
    if typ == "b":
        return raw.text == "1"
    if typ in ("str", "e"):
        return raw.text
    try:
        value = float(raw.text)
        return int(value) if value.is_integer() else value
    except ValueError:
        return raw.text


def sheet_dicts(zf: zipfile.ZipFile, paths: dict[str, str], shared: list[str], name: str, header_row: int = 1) -> list[dict]:
    if name not in paths:
        return []
    root = ET.fromstring(zf.read(paths[name]))
    data = root.find(f"{{{NS_MAIN}}}sheetData")
    if data is None:
        return []
    rows = []
    for row in data.findall(f"{{{NS_MAIN}}}row"):
        values = {col_index(cell.attrib.get("r", "A1")): cell_value(cell, shared)
                  for cell in row.findall(f"{{{NS_MAIN}}}c")}
        rows.append(values)
    if not rows:
        return []
    if len(rows) < header_row:
        return []
    headers = {i: str(v).strip() for i, v in rows[header_row - 1].items() if v not in (None, "")}
    result = []
    for row in rows[header_row:]:
        item = {header: row.get(index) for index, header in headers.items()}
        if any(v not in (None, "") for v in item.values()):
            result.append(item)
    return result


def text(v) -> str:
    return "" if v is None else str(v).strip()


def yes(v) -> bool:
    return text(v).lower() in ("yes", "true", "y", "1")


def number(v):
    if v in (None, ""):
        return None
    try:
        n = float(v)
        return int(n) if n.is_integer() else n
    except (TypeError, ValueError):
        return None


def csv_items(v) -> list[str]:
    return [x.strip() for x in text(v).split(",") if x.strip()]


def image_columns(r: dict, max_count: int = 3) -> list[str]:
    return [text(r.get(f"image_{i}")) for i in range(1, max_count + 1) if text(r.get(f"image_{i}"))]


def unique_rows(rows: list[dict], id_key: str, name: str) -> dict[str, dict]:
    by_id = {}
    for row in rows:
        key = text(row.get(id_key))
        if not key:
            continue
        if key in by_id:
            raise SystemExit(f"Duplicate {name} ID: {key}")
        by_id[key] = row
    return by_id


def build_catalog(workbook_path: Path) -> dict:
    with zipfile.ZipFile(workbook_path) as zf:
        shared = parse_shared_strings(zf)
        paths = workbook_sheet_paths(zf)
        required = ("Products", "Categories", "Collections", "Characters", "Social",
                    "Shop Filters", "Shop Sort", "Vinyl Options", "Sticker Finishes", "Size Options", "Price Entry")
        missing = [name for name in required if name not in paths]
        if missing:
            raise SystemExit("Missing spreadsheet tabs: " + ", ".join(missing))
        read = lambda name: sheet_dicts(zf, paths, shared, name)
        product_rows, cat_rows, col_rows, char_rows = (read(n) for n in ("Products", "Categories", "Collections", "Characters"))
        social_rows = read("Social")
        filter_rows, sort_rows = read("Shop Filters"), read("Shop Sort")
        vinyl_rows, finish_rows, size_rows = (read(n) for n in ("Vinyl Options", "Sticker Finishes", "Size Options"))
        photo_rows, video_rows = read("Photo Assignments"), read("Video Assignments")
        price_entry_rows = sheet_dicts(zf, paths, shared, "Price Entry", header_row=3)

    cat_raw = unique_rows(cat_rows, "category_id", "category")
    categories = sorted([{
        "category_id": cid,
        "name": text(r.get("display_name")),
        "default_product_type": text(r.get("default_product_type")),
        "display_order": number(r.get("display_order")),
        "description": text(r.get("description")),
        "slug": cid,
        "active": yes(r.get("active")),
    } for cid, r in cat_raw.items()], key=lambda r: (r["display_order"] is None, r["display_order"] or 9999))
    category_by_id = {c["category_id"]: c for c in categories}

    col_raw = unique_rows(col_rows, "collection_id", "collection")
    collections = []
    positions = set()
    for cid, r in col_raw.items():
        position = number(r.get("homepage_position"))
        if position is not None:
            if position not in (1, 2, 3) or position in positions:
                raise SystemExit(f"Collection {cid}: homepage_position must be unique and 1, 2, or 3")
            positions.add(position)
        collections.append({
            "collection_id": cid, "name": text(r.get("name")),
            "description": text(r.get("description")), "images": image_columns(r, 2),
            "homepage_position": position, "button_text": text(r.get("button_text")),
            "slug": text(r.get("slug")) or cid, "active": yes(r.get("active")),
        })
    collections.sort(key=lambda r: (r["homepage_position"] is None, r["homepage_position"] or 9999, r["name"].lower()))

    char_raw = unique_rows(char_rows, "character_id", "character")
    characters = [{
        "character_id": cid, "name": text(r.get("name")),
        "description": text(r.get("description")), "images": image_columns(r, 2),
        "homepage_position": number(r.get("homepage_position")),
        "button_text": text(r.get("button_text")),
        "slug": text(r.get("slug")) or cid, "active": yes(r.get("active")),
    } for cid, r in char_raw.items()]
    characters.sort(key=lambda c: (c["homepage_position"] is None, c["homepage_position"] or 9999))

    sizes = [{
        "product_type": text(r.get("product_type")).lower(),
        "size_id": text(r.get("size_id")), "label": text(r.get("size_label")),
        "display_order": number(r.get("display_order")), "status": text(r.get("status")),
        "available": text(r.get("status")).lower() == "available",
    } for r in size_rows if text(r.get("product_type")) and text(r.get("size_id"))]
    sizes.sort(key=lambda s: (s["product_type"], s["display_order"] or 9999))
    vinyl = [{
        "vinyl_option_id": text(r.get("vinyl_option_id")), "color": text(r.get("color")),
        "finish": text(r.get("finish")), "pricing_tier": text(r.get("pricing_tier")),
        "status": text(r.get("status")), "available": text(r.get("status")).lower() == "available",
    } for r in vinyl_rows if text(r.get("vinyl_option_id"))]
    finishes = [{
        "finish_id": text(r.get("finish_id")), "name": text(r.get("finish_name")),
        "pricing_tier": text(r.get("pricing_tier")), "status": text(r.get("status")),
        "available": text(r.get("status")).lower() == "available",
    } for r in finish_rows if text(r.get("finish_id"))]
    # Price Entry is the only editable pricing source. Every tier/size pair is
    # exported separately, so a new finish uses its existing pricing tier.
    price_layout = {
        "decal": (("small", "Small"), ("medium", "Medium"), ("large", "Large"), ("xl", "XL")),
        "sticker": (("small", "Small"), ("medium", "Medium"), ("large", "Large")),
        "sticker sheet": (("one-size", "One size"),),
        "sticker multi-pack": (("one-size", "One size"),),
        "magnet": (("small-round", "Small (round)"), ("large-square", "Large (square)"), ("heart", "Heart")),
        "pin": (("small-round", "Small (round)"), ("large-square", "Large (square)"), ("heart", "Heart")),
    }
    # Price Entry is the ONLY source for standard prices. The retained legacy
    # Pricing Rules tab is ignored, preventing conflicting values.
    if not price_entry_rows:
        raise SystemExit("Price Entry has no pricing rows. Use the Price Entry tab.")
    pricing = []
    seen_prices = set()
    for r in price_entry_rows:
        kind, tier = text(r.get("product_type")).lower(), text(r.get("pricing_tier"))
        if not kind or not tier:
            continue
        if kind not in price_layout:
            raise SystemExit(f"Price Entry has unsupported product type: {kind}")
        for size_id, column in price_layout[kind]:
            key = (kind, tier, size_id)
            if key in seen_prices:
                raise SystemExit(f"Duplicate Price Entry rule: {key}")
            seen_prices.add(key)
            price = number(r.get(column))
            if price is not None and price < 0:
                raise SystemExit(f"Price Entry cannot have negative prices: {key}")
            pricing.append({"product_type": kind, "size_id": size_id,
                            "pricing_tier": tier, "price": price})

    product_raw = unique_rows(product_rows, "product_id", "product")
    products = []
    for pid, r in product_raw.items():
        category_id = text(r.get("category_id"))
        if category_id not in category_by_id:
            raise SystemExit(f"Product {pid} has invalid or missing category_id: {category_id!r}. Add it to Categories first.")
        collection_ids = csv_items(r.get("collection_id"))
        unknown = [cid for cid in collection_ids if cid not in col_raw]
        if unknown:
            raise SystemExit(f"Product {pid} has unknown collection IDs: {', '.join(unknown)}")
        char_id = text(r.get("character_id"))
        if char_id and char_id not in char_raw:
            raise SystemExit(f"Product {pid} has unknown character_id: {char_id}")
        kind = text(r.get("product_type")).lower()
        base_images = image_columns(r)
        products.append({
            "product_id": pid, "sku": text(r.get("sku")),
            "slug": text(r.get("slug")) or pid, "title": text(r.get("title")),
            "short_description": text(r.get("short_description")), "full_description": text(r.get("full_description")),
            "price": None, "price_override": number(r.get("price_override")),
            "compare_at_price": number(r.get("compare_at_price")),
            "status": text(r.get("status")), "product_type": kind,
            "category_id": category_id, "category_name": category_by_id[category_id]["name"],
            "collection_id": text(r.get("collection_id")), "collection_ids": collection_ids,
            "character_id": char_id, "tags": csv_items(r.get("tags")),
            "images": base_images, "videos": [], "media": [],
            "image_alt_text": text(r.get("image_alt_text")) or text(r.get("title")),
            "homepage_section": text(r.get("homepage_section")),
            "homepage_position": number(r.get("homepage_position")),
            "new_arrival": yes(r.get("new_arrival")),
            "inventory_status": text(r.get("inventory_status")),
            "inventory_quantity": number(r.get("inventory_quantity")),
            "active": yes(r.get("active")),
            "size_options": [size.copy() for size in sizes if size["product_type"] == kind],
            "finish_options": [f.copy() for f in finishes] if kind in {"sticker", "sticker sheet", "sticker multi-pack"} else [],
            "vinyl_options": [v.copy() for v in vinyl] if kind == "decal" else [],
        })

    product_by_id = {p["product_id"]: p for p in products}
    shared_media = []
    for r in photo_rows:
        pid = text(r.get("product_id"))
        path = text(r.get("website_image_path"))
        if not path:
            continue
        item = {
            "type": "image", "path": path,
            "role": text(r.get("role")), "color": text(r.get("color")),
            "finish": text(r.get("finish")), "size": text(r.get("size")),
            "photo_number": number(r.get("photo_number")),
        }
        if pid and pid in product_by_id:
            product_by_id[pid]["media"].append(item)
        elif pid:
            raise SystemExit(f"Photo {r.get('photo_number')} refers to unknown product {pid}")
        else:
            shared_media.append(item)
    for r in video_rows:
        pid = text(r.get("product_id"))
        path = text(r.get("website_video_path"))
        if not path:
            continue
        if pid not in product_by_id:
            raise SystemExit(f"Video {path} refers to unknown product {pid}")
        product_by_id[pid]["media"].append({"type":"video", "path": path, "role": text(r.get("role"))})

    for p in products:
        gallery = [m["path"] for m in p["media"] if m["type"] == "image"]
        if gallery:
            p["images"] = gallery
        p["videos"] = [m["path"] for m in p["media"] if m["type"] == "video"]
        # Price Entry is authoritative; a product-level override is optional.
        # Keep numeric starting prices for legacy homepage/shop cards. Never invent $0.
        override = p["price_override"]
        if override is not None and override < 0:
            raise SystemExit(f"Product {p['product_id']} has a negative price_override")
        kind = p["product_type"]
        sizes_for_sale = {s["size_id"] for s in p["size_options"] if s["available"]}
        option_tiers = (
            {v["pricing_tier"] for v in p["vinyl_options"] if v["available"]}
            if kind == "decal" else
            {f["pricing_tier"] for f in p["finish_options"] if f["available"]}
            if kind in {"sticker", "sticker sheet", "sticker multi-pack"} else
            {"Standard"}
        )
        viable_prices = sorted({r["price"] for r in pricing
                                if r["product_type"] == kind
                                and r["size_id"] in sizes_for_sale
                                and r["pricing_tier"] in option_tiers
                                and r["price"] is not None})
        p["price"] = override if override is not None else (viable_prices[0] if viable_prices else None)
        p["starting_price"] = p["price"]
        p["price_min"] = p["price"]
        p["price_max"] = override if override is not None else (viable_prices[-1] if viable_prices else None)
        p["has_price"] = p["price"] is not None
        # Unpriced active items can be browsed while checkout is not configured.
        # The storefront pricing controls remain disabled until a real price exists.

    for c in collections:
        c["product_ids"] = [p["product_id"] for p in products if c["collection_id"] in p["collection_ids"]]
        c["product_count"] = len(c["product_ids"])
    for c in categories:
        c["product_ids"] = [p["product_id"] for p in products if p["category_id"] == c["category_id"]]
        c["product_count"] = len(c["product_ids"])

    def filter_options(key: str):
        if key == "category":
            return [{"value": c["category_id"], "label": c["name"]} for c in categories if c["active"]]
        if key == "collection":
            return [{"value": c["collection_id"], "label": c["name"]} for c in collections if c["active"]]
        if key == "character":
            return [{"value": c["character_id"], "label": c["name"]} for c in characters if c["active"]]
        if key == "product_type":
            return [{"value": k, "label": k.title()} for k in sorted({p["product_type"] for p in products})]
        return []

    shop_filters = sorted([{
        "key": text(r.get("filter_key")), "label": text(r.get("display_name")),
        "field": text(r.get("product_field")), "order": number(r.get("display_order")),
        "options": filter_options(text(r.get("filter_key"))),
    } for r in filter_rows if yes(r.get("active")) and text(r.get("filter_key"))], key=lambda r: r["order"] or 9999)
    shop_sorts = sorted([{
        "value": text(r.get("sort_key")), "label": text(r.get("display_name")),
        "order": number(r.get("display_order")),
    } for r in sort_rows if yes(r.get("active")) and text(r.get("sort_key"))], key=lambda r: r["order"] or 9999)

    socials = []
    seen_positions = set()
    for r in social_rows:
        pos = number(r.get("position"))
        if pos is None:
            continue
        active = yes(r.get("active"))
        mode = text(r.get("content_type")) or "Post"
        if mode not in ("Post", "Product Feature", "Placeholder"):
            raise SystemExit(f"Social row {pos}: unknown content_type {mode!r}")
        uri = text(r.get("post_url"))
        image = text(r.get("image"))
        featured_id = text(r.get("featured_product_id"))
        featured = product_by_id.get(featured_id) if featured_id else None
        if active and pos in seen_positions:
            raise SystemExit(f"Social position {pos} must be unique")
        if active and mode == "Post" and (not uri.startswith(("https://", "http://")) or not image):
            raise SystemExit(f"Social post {pos} needs its post URL and thumbnail")
        if active and mode == "Product Feature" and not featured:
            raise SystemExit(f"Social product feature {pos} needs a valid featured_product_id")
        if featured_id and not featured:
            raise SystemExit(f"Social row {pos} has unknown featured_product_id: {featured_id}")
        if active:
            seen_positions.add(pos)
        resolved_image = image or (featured["images"][0] if featured and featured["images"] else "")
        if resolved_image and not resolved_image.startswith(("images/", "http://", "https://")):
            resolved_image = "images/social/" + resolved_image
        link_url = (uri if mode == "Post" else
                    "product.html?product=" + featured["slug"] if mode == "Product Feature" and featured else "")
        socials.append({
            "position": pos, "platform": text(r.get("platform")) if mode == "Post" else "",
            "post_url": uri if mode == "Post" else "",
            "content_type": mode, "featured_product_id": featured_id,
            "link_url": link_url,
            "image": image, "image_path": resolved_image,
            "alt_text": text(r.get("alt_text")) or (featured["title"] if featured else ""),
            "active": active,
        })
    socials.sort(key=lambda row: row["position"])

    return {
        "products": products, "categories": categories, "collections": collections,
        "characters": characters, "shop_filters": shop_filters, "shop_sorts": shop_sorts,
        "vinyl_options": vinyl, "sticker_finishes": finishes,
        "size_options": sizes, "pricing_rules": pricing,
        "new_arrivals": [p["product_id"] for p in products if p["new_arrival"] and p["active"]],
        "shared_media": shared_media, "social": socials,
    }


def main():
    here = Path(__file__).resolve().parent
    workbook = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else here / "Stinkos_Product_Catalog.xlsx"
    destination = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else here.parent / "website" / "data"
    if not workbook.exists():
        raise SystemExit("Workbook not found: " + str(workbook))
    catalog = build_catalog(workbook)
    destination.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(catalog, indent=2, ensure_ascii=False) + "\n"
    (destination / "catalog.json").write_text(payload, encoding="utf-8")
    (destination / "catalog.js").write_text(
        "// AUTO-GENERATED FROM Stinkos_Product_Catalog.xlsx. DO NOT EDIT BY HAND.\n"
        "window.STINKOS_CATALOG = " + payload.rstrip() + ";\n", encoding="utf-8")
    print(f"Updated: {destination / 'catalog.json'}")
    print(f"Updated: {destination / 'catalog.js'}")
    print(f"Products: {len(catalog['products'])}")
    print(f"Categories: {len(catalog['categories'])}")
    print(f"Collections: {len(catalog['collections'])}")
    print(f"Shop filters: {len(catalog['shop_filters'])}")
    print(f"Shop sorts: {len(catalog['shop_sorts'])}")
    print(f"Product gallery photos: {sum(len(p['images']) for p in catalog['products'])}")
    print(f"Product videos: {sum(len(p['videos']) for p in catalog['products'])}")
    print(f"Active products: {sum(p['active'] for p in catalog['products'])}")


if __name__ == "__main__":
    main()
