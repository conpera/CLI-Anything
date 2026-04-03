"""Unit tests for cli-anything-tiled core modules.

All tests use synthetic data — no external files or Tiled installation required.
"""

import copy
import json
import os
import sys
import tempfile

import pytest

from cli_anything.tiled.core import map_ops
from cli_anything.tiled.core import layer_ops
from cli_anything.tiled.core import tileset_ops
from cli_anything.tiled.core import object_ops
from cli_anything.tiled.core import tile_ops
from cli_anything.tiled.core import export_ops
from cli_anything.tiled.core.session import Session


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory(prefix="tiled-test-") as d:
        yield d


@pytest.fixture
def basic_map():
    """Create a basic 10x8 map for testing."""
    return map_ops.create_map(width=10, height=8, name="test_map")


@pytest.fixture
def map_with_tileset():
    """Create a map with a tileset."""
    m = map_ops.create_map(width=10, height=8, name="test_map")
    tileset_ops.add_tileset(
        m, name="test_tileset", image="test.png",
        tile_width=32, tile_height=32,
        columns=10, image_width=320, image_height=320,
    )
    return m


@pytest.fixture
def map_with_objects():
    """Create a map with objects in the object layer."""
    m = map_ops.create_map(width=10, height=8, name="test_map")
    object_ops.add_object(m, name="Counter", obj_type="interact", tile_x=3, tile_y=2)
    object_ops.add_object(m, name="Spawn", obj_type="spawn", tile_x=5, tile_y=6)
    object_ops.add_object(m, name="Exit", obj_type="exit", tile_x=5, tile_y=7)
    return m


# ── map_ops tests ────────────────────────────────────────────────────

class TestMapOps:

    def test_create_map_default(self):
        m = map_ops.create_map()
        assert m["width"] == 10
        assert m["height"] == 8
        assert m["tilewidth"] == 32
        assert m["tileheight"] == 32
        assert m["orientation"] == "orthogonal"
        assert len(m["layers"]) == 2  # Ground + Objects

    def test_create_map_custom(self):
        m = map_ops.create_map(width=20, height=15, tile_width=16, tile_height=16,
                               name="custom", orientation="isometric")
        assert m["width"] == 20
        assert m["height"] == 15
        assert m["tilewidth"] == 16
        assert m["orientation"] == "isometric"
        assert m["properties"]["name"] == "custom"

    def test_create_map_template(self):
        m = map_ops.create_map(template="shop")
        assert m["width"] == 10
        assert m["height"] == 8

    def test_create_map_invalid_template(self):
        with pytest.raises(ValueError, match="Unknown template"):
            map_ops.create_map(template="nonexistent")

    def test_create_map_invalid_dimensions(self):
        with pytest.raises(ValueError, match="positive"):
            map_ops.create_map(width=0, height=5)

    def test_get_map_info(self, basic_map):
        info = map_ops.get_map_info(basic_map)
        assert info["width"] == 10
        assert info["height"] == 8
        assert info["pixel_width"] == 320
        assert info["pixel_height"] == 256
        assert info["tile_layers"] == 1
        assert info["object_layers"] == 1
        assert info["total_layers"] == 2

    def test_resize_map_grow(self, basic_map):
        # Put a tile to test preservation
        basic_map["layers"][0]["data"][0] = 5
        result = map_ops.resize_map(basic_map, 15, 12, anchor="top-left")
        assert basic_map["width"] == 15
        assert basic_map["height"] == 12
        assert len(basic_map["layers"][0]["data"]) == 15 * 12
        assert basic_map["layers"][0]["data"][0] == 5  # Preserved

    def test_resize_map_shrink(self, basic_map):
        result = map_ops.resize_map(basic_map, 5, 4, anchor="top-left")
        assert basic_map["width"] == 5
        assert basic_map["height"] == 4
        assert len(basic_map["layers"][0]["data"]) == 5 * 4

    def test_resize_map_center_anchor(self, basic_map):
        result = map_ops.resize_map(basic_map, 14, 12, anchor="center")
        assert result["anchor"] == "center"
        assert result["offset"]["x"] == 2  # (14 - 10) // 2
        assert result["offset"]["y"] == 2  # (12 - 8) // 2

    def test_list_templates(self):
        templates = map_ops.list_templates()
        assert len(templates) > 0
        names = [t["name"] for t in templates]
        assert "shop" in names
        assert "room-small" in names


# ── layer_ops tests ──────────────────────────────────────────────────

class TestLayerOps:

    def test_list_layers(self, basic_map):
        layers = layer_ops.list_layers(basic_map)
        assert len(layers) == 2
        assert layers[0]["type"] == "tilelayer"
        assert layers[0]["name"] == "Ground"
        assert layers[1]["type"] == "objectgroup"
        assert layers[1]["name"] == "Objects"

    def test_add_tile_layer(self, basic_map):
        result = layer_ops.add_layer(basic_map, name="Walls", layer_type="tilelayer")
        assert result["name"] == "Walls"
        assert result["type"] == "tilelayer"
        assert len(basic_map["layers"]) == 3
        # Verify data is empty
        new_layer = basic_map["layers"][-1]
        assert len(new_layer["data"]) == 10 * 8
        assert all(t == 0 for t in new_layer["data"])

    def test_add_object_layer(self, basic_map):
        result = layer_ops.add_layer(basic_map, name="Furniture", layer_type="objectgroup")
        assert result["type"] == "objectgroup"
        assert len(basic_map["layers"]) == 3

    def test_add_layer_at_position(self, basic_map):
        layer_ops.add_layer(basic_map, name="Bottom", position=0)
        assert basic_map["layers"][0]["name"] == "Bottom"
        assert basic_map["layers"][1]["name"] == "Ground"

    def test_remove_layer(self, basic_map):
        result = layer_ops.remove_layer(basic_map, 0)
        assert result["removed"] is True
        assert result["name"] == "Ground"
        assert len(basic_map["layers"]) == 1

    def test_remove_layer_out_of_range(self, basic_map):
        with pytest.raises(IndexError):
            layer_ops.remove_layer(basic_map, 99)

    def test_rename_layer(self, basic_map):
        result = layer_ops.rename_layer(basic_map, 0, "Floor")
        assert result["old_name"] == "Ground"
        assert result["new_name"] == "Floor"
        assert basic_map["layers"][0]["name"] == "Floor"

    def test_fill_layer(self, basic_map):
        result = layer_ops.fill_layer(basic_map, 0, 5)
        assert result["tile_id"] == 5
        assert result["tiles_filled"] == 10 * 8
        assert all(t == 5 for t in basic_map["layers"][0]["data"])

    def test_paint_tile(self, basic_map):
        result = layer_ops.paint_tile(basic_map, 0, 3, 2, 7)
        assert result["x"] == 3
        assert result["y"] == 2
        assert result["new_tile_id"] == 7
        idx = 2 * 10 + 3  # y * width + x
        assert basic_map["layers"][0]["data"][idx] == 7

    def test_paint_rect(self, basic_map):
        result = layer_ops.paint_rect(basic_map, 0, 1, 1, 3, 3, 9)
        assert result["tiles_painted"] == 9  # 3x3 region
        # Check corners
        assert basic_map["layers"][0]["data"][1 * 10 + 1] == 9
        assert basic_map["layers"][0]["data"][3 * 10 + 3] == 9

    def test_get_layer_info(self, basic_map):
        info = layer_ops.get_layer(basic_map, 0)
        assert info["name"] == "Ground"
        assert info["type"] == "tilelayer"
        assert info["non_empty_tiles"] == 0

    def test_set_layer_property_visible(self, basic_map):
        result = layer_ops.set_layer_property(basic_map, 0, "visible", "false")
        assert basic_map["layers"][0]["visible"] is False

    def test_set_layer_property_opacity(self, basic_map):
        layer_ops.set_layer_property(basic_map, 0, "opacity", "0.5")
        assert basic_map["layers"][0]["opacity"] == 0.5


# ── tileset_ops tests ────────────────────────────────────────────────

class TestTilesetOps:

    def test_list_tilesets_empty(self, basic_map):
        tilesets = tileset_ops.list_tilesets(basic_map)
        assert len(tilesets) == 0

    def test_add_tileset(self, basic_map):
        result = tileset_ops.add_tileset(
            basic_map, name="tiles", image="tiles.png",
            tile_width=32, tile_height=32,
            columns=10, image_width=320, image_height=320,
        )
        assert result["name"] == "tiles"
        assert result["firstgid"] == 1
        assert result["tilecount"] == 100  # 10 columns * 10 rows
        assert len(basic_map["tilesets"]) == 1

    def test_add_tileset_auto_firstgid(self, map_with_tileset):
        result = tileset_ops.add_tileset(
            map_with_tileset, name="tiles2", image="tiles2.png",
            tile_width=32, tile_height=32,
            columns=5, image_width=160, image_height=160,
        )
        # First tileset has 100 tiles starting at GID 1
        # So next should start at 101
        assert result["firstgid"] == 101

    def test_get_tileset_info(self, map_with_tileset):
        info = tileset_ops.get_tileset_info(map_with_tileset, 0)
        assert info["name"] == "test_tileset"
        assert info["firstgid"] == 1
        assert info["type"] == "inline"

    def test_find_tileset_for_gid(self, map_with_tileset):
        result = tileset_ops.find_tileset_for_gid(map_with_tileset, 5)
        assert result is not None
        assert result["tileset_index"] == 0
        assert result["local_id"] == 4  # 5 - 1

    def test_remove_tileset(self, map_with_tileset):
        result = tileset_ops.remove_tileset(map_with_tileset, 0)
        assert result["removed"] is True
        assert len(map_with_tileset["tilesets"]) == 0


# ── object_ops tests ────────────────────────────────────────────────

class TestObjectOps:

    def test_list_objects_empty(self, basic_map):
        objects = object_ops.list_objects(basic_map)
        assert len(objects) == 0

    def test_add_object_tile_coords(self, basic_map):
        result = object_ops.add_object(
            basic_map, name="Counter", obj_type="interact",
            tile_x=3, tile_y=2, tile_w=2, tile_h=1,
        )
        assert result["name"] == "Counter"
        assert result["type"] == "interact"
        assert result["tile_x"] == 3
        assert result["tile_y"] == 2
        assert result["x"] == 96.0   # 3 * 32
        assert result["y"] == 64.0   # 2 * 32
        assert result["width"] == 64.0   # 2 * 32
        assert result["height"] == 32.0  # 1 * 32

    def test_add_object_pixel_coords(self, basic_map):
        result = object_ops.add_object(
            basic_map, name="Item", x=100.0, y=200.0,
            width=50.0, height=50.0,
        )
        assert result["x"] == 100.0
        assert result["y"] == 200.0

    def test_remove_object(self, map_with_objects):
        objects_before = object_ops.list_objects(map_with_objects)
        first_id = objects_before[0]["id"]
        result = object_ops.remove_object(map_with_objects, first_id)
        assert result["removed"] is True
        objects_after = object_ops.list_objects(map_with_objects)
        assert len(objects_after) == len(objects_before) - 1

    def test_remove_object_not_found(self, basic_map):
        with pytest.raises(ValueError, match="not found"):
            object_ops.remove_object(basic_map, 999)

    def test_set_object_property(self, map_with_objects):
        objects = object_ops.list_objects(map_with_objects)
        obj_id = objects[0]["id"]
        result = object_ops.set_object_property(
            map_with_objects, obj_id, "action", "buy_food",
        )
        assert result["property"] == "action"
        assert result["value"] == "buy_food"

    def test_move_object(self, map_with_objects):
        objects = object_ops.list_objects(map_with_objects)
        obj_id = objects[0]["id"]
        result = object_ops.move_object(map_with_objects, obj_id, tile_x=7, tile_y=5)
        assert result["new_position"]["x"] == 224.0  # 7 * 32
        assert result["new_position"]["y"] == 160.0  # 5 * 32

    def test_add_object_no_object_layer(self):
        """Error when no object layer exists."""
        m = map_ops.create_map()
        # Remove object layer
        m["layers"] = [l for l in m["layers"] if l["type"] != "objectgroup"]
        with pytest.raises(RuntimeError, match="No object layer"):
            object_ops.add_object(m, name="Test")


# ── tile_ops tests ───────────────────────────────────────────────────

class TestTileOps:

    def test_get_tile_empty(self, basic_map):
        result = tile_ops.get_tile(basic_map, 0, 0, 0)
        assert result["tile_id"] == 0
        assert result["empty"] is True

    def test_set_tile(self, basic_map):
        result = tile_ops.set_tile(basic_map, 3, 2, 5, 0)
        assert result["old_tile_id"] == 0
        assert result["new_tile_id"] == 5
        # Verify it was set
        check = tile_ops.get_tile(basic_map, 3, 2, 0)
        assert check["tile_id"] == 5

    def test_set_tile_out_of_bounds(self, basic_map):
        with pytest.raises(ValueError, match="out of bounds"):
            tile_ops.set_tile(basic_map, 99, 99, 1, 0)

    def test_check_collision_empty(self, basic_map):
        result = tile_ops.check_collision(basic_map, 5, 5)
        assert result["blocked"] is False

    def test_check_collision_named_layer(self, basic_map):
        # Add a collision layer with tiles
        layer_ops.add_layer(basic_map, name="Collision", layer_type="tilelayer")
        collision_idx = len(basic_map["layers"]) - 1
        layer_ops.paint_tile(basic_map, collision_idx, 3, 3, 1)

        result = tile_ops.check_collision(basic_map, 3, 3)
        assert result["blocked"] is True
        assert len(result["reasons"]) > 0

    def test_check_collision_out_of_bounds(self, basic_map):
        result = tile_ops.check_collision(basic_map, -1, -1)
        assert result["blocked"] is True
        assert result["reason"] == "out_of_bounds"

    def test_get_tile_region(self, basic_map):
        # Set some tiles
        tile_ops.set_tile(basic_map, 0, 0, 1, 0)
        tile_ops.set_tile(basic_map, 1, 0, 2, 0)
        tile_ops.set_tile(basic_map, 0, 1, 3, 0)
        tile_ops.set_tile(basic_map, 1, 1, 4, 0)

        result = tile_ops.get_tile_region(basic_map, 0, 0, 1, 1, 0)
        assert result["width"] == 2
        assert result["height"] == 2
        assert result["tiles"] == [[1, 2], [3, 4]]

    def test_get_tile_at_all_layers(self, basic_map):
        layer_ops.add_layer(basic_map, name="Layer2", layer_type="tilelayer")
        tile_ops.set_tile(basic_map, 0, 0, 5, 0)
        tile_ops.set_tile(basic_map, 0, 0, 10, 2)  # layer index 2

        result = tile_ops.get_tile_at_all_layers(basic_map, 0, 0)
        assert len(result) == 2  # 2 tile layers
        assert result[0]["tile_id"] == 5
        assert result[1]["tile_id"] == 10


# ── export_ops tests ─────────────────────────────────────────────────

class TestExportOps:

    def test_to_json(self, basic_map, tmp_dir):
        out = os.path.join(tmp_dir, "test.json")
        result = export_ops.to_json(basic_map, out)
        assert result["format"] == "json"
        assert os.path.exists(result["output"])
        # Verify it's valid JSON
        with open(result["output"]) as f:
            data = json.load(f)
        assert data["width"] == 10
        assert data["height"] == 8

    def test_to_json_no_overwrite(self, basic_map, tmp_dir):
        out = os.path.join(tmp_dir, "test.json")
        export_ops.to_json(basic_map, out)
        with pytest.raises(FileExistsError):
            export_ops.to_json(basic_map, out)

    def test_to_convex(self, basic_map, tmp_dir):
        out = os.path.join(tmp_dir, "convex.json")
        result = export_ops.to_convex(
            basic_map, out,
            scene_name="test_scene",
            display_name="Test Scene",
        )
        assert result["format"] == "convex"
        assert result["scene_name"] == "test_scene"
        assert result["map_size"] == "10x8"

        # Verify structure
        with open(result["output"]) as f:
            data = json.load(f)
        assert data["name"] == "test_scene"
        assert data["displayName"] == "Test Scene"
        assert "mapData" in data
        assert "furniture" in data
        assert "spawnPoint" in data
        assert "exitPoint" in data
        assert data["mapData"]["mapwidth"] == 10
        assert data["mapData"]["mapheight"] == 8
        assert data["mapData"]["tiledim"] == 32

    def test_to_convex_special_objects(self, map_with_objects, tmp_dir):
        out = os.path.join(tmp_dir, "convex.json")
        result = export_ops.to_convex(
            map_with_objects, out,
            scene_name="shop", display_name="Shop",
        )
        with open(result["output"]) as f:
            data = json.load(f)

        # Spawn and exit should be extracted, not in furniture
        assert data["spawnPoint"]["x"] == 5
        assert data["spawnPoint"]["y"] == 6
        assert data["exitPoint"]["x"] == 5
        assert data["exitPoint"]["y"] == 7

        # Counter should be in furniture
        assert len(data["furniture"]) == 1
        assert data["furniture"][0]["name"] == "Counter"
        assert data["furniture"][0]["type"] == "interact"

    def test_to_convex_tile_id_conversion(self, basic_map, tmp_dir):
        """Verify tile IDs are converted from 1-based to 0-based."""
        # Set some tiles (Tiled uses 1-based, 0=empty)
        basic_map["layers"][0]["data"][0] = 1   # Tiled ID 1
        basic_map["layers"][0]["data"][1] = 5   # Tiled ID 5
        basic_map["layers"][0]["data"][2] = 0   # Empty

        out = os.path.join(tmp_dir, "convex.json")
        export_ops.to_convex(basic_map, out, scene_name="test", display_name="Test")

        with open(out) as f:
            data = json.load(f)

        bg = data["mapData"]["bgtiles"]
        # bgtiles is [layer][x][y] format
        # bg[0] = first bg layer, bg[0][x][y] = tile at (x,y)
        assert bg[0][0][0] == 0   # 1 - 1 = 0 (Convex 0-based)
        assert bg[0][1][0] == 4   # 5 - 1 = 4
        assert bg[0][2][0] == -1  # 0 -> -1 (empty)


# ── session tests ────────────────────────────────────────────────────

class TestSession:

    def test_session_set_and_get(self):
        sess = Session()
        m = map_ops.create_map(name="test")
        sess.set_map(m, "/tmp/test.json")
        assert sess.has_map()
        assert sess.get_map()["properties"]["name"] == "test"
        assert sess.map_path == "/tmp/test.json"

    def test_session_no_map_error(self):
        sess = Session()
        with pytest.raises(RuntimeError, match="No map loaded"):
            sess.get_map()

    def test_undo_redo(self):
        sess = Session()
        m = map_ops.create_map(name="test")
        sess.set_map(m)

        # Make a change
        sess.snapshot("fill ground")
        layer_ops.fill_layer(m, 0, 5)
        assert m["layers"][0]["data"][0] == 5

        # Undo
        desc = sess.undo()
        assert desc == "fill ground"
        assert sess.get_map()["layers"][0]["data"][0] == 0  # Restored

        # Redo
        sess.redo()
        assert sess.get_map()["layers"][0]["data"][0] == 5  # Re-applied

    def test_undo_empty(self):
        sess = Session()
        m = map_ops.create_map()
        sess.set_map(m)
        with pytest.raises(RuntimeError, match="Nothing to undo"):
            sess.undo()

    def test_session_status(self):
        sess = Session()
        m = map_ops.create_map(name="test", width=10, height=8)
        sess.set_map(m, "/tmp/test.json")
        status = sess.status()
        assert status["has_map"] is True
        assert status["map_name"] == "test"
        assert status["map_size"] == "10x8"
        assert status["modified"] is False

    def test_session_save(self, tmp_dir):
        sess = Session()
        m = map_ops.create_map(name="test")
        path = os.path.join(tmp_dir, "test.json")
        sess.set_map(m, path)
        sess.snapshot("change")
        saved = sess.save_session()
        assert saved == path
        assert os.path.exists(path)
        assert sess._modified is False

    def test_selected_layer(self):
        sess = Session()
        m = map_ops.create_map()
        sess.set_map(m)
        assert sess.selected_layer == 0
        sess.selected_layer = 1
        assert sess.selected_layer == 1
        with pytest.raises(IndexError):
            sess.selected_layer = 99
