"""Tiled CLI - Map CRUD operations.

Handles creating new maps, opening existing maps, querying map info,
resizing, and saving to TMX/JSON formats.
"""

import os
from datetime import datetime
from typing import Any, Dict, Optional

from cli_anything.tiled.utils.tmx_parser import (
    load_map,
    save_map,
    write_tiled_json,
    write_tmx,
)


# ── Map Templates ────────────────────────────────────────────────────

MAP_TEMPLATES = {
    "room-small": {"width": 8, "height": 6, "desc": "Small room (8x6)"},
    "room-medium": {"width": 10, "height": 8, "desc": "Medium room (10x8)"},
    "room-large": {"width": 14, "height": 10, "desc": "Large room (14x10)"},
    "shop": {"width": 10, "height": 8, "desc": "Shop interior (10x8)"},
    "house": {"width": 12, "height": 10, "desc": "House interior (12x10)"},
    "dungeon": {"width": 16, "height": 12, "desc": "Dungeon room (16x12)"},
    "outdoor": {"width": 20, "height": 15, "desc": "Outdoor area (20x15)"},
}


def create_map(
    width: int = 10,
    height: int = 8,
    tile_width: int = 32,
    tile_height: int = 32,
    name: str = "untitled",
    orientation: str = "orthogonal",
    template: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new empty map.

    Args:
        width: Map width in tiles.
        height: Map height in tiles.
        tile_width: Width of each tile in pixels.
        tile_height: Height of each tile in pixels.
        name: Map name.
        orientation: Map orientation (orthogonal, isometric, hexagonal).
        template: Optional template name for predefined sizes.

    Returns:
        New map dict.
    """
    if template and template in MAP_TEMPLATES:
        t = MAP_TEMPLATES[template]
        width = t["width"]
        height = t["height"]
    elif template:
        raise ValueError(
            f"Unknown template: {template}. "
            f"Available: {list(MAP_TEMPLATES.keys())}"
        )

    if width < 1 or height < 1:
        raise ValueError(f"Map dimensions must be positive: {width}x{height}")
    if tile_width < 1 or tile_height < 1:
        raise ValueError(f"Tile dimensions must be positive: {tile_width}x{tile_height}")

    # Create empty tile data (all zeros = empty)
    empty_data = [0] * (width * height)

    map_data = {
        "version": "1.10",
        "tiledversion": "1.11.0",
        "orientation": orientation,
        "renderorder": "right-down",
        "width": width,
        "height": height,
        "tilewidth": tile_width,
        "tileheight": tile_height,
        "infinite": False,
        "nextlayerid": 3,
        "nextobjectid": 1,
        "properties": {
            "name": name,
            "created": datetime.now().isoformat(),
            "generator": "cli-anything-tiled",
        },
        "tilesets": [],
        "layers": [
            {
                "type": "tilelayer",
                "id": 1,
                "name": "Ground",
                "width": width,
                "height": height,
                "visible": True,
                "opacity": 1.0,
                "x": 0,
                "y": 0,
                "data": list(empty_data),
            },
            {
                "type": "objectgroup",
                "id": 2,
                "name": "Objects",
                "visible": True,
                "opacity": 1.0,
                "x": 0,
                "y": 0,
                "objects": [],
            },
        ],
    }

    return map_data


def open_map(path: str) -> Dict[str, Any]:
    """Open an existing map file (TMX or JSON).

    Args:
        path: Path to map file.

    Returns:
        Map dict.
    """
    return load_map(path)


def save_map_to(map_data: Dict[str, Any], path: str, overwrite: bool = False) -> Dict[str, Any]:
    """Save a map to a file.

    Args:
        map_data: Map dict.
        path: Output file path.
        overwrite: Whether to overwrite existing files.

    Returns:
        Result dict with output path and format info.
    """
    if os.path.exists(path) and not overwrite:
        raise FileExistsError(f"File exists: {path}. Use --overwrite.")

    abs_path = save_map(map_data, path)
    file_size = os.path.getsize(abs_path)
    ext = os.path.splitext(path)[1].lower()

    return {
        "output": abs_path,
        "format": "tmx" if ext == ".tmx" else "json",
        "file_size": file_size,
    }


def get_map_info(map_data: Dict[str, Any]) -> Dict[str, Any]:
    """Get map information summary.

    Args:
        map_data: Map dict.

    Returns:
        Info dict.
    """
    layers = map_data.get("layers", [])
    tile_layers = [l for l in layers if l.get("type") == "tilelayer"]
    object_layers = [l for l in layers if l.get("type") == "objectgroup"]

    total_objects = sum(
        len(l.get("objects", [])) for l in object_layers
    )

    tilesets = map_data.get("tilesets", [])

    return {
        "name": map_data.get("properties", {}).get("name", "untitled"),
        "width": map_data.get("width", 0),
        "height": map_data.get("height", 0),
        "tile_width": map_data.get("tilewidth", 32),
        "tile_height": map_data.get("tileheight", 32),
        "orientation": map_data.get("orientation", "orthogonal"),
        "pixel_width": map_data.get("width", 0) * map_data.get("tilewidth", 32),
        "pixel_height": map_data.get("height", 0) * map_data.get("tileheight", 32),
        "tile_layers": len(tile_layers),
        "object_layers": len(object_layers),
        "total_layers": len(layers),
        "total_objects": total_objects,
        "tilesets": len(tilesets),
        "tileset_names": [
            ts.get("name", ts.get("source", "unknown")) for ts in tilesets
        ],
        "properties": map_data.get("properties", {}),
    }


def resize_map(
    map_data: Dict[str, Any],
    new_width: int,
    new_height: int,
    anchor: str = "top-left",
) -> Dict[str, Any]:
    """Resize the map, adjusting all tile layer data.

    Args:
        map_data: Map dict.
        new_width: New width in tiles.
        new_height: New height in tiles.
        anchor: Where to anchor existing content.

    Returns:
        Result dict.
    """
    if new_width < 1 or new_height < 1:
        raise ValueError(f"Dimensions must be positive: {new_width}x{new_height}")

    old_w = map_data["width"]
    old_h = map_data["height"]

    # Calculate offsets based on anchor
    offsets = _calc_anchor_offsets(old_w, old_h, new_width, new_height, anchor)
    ox, oy = offsets

    # Resize each tile layer
    for layer in map_data.get("layers", []):
        if layer.get("type") == "tilelayer":
            old_data = layer.get("data", [])
            new_data = [0] * (new_width * new_height)

            for y in range(old_h):
                for x in range(old_w):
                    nx = x + ox
                    ny = y + oy
                    if 0 <= nx < new_width and 0 <= ny < new_height:
                        old_idx = y * old_w + x
                        new_idx = ny * new_width + nx
                        if old_idx < len(old_data):
                            new_data[new_idx] = old_data[old_idx]

            layer["data"] = new_data
            layer["width"] = new_width
            layer["height"] = new_height

        elif layer.get("type") == "objectgroup":
            # Offset objects
            tile_w = map_data.get("tilewidth", 32)
            tile_h = map_data.get("tileheight", 32)
            for obj in layer.get("objects", []):
                obj["x"] = obj.get("x", 0) + ox * tile_w
                obj["y"] = obj.get("y", 0) + oy * tile_h

    map_data["width"] = new_width
    map_data["height"] = new_height

    return {
        "old_size": f"{old_w}x{old_h}",
        "new_size": f"{new_width}x{new_height}",
        "anchor": anchor,
        "offset": {"x": ox, "y": oy},
    }


def _calc_anchor_offsets(
    old_w: int, old_h: int, new_w: int, new_h: int, anchor: str
) -> tuple:
    """Calculate x/y offsets for content when resizing.

    Returns:
        (offset_x, offset_y) tuple.
    """
    anchors = {
        "top-left": (0, 0),
        "top": ((new_w - old_w) // 2, 0),
        "top-right": (new_w - old_w, 0),
        "left": (0, (new_h - old_h) // 2),
        "center": ((new_w - old_w) // 2, (new_h - old_h) // 2),
        "right": (new_w - old_w, (new_h - old_h) // 2),
        "bottom-left": (0, new_h - old_h),
        "bottom": ((new_w - old_w) // 2, new_h - old_h),
        "bottom-right": (new_w - old_w, new_h - old_h),
    }

    if anchor not in anchors:
        raise ValueError(
            f"Unknown anchor: {anchor}. "
            f"Available: {list(anchors.keys())}"
        )

    return anchors[anchor]


def list_templates() -> list:
    """List available map templates.

    Returns:
        List of template info dicts.
    """
    return [
        {"name": name, **info}
        for name, info in MAP_TEMPLATES.items()
    ]
