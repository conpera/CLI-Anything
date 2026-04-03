# Tiled Map Editor — CLI Harness Architecture Analysis

## Software Overview

**Tiled** is a free, open-source 2D tilemap editor used for game development.
It supports orthogonal, isometric, and hexagonal maps with multiple tile layers,
object layers, and tileset management.

- **Homepage:** https://www.mapeditor.org/
- **Repository:** https://github.com/mapeditor/tiled
- **Installed at:** `/Applications/Tiled.app` (macOS) or `/opt/homebrew/bin/tiled`
- **License:** GPL-2.0

## Backend Engine

Tiled's native format is **TMX** (Tile Map XML) for maps and **TSX** (Tile Set XML)
for tilesets. It also supports JSON export. The data model is straightforward XML
that can be parsed and manipulated with Python's `xml.etree.ElementTree`.

### Key Formats

- **TMX** — XML-based map format with layers, tilesets, and objects
- **TSX** — XML-based tileset format (external tileset references)
- **JSON** — Tiled's JSON export format (equivalent to TMX but in JSON)
- **PNG** — Rendered map image (via Tiled CLI `--export-map`)

## GUI-to-CLI Mapping

| GUI Action | CLI Equivalent | Backend |
|------------|---------------|---------|
| File > New Map | `map new` | Generate TMX XML |
| File > Open | `map open` | Parse TMX/JSON |
| File > Save As | `map export` | Write TMX/JSON |
| File > Export As Image | `export to-png` | `tiled --export-map` |
| Map > Map Properties | `map info` | Parse TMX attributes |
| Map > Resize Map | `map resize` | Modify TMX width/height + layer data |
| Layer > New Tile Layer | `layer add` | Add `<layer>` element to TMX |
| Layer > Remove Layer | `layer remove` | Remove `<layer>` element |
| Layer > Rename Layer | `layer rename` | Modify layer `name` attribute |
| Tileset > Add Tileset | `tileset add` | Add `<tileset>` element |
| Objects > Insert Object | `object add` | Add `<object>` to objectgroup |
| Edit > Set Tile | `tile set` | Modify layer data array |
| Edit > Fill Region | `layer fill` | Fill layer data with tile ID |

## Data Model

### TMX Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<map version="1.10" tiledversion="1.11.0"
     orientation="orthogonal" renderorder="right-down"
     width="10" height="8" tilewidth="32" tileheight="32">

  <tileset firstgid="1" source="tileset.tsx"/>

  <layer id="1" name="Ground" width="10" height="8">
    <data encoding="csv">
      1,1,1,1,1,1,1,1,1,1,
      ...
    </data>
  </layer>

  <objectgroup id="3" name="Objects">
    <object id="1" name="Spawn" type="spawn" x="160" y="224" width="32" height="32"/>
    <object id="2" name="Counter" type="interact" x="96" y="64" width="64" height="32">
      <properties>
        <property name="action" value="buy_food"/>
      </properties>
    </object>
  </objectgroup>
</map>
```

### Tiled JSON Structure

```json
{
  "width": 10, "height": 8,
  "tilewidth": 32, "tileheight": 32,
  "orientation": "orthogonal",
  "layers": [
    { "type": "tilelayer", "name": "Ground", "data": [1,1,...], "width": 10, "height": 8 },
    { "type": "objectgroup", "name": "Objects", "objects": [...] }
  ],
  "tilesets": [
    { "firstgid": 1, "source": "tileset.tsx" }
  ]
}
```

## CLI Design

### Interaction Model

- **Subcommand CLI** for one-shot operations (scripting, agent pipelines)
- **Stateful REPL** for interactive sessions
- Both modes supported, REPL is default (invoke_without_command=True)

### Command Groups

1. `map` — Map CRUD: new, open, info, resize, export
2. `layer` — Layer management: list, add, remove, rename, fill, paint-tile
3. `tileset` — Tileset management: list, add, import, info
4. `object` — Object/furniture: list, add, remove, set-property
5. `tile` — Individual tile ops: get, set, check-collision
6. `export` — Export pipeline: to-json, to-png, to-convex
7. `session` — State management: status, undo, redo, history

### Backend Strategy

1. **Parse/manipulate TMX/JSON directly** using `xml.etree.ElementTree` and `json`
2. **Use Tiled CLI** (`tiled --export-map`) for PNG rendering
3. **Generate Convex-compatible JSON** for AI Town scene import

## Use Case: AI Town (Conpera Town)

The primary use case is AI agents creating/editing room interiors:
- Create a new room map (e.g., 10x8 tiles for a shop interior)
- Add tile layers (ground, walls, furniture)
- Place objects (spawn points, exits, interactive furniture)
- Export to Convex format for import into AI Town's scene system

The `to-convex` export command outputs JSON matching the `scene:importFromEditor`
mutation format used by the AI Town codebase.
