"""Document-level operations for layer files."""

from __future__ import annotations

from pathlib import Path
from typing import Any


from .project import Project


class DocumentStore:
    """Helper for CRUD on layer documents."""

    def __init__(self, project: Project):
        self.project = project

    def list_layer_files(self, layer: str) -> list[Path]:
        """List all markdown files in a layer (excluding .baseline)."""
        layer_dir = self.project.get_layer_dir(layer)
        if not layer_dir.exists():
            return []
        return sorted(
            [p for p in layer_dir.iterdir() if p.suffix == ".md"]
        )

    def list_subdirs(self, layer: str) -> list[Path]:
        layer_dir = self.project.get_layer_dir(layer)
        if not layer_dir.exists():
            return []
        return sorted(
            [p for p in layer_dir.iterdir() if p.is_dir() and p.name != ".baseline"]
        )

    def read(self, layer: str, filename: str) -> dict[str, Any]:
        return self.project.read_document(layer, filename)

    def write(self, layer: str, filename: str, content: str, **metadata: Any) -> Path:
        return self.project.write_document(layer, filename, content, **metadata)

    def exists(self, layer: str, filename: str) -> bool:
        return (self.project.get_layer_dir(layer) / filename).exists()
