from pathlib import Path

from backend.config import settings


def document_path(document):
    root = settings.media_root.resolve()
    path = (root / Path(document.storage_path)).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Invalid document storage path")
    return path
