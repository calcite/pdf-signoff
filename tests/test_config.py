"""Tests for layered Onacol configuration."""

import json
from pathlib import Path

import pytest
from onacol import ConfigValidationError

from pdf_signoff.config import (
    CliConfigArgumentError,
    discover_config_file,
    load_config,
)


def write_yaml(path: Path, values: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(values), encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def isolated_discovery(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))


def test_bundled_defaults_include_ephemeral_port() -> None:
    config = load_config(None, []).config

    assert config["output_suffix"] == "_signed"
    assert config["default_level"] == "l0"
    assert config["default_signature_width"] == 0.16
    assert config["open_browser"] is True
    assert config["host"] == "127.0.0.1"
    assert config["port"] == 0
    assert config["l1"] == {
        "pkcs12_path": "",
        "password_env": "PDF_SIGN_PKCS12_PASSWORD",
        "reason": "Internal document approval",
    }


def test_xdg_config_is_discovered_before_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    xdg_config = write_yaml(
        tmp_path / "xdg" / "pdf-signoff" / "config.yaml",
        {"output_suffix": "_xdg"},
    )
    write_yaml(
        tmp_path / "home" / ".config" / "pdf-signoff" / "config.yaml",
        {"output_suffix": "_home"},
    )

    assert discover_config_file() == xdg_config
    assert load_config(None, []).config["output_suffix"] == "_xdg"


def test_home_config_is_fallback(tmp_path: Path) -> None:
    home_config = write_yaml(
        tmp_path / "home" / ".config" / "pdf-signoff" / "config.yaml",
        {"output_suffix": "_home"},
    )

    assert discover_config_file() == home_config
    assert load_config(None, []).config["output_suffix"] == "_home"


def test_explicit_config_replaces_discovery(tmp_path: Path) -> None:
    write_yaml(
        tmp_path / "xdg" / "pdf-signoff" / "config.yaml",
        {"output_suffix": "_discovered"},
    )
    explicit = write_yaml(tmp_path / "explicit.yaml", {"output_suffix": "_explicit"})

    assert discover_config_file(explicit) == explicit
    assert load_config(explicit, []).config["output_suffix"] == "_explicit"


def test_environment_overrides_user_yaml(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    user_config = write_yaml(tmp_path / "user.yaml", {"default_level": "l1"})
    monkeypatch.setenv("PDF_SIGNOFF__DEFAULT_LEVEL", "l0")

    config = load_config(user_config, []).config

    assert config["default_level"] == "l0"


def test_nested_cli_overrides_environment_and_user_yaml(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    user_config = write_yaml(
        tmp_path / "user.yaml", {"general": {"log_level": "WARNING"}}
    )
    monkeypatch.setenv("PDF_SIGNOFF__GENERAL__LOG_LEVEL", "ERROR")

    config = load_config(user_config, ["--general--log-level", "DEBUG"]).config

    assert config["general"]["log_level"] == "DEBUG"


@pytest.mark.parametrize(
    ("cli_args", "message"),
    [
        (["--autoo", "true"], "Unrecognized option: --autoo"),
        (["unexpected"], "Unrecognized argument: unexpected"),
        (["--port"], "Configuration option --port requires a value"),
    ],
)
def test_cli_arguments_must_be_schema_backed_option_value_pairs(
    cli_args: list[str],
    message: str,
) -> None:
    with pytest.raises(CliConfigArgumentError, match=message):
        load_config(None, cli_args)


@pytest.mark.parametrize("configured_path", ["$CERT_HOME/signing.p12", "~/signing.p12"])
def test_configured_paths_expand_environment_and_home(
    configured_path: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("CERT_HOME", str(tmp_path / "certificates"))
    user_config = write_yaml(
        tmp_path / "user.yaml", {"l1": {"pkcs12_path": configured_path}}
    )

    config = load_config(user_config, []).config

    expected_parent = "certificates" if configured_path.startswith("$") else "home"
    assert config["l1"]["pkcs12_path"] == str(
        tmp_path / expected_parent / "signing.p12"
    )


def test_port_zero_from_user_config_is_valid(tmp_path: Path) -> None:
    user_config = write_yaml(tmp_path / "user.yaml", {"port": 0})

    assert load_config(user_config, []).config["port"] == 0


@pytest.mark.parametrize(
    "values",
    [
        {"default_level": "l2"},
        {"port": -1},
        {"default_signature_width": 2.0},
        {"open_browser": "sometimes"},
    ],
)
def test_invalid_user_configuration_fails_validation(
    values: dict,
    tmp_path: Path,
) -> None:
    user_config = write_yaml(tmp_path / "invalid.yaml", values)

    with pytest.raises(ConfigValidationError, match="Invalid configuration"):
        load_config(user_config, [])
