"""Tiled CLI - Session management with undo/redo.

Maintains map state, tracks modifications, and provides undo/redo
history for interactive editing sessions.
"""

import copy
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


def _locked_save_json(path, data, **dump_kwargs) -> None:
    """Atomically write JSON with exclusive file locking."""
    try:
        f = open(path, "r+")
    except FileNotFoundError:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        f = open(path, "w")
    with f:
        _locked = False
        try:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            _locked = True
        except (ImportError, OSError):
            pass
        try:
            f.seek(0)
            f.truncate()
            json.dump(data, f, **dump_kwargs)
            f.flush()
        finally:
            if _locked:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


class Session:
    """Manages map state with undo/redo history."""

    MAX_UNDO = 50

    def __init__(self):
        self.map_data: Optional[Dict[str, Any]] = None
        self.map_path: Optional[str] = None
        self._undo_stack: List[Dict[str, Any]] = []
        self._redo_stack: List[Dict[str, Any]] = []
        self._modified: bool = False
        self._selected_layer: int = 0

    def has_map(self) -> bool:
        """Check if a map is loaded."""
        return self.map_data is not None

    def get_map(self) -> Dict[str, Any]:
        """Get the current map data.

        Raises:
            RuntimeError: If no map is loaded.
        """
        if self.map_data is None:
            raise RuntimeError(
                "No map loaded. Use 'map new' or 'map open' first."
            )
        return self.map_data

    def set_map(self, map_data: Dict[str, Any], path: Optional[str] = None) -> None:
        """Set the current map and reset history.

        Args:
            map_data: Map dict.
            path: Optional file path.
        """
        self.map_data = map_data
        self.map_path = path
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._modified = False
        self._selected_layer = 0

    def snapshot(self, description: str = "") -> None:
        """Save current state to undo stack before a mutation.

        Args:
            description: Description of the operation about to happen.
        """
        if self.map_data is None:
            return

        state = {
            "map_data": copy.deepcopy(self.map_data),
            "description": description,
            "timestamp": datetime.now().isoformat(),
        }

        self._undo_stack.append(state)
        if len(self._undo_stack) > self.MAX_UNDO:
            self._undo_stack.pop(0)

        self._redo_stack.clear()
        self._modified = True

    def undo(self) -> str:
        """Undo the last operation.

        Returns:
            Description of undone action.

        Raises:
            RuntimeError: If nothing to undo.
        """
        if not self._undo_stack:
            raise RuntimeError("Nothing to undo.")
        if self.map_data is None:
            raise RuntimeError("No map loaded.")

        # Save current state to redo stack
        self._redo_stack.append({
            "map_data": copy.deepcopy(self.map_data),
            "description": "redo point",
            "timestamp": datetime.now().isoformat(),
        })

        # Restore previous state
        state = self._undo_stack.pop()
        self.map_data = state["map_data"]
        self._modified = True
        return state.get("description", "")

    def redo(self) -> str:
        """Redo the last undone operation.

        Returns:
            Description of redone action.

        Raises:
            RuntimeError: If nothing to redo.
        """
        if not self._redo_stack:
            raise RuntimeError("Nothing to redo.")
        if self.map_data is None:
            raise RuntimeError("No map loaded.")

        # Save current to undo stack
        self._undo_stack.append({
            "map_data": copy.deepcopy(self.map_data),
            "description": "undo point",
            "timestamp": datetime.now().isoformat(),
        })

        # Restore redo state
        state = self._redo_stack.pop()
        self.map_data = state["map_data"]
        self._modified = True
        return state.get("description", "")

    def status(self) -> Dict[str, Any]:
        """Get session status summary.

        Returns:
            Status dict.
        """
        map_name = "none"
        map_size = "N/A"
        layer_count = 0

        if self.map_data:
            map_name = self.map_data.get("properties", {}).get("name", "untitled")
            w = self.map_data.get("width", 0)
            h = self.map_data.get("height", 0)
            map_size = f"{w}x{h}"
            layer_count = len(self.map_data.get("layers", []))

        return {
            "has_map": self.map_data is not None,
            "map_path": self.map_path,
            "map_name": map_name,
            "map_size": map_size,
            "layer_count": layer_count,
            "selected_layer": self._selected_layer,
            "modified": self._modified,
            "undo_count": len(self._undo_stack),
            "redo_count": len(self._redo_stack),
        }

    def save_session(self, path: Optional[str] = None) -> str:
        """Save the map to disk.

        Args:
            path: Optional override path.

        Returns:
            Path where file was saved.
        """
        if self.map_data is None:
            raise RuntimeError("No map to save.")

        save_path = path or self.map_path
        if not save_path:
            raise ValueError("No save path specified.")

        self.map_data.setdefault("properties", {})["modified"] = datetime.now().isoformat()
        _locked_save_json(save_path, self.map_data, indent=2, default=str)

        self.map_path = save_path
        self._modified = False
        return save_path

    def list_history(self) -> List[Dict[str, str]]:
        """List undo history.

        Returns:
            List of history entry dicts (newest first).
        """
        result = []
        for i, state in enumerate(reversed(self._undo_stack)):
            result.append({
                "index": i,
                "description": state.get("description", ""),
                "timestamp": state.get("timestamp", ""),
            })
        return result

    @property
    def selected_layer(self) -> int:
        """Get the currently selected layer index."""
        return self._selected_layer

    @selected_layer.setter
    def selected_layer(self, index: int):
        """Set the selected layer index."""
        if self.map_data:
            layers = self.map_data.get("layers", [])
            if index < 0 or index >= len(layers):
                raise IndexError(
                    f"Layer index {index} out of range (0-{len(layers) - 1})"
                )
        self._selected_layer = index
