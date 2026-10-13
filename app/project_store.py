"""Portable project persistence for Charlie MJ OCR Studio.

Projects are self-contained folders: a JSON manifest plus an ``images`` folder.
The format is deliberately dependency-free and tolerant of future fields.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from typing import Any

FORMAT_VERSION = 1


def _safe_name(name: str) -> str:
    base = os.path.basename(name or "image")
    stem, ext = os.path.splitext(base)
    keep = "".join(c if c.isalnum() or c in " ._-" else "_" for c in stem).strip(" .") or "image"
    return keep + (ext.lower() if ext else ".png")


def save_project(path: str, project: dict[str, Any], images: list[tuple[Any, str]] | None = None) -> str:
    """Save a project atomically and return the project directory.

    ``images`` is an optional list of ``(PIL.Image, original_name)`` pairs. Existing
    image files are preserved unless their names collide, in which case a suffix is used.
    """
    path = os.path.abspath(path)
    os.makedirs(path, exist_ok=True)
    image_dir = os.path.join(path, "images")
    os.makedirs(image_dir, exist_ok=True)
    manifest = dict(project)
    manifest["format_version"] = FORMAT_VERSION
    manifest.setdefault("name", os.path.basename(path))
    manifest.setdefault("images", [])

    if images:
        manifest["images"] = []
        used = set()
        for image, original_name in images:
            filename = _safe_name(original_name)
            stem, ext = os.path.splitext(filename)
            n = 2
            while filename.lower() in used or os.path.exists(os.path.join(image_dir, filename)):
                filename = f"{stem}_{n}{ext}"
                n += 1
            used.add(filename.lower())
            image.save(os.path.join(image_dir, filename))
            manifest["images"].append({"name": original_name, "file": os.path.join("images", filename)})

    fd, tmp = tempfile.mkstemp(prefix="project-", suffix=".json", dir=path, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, os.path.join(path, "project.json"))
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return path


def load_project(path: str) -> dict[str, Any]:
    """Load a project manifest and normalize paths relative to its directory."""
    path = os.path.abspath(path)
    manifest_path = os.path.join(path, "project.json") if os.path.isdir(path) else path
    root = os.path.dirname(manifest_path)
    with open(manifest_path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Invalid Charlie MJ project: manifest is not an object")
    data.setdefault("format_version", 1)
    data.setdefault("images", [])
    for item in data["images"]:
        if isinstance(item, dict) and item.get("file"):
            item["path"] = os.path.abspath(os.path.join(root, item["file"]))
    data["project_dir"] = root
    return data


def export_bundle(project: dict[str, Any], destination: str) -> str:
    """Copy a project folder to a destination directory for backup/sharing."""
    root = project.get("project_dir")
    if not root or not os.path.isdir(root):
        raise ValueError("Project has no valid project_dir")
    destination = os.path.abspath(destination)
    if os.path.exists(destination):
        shutil.rmtree(destination)
    shutil.copytree(root, destination)
    return destination
