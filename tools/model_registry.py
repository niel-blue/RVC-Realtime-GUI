from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelEntry:
    name: str
    directory: Path
    model_path: Path
    index_path: Path | None


def discover_models(models_root: str | Path) -> list[ModelEntry]:
    """Discover one RVC model per direct child directory.

    A directory is listed when it contains at least one ``.pth`` file.
    When multiple files exist, names are sorted case-insensitively and the
    first file is selected.  An ``added_*.index`` file is preferred over
    other index files.
    """
    root = Path(models_root)
    if not root.is_dir():
        return []

    entries = []
    for directory in sorted(
        (path for path in root.iterdir() if path.is_dir()),
        key=lambda path: path.name.casefold(),
    ):
        model_files = sorted(
            directory.glob("*.pth"), key=lambda path: path.name.casefold()
        )
        if not model_files:
            continue

        index_files = sorted(
            directory.glob("*.index"),
            key=lambda path: (
                not path.name.casefold().startswith("added_"),
                path.name.casefold(),
            ),
        )
        entries.append(
            ModelEntry(
                name=directory.name,
                directory=directory.resolve(),
                model_path=model_files[0].resolve(),
                index_path=index_files[0].resolve() if index_files else None,
            )
        )
    return entries
