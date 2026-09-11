from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any

from .canonical import dump_yaml, parse_yaml
from .models import OwnerMode, ResourceDocument, ResourceKey

SAFE_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

REGISTRY_PLURAL: dict[str, str] = {
    "area": "areas",
    "floor": "floors",
    "label": "labels",
    "device": "devices",
    "entity": "entities",
}

REGISTRY_SINGULAR: dict[str, str] = {v: k for k, v in REGISTRY_PLURAL.items()} | {
    "entitys": "entity",
}


def validate_key(key: str) -> None:
    """Validate that a resource key is safe for filesystem paths."""
    if not SAFE_KEY_PATTERN.match(key):
        raise ValueError(
            f"Resource key '{key}' contains invalid characters (must match [a-zA-Z0-9_-]+)"
        )


def get_source_path(repo_root: Path, kind: str, key: str) -> Path:
    """Determine the authoritative filesystem path for a resource."""
    validate_key(key)
    base = repo_root / "home-assistant"

    if kind == "core" and key == "configuration":
        return base / "core" / "configuration.yaml"
    if kind == "automation":
        return base / "automations" / f"{key}.yaml"
    if kind == "script":
        return base / "scripts" / f"{key}.yaml"
    if kind == "scene":
        return base / "scenes" / f"{key}.yaml"
    if kind == "dashboard":
        return base / "dashboards" / f"{key}.yaml"
    if kind == "registry":
        return base / "registries" / f"{key}.yaml"
    if kind in REGISTRY_PLURAL:
        return base / "registries" / f"{REGISTRY_PLURAL[kind]}.yaml"
    if kind == "helper":
        return base / "helpers" / f"{key}.yaml"
    if kind == "integration":
        return base / "integrations" / f"{key}.yaml"

    return base / f"{kind}s" / f"{key}.yaml"


def load_source_tree(repo_root: Path) -> dict[str, ResourceDocument]:
    """Discover and parse all desired-configuration documents from the Git source tree."""
    base = repo_root / "home-assistant"
    if not base.is_dir():
        return {}

    resources: dict[str, ResourceDocument] = {}

    def _add_doc(
        kind: str, key: str, data: Any, file_path: Path, owner_mode: str
    ) -> None:
        rk = ResourceKey(kind, key)
        rk_str = str(rk)
        if rk_str in resources:
            raise ValueError(
                f"Duplicate resource found in source: {rk_str} (file: {file_path})"
            )
        resources[rk_str] = ResourceDocument(
            kind=kind,
            key=key,
            desired=data,
            owner_mode=owner_mode,
            metadata={"file_path": str(file_path.relative_to(repo_root))},
        )

    # Core configuration
    core_file = base / "core" / "configuration.yaml"
    if core_file.is_file():
        content = parse_yaml(core_file.read_text(encoding="utf-8"))
        _add_doc("core", "configuration", content, core_file, OwnerMode.GIT_OWNED.value)

    # Directories with <key>.yaml
    dir_mappings: tuple[tuple[str, str, str], ...] = (
        ("automations", "automation", OwnerMode.UI_EDITABLE.value),
        ("scripts", "script", OwnerMode.UI_EDITABLE.value),
        ("scenes", "scene", OwnerMode.UI_EDITABLE.value),
        ("dashboards", "dashboard", OwnerMode.UI_EDITABLE.value),
        ("helpers", "helper", OwnerMode.UI_EDITABLE.value),
        ("integrations", "integration", OwnerMode.OBSERVE_ONLY.value),
    )

    for dir_name, kind, mode in dir_mappings:
        target_dir = base / dir_name
        if target_dir.is_dir():
            for f in sorted(target_dir.glob("*.yaml")):
                key = f.stem
                if not SAFE_KEY_PATTERN.match(key):
                    continue
                content = parse_yaml(f.read_text(encoding="utf-8"))
                _add_doc(kind, key, content, f, mode)

    # Registries: areas, floors, labels, devices, entities
    reg_dir = base / "registries"
    if reg_dir.is_dir():
        for reg_file in sorted(reg_dir.glob("*.yaml")):
            stem = reg_file.stem
            singular = REGISTRY_SINGULAR.get(stem)
            if singular is None:
                singular = stem.rstrip("s") if stem.endswith("s") else stem
            content = parse_yaml(reg_file.read_text(encoding="utf-8"))
            if isinstance(content, list):
                # We store each list item or the whole registry
                _add_doc(
                    singular,
                    "collection",
                    content,
                    reg_file,
                    OwnerMode.UI_EDITABLE.value,
                )
            elif isinstance(content, dict):
                _add_doc(
                    singular,
                    "collection",
                    content,
                    reg_file,
                    OwnerMode.UI_EDITABLE.value,
                )

    return resources


def write_resource_atomic(repo_root: Path, doc: ResourceDocument) -> Path:
    """Atomically write a single resource document to its source path."""
    dest_path = get_source_path(repo_root, doc.kind, doc.key)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    yaml_text = dump_yaml(doc.desired)

    # Write via temporary file in same directory for atomic rename
    temp_file = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=dest_path.parent,
        prefix=f".{dest_path.name}.",
        delete=False,
    )
    temp_path = Path(temp_file.name)
    try:
        temp_file.write(yaml_text)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        temp_file.close()
        os.replace(temp_path, dest_path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise

    return dest_path


def adopt_resources(
    repo_root: Path,
    docs: list[ResourceDocument],
    selected_keys: set[str] | None = None,
) -> list[Path]:
    """Adopt selected live definitions into local Git source files with rollback safety."""
    docs_to_adopt = [
        d
        for d in docs
        if selected_keys is None
        or str(d.resource_key) in selected_keys
        or d.key in selected_keys
    ]

    if not docs_to_adopt:
        return []

    # Preflight check: validate keys and target paths
    targets: list[tuple[ResourceDocument, Path]] = []
    for doc in docs_to_adopt:
        path = get_source_path(repo_root, doc.kind, doc.key)
        targets.append((doc, path))

    # Backup existing files for atomic rollback
    backups: dict[Path, str | None] = {}
    for _, path in targets:
        if path.is_file():
            backups[path] = path.read_text(encoding="utf-8")
        else:
            backups[path] = None

    written: list[Path] = []
    try:
        for doc, _ in targets:
            written_path = write_resource_atomic(repo_root, doc)
            written.append(written_path)
    except Exception as exc:
        # Rollback on any failure
        for path, original in backups.items():
            if original is None:
                if path.exists():
                    path.unlink()
            else:
                path.write_text(original, encoding="utf-8")
        raise RuntimeError(
            f"Adoption failed during write, rolled back changes: {exc}"
        ) from exc

    return written


def remove_resource(repo_root: Path, kind: str, key: str) -> bool:
    """Remove a source resource file if it exists."""
    path = get_source_path(repo_root, kind, key)
    if path.is_file():
        path.unlink()
        return True
    return False
