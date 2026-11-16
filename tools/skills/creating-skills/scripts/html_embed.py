"""Helpers for embedding JSON safely in standalone HTML pages."""

import json
from typing import Any


def embed_json(data: Any) -> str:
    """Return ``data`` as JSON that cannot close a surrounding script tag."""
    return (
        json.dumps(data, ensure_ascii=False)
        .replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
