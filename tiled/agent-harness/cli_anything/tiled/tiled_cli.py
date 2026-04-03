#!/usr/bin/env python3
"""Tiled CLI — A stateful command-line interface for 2D tilemap editing.

This CLI provides full tilemap editing capabilities by parsing and
manipulating TMX/JSON files directly, with Tiled CLI backend for PNG
rendering.

Usage:
    # One-shot commands
    cli-anything-tiled map new --width 10 --height 8 -o room.tmx
    cli-anything-tiled --map room.tmx layer list
    cli-anything-tiled --map room.tmx tile set 3 2 --id 5

    # Interactive REPL
    cli-anything-tiled
"""

import json
import os
import shlex
import sys
from typing import Optional

import click

from cli_anything.tiled.core.session import Session
from cli_anything.tiled.core import map_ops
from cli_anything.tiled.core import layer_ops
from cli_anything.tiled.core import tileset_ops
from cli_anything.tiled.core import object_ops
from cli_anything.tiled.core import tile_ops
from cli_anything.tiled.core import export_ops

# Global session state
_session: Optional[Session] = None
_json_output = False
_repl_mode = False


def get_session() -> Session:
    global _session
    if _session is None:
        _session = Session()
    return _session


def output(data, message: str = ""):
    """Output data in JSON or human-readable format."""
    if _json_output:
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        if message:
            click.echo(message)
        if isinstance(data, dict):
            _print_dict(data)
        elif isinstance(data, list):
            _print_list(data)
        else:
            click.echo(str(data))


def _print_dict(d: dict, indent: int = 0):
    prefix = "  " * indent
    for k, v in d.items():
        if isinstance(v, dict):
            click.echo(f"{prefix}{k}:")
            _print_dict(v, indent + 1)
        elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
            click.echo(f"{prefix}{k}:")
            _print_list(v, indent + 1)
        elif isinstance(v, list):
            click.echo(f"{prefix}{k}: {v}")
        else:
            click.echo(f"{prefix}{k}: {v}")


def _print_list(items: list, indent: int = 0):
    prefix = "  " * indent
    for i, item in enumerate(items):
        if isinstance(item, dict):
            click.echo(f"{prefix}[{i}]")
            _print_dict(item, indent + 1)
        else:
            click.echo(f"{prefix}- {item}")


def handle_error(func):
    """Decorator to catch and format errors consistently."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            if _json_output:
                click.echo(json.dumps({"error": str(e), "type": "file_not_found"}))
            else:
                click.echo(f"Error: {e}", err=True)
            if not _repl_mode:
                sys.exit(1)
        except FileExistsError as e:
            if _json_output:
                click.echo(json.dumps({"error": str(e), "type": "file_exists"}))
            else:
                click.echo(f"Error: {e}", err=True)
            if not _repl_mode:
                sys.exit(1)
        except (ValueError, IndexError, RuntimeError) as e:
            if _json_output:
                click.echo(json.dumps({"error": str(e), "type": type(e).__name__}))
            else:
                click.echo(f"Error: {e}", err=True)
            if not _repl_mode:
                sys.exit(1)
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


# ── Main CLI Group ──────────────────────────────────────────────

@click.group(invoke_without_command=True)
@click.option("--json", "use_json", is_flag=True, help="Output as JSON")
@click.option("--map", "map_path", type=str, default=None,
              help="Path to .tmx or .json map file")
@click.pass_context
def cli(ctx, use_json, map_path):
    """Tiled CLI — Stateful 2D tilemap editing from the command line.

    Run without a subcommand to enter interactive REPL mode.
    """
    global _json_output
    _json_output = use_json

    if map_path:
        sess = get_session()
        if not sess.has_map():
            m = map_ops.open_map(map_path)
            sess.set_map(m, map_path)

    if ctx.invoked_subcommand is None:
        ctx.invoke(repl, map_path=None)


@cli.result_callback()
def auto_save_on_cli(result, **kwargs):
    """Auto-save map after CLI commands when --map is specified."""
    if not _repl_mode:
        sess = get_session()
        if sess.has_map() and sess._modified and sess.map_path:
            from cli_anything.tiled.utils.tmx_parser import save_map
            save_map(sess.get_map(), sess.map_path)


# ── Map Commands ───────────────────────────────────────────────

@cli.group("map")
def map_group():
    """Map management commands."""
    pass


@map_group.command("new")
@click.option("--width", "-w", type=int, default=10, help="Map width in tiles")
@click.option("--height", "-h", type=int, default=8, help="Map height in tiles")
@click.option("--tile-width", type=int, default=32, help="Tile width in pixels")
@click.option("--tile-height", type=int, default=32, help="Tile height in pixels")
@click.option("--name", "-n", default="untitled", help="Map name")
@click.option("--orientation", type=click.Choice(["orthogonal", "isometric", "hexagonal"]),
              default="orthogonal")
@click.option("--template", "-t", type=str, default=None,
              help="Map template (room-small, room-medium, shop, house, etc.)")
@click.option("--output", "-o", "output_path", type=str, default=None, help="Save path (.tmx or .json)")
@handle_error
def map_new(width, height, tile_width, tile_height, name, orientation, template, output_path):
    """Create a new empty map."""
    m = map_ops.create_map(
        width=width, height=height,
        tile_width=tile_width, tile_height=tile_height,
        name=name, orientation=orientation, template=template,
    )
    sess = get_session()
    sess.set_map(m, output_path)
    if output_path:
        map_ops.save_map_to(m, output_path, overwrite=True)
    info = map_ops.get_map_info(m)
    output(info, f"Created map: {name}")


@map_group.command("open")
@click.argument("path")
@handle_error
def map_open(path):
    """Open an existing map file."""
    m = map_ops.open_map(path)
    sess = get_session()
    sess.set_map(m, path)
    info = map_ops.get_map_info(m)
    output(info, f"Opened: {path}")


@map_group.command("info")
@handle_error
def map_info():
    """Show map information."""
    sess = get_session()
    info = map_ops.get_map_info(sess.get_map())
    output(info)


@map_group.command("resize")
@click.option("--width", "-w", type=int, required=True, help="New width in tiles")
@click.option("--height", "-h", type=int, required=True, help="New height in tiles")
@click.option("--anchor", default="top-left",
              help="Anchor: center, top-left, top-right, bottom-left, bottom-right")
@handle_error
def map_resize(width, height, anchor):
    """Resize the map."""
    sess = get_session()
    sess.snapshot(f"Resize to {width}x{height}")
    result = map_ops.resize_map(sess.get_map(), width, height, anchor)
    output(result, f"Map resized to {width}x{height}")


@map_group.command("save")
@click.argument("path", required=False)
@click.option("--overwrite", is_flag=True, help="Overwrite existing file")
@handle_error
def map_save(path, overwrite):
    """Save the current map."""
    sess = get_session()
    if path:
        result = map_ops.save_map_to(sess.get_map(), path, overwrite=overwrite)
        sess.map_path = result["output"]
        sess._modified = False
        output(result, f"Saved to: {result['output']}")
    else:
        saved = sess.save_session()
        output({"saved": saved}, f"Saved to: {saved}")


@map_group.command("templates")
@handle_error
def map_templates():
    """List available map templates."""
    templates = map_ops.list_templates()
    output(templates, "Available templates:")


@map_group.command("export")
@click.argument("output_path")
@click.option("--format", "fmt", type=click.Choice(["tmx", "json"]),
              default=None, help="Output format (auto-detected from extension)")
@click.option("--overwrite", is_flag=True, help="Overwrite existing file")
@handle_error
def map_export(output_path, fmt, overwrite):
    """Export map to TMX or JSON."""
    sess = get_session()
    result = map_ops.save_map_to(sess.get_map(), output_path, overwrite=overwrite)
    output(result, f"Exported to: {result['output']}")


# ── Layer Commands ─────────────────────────────────────────────

@cli.group()
def layer():
    """Layer management commands."""
    pass


@layer.command("list")
@handle_error
def layer_list():
    """List all layers in the map."""
    sess = get_session()
    layers = layer_ops.list_layers(sess.get_map())
    output(layers, "Layers:")


@layer.command("add")
@click.option("--name", "-n", default="New Layer", help="Layer name")
@click.option("--type", "layer_type", type=click.Choice(["tilelayer", "objectgroup"]),
              default="tilelayer", help="Layer type")
@click.option("--position", "-p", type=int, default=None, help="Insert position")
@handle_error
def layer_add(name, layer_type, position):
    """Add a new layer."""
    sess = get_session()
    sess.snapshot(f"Add layer: {name}")
    result = layer_ops.add_layer(sess.get_map(), name=name, layer_type=layer_type, position=position)
    output(result, f"Added layer: {name}")


@layer.command("remove")
@click.argument("index", type=int)
@handle_error
def layer_remove(index):
    """Remove a layer by index."""
    sess = get_session()
    sess.snapshot(f"Remove layer {index}")
    result = layer_ops.remove_layer(sess.get_map(), index)
    output(result, f"Removed layer {index}")


@layer.command("rename")
@click.argument("index", type=int)
@click.argument("new_name")
@handle_error
def layer_rename(index, new_name):
    """Rename a layer."""
    sess = get_session()
    sess.snapshot(f"Rename layer {index}")
    result = layer_ops.rename_layer(sess.get_map(), index, new_name)
    output(result, f"Renamed layer {index} to '{new_name}'")


@layer.command("fill")
@click.argument("index", type=int)
@click.argument("tile_id", type=int)
@handle_error
def layer_fill(index, tile_id):
    """Fill a tile layer with a single tile ID."""
    sess = get_session()
    sess.snapshot(f"Fill layer {index} with tile {tile_id}")
    result = layer_ops.fill_layer(sess.get_map(), index, tile_id)
    output(result, f"Filled layer {index} with tile {tile_id}")


@layer.command("paint-tile")
@click.argument("index", type=int)
@click.option("--x", type=int, required=True, help="Tile X coordinate")
@click.option("--y", type=int, required=True, help="Tile Y coordinate")
@click.option("--id", "tile_id", type=int, required=True, help="Tile ID")
@handle_error
def layer_paint_tile(index, x, y, tile_id):
    """Paint a single tile at (x, y)."""
    sess = get_session()
    sess.snapshot(f"Paint tile at ({x},{y}) on layer {index}")
    result = layer_ops.paint_tile(sess.get_map(), index, x, y, tile_id)
    output(result, f"Painted tile at ({x},{y})")


@layer.command("paint-rect")
@click.argument("index", type=int)
@click.option("--x1", type=int, required=True)
@click.option("--y1", type=int, required=True)
@click.option("--x2", type=int, required=True)
@click.option("--y2", type=int, required=True)
@click.option("--id", "tile_id", type=int, required=True, help="Tile ID")
@handle_error
def layer_paint_rect(index, x1, y1, x2, y2, tile_id):
    """Fill a rectangular region with a tile."""
    sess = get_session()
    sess.snapshot(f"Paint rect ({x1},{y1})-({x2},{y2}) on layer {index}")
    result = layer_ops.paint_rect(sess.get_map(), index, x1, y1, x2, y2, tile_id)
    output(result, f"Painted rectangle ({x1},{y1})-({x2},{y2})")


@layer.command("info")
@click.argument("index", type=int)
@handle_error
def layer_info(index):
    """Show detailed layer information."""
    sess = get_session()
    info = layer_ops.get_layer(sess.get_map(), index)
    output(info)


@layer.command("set")
@click.argument("index", type=int)
@click.argument("prop")
@click.argument("value")
@handle_error
def layer_set(index, prop, value):
    """Set a layer property (visible, opacity, name)."""
    sess = get_session()
    sess.snapshot(f"Set layer {index} {prop}={value}")
    result = layer_ops.set_layer_property(sess.get_map(), index, prop, value)
    output(result, f"Set layer {index} {prop} = {value}")


# ── Tileset Commands ───────────────────────────────────────────

@cli.group()
def tileset():
    """Tileset management commands."""
    pass


@tileset.command("list")
@handle_error
def tileset_list():
    """List all tilesets."""
    sess = get_session()
    tilesets = tileset_ops.list_tilesets(sess.get_map())
    output(tilesets, "Tilesets:")


@tileset.command("add")
@click.option("--name", "-n", required=True, help="Tileset name")
@click.option("--image", "-i", required=True, help="Path to tileset image")
@click.option("--tile-width", type=int, default=32, help="Tile width")
@click.option("--tile-height", type=int, default=32, help="Tile height")
@click.option("--columns", type=int, default=None, help="Number of columns")
@click.option("--image-width", type=int, default=None, help="Image width in pixels")
@click.option("--image-height", type=int, default=None, help="Image height in pixels")
@handle_error
def tileset_add(name, image, tile_width, tile_height, columns, image_width, image_height):
    """Add a tileset from an image file."""
    sess = get_session()
    sess.snapshot(f"Add tileset: {name}")
    result = tileset_ops.add_tileset(
        sess.get_map(), name=name, image=image,
        tile_width=tile_width, tile_height=tile_height,
        columns=columns, image_width=image_width, image_height=image_height,
    )
    output(result, f"Added tileset: {name}")


@tileset.command("import")
@click.argument("tsx_path")
@handle_error
def tileset_import(tsx_path):
    """Import a tileset from a .tsx file."""
    sess = get_session()
    sess.snapshot(f"Import tileset: {tsx_path}")
    result = tileset_ops.import_tileset(sess.get_map(), tsx_path)
    output(result, f"Imported tileset from: {tsx_path}")


@tileset.command("info")
@click.argument("index", type=int)
@handle_error
def tileset_info(index):
    """Show tileset details."""
    sess = get_session()
    info = tileset_ops.get_tileset_info(sess.get_map(), index)
    output(info)


@tileset.command("remove")
@click.argument("index", type=int)
@handle_error
def tileset_remove(index):
    """Remove a tileset by index."""
    sess = get_session()
    sess.snapshot(f"Remove tileset {index}")
    result = tileset_ops.remove_tileset(sess.get_map(), index)
    output(result, f"Removed tileset {index}")


# ── Object Commands ────────────────────────────────────────────

@cli.group("object")
def object_group():
    """Object/furniture management commands."""
    pass


@object_group.command("list")
@click.option("--layer", "-l", "layer_index", type=int, default=None,
              help="Only show objects from this layer")
@handle_error
def object_list(layer_index):
    """List all objects in the map."""
    sess = get_session()
    objects = object_ops.list_objects(sess.get_map(), layer_index=layer_index)
    output(objects, "Objects:")


@object_group.command("add")
@click.option("--name", "-n", required=True, help="Object name")
@click.option("--type", "obj_type", default="", help="Object type (spawn, exit, interact, blocked)")
@click.option("--tile-x", type=int, default=None, help="Tile X coordinate")
@click.option("--tile-y", type=int, default=None, help="Tile Y coordinate")
@click.option("--x", type=float, default=None, help="Pixel X coordinate")
@click.option("--y", type=float, default=None, help="Pixel Y coordinate")
@click.option("--tile-w", type=int, default=1, help="Width in tiles")
@click.option("--tile-h", type=int, default=1, help="Height in tiles")
@click.option("--layer", "-l", "layer_index", type=int, default=None,
              help="Target object layer index")
@handle_error
def object_add(name, obj_type, tile_x, tile_y, x, y, tile_w, tile_h, layer_index):
    """Add a new object (furniture, spawn point, etc.)."""
    sess = get_session()
    sess.snapshot(f"Add object: {name}")
    result = object_ops.add_object(
        sess.get_map(), name=name, obj_type=obj_type,
        x=x, y=y, tile_x=tile_x, tile_y=tile_y,
        tile_w=tile_w, tile_h=tile_h, layer_index=layer_index,
    )
    output(result, f"Added object: {name}")


@object_group.command("remove")
@click.argument("obj_id", type=int)
@handle_error
def object_remove(obj_id):
    """Remove an object by ID."""
    sess = get_session()
    sess.snapshot(f"Remove object {obj_id}")
    result = object_ops.remove_object(sess.get_map(), obj_id)
    output(result, f"Removed object {obj_id}")


@object_group.command("set-property")
@click.argument("obj_id", type=int)
@click.argument("prop_name")
@click.argument("prop_value")
@click.option("--type", "prop_type", type=click.Choice(["string", "int", "float", "bool"]),
              default="string", help="Property type")
@handle_error
def object_set_property(obj_id, prop_name, prop_value, prop_type):
    """Set a custom property on an object."""
    sess = get_session()
    sess.snapshot(f"Set property on object {obj_id}")
    result = object_ops.set_object_property(
        sess.get_map(), obj_id, prop_name, prop_value, prop_type,
    )
    output(result, f"Set {prop_name}={prop_value} on object {obj_id}")


@object_group.command("move")
@click.argument("obj_id", type=int)
@click.option("--tile-x", type=int, default=None, help="New tile X")
@click.option("--tile-y", type=int, default=None, help="New tile Y")
@click.option("--x", type=float, default=None, help="New pixel X")
@click.option("--y", type=float, default=None, help="New pixel Y")
@handle_error
def object_move(obj_id, tile_x, tile_y, x, y):
    """Move an object to a new position."""
    sess = get_session()
    sess.snapshot(f"Move object {obj_id}")
    result = object_ops.move_object(
        sess.get_map(), obj_id, x=x, y=y, tile_x=tile_x, tile_y=tile_y,
    )
    output(result, f"Moved object {obj_id}")


# ── Tile Commands ──────────────────────────────────────────────

@cli.group()
def tile():
    """Individual tile operations."""
    pass


@tile.command("get")
@click.argument("x", type=int)
@click.argument("y", type=int)
@click.option("--layer", "-l", "layer_index", type=int, default=0, help="Layer index")
@handle_error
def tile_get(x, y, layer_index):
    """Get tile info at (x, y)."""
    sess = get_session()
    info = tile_ops.get_tile(sess.get_map(), x, y, layer_index)
    output(info)


@tile.command("set")
@click.argument("x", type=int)
@click.argument("y", type=int)
@click.option("--id", "tile_id", type=int, required=True, help="Tile ID")
@click.option("--layer", "-l", "layer_index", type=int, default=0, help="Layer index")
@handle_error
def tile_set(x, y, tile_id, layer_index):
    """Set a tile at (x, y)."""
    sess = get_session()
    sess.snapshot(f"Set tile at ({x},{y})")
    result = tile_ops.set_tile(sess.get_map(), x, y, tile_id, layer_index)
    output(result, f"Set tile at ({x},{y}) = {tile_id}")


@tile.command("check-collision")
@click.argument("x", type=int)
@click.argument("y", type=int)
@handle_error
def tile_check_collision(x, y):
    """Check if a tile position is blocked/has collision."""
    sess = get_session()
    result = tile_ops.check_collision(sess.get_map(), x, y)
    output(result)


@tile.command("get-all")
@click.argument("x", type=int)
@click.argument("y", type=int)
@handle_error
def tile_get_all(x, y):
    """Get tile data at (x, y) across all tile layers."""
    sess = get_session()
    result = tile_ops.get_tile_at_all_layers(sess.get_map(), x, y)
    output(result)


@tile.command("region")
@click.option("--x1", type=int, required=True)
@click.option("--y1", type=int, required=True)
@click.option("--x2", type=int, required=True)
@click.option("--y2", type=int, required=True)
@click.option("--layer", "-l", "layer_index", type=int, default=0, help="Layer index")
@handle_error
def tile_region(x1, y1, x2, y2, layer_index):
    """Get tile data for a rectangular region."""
    sess = get_session()
    result = tile_ops.get_tile_region(sess.get_map(), x1, y1, x2, y2, layer_index)
    output(result)


# ── Export Commands ────────────────────────────────────────────

@cli.group("export")
def export_group():
    """Export commands."""
    pass


@export_group.command("to-json")
@click.argument("output_path")
@click.option("--overwrite", is_flag=True, help="Overwrite existing file")
@handle_error
def export_to_json(output_path, overwrite):
    """Export map to Tiled JSON format."""
    sess = get_session()
    result = export_ops.to_json(sess.get_map(), output_path, overwrite=overwrite)
    output(result, f"Exported to: {result['output']}")


@export_group.command("to-tmx")
@click.argument("output_path")
@click.option("--overwrite", is_flag=True, help="Overwrite existing file")
@handle_error
def export_to_tmx(output_path, overwrite):
    """Export map to TMX format."""
    sess = get_session()
    result = export_ops.to_tmx(sess.get_map(), output_path, overwrite=overwrite)
    output(result, f"Exported to: {result['output']}")


@export_group.command("to-png")
@click.argument("output_path")
@click.option("--overwrite", is_flag=True, help="Overwrite existing file")
@handle_error
def export_to_png(output_path, overwrite):
    """Export map to PNG using Tiled CLI backend."""
    sess = get_session()
    result = export_ops.to_png(sess.get_map(), output_path, overwrite=overwrite)
    output(result, f"Exported to: {result['output']}")


@export_group.command("to-convex")
@click.argument("output_path")
@click.option("--scene-name", "-s", default="scene", help="Scene identifier")
@click.option("--display-name", "-d", default="Scene", help="Human-readable name")
@click.option("--tileset-path", default="/ai-town/assets/gentle-obj.png",
              help="Web-accessible tileset path")
@click.option("--overwrite", is_flag=True, help="Overwrite existing file")
@handle_error
def export_to_convex(output_path, scene_name, display_name, tileset_path, overwrite):
    """Export map to Convex scene format for AI Town.

    Generates JSON matching the scene:importFromEditor mutation format.
    """
    sess = get_session()
    result = export_ops.to_convex(
        sess.get_map(), output_path,
        scene_name=scene_name, display_name=display_name,
        tileset_web_path=tileset_path, overwrite=overwrite,
    )
    output(result, f"Exported to Convex format: {result['output']}")


@export_group.command("check")
@handle_error
def export_check():
    """Check if Tiled CLI is available for PNG export."""
    available = export_ops.is_tiled_available()
    if available:
        path = export_ops.find_tiled_cli()
        result = {"available": True, "path": path}
        output(result, f"Tiled CLI found: {path}")
    else:
        result = {"available": False}
        output(result, "Tiled CLI not found. PNG export unavailable.")


# ── Session Commands ───────────────────────────────────────────

@cli.group()
def session():
    """Session management commands."""
    pass


@session.command("status")
@handle_error
def session_status():
    """Show session status."""
    sess = get_session()
    output(sess.status())


@session.command("undo")
@handle_error
def session_undo():
    """Undo the last operation."""
    sess = get_session()
    desc = sess.undo()
    output({"undone": desc}, f"Undone: {desc}")


@session.command("redo")
@handle_error
def session_redo():
    """Redo the last undone operation."""
    sess = get_session()
    desc = sess.redo()
    output({"redone": desc}, f"Redone: {desc}")


@session.command("history")
@handle_error
def session_history():
    """Show undo history."""
    sess = get_session()
    history = sess.list_history()
    output(history, "Undo history:")


@session.command("select-layer")
@click.argument("index", type=int)
@handle_error
def session_select_layer(index):
    """Set the active/selected layer."""
    sess = get_session()
    sess.selected_layer = index
    output({"selected_layer": index}, f"Selected layer {index}")


# ── REPL ───────────────────────────────────────────────────────

@cli.command()
@click.option("--map", "map_path", type=str, default=None)
@handle_error
def repl(map_path):
    """Start interactive REPL session."""
    from cli_anything.tiled.utils.repl_skin import ReplSkin

    global _repl_mode
    _repl_mode = True

    skin = ReplSkin("tiled", version="1.0.0")

    if map_path:
        sess = get_session()
        m = map_ops.open_map(map_path)
        sess.set_map(m, map_path)

    skin.print_banner()

    pt_session = skin.create_prompt_session()

    _repl_commands = {
        "map":      "new|open|info|resize|save|export|templates",
        "layer":    "list|add|remove|rename|fill|paint-tile|paint-rect|info|set",
        "tileset":  "list|add|import|info|remove",
        "object":   "list|add|remove|set-property|move",
        "tile":     "get|set|check-collision|get-all|region",
        "export":   "to-json|to-tmx|to-png|to-convex|check",
        "session":  "status|undo|redo|history|select-layer",
        "help":     "Show this help",
        "quit":     "Exit REPL",
    }

    while True:
        try:
            # Determine map name for prompt
            try:
                sess = get_session()
                map_name = ""
                if sess.has_map():
                    m = sess.get_map()
                    map_name = m.get("properties", {}).get("name", "")
                    if not map_name and sess.map_path:
                        map_name = os.path.basename(sess.map_path)
            except Exception:
                map_name = ""

            modified = sess._modified if sess.has_map() else False
            line = skin.get_input(pt_session, project_name=map_name, modified=modified)

            if not line:
                continue
            if line.lower() in ("quit", "exit", "q"):
                skin.print_goodbye()
                break
            if line.lower() == "help":
                skin.help(_repl_commands)
                continue

            # Parse and execute
            try:
                args = shlex.split(line)
            except ValueError:
                args = line.split()

            try:
                cli.main(args, standalone_mode=False)
            except SystemExit:
                pass
            except click.exceptions.UsageError as e:
                skin.warning(f"Usage error: {e}")
            except Exception as e:
                skin.error(f"{e}")

        except (EOFError, KeyboardInterrupt):
            skin.print_goodbye()
            break

    _repl_mode = False


# ── Entry Point ────────────────────────────────────────────────

def main():
    cli()


if __name__ == "__main__":
    main()
