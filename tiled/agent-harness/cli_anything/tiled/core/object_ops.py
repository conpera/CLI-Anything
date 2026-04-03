"""Tiled CLI - Object/furniture management operations.

Handles adding, removing, listing, and modifying objects within object
layers. Objects represent furniture, spawn points, exits, and interactive
elements in the map.
"""

from typing import Any, Dict, List, Optional


def list_objects(
    map_data: Dict[str, Any],
    layer_index: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """List all objects in the map (or a specific object layer).

    Args:
        map_data: Map dict.
        layer_index: If specified, only list objects from this layer.

    Returns:
        List of object info dicts.
    """
    result = []
    layers = map_data.get("layers", [])

    for i, layer in enumerate(layers):
        if layer.get("type") != "objectgroup":
            continue
        if layer_index is not None and i != layer_index:
            continue

        tile_w = map_data.get("tilewidth", 32)
        tile_h = map_data.get("tileheight", 32)

        for obj in layer.get("objects", []):
            info = {
                "id": obj.get("id", 0),
                "name": obj.get("name", ""),
                "type": obj.get("type", ""),
                "layer_index": i,
                "layer_name": layer.get("name", ""),
                "x": obj.get("x", 0),
                "y": obj.get("y", 0),
                "width": obj.get("width", 0),
                "height": obj.get("height", 0),
                "tile_x": int(obj.get("x", 0) / tile_w),
                "tile_y": int(obj.get("y", 0) / tile_h),
                "tile_w": max(1, int(obj.get("width", tile_w) / tile_w)),
                "tile_h": max(1, int(obj.get("height", tile_h) / tile_h)),
                "visible": obj.get("visible", True),
            }
            if obj.get("properties"):
                info["properties"] = obj["properties"]
            result.append(info)

    return result


def add_object(
    map_data: Dict[str, Any],
    name: str,
    obj_type: str = "",
    x: Optional[float] = None,
    y: Optional[float] = None,
    tile_x: Optional[int] = None,
    tile_y: Optional[int] = None,
    width: Optional[float] = None,
    height: Optional[float] = None,
    tile_w: int = 1,
    tile_h: int = 1,
    layer_index: Optional[int] = None,
    properties: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Add a new object to an object layer.

    Coordinates can be specified in pixels (x, y) or tiles (tile_x, tile_y).
    If tile coordinates are used, they are converted to pixels.

    Args:
        map_data: Map dict.
        name: Object name.
        obj_type: Object type/class (e.g., "spawn", "exit", "interact", "blocked").
        x: Pixel x coordinate.
        y: Pixel y coordinate.
        tile_x: Tile x coordinate (converted to pixels).
        tile_y: Tile y coordinate (converted to pixels).
        width: Object width in pixels.
        height: Object height in pixels.
        tile_w: Object width in tiles (used if width not specified).
        tile_h: Object height in tiles (used if height not specified).
        layer_index: Target object layer index (auto-finds first objectgroup if None).
        properties: Dict of custom properties.

    Returns:
        The new object info dict.
    """
    tile_pw = map_data.get("tilewidth", 32)
    tile_ph = map_data.get("tileheight", 32)

    # Convert tile coords to pixel coords
    if tile_x is not None and x is None:
        x = float(tile_x * tile_pw)
    if tile_y is not None and y is None:
        y = float(tile_y * tile_ph)
    if x is None:
        x = 0.0
    if y is None:
        y = 0.0

    # Calculate width/height
    if width is None:
        width = float(tile_w * tile_pw)
    if height is None:
        height = float(tile_h * tile_ph)

    # Find target object layer
    layers = map_data.get("layers", [])
    target_layer = None
    target_idx = None

    if layer_index is not None:
        if layer_index < 0 or layer_index >= len(layers):
            raise IndexError(f"Layer index {layer_index} out of range")
        if layers[layer_index].get("type") != "objectgroup":
            raise ValueError(f"Layer {layer_index} is not an object layer")
        target_layer = layers[layer_index]
        target_idx = layer_index
    else:
        # Find first object layer
        for i, layer in enumerate(layers):
            if layer.get("type") == "objectgroup":
                target_layer = layer
                target_idx = i
                break

    if target_layer is None:
        raise RuntimeError(
            "No object layer found. Add one with: layer add --type objectgroup"
        )

    # Generate next object ID
    next_id = map_data.get("nextobjectid", 1)
    map_data["nextobjectid"] = next_id + 1

    obj = {
        "id": next_id,
        "name": name,
        "type": obj_type,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "visible": True,
        "rotation": 0,
    }

    if properties:
        obj["properties"] = properties

    target_layer.setdefault("objects", []).append(obj)

    return {
        "id": next_id,
        "name": name,
        "type": obj_type,
        "layer_index": target_idx,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "tile_x": int(x / tile_pw),
        "tile_y": int(y / tile_ph),
        "properties": properties or {},
    }


def remove_object(
    map_data: Dict[str, Any],
    obj_id: int,
) -> Dict[str, Any]:
    """Remove an object by its ID.

    Searches all object layers for the object.

    Args:
        map_data: Map dict.
        obj_id: Object ID to remove.

    Returns:
        Info about removed object.
    """
    for layer in map_data.get("layers", []):
        if layer.get("type") != "objectgroup":
            continue

        objects = layer.get("objects", [])
        for i, obj in enumerate(objects):
            if obj.get("id") == obj_id:
                removed = objects.pop(i)
                return {
                    "removed": True,
                    "id": obj_id,
                    "name": removed.get("name", ""),
                    "type": removed.get("type", ""),
                }

    raise ValueError(f"Object with ID {obj_id} not found in any layer")


def set_object_property(
    map_data: Dict[str, Any],
    obj_id: int,
    prop_name: str,
    prop_value: str,
    prop_type: str = "string",
) -> Dict[str, Any]:
    """Set a custom property on an object.

    Args:
        map_data: Map dict.
        obj_id: Object ID.
        prop_name: Property name.
        prop_value: Property value (as string, will be type-cast).
        prop_type: Property type (string, int, float, bool).

    Returns:
        Result dict.
    """
    obj = _find_object(map_data, obj_id)
    if obj is None:
        raise ValueError(f"Object with ID {obj_id} not found")

    # Type-cast value
    if prop_type == "int":
        value = int(prop_value)
    elif prop_type == "float":
        value = float(prop_value)
    elif prop_type == "bool":
        value = prop_value.lower() in ("true", "1", "yes")
    else:
        value = prop_value

    props = obj.setdefault("properties", {})
    props[prop_name] = value

    return {
        "id": obj_id,
        "name": obj.get("name", ""),
        "property": prop_name,
        "value": value,
        "type": prop_type,
    }


def move_object(
    map_data: Dict[str, Any],
    obj_id: int,
    x: Optional[float] = None,
    y: Optional[float] = None,
    tile_x: Optional[int] = None,
    tile_y: Optional[int] = None,
) -> Dict[str, Any]:
    """Move an object to new coordinates.

    Args:
        map_data: Map dict.
        obj_id: Object ID.
        x: New pixel x coordinate.
        y: New pixel y coordinate.
        tile_x: New tile x coordinate (converted to pixels).
        tile_y: New tile y coordinate (converted to pixels).

    Returns:
        Result dict.
    """
    obj = _find_object(map_data, obj_id)
    if obj is None:
        raise ValueError(f"Object with ID {obj_id} not found")

    tile_pw = map_data.get("tilewidth", 32)
    tile_ph = map_data.get("tileheight", 32)

    old_x = obj.get("x", 0)
    old_y = obj.get("y", 0)

    if tile_x is not None and x is None:
        x = float(tile_x * tile_pw)
    if tile_y is not None and y is None:
        y = float(tile_y * tile_ph)

    if x is not None:
        obj["x"] = x
    if y is not None:
        obj["y"] = y

    return {
        "id": obj_id,
        "name": obj.get("name", ""),
        "old_position": {"x": old_x, "y": old_y},
        "new_position": {"x": obj["x"], "y": obj["y"]},
    }


def resize_object(
    map_data: Dict[str, Any],
    obj_id: int,
    width: Optional[float] = None,
    height: Optional[float] = None,
    tile_w: Optional[int] = None,
    tile_h: Optional[int] = None,
) -> Dict[str, Any]:
    """Resize an object.

    Args:
        map_data: Map dict.
        obj_id: Object ID.
        width: New width in pixels.
        height: New height in pixels.
        tile_w: New width in tiles.
        tile_h: New height in tiles.

    Returns:
        Result dict.
    """
    obj = _find_object(map_data, obj_id)
    if obj is None:
        raise ValueError(f"Object with ID {obj_id} not found")

    tile_pw = map_data.get("tilewidth", 32)
    tile_ph = map_data.get("tileheight", 32)

    if tile_w is not None and width is None:
        width = float(tile_w * tile_pw)
    if tile_h is not None and height is None:
        height = float(tile_h * tile_ph)

    if width is not None:
        obj["width"] = width
    if height is not None:
        obj["height"] = height

    return {
        "id": obj_id,
        "name": obj.get("name", ""),
        "width": obj.get("width", 0),
        "height": obj.get("height", 0),
    }


def _find_object(map_data: Dict[str, Any], obj_id: int) -> Optional[Dict[str, Any]]:
    """Find an object by ID across all object layers."""
    for layer in map_data.get("layers", []):
        if layer.get("type") != "objectgroup":
            continue
        for obj in layer.get("objects", []):
            if obj.get("id") == obj_id:
                return obj
    return None
