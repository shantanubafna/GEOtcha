"""Disease pack loader for pre-configured search and filtering profiles."""
from __future__ import annotations

import importlib.resources
import sys
from dataclasses import dataclass, field

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef]


@dataclass
class DiseasePack:
    """A pre-configured disease search profile."""

    name: str
    display_name: str
    description: str
    search_terms: list[str] = field(default_factory=list)
    relevance_keywords: list[str] = field(default_factory=list)
    expected_tissues: list[str] = field(default_factory=list)
    expected_treatments: list[str] = field(default_factory=list)


def _load_pack_toml(pack_name: str) -> dict:
    """Load a pack TOML file from package data."""
    filename = f"{pack_name}.toml"
    ref = importlib.resources.files("geotcha.data.packs").joinpath(filename)
    data = ref.read_bytes()
    return tomllib.loads(data.decode("utf-8"))


def load_pack(pack_name: str) -> DiseasePack:
    """Load a disease pack by name.

    Args:
        pack_name: Pack identifier (e.g., "ibd", "oncology").

    Raises:
        FileNotFoundError: If the pack TOML file doesn't exist.
    """
    try:
        data = _load_pack_toml(pack_name)
    except FileNotFoundError:
        available = list_packs()
        raise FileNotFoundError(
            f"Disease pack '{pack_name}' not found. "
            f"Available packs: {', '.join(available)}"
        )

    pack_info = data.get("pack", {})
    search = data.get("search", {})
    filters = data.get("filters", {})

    return DiseasePack(
        name=pack_info.get("name", pack_name),
        display_name=pack_info.get("display_name", pack_name),
        description=pack_info.get("description", ""),
        search_terms=search.get("terms", []),
        relevance_keywords=search.get("relevance_keywords", []),
        expected_tissues=filters.get("expected_tissues", []),
        expected_treatments=filters.get("expected_treatments", []),
    )


def list_packs() -> list[str]:
    """Return names of all available disease packs."""
    packs_dir = importlib.resources.files("geotcha.data.packs")
    names = []
    for item in packs_dir.iterdir():
        item_name = getattr(item, "name", str(item))
        if item_name.endswith(".toml"):
            names.append(item_name.removesuffix(".toml"))
    return sorted(names)
