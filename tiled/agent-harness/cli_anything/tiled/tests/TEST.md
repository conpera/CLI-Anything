# Test Plan — cli-anything-tiled

## Test Inventory Plan

- `test_core.py`: ~40 unit tests planned
- `test_full_e2e.py`: ~15 E2E tests planned

## Unit Test Plan

### map_ops.py (~8 tests)
- `test_create_map_default` — Create map with default dimensions
- `test_create_map_custom` — Create map with custom size/orientation
- `test_create_map_template` — Create map from template
- `test_create_map_invalid_template` — Error on unknown template
- `test_get_map_info` — Info returns correct counts
- `test_resize_map_grow` — Resize to larger dimensions
- `test_resize_map_shrink` — Resize to smaller dimensions (content clipped)
- `test_resize_map_anchors` — Anchor positions are correctly calculated

### layer_ops.py (~10 tests)
- `test_list_layers` — List returns correct layer info
- `test_add_tile_layer` — Add tile layer with empty data
- `test_add_object_layer` — Add object group layer
- `test_add_layer_at_position` — Insert at specific index
- `test_remove_layer` — Remove layer by index
- `test_remove_layer_out_of_range` — IndexError on invalid index
- `test_rename_layer` — Rename returns old and new names
- `test_fill_layer` — Fill sets all tiles to given ID
- `test_paint_tile` — Single tile paint at coordinates
- `test_paint_rect` — Rectangle fill with tile

### tileset_ops.py (~5 tests)
- `test_list_tilesets` — List empty and populated tilesets
- `test_add_tileset` — Add inline tileset
- `test_add_tileset_auto_firstgid` — Auto-calculated firstgid
- `test_get_tileset_info` — Query tileset details
- `test_find_tileset_for_gid` — GID lookup

### object_ops.py (~7 tests)
- `test_list_objects_empty` — Empty object list
- `test_add_object_tile_coords` — Add object with tile coordinates
- `test_add_object_pixel_coords` — Add object with pixel coordinates
- `test_remove_object` — Remove by ID
- `test_remove_object_not_found` — Error on invalid ID
- `test_set_object_property` — Set custom property
- `test_move_object` — Move to new position

### tile_ops.py (~5 tests)
- `test_get_tile` — Get tile at coordinates
- `test_set_tile` — Set tile value
- `test_check_collision_empty` — No collision on empty map
- `test_check_collision_blocked` — Collision on named collision layer
- `test_get_tile_region` — Region query returns 2D array

### export_ops.py (~3 tests)
- `test_to_json` — Export produces valid JSON
- `test_to_convex` — Export produces Convex-compatible structure
- `test_to_convex_special_objects` — Spawn/exit extracted correctly

### session.py (~5 tests)
- `test_session_set_and_get` — Set map and retrieve it
- `test_session_no_map_error` — Error when no map loaded
- `test_undo_redo` — Undo/redo restores previous state
- `test_undo_empty` — Error when nothing to undo
- `test_session_status` — Status reports correct state

## E2E Test Plan

### TMX Round-Trip (~3 tests)
- Create map -> write TMX -> read TMX -> verify identical data
- Create map with layers and objects -> TMX round-trip
- Ensure CSV encoding is valid

### JSON Round-Trip (~2 tests)
- Create map -> write JSON -> read JSON -> verify structure
- Full map with tilesets, layers, objects -> JSON round-trip

### Convex Export Workflow (~3 tests)
- Build shop room -> export to Convex -> verify structure
- Verify tile ID conversion (1-based to 0-based)
- Verify spawn/exit extraction from objects

### CLI Subprocess Tests (~5 tests)
- `test_cli_help` — --help exits successfully
- `test_cli_map_new_json` — Create map with JSON output
- `test_cli_full_workflow` — Create, edit, export workflow
- `test_cli_layer_operations` — Add, fill, list layers via CLI
- `test_cli_convex_export` — Full Convex export via CLI

### Realistic Workflows (~2 tests)
- **Shop interior build**: Create room, add tileset, fill ground, paint
  walls, add furniture objects, add spawn/exit, export to Convex
- **Map modification**: Open existing, resize, add layers, save

## Realistic Workflow Scenarios

### Workflow 1: Shop Interior Build
- **Simulates**: Building a shop room for AI Town
- **Operations**: map new -> tileset add -> layer fill -> layer paint-rect ->
  object add (counter, spawn, exit) -> export to-convex
- **Verified**: Convex JSON has correct dimensions, furniture count,
  spawn/exit points, tile data structure

### Workflow 2: Map Edit and Re-export
- **Simulates**: Iterative room editing
- **Operations**: map new -> save -> open -> resize -> layer add ->
  tile set -> undo -> save
- **Verified**: Map dimensions change, undo restores state, save persists

---

## Test Results

```
============================= test session starts ==============================
platform darwin -- Python 3.13.4, pytest-8.4.2, pluggy-1.6.0
collected 75 items

cli_anything/tiled/tests/test_core.py::TestMapOps::test_create_map_default PASSED
cli_anything/tiled/tests/test_core.py::TestMapOps::test_create_map_custom PASSED
cli_anything/tiled/tests/test_core.py::TestMapOps::test_create_map_template PASSED
cli_anything/tiled/tests/test_core.py::TestMapOps::test_create_map_invalid_template PASSED
cli_anything/tiled/tests/test_core.py::TestMapOps::test_create_map_invalid_dimensions PASSED
cli_anything/tiled/tests/test_core.py::TestMapOps::test_get_map_info PASSED
cli_anything/tiled/tests/test_core.py::TestMapOps::test_resize_map_grow PASSED
cli_anything/tiled/tests/test_core.py::TestMapOps::test_resize_map_shrink PASSED
cli_anything/tiled/tests/test_core.py::TestMapOps::test_resize_map_center_anchor PASSED
cli_anything/tiled/tests/test_core.py::TestMapOps::test_list_templates PASSED
cli_anything/tiled/tests/test_core.py::TestLayerOps::test_list_layers PASSED
cli_anything/tiled/tests/test_core.py::TestLayerOps::test_add_tile_layer PASSED
cli_anything/tiled/tests/test_core.py::TestLayerOps::test_add_object_layer PASSED
cli_anything/tiled/tests/test_core.py::TestLayerOps::test_add_layer_at_position PASSED
cli_anything/tiled/tests/test_core.py::TestLayerOps::test_remove_layer PASSED
cli_anything/tiled/tests/test_core.py::TestLayerOps::test_remove_layer_out_of_range PASSED
cli_anything/tiled/tests/test_core.py::TestLayerOps::test_rename_layer PASSED
cli_anything/tiled/tests/test_core.py::TestLayerOps::test_fill_layer PASSED
cli_anything/tiled/tests/test_core.py::TestLayerOps::test_paint_tile PASSED
cli_anything/tiled/tests/test_core.py::TestLayerOps::test_paint_rect PASSED
cli_anything/tiled/tests/test_core.py::TestLayerOps::test_get_layer_info PASSED
cli_anything/tiled/tests/test_core.py::TestLayerOps::test_set_layer_property_visible PASSED
cli_anything/tiled/tests/test_core.py::TestLayerOps::test_set_layer_property_opacity PASSED
cli_anything/tiled/tests/test_core.py::TestTilesetOps::test_list_tilesets_empty PASSED
cli_anything/tiled/tests/test_core.py::TestTilesetOps::test_add_tileset PASSED
cli_anything/tiled/tests/test_core.py::TestTilesetOps::test_add_tileset_auto_firstgid PASSED
cli_anything/tiled/tests/test_core.py::TestTilesetOps::test_get_tileset_info PASSED
cli_anything/tiled/tests/test_core.py::TestTilesetOps::test_find_tileset_for_gid PASSED
cli_anything/tiled/tests/test_core.py::TestTilesetOps::test_remove_tileset PASSED
cli_anything/tiled/tests/test_core.py::TestObjectOps::test_list_objects_empty PASSED
cli_anything/tiled/tests/test_core.py::TestObjectOps::test_add_object_tile_coords PASSED
cli_anything/tiled/tests/test_core.py::TestObjectOps::test_add_object_pixel_coords PASSED
cli_anything/tiled/tests/test_core.py::TestObjectOps::test_remove_object PASSED
cli_anything/tiled/tests/test_core.py::TestObjectOps::test_remove_object_not_found PASSED
cli_anything/tiled/tests/test_core.py::TestObjectOps::test_set_object_property PASSED
cli_anything/tiled/tests/test_core.py::TestObjectOps::test_move_object PASSED
cli_anything/tiled/tests/test_core.py::TestObjectOps::test_add_object_no_object_layer PASSED
cli_anything/tiled/tests/test_core.py::TestTileOps::test_get_tile_empty PASSED
cli_anything/tiled/tests/test_core.py::TestTileOps::test_set_tile PASSED
cli_anything/tiled/tests/test_core.py::TestTileOps::test_set_tile_out_of_bounds PASSED
cli_anything/tiled/tests/test_core.py::TestTileOps::test_check_collision_empty PASSED
cli_anything/tiled/tests/test_core.py::TestTileOps::test_check_collision_named_layer PASSED
cli_anything/tiled/tests/test_core.py::TestTileOps::test_check_collision_out_of_bounds PASSED
cli_anything/tiled/tests/test_core.py::TestTileOps::test_get_tile_region PASSED
cli_anything/tiled/tests/test_core.py::TestTileOps::test_get_tile_at_all_layers PASSED
cli_anything/tiled/tests/test_core.py::TestExportOps::test_to_json PASSED
cli_anything/tiled/tests/test_core.py::TestExportOps::test_to_json_no_overwrite PASSED
cli_anything/tiled/tests/test_core.py::TestExportOps::test_to_convex PASSED
cli_anything/tiled/tests/test_core.py::TestExportOps::test_to_convex_special_objects PASSED
cli_anything/tiled/tests/test_core.py::TestExportOps::test_to_convex_tile_id_conversion PASSED
cli_anything/tiled/tests/test_core.py::TestSession::test_session_set_and_get PASSED
cli_anything/tiled/tests/test_core.py::TestSession::test_session_no_map_error PASSED
cli_anything/tiled/tests/test_core.py::TestSession::test_undo_redo PASSED
cli_anything/tiled/tests/test_core.py::TestSession::test_undo_empty PASSED
cli_anything/tiled/tests/test_core.py::TestSession::test_session_status PASSED
cli_anything/tiled/tests/test_core.py::TestSession::test_session_save PASSED
cli_anything/tiled/tests/test_core.py::TestSession::test_selected_layer PASSED
cli_anything/tiled/tests/test_full_e2e.py::TestTMXRoundTrip::test_empty_map_tmx_roundtrip PASSED
cli_anything/tiled/tests/test_full_e2e.py::TestTMXRoundTrip::test_map_with_data_tmx_roundtrip PASSED
cli_anything/tiled/tests/test_full_e2e.py::TestTMXRoundTrip::test_csv_encoding_valid PASSED
cli_anything/tiled/tests/test_full_e2e.py::TestJSONRoundTrip::test_json_roundtrip PASSED
cli_anything/tiled/tests/test_full_e2e.py::TestJSONRoundTrip::test_full_map_json_roundtrip PASSED
cli_anything/tiled/tests/test_full_e2e.py::TestConvexExport::test_shop_room_convex_export PASSED
cli_anything/tiled/tests/test_full_e2e.py::TestConvexExport::test_convex_tile_id_conversion PASSED
cli_anything/tiled/tests/test_full_e2e.py::TestConvexExport::test_convex_layer_separation PASSED
cli_anything/tiled/tests/test_full_e2e.py::TestCLISubprocess::test_help PASSED
cli_anything/tiled/tests/test_full_e2e.py::TestCLISubprocess::test_map_new_json PASSED
cli_anything/tiled/tests/test_full_e2e.py::TestCLISubprocess::test_map_new_template PASSED
cli_anything/tiled/tests/test_full_e2e.py::TestCLISubprocess::test_layer_operations PASSED
cli_anything/tiled/tests/test_full_e2e.py::TestCLISubprocess::test_full_workflow PASSED
cli_anything/tiled/tests/test_full_e2e.py::TestCLISubprocess::test_convex_export_cli PASSED
cli_anything/tiled/tests/test_full_e2e.py::TestCLISubprocess::test_tile_operations_cli PASSED
cli_anything/tiled/tests/test_full_e2e.py::TestCLISubprocess::test_map_info_json PASSED
cli_anything/tiled/tests/test_full_e2e.py::TestRealisticWorkflows::test_shop_interior_build PASSED
cli_anything/tiled/tests/test_full_e2e.py::TestRealisticWorkflows::test_map_edit_and_reexport PASSED

============================== 75 passed in 1.26s ==============================
```

## Summary Statistics

- **Total tests**: 75
- **Passed**: 75 (100%)
- **Failed**: 0
- **Execution time**: 1.26s
- **Unit tests** (test_core.py): 57 passed
- **E2E tests** (test_full_e2e.py): 18 passed

## Coverage Notes

- All 7 core modules fully tested: map_ops, layer_ops, tileset_ops, object_ops, tile_ops, export_ops, session
- TMX and JSON round-trip tests verify file format correctness
- Convex export verified with tile ID conversion, layer separation, and special object extraction
- CLI subprocess tests invoke the real `cli-anything-tiled` command via `_resolve_cli`
- Realistic workflow tests simulate building a complete shop interior and iterative map editing
- PNG export (`to-png`) not tested as it requires Tiled to be installed; `export check` command verifies availability
