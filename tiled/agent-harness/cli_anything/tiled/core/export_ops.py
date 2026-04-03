"""Tiled CLI - Export operations.

Handles exporting maps to JSON, PNG (via Tiled CLI), and Convex scene
format for AI Town import.
"""

import json
import os
import shutil
import subprocess
from typing import Any, Dict, Optional

from cli_anything.tiled.utils.tmx_parser import write_tiled_json, write_tmx


# ── Tiled Backend ────────────────────────────────────────────────────

def find_tiled_cli() -> str:
    """Find the Tiled CLI executable.

    Returns:
        Path to tiled executable.

    Raises:
        RuntimeError: If Tiled is not installed.
    """
    # Check common locations
    candidates = [
        shutil.which("tiled"),
        "/opt/homebrew/bin/tiled",
        "/usr/local/bin/tiled",
        "/usr/bin/tiled",
    ]

    # macOS app bundle
    app_path = "/Applications/Tiled.app/Contents/MacOS/Tiled"
    if os.path.exists(app_path):
        candidates.append(app_path)

    for path in candidates:
        if path and os.path.exists(path):
            return path

    raise RuntimeError(
        "Tiled is not installed or not found in PATH.\n"
        "Install with:\n"
        "  macOS:  brew install tiled\n"
        "  Linux:  sudo apt install tiled  (or snap install tiled)\n"
        "  All:    https://www.mapeditor.org/download.html"
    )


def is_tiled_available() -> bool:
    """Check if Tiled CLI is available."""
    try:
        find_tiled_cli()
        return True
    except RuntimeError:
        return False


# ── Export to JSON ───────────────────────────────────────────────────

def to_json(
    map_data: Dict[str, Any],
    output_path: str,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """Export map to Tiled JSON format.

    Args:
        map_data: Map dict.
        output_path: Output .json path.
        overwrite: Whether to overwrite existing files.

    Returns:
        Result dict.
    """
    if os.path.exists(output_path) and not overwrite:
        raise FileExistsError(f"Output file exists: {output_path}. Use --overwrite.")

    abs_path = write_tiled_json(map_data, output_path)
    file_size = os.path.getsize(abs_path)

    return {
        "output": abs_path,
        "format": "json",
        "file_size": file_size,
        "file_size_human": _human_size(file_size),
    }


# ── Export to TMX ────────────────────────────────────────────────────

def to_tmx(
    map_data: Dict[str, Any],
    output_path: str,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """Export map to TMX format.

    Args:
        map_data: Map dict.
        output_path: Output .tmx path.
        overwrite: Whether to overwrite existing files.

    Returns:
        Result dict.
    """
    if os.path.exists(output_path) and not overwrite:
        raise FileExistsError(f"Output file exists: {output_path}. Use --overwrite.")

    abs_path = write_tmx(map_data, output_path)
    file_size = os.path.getsize(abs_path)

    return {
        "output": abs_path,
        "format": "tmx",
        "file_size": file_size,
        "file_size_human": _human_size(file_size),
    }


# ── Export to PNG ────────────────────────────────────────────────────

def to_png(
    map_data: Dict[str, Any],
    output_path: str,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """Export map to PNG using the Tiled CLI backend.

    This requires Tiled to be installed. The process:
    1. Write a temporary TMX file
    2. Call `tiled --export-map temp.tmx output.png`
    3. Clean up the temp file

    Args:
        map_data: Map dict.
        output_path: Output .png path.
        overwrite: Whether to overwrite existing files.

    Returns:
        Result dict.
    """
    if os.path.exists(output_path) and not overwrite:
        raise FileExistsError(f"Output file exists: {output_path}. Use --overwrite.")

    tiled = find_tiled_cli()

    # Write temporary TMX
    import tempfile
    tmp_dir = tempfile.mkdtemp(prefix="cli-anything-tiled-")
    tmp_tmx = os.path.join(tmp_dir, "export.tmx")

    try:
        write_tmx(map_data, tmp_tmx)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Call Tiled CLI for rendering
        result = subprocess.run(
            [tiled, "--export-map", tmp_tmx, os.path.abspath(output_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"Tiled export failed: {error_msg}")

        if not os.path.exists(output_path):
            raise RuntimeError(
                "Tiled export completed but output file not created. "
                "This may happen if tilesets are missing or paths are invalid."
            )

        file_size = os.path.getsize(output_path)

        return {
            "output": os.path.abspath(output_path),
            "format": "png",
            "file_size": file_size,
            "file_size_human": _human_size(file_size),
            "method": "tiled-cli",
            "tiled_path": tiled,
        }

    finally:
        # Clean up temp files
        import shutil as shutil_mod
        shutil_mod.rmtree(tmp_dir, ignore_errors=True)


# ── Export to Convex Scene Format ────────────────────────────────────

def to_convex(
    map_data: Dict[str, Any],
    output_path: str,
    scene_name: str = "scene",
    display_name: str = "Scene",
    tileset_web_path: str = "/ai-town/assets/gentle-obj.png",
    overwrite: bool = False,
) -> Dict[str, Any]:
    """Export map to Convex scene format for AI Town import.

    Generates JSON matching the scene:importFromEditor mutation format.
    This includes:
    - mapData: tile layers converted to [x][y] format
    - furniture: objects extracted from object layers
    - spawnPoint / exitPoint: special objects

    Args:
        map_data: Map dict.
        output_path: Output .json path.
        scene_name: Scene identifier (e.g., "shop_interior").
        display_name: Human-readable name (e.g., "General Store").
        tileset_web_path: Web-accessible path to tileset image.
        overwrite: Whether to overwrite existing files.

    Returns:
        Result dict.
    """
    if os.path.exists(output_path) and not overwrite:
        raise FileExistsError(f"Output file exists: {output_path}. Use --overwrite.")

    w = map_data.get("width", 10)
    h = map_data.get("height", 8)
    tile_dim = map_data.get("tilewidth", 32)

    # Get tileset info
    tileset_px_w = 1440
    tileset_px_h = 1024
    tilesets = map_data.get("tilesets", [])
    if tilesets:
        ts = tilesets[0]
        if ts.get("imagewidth"):
            tileset_px_w = ts["imagewidth"]
        if ts.get("imageheight"):
            tileset_px_h = ts["imageheight"]
        if ts.get("image"):
            basename = os.path.basename(ts["image"])
            tileset_web_path = f"/ai-town/assets/{basename}"

    # Separate layers into bg and collision
    bg_layers = []
    obj_layers = []
    furniture = []
    spawn_point = {"x": w // 2, "y": h - 2}
    exit_point = {"x": w // 2, "y": h - 1}

    for layer in map_data.get("layers", []):
        if layer.get("type") == "tilelayer":
            converted = _convert_layer_to_xy(layer.get("data", []), w, h)
            name = (layer.get("name", "") or "").lower()
            if any(tag in name for tag in ("collision", "obj", "wall", "block")):
                obj_layers.append(converted)
            else:
                bg_layers.append(converted)

        elif layer.get("type") == "objectgroup":
            for obj in layer.get("objects", []):
                tile_x = int(obj.get("x", 0) / tile_dim)
                tile_y = int(obj.get("y", 0) / tile_dim)
                tile_w_obj = max(1, int(obj.get("width", tile_dim) / tile_dim))
                tile_h_obj = max(1, int(obj.get("height", tile_dim) / tile_dim))

                obj_name = (obj.get("name", "") or "").lower()
                obj_type = (obj.get("type", "") or "").lower()

                # Handle special objects
                if obj_name == "spawn" or obj_type == "spawn":
                    spawn_point = {"x": tile_x, "y": tile_y}
                    continue
                if obj_name in ("exit", "door") or obj_type == "exit":
                    exit_point = {"x": tile_x, "y": tile_y}
                    continue

                # Determine furniture type
                furn_type = "decor"
                action = None
                if obj_type in ("interact", "counter", "shop"):
                    furn_type = "interact"
                    props = obj.get("properties", {})
                    action = props.get("action", "buy_food")
                elif obj_type in ("blocked", "wall", "obstacle"):
                    furn_type = "blocked"
                elif obj_type in ("work", "forge", "desk"):
                    furn_type = "interact"
                    action = "work"

                furniture.append({
                    "id": f"furn_{len(furniture) + 1}",
                    "name": obj.get("name", "") or obj.get("type", "") or "Object",
                    "type": furn_type,
                    "x": tile_x,
                    "y": tile_y,
                    "w": tile_w_obj,
                    "h": tile_h_obj,
                    "action": action,
                })

    # Ensure at least one layer each
    if not bg_layers:
        bg_layers.append(_empty_xy_layer(w, h))
    if not obj_layers:
        obj_layers.append(_empty_xy_layer(w, h))

    # Build Convex-compatible output
    convex_data = {
        "name": scene_name,
        "displayName": display_name,
        "mapData": {
            "tilesetpath": tileset_web_path,
            "tiledim": tile_dim,
            "tilesetpxw": tileset_px_w,
            "tilesetpxh": tileset_px_h,
            "bgtiles": bg_layers,
            "objmap": obj_layers,
            "mapwidth": w,
            "mapheight": h,
        },
        "furniture": furniture,
        "spawnPoint": spawn_point,
        "exitPoint": exit_point,
    }

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(convex_data, f, indent=2)

    file_size = os.path.getsize(output_path)

    return {
        "output": os.path.abspath(output_path),
        "format": "convex",
        "scene_name": scene_name,
        "display_name": display_name,
        "map_size": f"{w}x{h}",
        "bg_layers": len(bg_layers),
        "obj_layers": len(obj_layers),
        "furniture_count": len(furniture),
        "spawn_point": spawn_point,
        "exit_point": exit_point,
        "file_size": file_size,
        "file_size_human": _human_size(file_size),
    }


def _convert_layer_to_xy(data: list, w: int, h: int) -> list:
    """Convert 1D row-major tile data to [x][y] format.

    Tiled uses 1-based tile IDs (0 = empty).
    Convex format uses tile indices (0-based), with -1 = empty.
    """
    arr = []
    for x in range(w):
        col = []
        for y in range(h):
            idx = y * w + x
            tiled_id = data[idx] if idx < len(data) else 0
            col.append(tiled_id - 1 if tiled_id > 0 else -1)
        arr.append(col)
    return arr


def _empty_xy_layer(w: int, h: int) -> list:
    """Create an empty [x][y] layer filled with -1."""
    return [[-1] * h for _ in range(w)]


def _human_size(nbytes: int) -> str:
    """Convert byte count to human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} TB"
