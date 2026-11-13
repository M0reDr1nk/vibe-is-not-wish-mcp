"""Validation utilities for SE-MCP."""

from pathlib import Path
from typing import Optional
import re

SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9_\-\.]+$")


def validate_project_name(name: str) -> Optional[str]:
    """Validate project name. Returns error message or None."""
    if not name or len(name) > 64:
        return "Project name must be 1-64 characters."
    if not SAFE_NAME_RE.match(name):
        return "Project name contains invalid characters."
    return None


def validate_layer_name(layer: str, valid_layers: list[str]) -> Optional[str]:
    if layer not in valid_layers:
        return f"Invalid layer '{layer}'. Valid: {', '.join(valid_layers)}"
    return None


def validate_baseline_version(version: str) -> Optional[str]:
    if not re.match(r"^v\d{3,}$", version):
        return "Baseline version must be 'vXXX' format (e.g., v001)."
    return None


def ensure_safe_path(root: Path, target: str) -> Path:
    """Prevent path traversal."""
    resolved = (root / target).resolve()
    if not str(resolved).startswith(str(root.resolve())):
        raise ValueError(f"Path traversal detected: {target}")
    return resolved
