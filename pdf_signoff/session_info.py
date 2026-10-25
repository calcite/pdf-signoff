"""Private, opt-in readiness-file handoff for a CLI review session."""

import json
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def publish_session_info(path: Path | None, url: str) -> Iterator[None]:
    """Publish complete mode-0600 JSON without replacing an existing destination."""
    if path is None:
        yield
        return

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    ) as staging:
        json.dump({"version": 1, "url": url}, staging)
        staging.write("\n")
        staging.flush()
        os.link(staging.name, path)
        try:
            yield
        finally:
            path.unlink(missing_ok=True)
