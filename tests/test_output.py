"""Tests for deterministic output selection and transactional commits."""

import os
from pathlib import Path

import pytest

import pdf_signoff.output as output_module
from pdf_signoff.output import (
    OutputExistsError,
    OutputPathError,
    resolve_output_path,
    write_output_atomically,
)


@pytest.mark.parametrize(
    ("input_name", "configured_suffix", "expected_name"),
    [
        ("report.pdf", None, "report_signed.pdf"),
        ("report.pdf", "_approved", "report_approved.pdf"),
        ("report.v2.pdf", None, "report.v2_signed.pdf"),
        ("report.v2.pdf", "-final", "report.v2-final.pdf"),
    ],
)
def test_suffix_output_preserves_the_input_extension_and_multi_dot_base(
    tmp_path: Path,
    input_name: str,
    configured_suffix: str | None,
    expected_name: str,
) -> None:
    input_path = tmp_path / input_name
    input_path.touch()

    assert (
        resolve_output_path(input_path, output_suffix=configured_suffix)
        == tmp_path / expected_name
    )


def test_explicit_output_takes_precedence_over_configured_suffix(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "report.pdf"
    explicit_output = tmp_path / "chosen.pdf"
    input_path.touch()

    assert (
        resolve_output_path(
            input_path,
            explicit_output=explicit_output,
            output_suffix="_ignored",
        )
        == explicit_output
    )


@pytest.mark.parametrize("overwrite", [False, True])
def test_same_lexical_path_is_rejected_even_with_overwrite(
    tmp_path: Path, overwrite: bool
) -> None:
    input_path = tmp_path / "report.pdf"
    input_path.touch()

    with pytest.raises(OutputPathError, match="different files"):
        resolve_output_path(
            input_path,
            explicit_output=input_path,
            overwrite=overwrite,
        )


def test_resolved_path_alias_is_rejected(tmp_path: Path) -> None:
    input_path = tmp_path / "documents" / "report.pdf"
    input_path.parent.mkdir()
    input_path.touch()
    alias_directory = tmp_path / "alias"
    alias_directory.symlink_to(input_path.parent, target_is_directory=True)

    with pytest.raises(OutputPathError, match="different files"):
        resolve_output_path(
            input_path,
            explicit_output=alias_directory / input_path.name,
            overwrite=True,
        )


def test_hard_link_alias_is_rejected(tmp_path: Path) -> None:
    input_path = tmp_path / "report.pdf"
    alias_path = tmp_path / "alias.pdf"
    input_path.write_bytes(b"source")
    os.link(input_path, alias_path)

    with pytest.raises(OutputPathError, match="different files"):
        resolve_output_path(
            input_path,
            explicit_output=alias_path,
            overwrite=True,
        )


def test_unresolvable_symlink_loop_is_rejected_conservatively(tmp_path: Path) -> None:
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    first.symlink_to(second.name)
    second.symlink_to(first.name)

    with pytest.raises(OutputPathError, match="safely compare"):
        resolve_output_path(first, explicit_output=tmp_path / "output.pdf")


def test_path_resolution_error_is_rejected_conservatively(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_path = tmp_path / "input.pdf"
    output_path = tmp_path / "output.pdf"

    def failed_resolve(self: Path, *, strict: bool = False) -> Path:
        raise RuntimeError(self, strict)

    monkeypatch.setattr(Path, "resolve", failed_resolve)

    with pytest.raises(OutputPathError, match="safely resolve"):
        resolve_output_path(input_path, explicit_output=output_path)


def test_same_file_comparison_error_is_rejected_conservatively(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_path = tmp_path / "input.pdf"
    output_path = tmp_path / "output.pdf"
    input_path.touch()

    def inaccessible_samefile(self: Path, other: Path) -> bool:
        raise PermissionError(other)

    monkeypatch.setattr(Path, "samefile", inaccessible_samefile)

    with pytest.raises(OutputPathError, match="safely compare"):
        resolve_output_path(input_path, explicit_output=output_path)


@pytest.mark.parametrize("broken_symlink", [False, True])
def test_existing_destination_is_rejected_without_overwrite(
    tmp_path: Path, broken_symlink: bool
) -> None:
    input_path = tmp_path / "input.pdf"
    output_path = tmp_path / "output.pdf"
    input_path.touch()
    if broken_symlink:
        output_path.symlink_to("missing.pdf")
    else:
        output_path.write_bytes(b"existing")

    with pytest.raises(OutputExistsError, match="--overwrite"):
        resolve_output_path(input_path, explicit_output=output_path)


def test_existing_destination_is_accepted_with_overwrite(tmp_path: Path) -> None:
    input_path = tmp_path / "input.pdf"
    output_path = tmp_path / "output.pdf"
    input_path.touch()
    output_path.write_bytes(b"existing")

    assert (
        resolve_output_path(
            input_path,
            explicit_output=output_path,
            overwrite=True,
        )
        == output_path
    )


def test_successful_write_uses_same_directory_and_returns_writer_result(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "output.pdf"
    observed_temporary_path: Path | None = None

    def writer(temporary_path: Path) -> str:
        nonlocal observed_temporary_path
        observed_temporary_path = temporary_path
        assert temporary_path.parent == output_path.parent
        assert temporary_path != output_path
        temporary_path.write_bytes(b"complete PDF")
        assert not output_path.exists()
        return "profile"

    result = write_output_atomically(output_path, writer)

    assert result == "profile"
    assert output_path.read_bytes() == b"complete PDF"
    assert observed_temporary_path is not None
    assert not observed_temporary_path.exists()


def test_existing_destination_is_rejected_before_writer_runs(tmp_path: Path) -> None:
    output_path = tmp_path / "output.pdf"
    output_path.write_bytes(b"existing")
    writer_called = False

    def writer(_temporary_path: Path) -> None:
        nonlocal writer_called
        writer_called = True

    with pytest.raises(OutputExistsError, match="--overwrite"):
        write_output_atomically(output_path, writer)

    assert writer_called is False
    assert output_path.read_bytes() == b"existing"


def test_overwrite_keeps_old_destination_until_atomic_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_path = tmp_path / "output.pdf"
    output_path.write_bytes(b"old PDF")
    real_replace = os.replace
    replaced_from: Path | None = None

    def observed_replace(source: Path, destination: Path) -> None:
        nonlocal replaced_from
        replaced_from = Path(source)
        assert Path(source).parent == output_path.parent
        assert Path(destination) == output_path
        assert output_path.read_bytes() == b"old PDF"
        real_replace(source, destination)

    monkeypatch.setattr(output_module.os, "replace", observed_replace)

    write_output_atomically(
        output_path,
        lambda temporary_path: temporary_path.write_bytes(b"new PDF"),
        overwrite=True,
    )

    assert output_path.read_bytes() == b"new PDF"
    assert replaced_from is not None
    assert not replaced_from.exists()


def test_destination_created_during_non_overwrite_write_is_not_replaced(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "output.pdf"

    def racing_writer(temporary_path: Path) -> None:
        temporary_path.write_bytes(b"generated PDF")
        output_path.write_bytes(b"concurrent PDF")

    with pytest.raises(OutputExistsError, match="created while writing"):
        write_output_atomically(output_path, racing_writer)

    assert output_path.read_bytes() == b"concurrent PDF"
    assert list(tmp_path.iterdir()) == [output_path]


@pytest.mark.parametrize("failure", [RuntimeError("failed"), KeyboardInterrupt()])
def test_writer_failure_or_interruption_removes_temporary_output(
    tmp_path: Path, failure: BaseException
) -> None:
    input_path = tmp_path / "input.pdf"
    output_path = tmp_path / "output.pdf"
    source_bytes = b"original PDF"
    input_path.write_bytes(source_bytes)

    def failing_writer(temporary_path: Path) -> None:
        temporary_path.write_bytes(b"partial PDF")
        raise failure

    with pytest.raises(type(failure)):
        write_output_atomically(output_path, failing_writer)

    assert input_path.read_bytes() == source_bytes
    assert not output_path.exists()
    assert list(tmp_path.iterdir()) == [input_path]


def test_failed_overwrite_leaves_existing_destination_untouched(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "output.pdf"
    output_path.write_bytes(b"old PDF")

    def failing_writer(temporary_path: Path) -> None:
        temporary_path.write_bytes(b"partial PDF")
        raise RuntimeError("failed")

    with pytest.raises(RuntimeError, match="failed"):
        write_output_atomically(output_path, failing_writer, overwrite=True)

    assert output_path.read_bytes() == b"old PDF"
    assert list(tmp_path.iterdir()) == [output_path]


def test_failed_atomic_replace_removes_temporary_and_preserves_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_path = tmp_path / "output.pdf"
    output_path.write_bytes(b"old PDF")

    def failed_replace(_source: Path, _destination: Path) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(output_module.os, "replace", failed_replace)

    with pytest.raises(OSError, match="replace failed"):
        write_output_atomically(
            output_path,
            lambda temporary_path: temporary_path.write_bytes(b"new PDF"),
            overwrite=True,
        )

    assert output_path.read_bytes() == b"old PDF"
    assert list(tmp_path.iterdir()) == [output_path]
