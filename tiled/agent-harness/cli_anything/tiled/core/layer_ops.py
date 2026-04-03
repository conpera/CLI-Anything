"""Tiled CLI - Layer management operations.

Handles creating, removing, renaming, listing, filling, and painting
tile layers within a Tiled map.
"""

from typing import Any, Dict, List, Optional


def list_layers(map_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List all layers in the map.

    Returns:
        List of layer summary dicts.
    """
    result = []
    for i, layer in enumerate(map_data.get("layers", [])):
        info = {
            "index": i,
            "id": layer.get("id", 0),
            "name": layer.get("name", ""),
            "type": layer.get("type", "unknown"),
            "visible": layer.get("visible", True),
            "opacity": layer.get("opacity", 1.0),
        }
        if layer.get("type") == "tilelayer":
            info["width"] = layer.get("width", 0)
            info["height"] = layer.get("height", 0)
            data = layer.get("data", [])
            info["non_empty_tiles"] = sum(1 for t in data if t != 0)
            info["total_tiles"] = len(data)
        elif layer.get("type") == "objectgroup":
            info["object_count"] = len(layer.get("objects", []))
        result.append(info)
    return result


def add_layer(
    map_data: Dict[str, Any],
    name: str = "New Layer",
    layer_type: str = "tilelayer",
    position: Optional[int] = None,
    visible: bool = True,
    opacity: float = 1.0,
) -> Dict[str, Any]:
    """Add a new layer to the map.

    Args:
        map_data: Map dict.
        name: Layer name.
        layer_type: "tilelayer" or "objectgroup".
        position: Insert position (None = append to end).
        visible: Whether layer is visible.
        opacity: Layer opacity (0.0-1.0).

    Returns:
        The new layer dict.
    """
    layers = map_data.setdefault("layers", [])
    next_id = map_data.get("nextlayerid", len(layers) + 1)
    map_data["nextlayerid"] = next_id + 1

    if layer_type == "tilelayer":
        w = map_data.get("width", 10)
        h = map_data.get("height", 8)
        layer = {
            "type": "tilelayer",
            "id": next_id,
            "name": name,
            "width": w,
            "height": h,
            "visible": visible,
            "opacity": opacity,
            "x": 0,
            "y": 0,
            "data": [0] * (w * h),
        }
    elif layer_type == "objectgroup":
        layer = {
            "type": "objectgroup",
            "id": next_id,
            "name": name,
            "visible": visible,
            "opacity": opacity,
            "x": 0,
            "y": 0,
            "objects": [],
        }
    else:
        raise ValueError(f"Unknown layer type: {layer_type}. Use 'tilelayer' or 'objectgroup'.")

    if position is not None:
        if position < 0 or position > len(layers):
            raise IndexError(f"Position {position} out of range (0-{len(layers)})")
        layers.insert(position, layer)
    else:
        layers.append(layer)

    return {
        "id": layer["id"],
        "name": layer["name"],
        "type": layer["type"],
        "index": layers.index(layer),
    }


def remove_layer(map_data: Dict[str, Any], index: int) -> Dict[str, Any]:
    """Remove a layer by index.

    Args:
        map_data: Map dict.
        index: Layer index to remove.

    Returns:
        Info about removed layer.
    """
    layers = map_data.get("layers", [])
    if index < 0 or index >= len(layers):
        raise IndexError(f"Layer index {index} out of range (0-{len(layers) - 1})")

    removed = layers.pop(index)
    return {
        "removed": True,
        "name": removed.get("name", ""),
        "type": removed.get("type", ""),
        "index": index,
    }


def rename_layer(map_data: Dict[str, Any], index: int, new_name: str) -> Dict[str, Any]:
    """Rename a layer.

    Args:
        map_data: Map dict.
        index: Layer index.
        new_name: New layer name.

    Returns:
        Result dict.
    """
    layers = map_data.get("layers", [])
    if index < 0 or index >= len(layers):
        raise IndexError(f"Layer index {index} out of range (0-{len(layers) - 1})")

    old_name = layers[index].get("name", "")
    layers[index]["name"] = new_name

    return {
        "index": index,
        "old_name": old_name,
        "new_name": new_name,
    }


def fill_layer(
    map_data: Dict[str, Any],
    index: int,
    tile_id: int,
) -> Dict[str, Any]:
    """Fill an entire tile layer with a single tile ID.

    Args:
        map_data: Map dict.
        index: Layer index (must be a tile layer).
        tile_id: Tile ID to fill with (0 = empty).

    Returns:
        Result dict.
    """
    layers = map_data.get("layers", [])
    if index < 0 or index >= len(layers):
        raise IndexError(f"Layer index {index} out of range (0-{len(layers) - 1})")

    layer = layers[index]
    if layer.get("type") != "tilelayer":
        raise ValueError(f"Layer {index} is not a tile layer (type: {layer.get('type')})")

    w = layer.get("width", map_data.get("width", 10))
    h = layer.get("height", map_data.get("height", 8))
    layer["data"] = [tile_id] * (w * h)

    return {
        "index": index,
        "name": layer.get("name", ""),
        "tile_id": tile_id,
        "tiles_filled": w * h,
    }


def paint_tile(
    map_data: Dict[str, Any],
    layer_index: int,
    x: int,
    y: int,
    tile_id: int,
) -> Dict[str, Any]:
    """Set a single tile at (x, y) in a tile layer.

    Args:
        map_data: Map dict.
        layer_index: Layer index.
        x: Tile x coordinate.
        y: Tile y coordinate.
        tile_id: Tile ID to place (0 = clear).

    Returns:
        Result dict.
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

    idx = y * w + x
    data = layer.get("data", [])

    # Ensure data is large enough
    while len(data) <= idx:
        data.append(0)
    layer["data"] = data

    old_tile = data[idx]
    data[idx] = tile_id

    return {
        "layer": layer_index,
        "x": x,
        "y": y,
        "old_tile_id": old_tile,
        "new_tile_id": tile_id,
    }


def paint_rect(
    map_data: Dict[str, Any],
    layer_index: int,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    tile_id: int,
) -> Dict[str, Any]:
    """Fill a rectangular region with a tile ID.

    Args:
        map_data: Map dict.
        layer_index: Layer index.
        x1, y1: Top-left corner (inclusive).
        x2, y2: Bottom-right corner (inclusive).
        tile_id: Tile ID to fill with.

    Returns:
        Result dict.
    """
    layers = map_data.get("layers", [])
    if layer_index < 0 or layer_index >= len(layers):
        raise IndexError(f"Layer index {layer_index} out of range")

    layer = layers[layer_index]
    if layer.get("type") != "tilelayer":
        raise ValueError(f"Layer {layer_index} is not a tile layer")

    w = layer.get("width", map_data.get("width", 10))
    h = layer.get("height", map_data.get("height", 8))

    # Clamp to bounds
    x1 = max(0, min(x1, w - 1))
    y1 = max(0, min(y1, h - 1))
    x2 = max(0, min(x2, w - 1))
    y2 = max(0, min(y2, h - 1))

    data = layer.get("data", [0] * (w * h))
    while len(data) < w * h:
        data.append(0)
    layer["data"] = data

    count = 0
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            idx = y * w + x
            data[idx] = tile_id
            count += 1

    return {
        "layer": layer_index,
        "region": f"({x1},{y1})-({x2},{y2})",
        "tile_id": tile_id,
        "tiles_painted": count,
    }


def get_layer(map_data: Dict[str, Any], index: int) -> Dict[str, Any]:
    """Get detailed info about a specific layer.

    Args:
        map_data: Map dict.
        index: Layer index.

    Returns:
        Layer detail dict.
    """
    layers = map_data.get("layers", [])
    if index < 0 or index >= len(layers):
        raise IndexError(f"Layer index {index} out of range (0-{len(layers) - 1})")

    layer = layers[index]
    info = {
        "index": index,
        "id": layer.get("id", 0),
        "name": layer.get("name", ""),
        "type": layer.get("type", ""),
        "visible": layer.get("visible", True),
        "opacity": layer.get("opacity", 1.0),
    }

    if layer.get("type") == "tilelayer":
        data = layer.get("data", [])
        info["width"] = layer.get("width", 0)
        info["height"] = layer.get("height", 0)
        info["non_empty_tiles"] = sum(1 for t in data if t != 0)
        info["total_tiles"] = len(data)
        # Unique tile IDs used
        unique = set(t for t in data if t != 0)
        info["unique_tiles"] = sorted(unique)
    elif layer.get("type") == "objectgroup":
        info["object_count"] = len(layer.get("objects", []))
        info["objects"] = [
            {
                "id": o.get("id"),
                "name": o.get("name", ""),
                "type": o.get("type", ""),
                "x": o.get("x", 0),
                "y": o.get("y", 0),
            }
            for o in layer.get("objects", [])
        ]

    return info


def set_layer_property(
    map_data: Dict[str, Any],
    index: int,
    prop: str,
    value: str,
) -> Dict[str, Any]:
    """Set a layer property.

    Args:
        map_data: Map dict.
        index: Layer index.
        prop: Property name (visible, opacity, name).
        value: Property value.

    Returns:
        Result dict.
    """
    layers = map_data.get("layers", [])
    if index < 0 or index >= len(layers):
        raise IndexError(f"Layer index {index} out of range")

    layer = layers[index]

    if prop == "visible":
        layer["visible"] = value.lower() in ("true", "1", "yes")
    elif prop == "opacity":
        layer["opacity"] = float(value)
    elif prop == "name":
        layer["name"] = value
    else:
        raise ValueError(f"Unknown property: {prop}. Use: visible, opacity, name")

    return {
        "index": index,
        "property": prop,
        "value": layer.get(prop),
    }
