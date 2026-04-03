"""End-to-end tests for cli-anything-tiled.

Tests real file generation, TMX/JSON round-trips, Convex export,
and CLI subprocess invocation.
"""

import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import pytest

from cli_anything.tiled.core import map_ops
from cli_anything.tiled.core import layer_ops
from cli_anything.tiled.core import tileset_ops
from cli_anything.tiled.core import object_ops
from cli_anything.tiled.core import tile_ops
from cli_anything.tiled.core import export_ops
from cli_anything.tiled.utils.tmx_parser import (
    parse_tmx,
    write_tmx,
    read_tiled_json,
    write_tiled_json,
)


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory(prefix="tiled-e2e-") as d:
        yield d


# ── CLI resolution helper ────────────────────────────────────────────

def _resolve_cli(name):
    """Resolve installed CLI command; falls back to python -m for dev.

    Set env CLI_ANYTHING_FORCE_INSTALLED=1 to require the installed command.
    """
    import shutil
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = "cli_anything.tiled.tiled_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


def _get_dev_env():
    """Get environment with PYTHONPATH set for dev mode."""
    env = os.environ.copy()
    harness_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = harness_dir + (":" + existing if existing else "")
    return env


# ── TMX Round-Trip Tests ─────────────────────────────────────────────

class TestTMXRoundTrip:

    def test_empty_map_tmx_roundtrip(self, tmp_dir):
        """Create map -> write TMX -> read TMX -> verify identical data."""
        m = map_ops.create_map(width=10, height=8, name="roundtrip")
        tmx_path = os.path.join(tmp_dir, "test.tmx")

        write_tmx(m, tmx_path)
        assert os.path.exists(tmx_path)
        file_size = os.path.getsize(tmx_path)
        assert file_size > 0
        print(f"\n  TMX: {tmx_path} ({file_size:,} bytes)")

        # Verify valid XML
        tree = ET.parse(tmx_path)
        root = tree.getroot()
        assert root.tag == "map"
        assert root.get("width") == "10"
        assert root.get("height") == "8"

        # Read back
        m2 = parse_tmx(tmx_path)
        assert m2["width"] == m["width"]
        assert m2["height"] == m["height"]
        assert m2["tilewidth"] == m["tilewidth"]
        assert len(m2["layers"]) == len(m["layers"])

    def test_map_with_data_tmx_roundtrip(self, tmp_dir):
        """Map with tile data + objects survives TMX round-trip."""
        m = map_ops.create_map(width=5, height=5, name="data_test")

        # Add tiles
        for i in range(25):
            m["layers"][0]["data"][i] = i + 1

        # Add objects
        object_ops.add_object(m, name="Spawn", obj_type="spawn", tile_x=2, tile_y=2)
        object_ops.add_object(m, name="Counter", obj_type="interact",
                              tile_x=1, tile_y=1, tile_w=2, tile_h=1)

        tmx_path = os.path.join(tmp_dir, "data.tmx")
        write_tmx(m, tmx_path)

        m2 = parse_tmx(tmx_path)
        assert m2["layers"][0]["data"][0] == 1
        assert m2["layers"][0]["data"][24] == 25
        assert len(m2["layers"]) >= 2

        # Verify object layer
        obj_layers = [l for l in m2["layers"] if l["type"] == "objectgroup"]
        assert len(obj_layers) > 0
        assert len(obj_layers[0]["objects"]) == 2

        print(f"\n  TMX with data: {tmx_path} ({os.path.getsize(tmx_path):,} bytes)")

    def test_csv_encoding_valid(self, tmp_dir):
        """Ensure CSV encoding produces valid comma-separated values."""
        m = map_ops.create_map(width=3, height=3)
        m["layers"][0]["data"] = [1, 2, 3, 4, 5, 6, 7, 8, 9]

        tmx_path = os.path.join(tmp_dir, "csv.tmx")
        write_tmx(m, tmx_path)

        # Parse the raw XML and check CSV format
        tree = ET.parse(tmx_path)
        data_el = tree.find(".//data")
        assert data_el is not None
        assert data_el.get("encoding") == "csv"
        text = data_el.text.strip()
        # Should contain comma-separated integers
        values = [int(v.strip()) for v in text.replace("\n", ",").split(",") if v.strip()]
        assert values == [1, 2, 3, 4, 5, 6, 7, 8, 9]


# ── JSON Round-Trip Tests ────────────────────────────────────────────

class TestJSONRoundTrip:

    def test_json_roundtrip(self, tmp_dir):
        """Create map -> write JSON -> read JSON -> verify structure."""
        m = map_ops.create_map(width=10, height=8, name="json_test")
        json_path = os.path.join(tmp_dir, "test.json")

        write_tiled_json(m, json_path)
        assert os.path.exists(json_path)
        file_size = os.path.getsize(json_path)
        assert file_size > 0

        m2 = read_tiled_json(json_path)
        assert m2["width"] == 10
        assert m2["height"] == 8
        assert len(m2["layers"]) == 2

        print(f"\n  JSON: {json_path} ({file_size:,} bytes)")

    def test_full_map_json_roundtrip(self, tmp_dir):
        """Complex map with everything survives JSON round-trip."""
        m = map_ops.create_map(width=10, height=8, name="full_test")

        # Add tileset
        tileset_ops.add_tileset(
            m, name="tiles", image="tiles.png",
            tile_width=32, tile_height=32,
            columns=10, image_width=320, image_height=320,
        )

        # Add layers
        layer_ops.add_layer(m, name="Walls", layer_type="tilelayer")
        layer_ops.fill_layer(m, 0, 1)

        # Add objects
        object_ops.add_object(m, name="Spawn", obj_type="spawn", tile_x=5, tile_y=6)

        json_path = os.path.join(tmp_dir, "full.json")
        write_tiled_json(m, json_path)

        m2 = read_tiled_json(json_path)
        assert len(m2["tilesets"]) == 1
        assert m2["tilesets"][0]["name"] == "tiles"
        assert len(m2["layers"]) == 3
        assert m2["layers"][0]["data"][0] == 1  # Filled

        print(f"\n  Full JSON: {json_path} ({os.path.getsize(json_path):,} bytes)")


# ── Convex Export Tests ──────────────────────────────────────────────

class TestConvexExport:

    def test_shop_room_convex_export(self, tmp_dir):
        """Build a shop room and export to Convex format."""
        m = map_ops.create_map(template="shop", name="general_store")

        # Add tileset
        tileset_ops.add_tileset(
            m, name="gentle-obj", image="gentle-obj.png",
            tile_width=32, tile_height=32,
            columns=45, image_width=1440, image_height=1024,
        )

        # Fill ground
        layer_ops.fill_layer(m, 0, 1)

        # Add collision layer and paint walls
        layer_ops.add_layer(m, name="Walls", layer_type="tilelayer")
        walls_idx = len(m["layers"]) - 1
        # Top and bottom walls
        layer_ops.paint_rect(m, walls_idx, 0, 0, 9, 0, 5)
        layer_ops.paint_rect(m, walls_idx, 0, 7, 9, 7, 5)

        # Add furniture
        object_ops.add_object(
            m, name="Counter", obj_type="interact",
            tile_x=3, tile_y=2, tile_w=2, tile_h=1,
        )
        counter_id = m["layers"][1]["objects"][-1]["id"]
        object_ops.set_object_property(m, counter_id, "action", "buy_food")

        # Add spawn and exit
        object_ops.add_object(m, name="Spawn", obj_type="spawn", tile_x=5, tile_y=6)
        object_ops.add_object(m, name="Exit", obj_type="exit", tile_x=5, tile_y=7)

        # Export
        out = os.path.join(tmp_dir, "shop_convex.json")
        result = export_ops.to_convex(
            m, out,
            scene_name="general_store",
            display_name="General Store",
        )

        assert result["format"] == "convex"
        assert result["furniture_count"] == 1  # Only Counter (spawn/exit excluded)

        # Verify structure
        with open(out) as f:
            data = json.load(f)

        assert data["name"] == "general_store"
        assert data["displayName"] == "General Store"
        assert data["mapData"]["mapwidth"] == 10
        assert data["mapData"]["mapheight"] == 8
        assert data["mapData"]["tiledim"] == 32
        assert len(data["mapData"]["bgtiles"]) >= 1  # at least 1 bg layer
        assert len(data["mapData"]["bgtiles"][0]) == 10  # 10 columns
        assert len(data["mapData"]["bgtiles"][0][0]) == 8  # 8 rows per column
        assert data["spawnPoint"] == {"x": 5, "y": 6}
        assert data["exitPoint"] == {"x": 5, "y": 7}
        assert data["furniture"][0]["name"] == "Counter"
        assert data["furniture"][0]["type"] == "interact"

        file_size = os.path.getsize(out)
        print(f"\n  Convex JSON: {out} ({file_size:,} bytes)")

    def test_convex_tile_id_conversion(self, tmp_dir):
        """Verify Tiled 1-based IDs become Convex 0-based IDs."""
        m = map_ops.create_map(width=3, height=3)
        m["layers"][0]["data"] = [1, 2, 3, 0, 5, 0, 7, 8, 9]

        out = os.path.join(tmp_dir, "ids.json")
        export_ops.to_convex(m, out, scene_name="test", display_name="Test")

        with open(out) as f:
            data = json.load(f)

        bg = data["mapData"]["bgtiles"]
        # Check [x][y] format: bg[x][y]
        # bgtiles is [layer_index][x][y] format
        # bg[0] = first bg layer
        # x=0: data[0]=1, data[3]=0, data[6]=7 -> [0, -1, 6]
        assert bg[0][0] == [0, -1, 6]
        # x=1: data[1]=2, data[4]=5, data[7]=8 -> [1, 4, 7]
        assert bg[0][1] == [1, 4, 7]
        # x=2: data[2]=3, data[5]=0, data[8]=9 -> [2, -1, 8]
        assert bg[0][2] == [2, -1, 8]

    def test_convex_layer_separation(self, tmp_dir):
        """Verify collision layers go to objmap, others to bgtiles."""
        m = map_ops.create_map(width=3, height=3)
        layer_ops.fill_layer(m, 0, 1)  # Ground -> bgtiles

        # Add a collision layer
        layer_ops.add_layer(m, name="Collision", layer_type="tilelayer")
        collision_idx = len(m["layers"]) - 1
        layer_ops.fill_layer(m, collision_idx, 2)  # Walls -> objmap

        out = os.path.join(tmp_dir, "layers.json")
        export_ops.to_convex(m, out, scene_name="test", display_name="Test")

        with open(out) as f:
            data = json.load(f)

        # bgtiles[layer][x][y] — ground layer (tile ID 1 -> 0)
        assert data["mapData"]["bgtiles"][0][0][0] == 0

        # objmap[layer][x][y] — collision layer (tile ID 2 -> 1)
        assert data["mapData"]["objmap"][0][0][0] == 1


# ── CLI Subprocess Tests ─────────────────────────────────────────────

class TestCLISubprocess:
    CLI_BASE = _resolve_cli("cli-anything-tiled")

    def _run(self, args, check=True):
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True, text=True,
            check=check,
            env=_get_dev_env(),
        )

    def test_help(self):
        result = self._run(["--help"])
        assert result.returncode == 0
        assert "Tiled CLI" in result.stdout

    def test_map_new_json(self, tmp_dir):
        out = os.path.join(tmp_dir, "test.json")
        result = self._run(["--json", "map", "new", "-o", out])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["width"] == 10
        assert data["height"] == 8
        assert os.path.exists(out)

    def test_map_new_template(self, tmp_dir):
        out = os.path.join(tmp_dir, "shop.json")
        result = self._run(["--json", "map", "new", "--template", "shop", "-o", out])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["width"] == 10
        assert data["height"] == 8

    def test_layer_operations(self, tmp_dir):
        """Add, fill, and list layers via CLI."""
        out = os.path.join(tmp_dir, "layers.json")

        # Create map
        self._run(["map", "new", "-o", out])
        assert os.path.exists(out)

        # List layers
        result = self._run(["--json", "--map", out, "layer", "list"])
        assert result.returncode == 0
        layers = json.loads(result.stdout)
        assert len(layers) == 2  # Ground + Objects

        # Add a layer
        self._run(["--map", out, "layer", "add", "--name", "Walls"])

        # Fill ground
        self._run(["--map", out, "layer", "fill", "0", "1"])

        # List again
        result = self._run(["--json", "--map", out, "layer", "list"])
        layers = json.loads(result.stdout)
        assert len(layers) == 3

    def test_full_workflow(self, tmp_dir):
        """Full workflow: create, edit, export."""
        map_path = os.path.join(tmp_dir, "room.json")
        convex_path = os.path.join(tmp_dir, "room_convex.json")

        # Create map
        self._run(["map", "new", "--template", "room-small", "--name", "test_room", "-o", map_path])

        # Add object
        self._run(["--map", map_path, "object", "add", "--name", "Spawn",
                    "--type", "spawn", "--tile-x", "4", "--tile-y", "5"])

        # Add exit
        self._run(["--map", map_path, "object", "add", "--name", "Exit",
                    "--type", "exit", "--tile-x", "4", "--tile-y", "5"])

        # Fill ground
        self._run(["--map", map_path, "layer", "fill", "0", "1"])

        # Export to Convex
        self._run(["--map", map_path, "export", "to-convex", convex_path,
                    "--scene-name", "test_room", "--display-name", "Test Room",
                    "--overwrite"])

        assert os.path.exists(convex_path)
        with open(convex_path) as f:
            data = json.load(f)

        assert data["name"] == "test_room"
        assert data["displayName"] == "Test Room"
        assert "mapData" in data
        assert "furniture" in data
        assert "spawnPoint" in data

        file_size = os.path.getsize(convex_path)
        print(f"\n  CLI Convex export: {convex_path} ({file_size:,} bytes)")

    def test_convex_export_cli(self, tmp_dir):
        """Test Convex export via CLI with JSON output."""
        map_path = os.path.join(tmp_dir, "shop.json")
        convex_path = os.path.join(tmp_dir, "shop_convex.json")

        # Create and setup
        self._run(["map", "new", "--template", "shop", "-o", map_path])
        self._run(["--map", map_path, "object", "add", "--name", "Counter",
                    "--type", "interact", "--tile-x", "3", "--tile-y", "2"])

        # Export with JSON output
        result = self._run(["--json", "--map", map_path, "export", "to-convex",
                            convex_path, "--scene-name", "shop",
                            "--display-name", "Shop", "--overwrite"])
        assert result.returncode == 0
        export_result = json.loads(result.stdout)
        assert export_result["format"] == "convex"
        assert export_result["scene_name"] == "shop"

    def test_tile_operations_cli(self, tmp_dir):
        """Test tile get/set via CLI."""
        map_path = os.path.join(tmp_dir, "tiles.json")

        self._run(["map", "new", "-o", map_path])

        # Set a tile
        self._run(["--map", map_path, "tile", "set", "3", "2", "--id", "5"])

        # Get tile
        result = self._run(["--json", "--map", map_path, "tile", "get", "3", "2"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["tile_id"] == 5
        assert data["empty"] is False

    def test_map_info_json(self, tmp_dir):
        """Test map info with JSON output."""
        map_path = os.path.join(tmp_dir, "info.json")
        self._run(["map", "new", "--width", "12", "--height", "10",
                    "--name", "info_test", "-o", map_path])

        result = self._run(["--json", "--map", map_path, "map", "info"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["width"] == 12
        assert data["height"] == 10
        assert data["name"] == "info_test"


# ── Realistic Workflow Tests ─────────────────────────────────────────

class TestRealisticWorkflows:

    def test_shop_interior_build(self, tmp_dir):
        """Simulate building a complete shop room for AI Town."""
        m = map_ops.create_map(template="shop", name="blacksmith")

        # Step 1: Add tileset
        tileset_ops.add_tileset(
            m, name="gentle-obj", image="gentle-obj.png",
            tile_width=32, tile_height=32,
            columns=45, image_width=1440, image_height=1024,
        )

        # Step 2: Fill ground layer
        layer_ops.fill_layer(m, 0, 1)

        # Step 3: Add walls layer and paint walls
        layer_ops.add_layer(m, name="Walls", layer_type="tilelayer")
        walls_idx = 2  # Ground=0, Objects=1, Walls=2

        # Top wall
        layer_ops.paint_rect(m, walls_idx, 0, 0, 9, 0, 10)
        # Bottom wall (with gap for door)
        layer_ops.paint_rect(m, walls_idx, 0, 7, 3, 7, 10)
        layer_ops.paint_rect(m, walls_idx, 6, 7, 9, 7, 10)
        # Side walls
        for y in range(1, 7):
            layer_ops.paint_tile(m, walls_idx, 0, y, 10)
            layer_ops.paint_tile(m, walls_idx, 9, y, 10)

        # Step 4: Add furniture
        # Anvil
        object_ops.add_object(
            m, name="Anvil", obj_type="work",
            tile_x=2, tile_y=2, tile_w=1, tile_h=1,
        )
        # Counter
        object_ops.add_object(
            m, name="Counter", obj_type="interact",
            tile_x=5, tile_y=2, tile_w=3, tile_h=1,
        )
        counter_id = m["layers"][1]["objects"][-1]["id"]
        object_ops.set_object_property(m, counter_id, "action", "buy_weapon")

        # Decorations
        object_ops.add_object(
            m, name="Barrel", obj_type="blocked",
            tile_x=1, tile_y=5, tile_w=1, tile_h=1,
        )

        # Step 5: Spawn and exit
        object_ops.add_object(m, name="Spawn", obj_type="spawn", tile_x=5, tile_y=6)
        object_ops.add_object(m, name="Exit", obj_type="exit", tile_x=5, tile_y=7)

        # Step 6: Save as JSON
        json_path = os.path.join(tmp_dir, "blacksmith.json")
        map_ops.save_map_to(m, json_path, overwrite=True)

        # Step 7: Export to Convex
        convex_path = os.path.join(tmp_dir, "blacksmith_convex.json")
        result = export_ops.to_convex(
            m, convex_path,
            scene_name="blacksmith",
            display_name="Blacksmith Shop",
        )

        # Verify
        assert result["furniture_count"] == 3  # Anvil, Counter, Barrel
        assert result["spawn_point"] == {"x": 5, "y": 6}
        assert result["exit_point"] == {"x": 5, "y": 7}

        with open(convex_path) as f:
            data = json.load(f)

        # Verify furniture types
        furn_types = {f["name"]: f["type"] for f in data["furniture"]}
        assert furn_types["Anvil"] == "interact"  # work -> interact
        assert furn_types["Counter"] == "interact"
        assert furn_types["Barrel"] == "blocked"

        # Verify tile data exists (bgtiles[layer][x][y])
        assert len(data["mapData"]["bgtiles"]) >= 1
        assert len(data["mapData"]["bgtiles"][0]) == 10  # 10 columns
        assert len(data["mapData"]["objmap"]) > 0

        print(f"\n  Shop JSON: {json_path} ({os.path.getsize(json_path):,} bytes)")
        print(f"  Shop Convex: {convex_path} ({os.path.getsize(convex_path):,} bytes)")

    def test_map_edit_and_reexport(self, tmp_dir):
        """Simulate iterative editing: create, save, open, modify, save."""
        # Create initial map
        m = map_ops.create_map(width=8, height=6, name="cottage")
        layer_ops.fill_layer(m, 0, 1)

        path = os.path.join(tmp_dir, "cottage.json")
        map_ops.save_map_to(m, path, overwrite=True)

        # Re-open
        m2 = map_ops.open_map(path)
        assert m2["width"] == 8
        assert m2["height"] == 6

        # Resize
        map_ops.resize_map(m2, 10, 8, anchor="top-left")
        assert m2["width"] == 10
        assert m2["height"] == 8

        # Add a new layer
        layer_ops.add_layer(m2, name="Furniture", layer_type="tilelayer")

        # Set some tiles
        tile_ops.set_tile(m2, 3, 3, 15, 0)
        tile_val = tile_ops.get_tile(m2, 3, 3, 0)
        assert tile_val["tile_id"] == 15

        # Save again
        map_ops.save_map_to(m2, path, overwrite=True)

        # Verify final state
        m3 = map_ops.open_map(path)
        assert m3["width"] == 10
        assert m3["height"] == 8
        assert len(m3["layers"]) == 3

        print(f"\n  Edited map: {path} ({os.path.getsize(path):,} bytes)")
