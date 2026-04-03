"""TMX/TSX XML parser and writer for Tiled Map Editor files.

Handles reading, writing, and converting between TMX (XML) and Tiled JSON
formats. This is the data layer foundation for all map operations.

TMX format reference: https://doc.mapeditor.org/en/stable/reference/tmx-map-format/
"""

import json
import os
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional


# ── TMX Reading ──────────────────────────────────────────────────────

def parse_tmx(path: str) -> Dict[str, Any]:
    """Parse a TMX file into a normalized dict (same shape as Tiled JSON).

    Args:
        path: Path to a .tmx file.

    Returns:
        Dict matching Tiled JSON export structure.

    Raises:
        FileNotFoundError: If path does not exist.
        ValueError: If file is not valid TMX.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"TMX file not found: {path}")

    tree = ET.parse(path)
    root = tree.getroot()

    if root.tag != "map":
        raise ValueError(f"Not a valid TMX file (root tag is '{root.tag}', expected 'map')")

    map_data = {
        "version": root.get("version", "1.10"),
        "tiledversion": root.get("tiledversion", "1.11.0"),
        "orientation": root.get("orientation", "orthogonal"),
        "renderorder": root.get("renderorder", "right-down"),
        "width": int(root.get("width", 10)),
        "height": int(root.get("height", 8)),
        "tilewidth": int(root.get("tilewidth", 32)),
        "tileheight": int(root.get("tileheight", 32)),
        "infinite": root.get("infinite", "0") == "1",
        "nextlayerid": int(root.get("nextlayerid", 1)),
        "nextobjectid": int(root.get("nextobjectid", 1)),
        "layers": [],
        "tilesets": [],
        "properties": {},
    }

    # Parse map-level properties
    props_el = root.find("properties")
    if props_el is not None:
        map_data["properties"] = _parse_properties(props_el)

    # Parse tilesets
    for ts_el in root.findall("tileset"):
        tileset = _parse_tileset_element(ts_el)
        map_data["tilesets"].append(tileset)

    # Parse layers
    for child in root:
        if child.tag == "layer":
            map_data["layers"].append(_parse_tile_layer(child))
        elif child.tag == "objectgroup":
            map_data["layers"].append(_parse_object_layer(child))
        elif child.tag == "imagelayer":
            map_data["layers"].append(_parse_image_layer(child))
        elif child.tag == "group":
            map_data["layers"].append(_parse_group_layer(child))

    return map_data


def _parse_tileset_element(el: ET.Element) -> Dict[str, Any]:
    """Parse a <tileset> element."""
    ts = {
        "firstgid": int(el.get("firstgid", 1)),
    }

    source = el.get("source")
    if source:
        # External tileset reference
        ts["source"] = source
    else:
        # Inline tileset
        ts["name"] = el.get("name", "")
        ts["tilewidth"] = int(el.get("tilewidth", 32))
        ts["tileheight"] = int(el.get("tileheight", 32))
        ts["tilecount"] = int(el.get("tilecount", 0))
        ts["columns"] = int(el.get("columns", 0))

        img = el.find("image")
        if img is not None:
            ts["image"] = img.get("source", "")
            ts["imagewidth"] = int(img.get("width", 0))
            ts["imageheight"] = int(img.get("height", 0))

    return ts


def _parse_tile_layer(el: ET.Element) -> Dict[str, Any]:
    """Parse a <layer> (tile layer) element."""
    layer = {
        "type": "tilelayer",
        "id": int(el.get("id", 0)),
        "name": el.get("name", ""),
        "width": int(el.get("width", 0)),
        "height": int(el.get("height", 0)),
        "visible": el.get("visible", "1") != "0",
        "opacity": float(el.get("opacity", 1.0)),
        "x": int(el.get("x", 0)),
        "y": int(el.get("y", 0)),
    }

    # Parse properties
    props_el = el.find("properties")
    if props_el is not None:
        layer["properties"] = _parse_properties(props_el)

    # Parse tile data
    data_el = el.find("data")
    if data_el is not None:
        encoding = data_el.get("encoding", "csv")
        if encoding == "csv":
            text = data_el.text.strip() if data_el.text else ""
            layer["data"] = [int(x.strip()) for x in text.split(",") if x.strip()]
        else:
            # base64 encoding not yet supported; store raw
            layer["data"] = []
            layer["encoding"] = encoding
    else:
        layer["data"] = []

    return layer


def _parse_object_layer(el: ET.Element) -> Dict[str, Any]:
    """Parse an <objectgroup> element."""
    layer = {
        "type": "objectgroup",
        "id": int(el.get("id", 0)),
        "name": el.get("name", ""),
        "visible": el.get("visible", "1") != "0",
        "opacity": float(el.get("opacity", 1.0)),
        "x": int(el.get("x", 0)),
        "y": int(el.get("y", 0)),
        "objects": [],
    }

    props_el = el.find("properties")
    if props_el is not None:
        layer["properties"] = _parse_properties(props_el)

    for obj_el in el.findall("object"):
        obj = {
            "id": int(obj_el.get("id", 0)),
            "name": obj_el.get("name", ""),
            "type": obj_el.get("type", obj_el.get("class", "")),
            "x": float(obj_el.get("x", 0)),
            "y": float(obj_el.get("y", 0)),
            "width": float(obj_el.get("width", 0)),
            "height": float(obj_el.get("height", 0)),
            "visible": obj_el.get("visible", "1") != "0",
            "rotation": float(obj_el.get("rotation", 0)),
        }

        # Parse object properties
        obj_props = obj_el.find("properties")
        if obj_props is not None:
            obj["properties"] = _parse_properties(obj_props)

        # Check for point/ellipse/polygon
        if obj_el.find("point") is not None:
            obj["point"] = True
        if obj_el.find("ellipse") is not None:
            obj["ellipse"] = True

        layer["objects"].append(obj)

    return layer


def _parse_image_layer(el: ET.Element) -> Dict[str, Any]:
    """Parse an <imagelayer> element."""
    layer = {
        "type": "imagelayer",
        "id": int(el.get("id", 0)),
        "name": el.get("name", ""),
        "visible": el.get("visible", "1") != "0",
        "opacity": float(el.get("opacity", 1.0)),
        "x": int(el.get("x", 0)),
        "y": int(el.get("y", 0)),
    }

    img = el.find("image")
    if img is not None:
        layer["image"] = img.get("source", "")

    return layer


def _parse_group_layer(el: ET.Element) -> Dict[str, Any]:
    """Parse a <group> element (layer group)."""
    layer = {
        "type": "group",
        "id": int(el.get("id", 0)),
        "name": el.get("name", ""),
        "visible": el.get("visible", "1") != "0",
        "opacity": float(el.get("opacity", 1.0)),
        "layers": [],
    }

    for child in el:
        if child.tag == "layer":
            layer["layers"].append(_parse_tile_layer(child))
        elif child.tag == "objectgroup":
            layer["layers"].append(_parse_object_layer(child))

    return layer


def _parse_properties(el: ET.Element) -> Dict[str, Any]:
    """Parse a <properties> element into a dict."""
    props = {}
    for prop in el.findall("property"):
        name = prop.get("name", "")
        ptype = prop.get("type", "string")
        value = prop.get("value", prop.text or "")

        if ptype == "int":
            props[name] = int(value)
        elif ptype == "float":
            props[name] = float(value)
        elif ptype == "bool":
            props[name] = value.lower() in ("true", "1")
        else:
            props[name] = value

    return props


# ── TMX Writing ──────────────────────────────────────────────────────

def write_tmx(map_data: Dict[str, Any], path: str) -> str:
    """Write a map dict to a TMX file.

    Args:
        map_data: Map dict (Tiled JSON structure).
        path: Output .tmx file path.

    Returns:
        Absolute path to written file.
    """
    root = ET.Element("map")
    root.set("version", str(map_data.get("version", "1.10")))
    root.set("tiledversion", str(map_data.get("tiledversion", "1.11.0")))
    root.set("orientation", map_data.get("orientation", "orthogonal"))
    root.set("renderorder", map_data.get("renderorder", "right-down"))
    root.set("width", str(map_data.get("width", 10)))
    root.set("height", str(map_data.get("height", 8)))
    root.set("tilewidth", str(map_data.get("tilewidth", 32)))
    root.set("tileheight", str(map_data.get("tileheight", 32)))
    root.set("infinite", "1" if map_data.get("infinite", False) else "0")
    root.set("nextlayerid", str(map_data.get("nextlayerid", 1)))
    root.set("nextobjectid", str(map_data.get("nextobjectid", 1)))

    # Map properties
    if map_data.get("properties"):
        _write_properties(root, map_data["properties"])

    # Tilesets
    for ts in map_data.get("tilesets", []):
        _write_tileset_element(root, ts)

    # Layers
    for layer in map_data.get("layers", []):
        ltype = layer.get("type", "tilelayer")
        if ltype == "tilelayer":
            _write_tile_layer(root, layer)
        elif ltype == "objectgroup":
            _write_object_layer(root, layer)
        elif ltype == "imagelayer":
            _write_image_layer(root, layer)
        elif ltype == "group":
            _write_group_layer(root, layer)

    tree = ET.ElementTree(root)
    ET.indent(tree, space=" ")

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tree.write(path, encoding="UTF-8", xml_declaration=True)

    return os.path.abspath(path)


def _write_tileset_element(parent: ET.Element, ts: Dict[str, Any]):
    """Write a <tileset> element."""
    el = ET.SubElement(parent, "tileset")
    el.set("firstgid", str(ts.get("firstgid", 1)))

    if "source" in ts:
        el.set("source", ts["source"])
    else:
        if "name" in ts:
            el.set("name", ts["name"])
        if "tilewidth" in ts:
            el.set("tilewidth", str(ts["tilewidth"]))
        if "tileheight" in ts:
            el.set("tileheight", str(ts["tileheight"]))
        if "tilecount" in ts:
            el.set("tilecount", str(ts["tilecount"]))
        if "columns" in ts:
            el.set("columns", str(ts["columns"]))

        if "image" in ts:
            img = ET.SubElement(el, "image")
            img.set("source", ts["image"])
            if "imagewidth" in ts:
                img.set("width", str(ts["imagewidth"]))
            if "imageheight" in ts:
                img.set("height", str(ts["imageheight"]))


def _write_tile_layer(parent: ET.Element, layer: Dict[str, Any]):
    """Write a <layer> element."""
    el = ET.SubElement(parent, "layer")
    el.set("id", str(layer.get("id", 0)))
    el.set("name", layer.get("name", ""))
    el.set("width", str(layer.get("width", 0)))
    el.set("height", str(layer.get("height", 0)))

    if not layer.get("visible", True):
        el.set("visible", "0")
    if layer.get("opacity", 1.0) != 1.0:
        el.set("opacity", str(layer["opacity"]))

    if layer.get("properties"):
        _write_properties(el, layer["properties"])

    data = layer.get("data", [])
    if data:
        data_el = ET.SubElement(el, "data")
        data_el.set("encoding", "csv")
        # Format CSV data with line breaks per row
        w = layer.get("width", 0)
        rows = []
        for y in range(0, len(data), w) if w > 0 else []:
            row = data[y:y + w]
            rows.append(",".join(str(v) for v in row))
        data_el.text = "\n" + ",\n".join(rows) + "\n"


def _write_object_layer(parent: ET.Element, layer: Dict[str, Any]):
    """Write an <objectgroup> element."""
    el = ET.SubElement(parent, "objectgroup")
    el.set("id", str(layer.get("id", 0)))
    el.set("name", layer.get("name", ""))

    if not layer.get("visible", True):
        el.set("visible", "0")

    if layer.get("properties"):
        _write_properties(el, layer["properties"])

    for obj in layer.get("objects", []):
        obj_el = ET.SubElement(el, "object")
        obj_el.set("id", str(obj.get("id", 0)))
        if obj.get("name"):
            obj_el.set("name", obj["name"])
        if obj.get("type"):
            obj_el.set("type", obj["type"])
        obj_el.set("x", str(obj.get("x", 0)))
        obj_el.set("y", str(obj.get("y", 0)))
        if obj.get("width", 0) > 0:
            obj_el.set("width", str(obj["width"]))
        if obj.get("height", 0) > 0:
            obj_el.set("height", str(obj["height"]))
        if obj.get("rotation", 0) != 0:
            obj_el.set("rotation", str(obj["rotation"]))
        if not obj.get("visible", True):
            obj_el.set("visible", "0")

        if obj.get("properties"):
            _write_properties(obj_el, obj["properties"])

        if obj.get("point"):
            ET.SubElement(obj_el, "point")
        if obj.get("ellipse"):
            ET.SubElement(obj_el, "ellipse")


def _write_image_layer(parent: ET.Element, layer: Dict[str, Any]):
    """Write an <imagelayer> element."""
    el = ET.SubElement(parent, "imagelayer")
    el.set("id", str(layer.get("id", 0)))
    el.set("name", layer.get("name", ""))
    if "image" in layer:
        img = ET.SubElement(el, "image")
        img.set("source", layer["image"])


def _write_group_layer(parent: ET.Element, layer: Dict[str, Any]):
    """Write a <group> element."""
    el = ET.SubElement(parent, "group")
    el.set("id", str(layer.get("id", 0)))
    el.set("name", layer.get("name", ""))
    for child in layer.get("layers", []):
        ctype = child.get("type", "tilelayer")
        if ctype == "tilelayer":
            _write_tile_layer(el, child)
        elif ctype == "objectgroup":
            _write_object_layer(el, child)


def _write_properties(parent: ET.Element, props: Dict[str, Any]):
    """Write a <properties> element."""
    if not props:
        return
    props_el = ET.SubElement(parent, "properties")
    for name, value in props.items():
        prop_el = ET.SubElement(props_el, "property")
        prop_el.set("name", name)
        if isinstance(value, bool):
            prop_el.set("type", "bool")
            prop_el.set("value", "true" if value else "false")
        elif isinstance(value, int):
            prop_el.set("type", "int")
            prop_el.set("value", str(value))
        elif isinstance(value, float):
            prop_el.set("type", "float")
            prop_el.set("value", str(value))
        else:
            prop_el.set("value", str(value))


# ── JSON I/O ─────────────────────────────────────────────────────────

def read_tiled_json(path: str) -> Dict[str, Any]:
    """Read a Tiled JSON file.

    Args:
        path: Path to .json file.

    Returns:
        Map dict.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Normalize: ensure required keys exist
    data.setdefault("layers", [])
    data.setdefault("tilesets", [])
    data.setdefault("properties", {})
    data.setdefault("orientation", "orthogonal")
    data.setdefault("renderorder", "right-down")
    data.setdefault("tilewidth", 32)
    data.setdefault("tileheight", 32)

    return data


def write_tiled_json(map_data: Dict[str, Any], path: str) -> str:
    """Write a map dict to a Tiled JSON file.

    Args:
        map_data: Map dict.
        path: Output .json file path.

    Returns:
        Absolute path to written file.
    """
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(map_data, f, indent=2, default=str)

    return os.path.abspath(path)


# ── Auto-detect format ───────────────────────────────────────────────

def load_map(path: str) -> Dict[str, Any]:
    """Load a map from either TMX or JSON format (auto-detected).

    Args:
        path: Path to .tmx or .json file.

    Returns:
        Normalized map dict.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".tmx":
        return parse_tmx(path)
    elif ext == ".json":
        return read_tiled_json(path)
    else:
        # Try JSON first, then TMX
        try:
            return read_tiled_json(path)
        except (json.JSONDecodeError, KeyError):
            return parse_tmx(path)


def save_map(map_data: Dict[str, Any], path: str) -> str:
    """Save a map to either TMX or JSON format (auto-detected by extension).

    Args:
        map_data: Map dict.
        path: Output file path (.tmx or .json).

    Returns:
        Absolute path to written file.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".tmx":
        return write_tmx(map_data, path)
    else:
        return write_tiled_json(map_data, path)


# ── TSX Reading ──────────────────────────────────────────────────────

def parse_tsx(path: str) -> Dict[str, Any]:
    """Parse a TSX (external tileset) file.

    Args:
        path: Path to .tsx file.

    Returns:
        Tileset dict.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"TSX file not found: {path}")

    tree = ET.parse(path)
    root = tree.getroot()

    if root.tag != "tileset":
        raise ValueError(f"Not a valid TSX file (root tag is '{root.tag}', expected 'tileset')")

    ts = {
        "name": root.get("name", ""),
        "tilewidth": int(root.get("tilewidth", 32)),
        "tileheight": int(root.get("tileheight", 32)),
        "tilecount": int(root.get("tilecount", 0)),
        "columns": int(root.get("columns", 0)),
    }

    img = root.find("image")
    if img is not None:
        ts["image"] = img.get("source", "")
        ts["imagewidth"] = int(img.get("width", 0))
        ts["imageheight"] = int(img.get("height", 0))

    return ts
