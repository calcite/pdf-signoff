"""Output path resolution and atomic file commit boundary."""

import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

DEFAULT_OUTPUT_SUFFIX = "_signed"

Result = TypeVar("Result")


class OutputError(Exception):
    """Base class for safe-output failures."""


class OutputPathError(OutputError):
    """Raised when input and output paths cannot be safely distinguished."""


class OutputExistsError(OutputError):
    """Raised when a destination exists without overwrite permission."""


def resolve_output_path(
    input_path: Path,
    *,
    explicit_output: Path | None = None,
    output_suffix: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Select and validate a deterministic output path.

    An explicit path takes precedence over the configured suffix. Passing no
    suffix uses the built-in ``_signed`` default.
    """
    if explicit_output is not None:
        output_path = explicit_output
    else:
        suffix = DEFAULT_OUTPUT_SUFFIX if output_suffix is None else output_suffix
        output_path = input_path.with_name(
            f"{input_path.stem}{suffix}{input_path.suffix}"
        )

    if _paths_refer_to_same_file(input_path, output_path):
        raise OutputPathError("Input and output must resolve to different files.")
    if _path_exists(output_path) and not overwrite:
        raise OutputExistsError(
            f"Output already exists; use --overwrite to replace it: {output_path}"
        )
    return output_path


def write_output_atomically(
    output_path: Path,
    writer: Callable[[Path], Result],
    *,
    overwrite: bool = False,
) -> Result:
    """Write through a same-directory temporary path and atomically publish it.

    The writer may perform one or more output stages against the provided path.
    Its return value is returned only after the completed file is committed.
    """
    if _path_exists(output_path) and not overwrite:
        raise OutputExistsError(
            f"Output already exists; use --overwrite to replace it: {output_path}"
        )

    descriptor, temporary_name = tempfile.mkstemp(
        dir=output_path.parent,
        prefix=f".{output_path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    os.close(descriptor)

    try:
        result = writer(temporary_path)
        if overwrite:
            os.replace(temporary_path, output_path)
        else:
            try:
                os.link(temporary_path, output_path)
            except FileExistsError as exc:
                raise OutputExistsError(
                    f"Output was created while writing and was not replaced: "
                    f"{output_path}"
                ) from exc
            temporary_path.unlink()
        return result
    finally:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass


def _paths_refer_to_same_file(input_path: Path, output_path: Path) -> bool:
    try:
        if input_path.resolve(strict=False) == output_path.resolve(strict=False):
            return True
    except (OSError, RuntimeError) as exc:
        raise OutputPathError(
            "Unable to safely resolve input and output paths."
        ) from exc

    try:
        return input_path.samefile(output_path)
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise OutputPathError(
            "Unable to safely compare input and output paths."
        ) from exc


def _path_exists(path: Path) -> bool:
    """Include broken symlinks in conservative destination collision checks."""
    return os.path.lexists(path)
