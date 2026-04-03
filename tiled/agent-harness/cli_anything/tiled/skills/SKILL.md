---
name: >-
  cli-anything-tiled
description: >-
  Command-line interface for Tiled Map Editor - A stateful CLI for 2D tilemap editing via direct TMX/JSON manipulation. Export to Convex scene format for AI Town integration. Designed for AI agents and automation.
---

# cli-anything-tiled

A stateful command-line interface for 2D tilemap editing, built on direct TMX/JSON file manipulation with the Tiled CLI backend for PNG rendering. Designed for AI agents creating room interiors for AI Town (Conpera Town).

## Installation

This CLI is installed as part of the cli-anything-tiled package:

```bash
pip install cli-anything-tiled
```

**Prerequisites:**
- Python 3.10+
- Tiled Map Editor (for PNG export): `brew install tiled` or https://www.mapeditor.org/

## Usage

### Basic Commands

```bash
# Show help
cli-anything-tiled --help

# Start interactive REPL mode
cli-anything-tiled

# Create a new map
cli-anything-tiled map new --template shop --name "my_shop" -o shop.json

# Run with JSON output (for agent consumption)
cli-anything-tiled --json --map shop.json map info
```

### REPL Mode

When invoked without a subcommand, the CLI enters an interactive REPL session:

```bash
cli-anything-tiled
# Enter commands interactively with tab-completion and history
```

## Command Groups

### Map

Map management commands.

| Command | Description |
|---------|-------------|
| `new` | Create a new empty map (with optional template) |
| `open` | Open an existing TMX or JSON map file |
| `info` | Show map information (size, layers, tilesets) |
| `resize` | Resize the map with anchor positioning |
| `save` | Save the current map |
| `export` | Export map to TMX or JSON |
| `templates` | List available map templates |

### Layer

Layer management commands.

| Command | Description |
|---------|-------------|
| `list` | List all layers with tile counts |
| `add` | Add a new tile layer or object group |
| `remove` | Remove a layer by index |
| `rename` | Rename a layer |
| `fill` | Fill entire layer with a single tile ID |
| `paint-tile` | Set a single tile at (x,y) |
| `paint-rect` | Fill a rectangular region with tiles |
| `info` | Show detailed layer information |
| `set` | Set layer property (visible, opacity, name) |

### Tileset

Tileset management commands.

| Command | Description |
|---------|-------------|
| `list` | List all tilesets with GID info |
| `add` | Add a tileset from an image file |
| `import` | Import a tileset from a .tsx file |
| `info` | Show tileset details (GID range, tile count) |
| `remove` | Remove a tileset by index |

### Object

Object/furniture management for map entities.

| Command | Description |
|---------|-------------|
| `list` | List all objects with tile coordinates |
| `add` | Add an object (furniture, spawn, exit, etc.) |
| `remove` | Remove an object by ID |
| `set-property` | Set a custom property on an object |
| `move` | Move an object to new coordinates |

### Tile

Individual tile query and manipulation.

| Command | Description |
|---------|-------------|
| `get` | Get tile info at (x,y) on a layer |
| `set` | Set a tile at (x,y) |
| `check-collision` | Check if position is blocked |
| `get-all` | Get tile data across all layers at (x,y) |
| `region` | Get tile data for a rectangular area |

### Export

Export to various formats.

| Command | Description |
|---------|-------------|
| `to-json` | Export to Tiled JSON format |
| `to-tmx` | Export to TMX (XML) format |
| `to-png` | Render to PNG via Tiled CLI |
| `to-convex` | Export to Convex scene format for AI Town |
| `check` | Check if Tiled CLI is available |

### Session

State management with undo/redo.

| Command | Description |
|---------|-------------|
| `status` | Show session status |
| `undo` | Undo the last operation |
| `redo` | Redo the last undone operation |
| `history` | Show undo history |
| `select-layer` | Set the active layer |

## Examples

### Create a Shop Room for AI Town

```bash
# Create map from template
cli-anything-tiled map new --template shop --name "bakery" -o bakery.json

# Add tileset
cli-anything-tiled --map bakery.json tileset add \
  --name "gentle-obj" --image "gentle-obj.png" \
  --tile-width 32 --tile-height 32

# Fill ground, add walls, place furniture
cli-anything-tiled --map bakery.json layer fill 0 1
cli-anything-tiled --map bakery.json object add --name "Counter" --type interact \
  --tile-x 3 --tile-y 2 --tile-w 2 --tile-h 1
cli-anything-tiled --map bakery.json object add --name "Spawn" --type spawn \
  --tile-x 5 --tile-y 6

# Export for AI Town
cli-anything-tiled --map bakery.json export to-convex bakery_scene.json \
  --scene-name "bakery" --display-name "Bakery" --overwrite
```

### Query Tile Data (for AI perception)

```bash
# Check what's at a position
cli-anything-tiled --json --map room.json tile get 3 2

# Check collision
cli-anything-tiled --json --map room.json tile check-collision 3 2

# Get full region
cli-anything-tiled --json --map room.json tile region --x1 0 --y1 0 --x2 9 --y2 7
```

## State Management

The CLI maintains session state with:

- **Undo/Redo**: Up to 50 levels of history
- **Map persistence**: Save/load map state as TMX or JSON
- **Selected layer tracking**: Track which layer is active

## Output Formats

All commands support dual output modes:

- **Human-readable** (default): Tables, colors, formatted text
- **Machine-readable** (`--json` flag): Structured JSON for agent consumption

```bash
# Human output
cli-anything-tiled --map room.json layer list

# JSON output for agents
cli-anything-tiled --json --map room.json layer list
```

## For AI Agents

When using this CLI programmatically:

1. **Always use `--json` flag** for parseable output
2. **Use `--map` flag** to specify the map file for each command
3. **Use tile coordinates** (--tile-x, --tile-y) instead of pixel coordinates
4. **Check collision** before placing objects
5. **Export to Convex** format for AI Town integration
6. **Object types**: spawn, exit, interact, blocked, counter, work, decor

## Convex Scene Format

The `to-convex` export produces JSON compatible with `scene:importFromEditor`:
- Tile layers split into background (bgtiles) and collision (objmap)
- Objects converted to furniture items with type, position, and action
- Spawn and exit points extracted from special objects
- Tile IDs converted from 1-based (Tiled) to 0-based (Convex), with -1 for empty

## Version

1.0.0
