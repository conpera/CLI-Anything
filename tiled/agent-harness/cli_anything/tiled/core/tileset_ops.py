"""Tiled CLI - Tileset management operations.

Handles listing, adding, importing, and querying tilesets within a map.
Tilesets can be either inline (embedded in the TMX) or external (referencing a .tsx file).
"""

import os
from typing import Any, Dict, List, Optional

from cli_anything.tiled.utils.tmx_parser import parse_tsx


def list_tilesets(map_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List all tilesets in the map.

    Returns:
        List of tileset summary dicts.
    """
    result = []
    for i, ts in enumerate(map_data.get("tilesets", [])):
        info = {
            "index": i,
            "firstgid": ts.get("firstgid", 1),
        }

        if "source" in ts:
            info["type"] = "external"
            info["source"] = ts["source"]
        else:
            info["type"] = "inline"
            info["name"] = ts.get("name", "")
            info["tilewidth"] = ts.get("tilewidth", 32)
            info["tileheight"] = ts.get("tileheight", 32)
            info["tilecount"] = ts.get("tilecount", 0)
            info["columns"] = ts.get("columns", 0)
            if "image" in ts:
                info["image"] = ts["image"]
                info["imagewidth"] = ts.get("imagewidth", 0)
                info["imageheight"] = ts.get("imageheight", 0)

        result.append(info)

    return result


def add_tileset(
    map_data: Dict[str, Any],
    name: str,
    image: str,
    tile_width: int = 32,
    tile_height: int = 32,
    columns: Optional[int] = None,
    image_width: Optional[int] = None,
    image_height: Optional[int] = None,
    firstgid: Optional[int] = None,
) -> Dict[str, Any]:
    """Add an inline tileset to the map.

    Args:
        map_data: Map dict.
        name: Tileset name.
        image: Path to tileset image.
        tile_width: Width of each tile in pixels.
        tile_height: Height of each tile in pixels.
        columns: Number of columns in the tileset image.
        image_width: Total image width in pixels.
        image_height: Total image height in pixels.
        firstgid: First global ID (auto-calculated if None).

    Returns:
        The new tileset info dict.
    """
    tilesets = map_data.setdefault("tilesets", [])

    # Auto-calculate firstgid
    if firstgid is None:
        if tilesets:
            last = tilesets[-1]
            last_firstgid = last.get("firstgid", 1)
            last_count = last.get("tilecount", 0)
            firstgid = last_firstgid + last_count
        else:
            firstgid = 1

    # Try to get image dimensions and calculate tile count/columns
    actual_iw = image_width or 0
    actual_ih = image_height or 0

    if columns is None and actual_iw > 0:
        columns = actual_iw // tile_width

    calc_cols = columns or 1
    tilecount = 0
    if actual_iw > 0 and actual_ih > 0:
        rows = actual_ih // tile_height
        tilecount = calc_cols * rows

    ts = {
        "firstgid": firstgid,
        "name": name,
        "tilewidth": tile_width,
        "tileheight": tile_height,
        "tilecount": tilecount,
        "columns": calc_cols,
        "image": image,
        "imagewidth": actual_iw,
        "imageheight": actual_ih,
    }

    tilesets.append(ts)

    return {
        "index": len(tilesets) - 1,
        "name": name,
        "firstgid": firstgid,
        "tilecount": tilecount,
        "columns": calc_cols,
        "image": image,
    }


def import_tileset(
    map_data: Dict[str, Any],
    tsx_path: str,
    firstgid: Optional[int] = None,
) -> Dict[str, Any]:
    """Import an external tileset (.tsx file) into the map.

    This adds a tileset reference. The tsx_path is stored as the source attribute.

    Args:
        map_data: Map dict.
        tsx_path: Path to .tsx file.
        firstgid: First global ID (auto-calculated if None).

    Returns:
        Import result dict.
    """
    if not os.path.exists(tsx_path):
        raise FileNotFoundError(f"TSX file not found: {tsx_path}")

    tilesets = map_data.setdefault("tilesets", [])

    # Auto-calculate firstgid
    if firstgid is None:
        if tilesets:
            last = tilesets[-1]
            last_firstgid = last.get("firstgid", 1)
            last_count = last.get("tilecount", 0)
            firstgid = last_firstgid + last_count
        else:
            firstgid = 1

    # Parse the TSX to get metadata
    tsx_info = parse_tsx(tsx_path)

    ts = {
        "firstgid": firstgid,
        "source": tsx_path,
        # Also store parsed info for convenience
        "name": tsx_info.get("name", ""),
        "tilewidth": tsx_info.get("tilewidth", 32),
        "tileheight": tsx_info.get("tileheight", 32),
        "tilecount": tsx_info.get("tilecount", 0),
        "columns": tsx_info.get("columns", 0),
    }

    if "image" in tsx_info:
        ts["image"] = tsx_info["image"]
        ts["imagewidth"] = tsx_info.get("imagewidth", 0)
        ts["imageheight"] = tsx_info.get("imageheight", 0)

    tilesets.append(ts)

    return {
        "index": len(tilesets) - 1,
        "source": tsx_path,
        "name": tsx_info.get("name", ""),
        "firstgid": firstgid,
        "tilecount": tsx_info.get("tilecount", 0),
    }


def get_tileset_info(
    map_data: Dict[str, Any],
    index: int,
) -> Dict[str, Any]:
    """Get detailed information about a tileset.

    Args:
        map_data: Map dict.
        index: Tileset index.

    Returns:
        Tileset info dict.
    """
    tilesets = map_data.get("tilesets", [])
    if index < 0 or index >= len(tilesets):
        raise IndexError(f"Tileset index {index} out of range (0-{len(tilesets) - 1})")

    ts = tilesets[index]
    info = {
        "index": index,
        "firstgid": ts.get("firstgid", 1),
    }

    if "source" in ts:
        info["type"] = "external"
        info["source"] = ts["source"]
    else:
        info["type"] = "inline"

    # Copy all available metadata
    for key in ("name", "tilewidth", "tileheight", "tilecount", "columns",
                "image", "imagewidth", "imageheight"):
        if key in ts:
            info[key] = ts[key]

    # Calculate GID range
    first = ts.get("firstgid", 1)
    count = ts.get("tilecount", 0)
    if count > 0:
        info["gid_range"] = f"{first}-{first + count - 1}"
        info["last_gid"] = first + count - 1

    return info


def remove_tileset(
    map_data: Dict[str, Any],
    index: int,
) -> Dict[str, Any]:
    """Remove a tileset by index.

    Warning: This does not clean up tile references in layers.

    Args:
        map_data: Map dict.
        index: Tileset index.

    Returns:
        Info about removed tileset.
    """
    tilesets = map_data.get("tilesets", [])
    if index < 0 or index >= len(tilesets):
        raise IndexError(f"Tileset index {index} out of range (0-{len(tilesets) - 1})")

    removed = tilesets.pop(index)
    return {
        "removed": True,
        "name": removed.get("name", removed.get("source", "")),
        "firstgid": removed.get("firstgid", 0),
        "index": index,
    }


def find_tileset_for_gid(
    map_data: Dict[str, Any],
    gid: int,
) -> Optional[Dict[str, Any]]:
    """Find which tileset a global tile ID belongs to.

    Args:
        map_data: Map dict.
        gid: Global tile ID.

    Returns:
        Tileset info dict or None if not found.
    """
    tilesets = map_data.get("tilesets", [])

    # Sort by firstgid descending to find the right tileset
    sorted_ts = sorted(
        enumerate(tilesets),
        key=lambda x: x[1].get("firstgid", 0),
        reverse=True,
    )

    for idx, ts in sorted_ts:
        firstgid = ts.get("firstgid", 1)
        if gid >= firstgid:
            tilecount = ts.get("tilecount", 0)
            local_id = gid - firstgid
            return {
                "tileset_index": idx,
                "tileset_name": ts.get("name", ts.get("source", "")),
                "firstgid": firstgid,
                "local_id": local_id,
                "gid": gid,
                "in_range": tilecount == 0 or local_id < tilecount,
            }

    return None
