"""Tiled CLI - Individual tile operations.

Handles querying and setting individual tiles, checking collision data,
and providing tile-level introspection.
"""

from typing import Any, Dict, List, Optional


def get_tile(
    map_data: Dict[str, Any],
    x: int,
    y: int,
    layer_index: int = 0,
) -> Dict[str, Any]:
    """Get tile information at (x, y) in a tile layer.

    Args:
        map_data: Map dict.
        x: Tile x coordinate.
        y: Tile y coordinate.
        layer_index: Layer index (default 0).

    Returns:
        Tile info dict.
    """
    layers = map_data.get("layers", [])
    if layer_index < 0 or layer_index >= len(layers):
        raise IndexError(f"Layer index {layer_index} out of range")

    layer = layers[layer_index]
    if layer.get("type") != "tilelayer":
        raise ValueError(f"Layer {layer_index} is not a tile layer")

    w = layer.get("width", map_data.get("width", 10))
    h = layer.get("height", map_data.get("height", 8))

    if x < 0 or x >= w or y < 0 or y >= h:
        raise ValueError(f"Coordinates ({x}, {y}) out of bounds (0-{w - 1}, 0-{h - 1})")

    data = layer.get("data", [])
    idx = y * w + x
    tile_id = data[idx] if idx < len(data) else 0

    result = {
        "x": x,
        "y": y,
        "layer_index": layer_index,
        "layer_name": layer.get("name", ""),
        "tile_id": tile_id,
        "empty": tile_id == 0,
    }

    # Look up tileset info if tile is not empty
    if tile_id > 0:
        from cli_anything.tiled.core.tileset_ops import find_tileset_for_gid
        ts_info = find_tileset_for_gid(map_data, tile_id)
        if ts_info:
            result["tileset"] = ts_info["tileset_name"]
            result["local_id"] = ts_info["local_id"]

    return result


def set_tile(
    map_data: Dict[str, Any],
    x: int,
    y: int,
    tile_id: int,
    layer_index: int = 0,
) -> Dict[str, Any]:
    """Set a tile at (x, y) in a tile layer.

    Args:
        map_data: Map dict.
        x: Tile x coordinate.
        y: Tile y coordinate.
        tile_id: Tile ID to set (0 = clear).
        layer_index: Layer index (default 0).

    Returns:
        Result dict with old and new tile IDs.
    """
    layers = map_data.get("layers", [])
    if layer_index < 0 or layer_index >= len(layers):
        raise IndexError(f"Layer index {layer_index} out of range")

    layer = layers[layer_index]
    if layer.get("type") != "tilelayer":
        raise ValueError(f"Layer {layer_index} is not a tile layer")

    w = layer.get("width", map_data.get("width", 10))
    h = layer.get("height", map_data.get("height", 8))

    if x < 0 or x >= w or y < 0 or y >= h:
        raise ValueError(f"Coordinates ({x}, {y}) out of bounds (0-{w - 1}, 0-{h - 1})")

    data = layer.get("data", [])
    # Ensure data is sized correctly
    while len(data) < w * h:
        data.append(0)
    layer["data"] = data

    idx = y * w + x
    old_tile = data[idx]
    data[idx] = tile_id

    return {
        "x": x,
        "y": y,
        "layer_index": layer_index,
        "old_tile_id": old_tile,
        "new_tile_id": tile_id,
    }


def get_tile_at_all_layers(
    map_data: Dict[str, Any],
    x: int,
    y: int,
) -> List[Dict[str, Any]]:
    """Get tile info at (x, y) across all tile layers.

    Args:
        map_data: Map dict.
        x: Tile x coordinate.
        y: Tile y coordinate.

    Returns:
        List of tile info dicts, one per tile layer.
    """
    result = []
    for i, layer in enumerate(map_data.get("layers", [])):
        if layer.get("type") != "tilelayer":
            continue

        w = layer.get("width", map_data.get("width", 10))
        h = layer.get("height", map_data.get("height", 8))

        if x < 0 or x >= w or y < 0 or y >= h:
            continue

        data = layer.get("data", [])
        idx = y * w + x
        tile_id = data[idx] if idx < len(data) else 0

        result.append({
            "layer_index": i,
            "layer_name": layer.get("name", ""),
            "tile_id": tile_id,
            "empty": tile_id == 0,
        })

    return result


def check_collision(
    map_data: Dict[str, Any],
    x: int,
    y: int,
) -> Dict[str, Any]:
    """Check if a tile position has collision (is blocked).

    Collision is determined by:
    1. Checking tile layers named 'collision', 'walls', 'obj' for non-empty tiles
    2. Checking object layers for objects of type 'blocked', 'wall', 'obstacle'

    Args:
        map_data: Map dict.
        x: Tile x coordinate.
        y: Tile y coordinate.

    Returns:
        Collision info dict.
    """
    tile_w = map_data.get("tilewidth", 32)
    tile_h = map_data.get("tileheight", 32)
    map_w = map_data.get("width", 10)
    map_h = map_data.get("height", 8)

    if x < 0 or x >= map_w or y < 0 or y >= map_h:
        return {
            "x": x,
            "y": y,
            "blocked": True,
            "reason": "out_of_bounds",
        }

    blocked = False
    reasons = []

    for i, layer in enumerate(map_data.get("layers", [])):
        name = (layer.get("name", "") or "").lower()

        if layer.get("type") == "tilelayer":
            # Check collision-related tile layers
            if any(tag in name for tag in ("collision", "wall", "obj", "block")):
                w = layer.get("width", map_w)
                data = layer.get("data", [])
                idx = y * w + x
                if idx < len(data) and data[idx] != 0:
                    blocked = True
                    reasons.append({
                        "type": "tile",
                        "layer_index": i,
                        "layer_name": layer.get("name", ""),
                        "tile_id": data[idx],
                    })

        elif layer.get("type") == "objectgroup":
            # Check object layer for blocking objects
            for obj in layer.get("objects", []):
                obj_type = (obj.get("type", "") or "").lower()
                if obj_type not in ("blocked", "wall", "obstacle", "collision"):
                    continue

                obj_x = obj.get("x", 0) / tile_w
                obj_y = obj.get("y", 0) / tile_h
                obj_w = max(1, obj.get("width", tile_w) / tile_w)
                obj_h = max(1, obj.get("height", tile_h) / tile_h)

                if obj_x <= x < obj_x + obj_w and obj_y <= y < obj_y + obj_h:
                    blocked = True
                    reasons.append({
                        "type": "object",
                        "id": obj.get("id", 0),
                        "name": obj.get("name", ""),
                        "obj_type": obj.get("type", ""),
                    })

    return {
        "x": x,
        "y": y,
        "blocked": blocked,
        "reasons": reasons,
    }


def get_tile_region(
    map_data: Dict[str, Any],
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    layer_index: int = 0,
) -> Dict[str, Any]:
    """Get tile data for a rectangular region.

    Args:
        map_data: Map dict.
        x1, y1: Top-left corner (inclusive).
        x2, y2: Bottom-right corner (inclusive).
        layer_index: Layer index.

    Returns:
        Region info dict with 2D tile data.
    """
    layers = map_data.get("layers", [])
    if layer_index < 0 or layer_index >= len(layers):
        raise IndexError(f"Layer index {layer_index} out of range")

    layer = layers[layer_index]
    if layer.get("type") != "tilelayer":
        raise ValueError(f"Layer {layer_index} is not a tile layer")

    w = layer.get("width", map_data.get("width", 10))
    h = layer.get("height", map_data.get("height", 8))
    data = layer.get("data", [])

    # Clamp to bounds
    x1 = max(0, min(x1, w - 1))
    y1 = max(0, min(y1, h - 1))
    x2 = max(0, min(x2, w - 1))
    y2 = max(0, min(y2, h - 1))

    region = []
    for y in range(y1, y2 + 1):
        row = []
        for x in range(x1, x2 + 1):
            idx = y * w + x
            row.append(data[idx] if idx < len(data) else 0)
        region.append(row)

    return {
        "layer_index": layer_index,
        "layer_name": layer.get("name", ""),
        "region": f"({x1},{y1})-({x2},{y2})",
        "width": x2 - x1 + 1,
        "height": y2 - y1 + 1,
        "tiles": region,
    }
